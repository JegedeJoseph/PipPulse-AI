"""
Database Connection Module
Handles connections to MongoDB, Redis, PostgreSQL, and InfluxDB
"""

from typing import Optional
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import get_settings

settings = get_settings()

# MongoDB Connection
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_database = None


async def connect_mongodb():
    """Connect to MongoDB"""
    global mongodb_client, mongodb_database

    mongodb_client = AsyncIOMotorClient(settings.mongodb_uri)
    mongodb_database = mongodb_client[settings.mongodb_database]

    # Create indexes
    await create_mongodb_indexes()

    print(f"Connected to MongoDB: {settings.mongodb_database}")


async def disconnect_mongodb():
    """Disconnect from MongoDB"""
    global mongodb_client

    if mongodb_client:
        mongodb_client.close()
        print("Disconnected from MongoDB")


async def create_mongodb_indexes():
    """Create MongoDB indexes for better query performance"""
    if mongodb_database is None:
        return

    # Raw news collection indexes
    await mongodb_database.raw_news.create_index([("source", 1)])
    await mongodb_database.raw_news.create_index([("timestamp", -1)])
    await mongodb_database.raw_news.create_index([("currency_pairs", 1)])
    await mongodb_database.raw_news.create_index([("content_hash", 1)], unique=True)

    # Processed news collection indexes
    await mongodb_database.news.create_index([("timestamp", -1)])
    await mongodb_database.news.create_index([("currency_pairs", 1)])
    await mongodb_database.news.create_index([("sentiment.label", 1)])
    await mongodb_database.news.create_index([("content_hash", 1)], unique=True)

    # Signals collection indexes
    await mongodb_database.signals.create_index([("timestamp", -1)])
    await mongodb_database.signals.create_index([("currency_pair", 1)])
    await mongodb_database.signals.create_index([("time_window", 1)])


# Redis Connection
redis_client: Optional[aioredis.Redis] = None


async def connect_redis():
    """Connect to Redis"""
    global redis_client

    redis_client = await aioredis.from_url(
        settings.redis_uri,
        encoding="utf-8",
        decode_responses=True
    )

    print(f"Connected to Redis: {settings.redis_uri}")


async def disconnect_redis():
    """Disconnect from Redis"""
    global redis_client

    if redis_client:
        await redis_client.close()
        print("Disconnected from Redis")


# PostgreSQL Connection
Base = declarative_base()
from app.models import tables  # noqa: F401
async_engine = None
async_session_maker = None


async def connect_postgres():
    """Connect to PostgreSQL"""
    global async_engine, async_session_maker

    async_engine = create_async_engine(
        settings.postgres_uri,
        echo=settings.debug,
        pool_pre_ping=True
    )

    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print(f"Connected to PostgreSQL: {settings.postgres_db}")


async def disconnect_postgres():
    """Disconnect from PostgreSQL"""
    global async_engine

    if async_engine:
        await async_engine.dispose()
        print("Disconnected from PostgreSQL")


# InfluxDB Connection
influxdb_client: Optional[InfluxDBClient] = None
influxdb_write_api = None


async def connect_influxdb():
    """Connect to InfluxDB"""
    global influxdb_client, influxdb_write_api

    influxdb_client = InfluxDBClient(
        url=settings.influxdb_url,
        token=settings.influxdb_token,
        org=settings.influxdb_org
    )

    influxdb_write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

    # Create bucket if it doesn't exist
    buckets_api = influxdb_client.buckets_api()
    buckets = buckets_api.find_buckets()

    bucket_exists = any(
        bucket.name == settings.influxdb_bucket
        for bucket in buckets.buckets
    )

    if not bucket_exists:
        buckets_api.create_bucket(
            bucket_name=settings.influxdb_bucket,
            org=settings.influxdb_org
        )
        print(f"Created InfluxDB bucket: {settings.influxdb_bucket}")

    print(f"Connected to InfluxDB: {settings.influxdb_bucket}")


async def disconnect_influxdb():
    """Disconnect from InfluxDB"""
    global influxdb_client, influxdb_write_api

    if influxdb_write_api:
        influxdb_write_api.close()

    if influxdb_client:
        influxdb_client.close()
        print("Disconnected from InfluxDB")


# Connect all databases
async def connect_all_databases():
    """Connect to all databases"""
    await asyncio.gather(
        connect_mongodb(),
        connect_redis(),
        connect_postgres(),
        connect_influxdb()
    )


# Disconnect all databases
async def disconnect_all_databases():
    """Disconnect from all databases"""
    await asyncio.gather(
        disconnect_mongodb(),
        disconnect_redis(),
        disconnect_postgres(),
        disconnect_influxdb()
    )


# Get database instances
def get_mongodb():
    """Get MongoDB database instance"""
    return mongodb_database


def get_redis():
    """Get Redis client instance"""
    return redis_client


def get_postgres_session():
    """Get PostgreSQL session"""
    return async_session_maker()


def get_postgres_engine():
    """Get PostgreSQL async engine"""
    return async_engine


def get_influxdb_write_api():
    """Get InfluxDB write API"""
    return influxdb_write_api


def get_influxdb_query_api():
    """Get InfluxDB query API"""
    if influxdb_client:
        return influxdb_client.query_api()
    return None


def get_influxdb_client():
    """Get InfluxDB client"""
    return influxdb_client
