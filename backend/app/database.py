from motor.motor_asyncio import AsyncIOMotorClient as AsyncMongoClient, AsyncIOMotorDatabase as AsyncMongoDB
import redis.asyncio as aioredis
from influxdb_client import InfluxDBClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os
from typing import Optional

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

async def init_databases():
    global mongodb_client, mongodb, redis_client, influxdb_client, postgres_engine, postgres_session_local
    
    # Initialize MongoDB
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    mongodb_client = AsyncMongoClient(mongodb_uri)
    mongodb = mongodb_client.get_database(os.getenv('MONGODB_DB', 'pippulse'))
    
    # Initialize Redis
    redis_uri = os.getenv('REDIS_URI', 'redis://localhost:6379/0')
    redis_client = await aioredis.from_url(redis_uri, decode_responses=True)
    
    # Initialize InfluxDB
    influxdb_url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
    influxdb_token = os.getenv('INFLUXDB_TOKEN', '')
    influxdb_org = os.getenv('INFLUXDB_ORG', 'pippulse')
    if influxdb_token:
        influxdb_client = InfluxDBClient(
            url=influxdb_url,
            token=influxdb_token,
            org=influxdb_org
        )
    
    # Initialize PostgreSQL
    postgres_uri = os.getenv('POSTGRES_URI', 'postgresql+asyncpg://postgres:password@localhost:5432/pippulse')
    postgres_engine = create_async_engine(postgres_uri, echo=True)
    postgres_session_local = async_sessionmaker(
        postgres_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create tables
    async with postgres_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
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
