from motor.motor_asyncio import AsyncIOMotorClient as AsyncMongoClient, AsyncIOMotorDatabase as AsyncMongoDB
from burner_redis import BurnerRedis
from tinyflux import TinyFlux, Point
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os
from typing import Optional

# MongoDB
mongodb_client: Optional[AsyncMongoClient] = None
mongodb: Optional[AsyncMongoDB] = None

# Redis (BurnerRedis - embedded Redis replacement)
redis_client: Optional[BurnerRedis] = None

# InfluxDB (TinyFlux - embedded time-series database replacement)
influxdb_client: Optional[TinyFlux] = None
influxdb_price_client: Optional[TinyFlux] = None

# PostgreSQL
postgres_engine = None
postgres_session_local: Optional[async_sessionmaker] = None
Base = declarative_base()

async def init_databases():
    global mongodb_client, mongodb, redis_client, influxdb_client, influxdb_price_client, postgres_engine, postgres_session_local
    
    # Initialize MongoDB
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    mongodb_client = AsyncMongoClient(mongodb_uri)
    mongodb = mongodb_client.get_database(os.getenv('MONGODB_DB', 'pippulse'))
    
    # Initialize Redis (BurnerRedis - embedded)
    redis_persistence_path = os.getenv('REDIS_PERSISTENCE_PATH', 'redis_data.dat')
    redis_client = BurnerRedis(persistence_path=redis_persistence_path)
    
    # Initialize InfluxDB (TinyFlux - embedded time-series)
    signals_db_path = os.getenv('TINYFLUX_SIGNALS_PATH', 'tinyflux_signals.csv')
    prices_db_path = os.getenv('TINYFLUX_PRICES_PATH', 'tinyflux_prices.csv')
    
    influxdb_client = TinyFlux(signals_db_path)
    influxdb_price_client = TinyFlux(prices_db_path)
    
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
    global mongodb_client, redis_client, influxdb_client, influxdb_price_client, postgres_engine
    
    if mongodb_client:
        mongodb_client.close()
    if redis_client:
        # BurnerRedis doesn't have async close, it's embedded
        pass
    if influxdb_client:
        # TinyFlux doesn't need explicit close for file-based storage
        pass
    if influxdb_price_client:
        # TinyFlux doesn't need explicit close for file-based storage
        pass
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

# TinyFlux helper functions to mimic InfluxDB API
def get_influxdb_write_api():
    """Get TinyFlux client for writing signals"""
    global influxdb_client
    if influxdb_client is None:
        # Sync initialization for TinyFlux
        signals_db_path = os.getenv('TINYFLUX_SIGNALS_PATH', 'tinyflux_signals.csv')
        influxdb_client = TinyFlux(signals_db_path)
    return influxdb_client

def get_influxdb_query_api():
    """Get TinyFlux client for querying signals"""
    global influxdb_client
    if influxdb_client is None:
        signals_db_path = os.getenv('TINYFLUX_SIGNALS_PATH', 'tinyflux_signals.csv')
        influxdb_client = TinyFlux(signals_db_path)
    return influxdb_client

def get_influxdb_price_client():
    """Get TinyFlux client for price data"""
    global influxdb_price_client
    if influxdb_price_client is None:
        prices_db_path = os.getenv('TINYFLUX_PRICES_PATH', 'tinyflux_prices.csv')
        influxdb_price_client = TinyFlux(prices_db_path)
    return influxdb_price_client

# Compatibility function for health checks
async def get_influxdb_client():
    """Get InfluxDB client for health checks (returns TinyFlux instance)"""
    return get_influxdb_query_api()
