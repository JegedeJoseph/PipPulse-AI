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
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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

    If the URI contains authMechanism=MONGODB-OIDC with CLIENT_ID / CLIENT_SECRET
    in authMechanismProperties, strip those out and use a custom OIDCCallback so
    PyMongo can perform the OAuth 2.0 Client-Credentials token exchange at runtime.
    """
    parsed = urlparse(uri)
    qs = parse_qs(parsed.query, keep_blank_values=True)

    auth_mechanism = qs.get("authMechanism", [None])[0]

    if auth_mechanism and auth_mechanism.upper() == "MONGODB-OIDC":
        # Extract authMechanismProperties
        props_raw = qs.get("authMechanismProperties", [""])[0]
        props = dict(item.split(":", 1) for item in props_raw.split(",") if ":" in item)

        client_id = props.pop("CLIENT_ID", None)
        client_secret = props.pop("CLIENT_SECRET", None)

        if client_id and client_secret:
            # Rebuild the URI *without* CLIENT_ID / CLIENT_SECRET in the query
            remaining_props = ",".join(f"{k}:{v}" for k, v in props.items())
            new_qs = {k: v for k, v in qs.items() if k != "authMechanismProperties"}
            if remaining_props:
                new_qs["authMechanismProperties"] = [remaining_props]
            # Remove authMechanism from query — we'll pass it programmatically
            new_qs.pop("authMechanism", None)

            clean_query = urlencode(new_qs, doseq=True)
            clean_uri = urlunparse(parsed._replace(query=clean_query))

            # Import OIDC callback helpers
            try:
                from pymongo.auth_oidc import OIDCCallback, OIDCCallbackContext, OIDCCallbackResult
            except ImportError:
                logger.warning(
                    "pymongo.auth_oidc not available — falling back to URI-based auth. "
                    "Upgrade pymongo to >=4.8 for OIDC support."
                )
                return AsyncMongoClient(uri)

            import requests as _requests

            class AtlasServiceAccountCallback(OIDCCallback):
                """Fetch an access token from MongoDB Atlas using Client Credentials."""

                _TOKEN_URL = "https://cloud.mongodb.com/api/oauth/token"

                def fetch(self, context: OIDCCallbackContext) -> OIDCCallbackResult:
                    resp = _requests.post(
                        self._TOKEN_URL,
                        data={"grant_type": "client_credentials"},
                        auth=(client_id, client_secret),
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=30,
                    )
                    resp.raise_for_status()
                    token = resp.json()["access_token"]
                    return OIDCCallbackResult(access_token=token)

            logger.info("Using OIDC Service Account callback for MongoDB authentication")
            return AsyncMongoClient(
                clean_uri,
                authMechanism="MONGODB-OIDC",
                authMechanismProperties={"OIDC_CALLBACK": AtlasServiceAccountCallback()},
            )

    # Default — no special OIDC handling needed
    return AsyncMongoClient(uri)


def _fix_postgres_uri(uri: str) -> str:
    """
    Ensure the PostgreSQL URI uses the asyncpg dialect.
    Converts 'postgresql://' to 'postgresql+asyncpg://'.
    """
    if uri.startswith("postgresql://") and "+asyncpg" not in uri:
        uri = uri.replace("postgresql://", "postgresql+asyncpg://", 1)
    return uri


async def init_databases():
    global mongodb_client, mongodb, redis_client, influxdb_client
    global postgres_engine, postgres_session_local

    # ---- MongoDB ----
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    try:
        mongodb_client = _build_mongo_client(mongodb_uri)
        db_name = os.getenv("MONGODB_DB", "pippulse")
        mongodb = mongodb_client.get_database(db_name)
        # Quick connectivity check
        await mongodb.command("ping")
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
    postgres_uri = _fix_postgres_uri(postgres_uri)
    try:
        postgres_engine = create_async_engine(postgres_uri, echo=False)
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
