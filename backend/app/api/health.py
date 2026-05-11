"""
Health Check API
Provides health check endpoints for monitoring
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
import asyncio

from app.database import get_mongodb, get_redis, get_postgres, get_influxdb

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "pippulse-backend"
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with database status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "pippulse-backend",
        "components": {}
    }

    # Check MongoDB
    try:
        mongodb = get_mongodb()
        if mongodb:
            await mongodb.command("ping")
            health_status["components"]["mongodb"] = {
                "status": "healthy",
                "message": "MongoDB is responsive"
            }
        else:
            health_status["components"]["mongodb"] = {
                "status": "unhealthy",
                "message": "MongoDB connection not established"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["mongodb"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["status"] = "degraded"

    # Check Redis
    try:
        redis = get_redis()
        if redis:
            await redis.ping()
            health_status["components"]["redis"] = {
                "status": "healthy",
                "message": "Redis is responsive"
            }
        else:
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "message": "Redis connection not established"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["status"] = "degraded"

    # Check PostgreSQL
    try:
        postgres = get_postgres()
        if postgres:
            # Simple query to test connection
            await postgres.fetchval("SELECT 1")
            health_status["components"]["postgres"] = {
                "status": "healthy",
                "message": "PostgreSQL is responsive"
            }
        else:
            health_status["components"]["postgres"] = {
                "status": "unhealthy",
                "message": "PostgreSQL connection not established"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["postgres"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["status"] = "degraded"

    # Check InfluxDB
    try:
        influxdb = get_influxdb()
        if influxdb:
            health_status["components"]["influxdb"] = {
                "status": "healthy",
                "message": "InfluxDB connection established"
            }
        else:
            health_status["components"]["influxdb"] = {
                "status": "unhealthy",
                "message": "InfluxDB connection not established"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["influxdb"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["status"] = "degraded"

    return health_status


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check - is the service ready to accept traffic?"""
    # Check if all critical components are ready
    try:
        redis = get_redis()
        if redis:
            await redis.ping()
        else:
            raise HTTPException(status_code=503, detail="Redis not ready")

        mongodb = get_mongodb()
        if mongodb:
            await mongodb.command("ping")
        else:
            raise HTTPException(status_code=503, detail="MongoDB not ready")

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check - is the service alive?"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
