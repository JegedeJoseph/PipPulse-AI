"""
Database connection module.
Handles MongoDB (with OIDC Service Account support), Redis, InfluxDB, and PostgreSQL.
All connections fail gracefully so the app can still start if a service is unavailable.
"""

from motor.motor_asyncio import (
    AsyncIOMotorClient as AsyncMongoClient,
    AsyncIOMotorDatabase as AsyncMongoDB,
)
import redis.asyncio as aioredis
from influxdb_client import InfluxDBClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os
import logging
import ssl as _ssl
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

try:
    import certifi
    CERTIFI_CA = certifi.where()
except ImportError:
    CERTIFI_CA = None

logger = logging.getLogger(__name__)

# MongoDB
mongodb_client: Optional[AsyncMongoClient] = None
mongodb: Optional[AsyncMongoDB] = None

# Redis
redis_client: Optional[aioredis.Redis] = None

# InfluxDB
influxdb_client: Optional[InfluxDBClient] = None

# PostgreSQL
postgres_engine = None
postgres_session_local: Optional[async_sessionmaker] = None
Base = declarative_base()


def _build_mongo_client(uri: str) -> AsyncMongoClient:
    """
    Build a Motor AsyncMongoClient from the given URI.

    Applies sensible defaults:
    - Short timeouts so the app doesn't hang if MongoDB is unreachable.
    - Uses certifi CA bundle for TLS (required in slim Docker images).
    """
    kwargs = {
        "serverSelectionTimeoutMS": 5000,
        "connectTimeoutMS": 5000,
    }
    if CERTIFI_CA:
        kwargs["tlsCAFile"] = CERTIFI_CA
    return AsyncMongoClient(uri, **kwargs)


def _fix_postgres_uri(uri: str) -> Tuple[str, bool]:
    """
    Ensure the PostgreSQL URI uses the asyncpg dialect and handle sslmode.

    asyncpg does not accept 'sslmode' as a query parameter — it uses the
    'ssl' connect_arg instead. This function strips sslmode from the URI
    and returns a boolean indicating whether SSL should be enabled.
    """
    use_ssl = False

    # Switch to asyncpg dialect
    if uri.startswith("postgresql://") and "+asyncpg" not in uri:
        uri = uri.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Strip sslmode from query params (asyncpg doesn't understand it)
    parsed = urlparse(uri)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if "sslmode" in qs:
        sslmode = qs.pop("sslmode", ["disable"])[0]
        if sslmode in ("require", "verify-ca", "verify-full", "prefer"):
            use_ssl = True
        uri = urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))

    return uri, use_ssl


async def init_databases():
    global mongodb_client, mongodb, redis_client, influxdb_client
    global postgres_engine, postgres_session_local

    # ---- MongoDB ----
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    try:
        import asyncio
        mongodb_client = _build_mongo_client(mongodb_uri)
        db_name = os.getenv("MONGODB_DB", "pippulse")
        mongodb = mongodb_client.get_database(db_name)
        # Quick connectivity check with a tight timeout
        await asyncio.wait_for(mongodb.command("ping"), timeout=10)
        logger.info("MongoDB connected successfully")
    except Exception as exc:
        logger.warning(f"MongoDB connection failed — running without MongoDB: {exc}")
        mongodb_client = None
        mongodb = None

    # ---- Redis ----
    redis_uri = os.getenv("REDIS_URI", "redis://localhost:6379/0")
    try:
        redis_client = await aioredis.from_url(redis_uri, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as exc:
        logger.warning(f"Redis connection failed — running without Redis: {exc}")
        redis_client = None

    # ---- InfluxDB ----
    influxdb_url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    influxdb_token = os.getenv("INFLUXDB_TOKEN", "")
    influxdb_org = os.getenv("INFLUXDB_ORG", "pippulse")
    if influxdb_token:
        try:
            influxdb_client = InfluxDBClient(
                url=influxdb_url, token=influxdb_token, org=influxdb_org
            )
            logger.info("InfluxDB client initialised")
        except Exception as exc:
            logger.warning(f"InfluxDB init failed — running without InfluxDB: {exc}")
            influxdb_client = None

    # ---- PostgreSQL ----
    postgres_uri = os.getenv(
        "POSTGRES_URI",
        "postgresql+asyncpg://postgres:password@localhost:5432/pippulse",
    )
    postgres_uri, pg_use_ssl = _fix_postgres_uri(postgres_uri)
    try:
        connect_args = {}
        if pg_use_ssl:
            # Create a permissive SSL context (Neon requires SSL but uses
            # its own CA; "require" mode does not verify the server cert).
            ssl_ctx = _ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = _ssl.CERT_NONE
            connect_args["ssl"] = ssl_ctx

        postgres_engine = create_async_engine(
            postgres_uri, echo=False, connect_args=connect_args
        )
        postgres_session_local = async_sessionmaker(
            postgres_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with postgres_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL connected successfully")
    except Exception as exc:
        logger.warning(f"PostgreSQL connection failed — running without Postgres: {exc}")
        postgres_engine = None
        postgres_session_local = None

    return mongodb, redis_client, influxdb_client


async def close_databases():
    global mongodb_client, redis_client, influxdb_client, postgres_engine

    if mongodb_client:
        mongodb_client.close()
    if redis_client:
        await redis_client.close()
    if influxdb_client:
        influxdb_client.close()
    if postgres_engine:
        await postgres_engine.dispose()


# ---- Dependency helpers ----

async def get_mongodb():
    global mongodb
    if mongodb is None:
        await init_databases()
    return mongodb


async def get_redis():
    global redis_client
    if redis_client is None:
        await init_databases()
    return redis_client


async def get_influxdb():
    global influxdb_client
    if influxdb_client is None:
        await init_databases()
    return influxdb_client


async def get_postgres_session():
    global postgres_session_local
    if postgres_session_local is None:
        await init_databases()
    async with postgres_session_local() as session:
        yield session


def get_influxdb_client():
    global influxdb_client
    return influxdb_client


def get_influxdb_query_api():
    global influxdb_client
    if influxdb_client:
        return influxdb_client.query_api()
    return None


def get_influxdb_write_api():
    global influxdb_client
    if influxdb_client:
        from influxdb_client.client.write_api import SYNCHRONOUS
        return influxdb_client.write_api(write_options=SYNCHRONOUS)
    return None
