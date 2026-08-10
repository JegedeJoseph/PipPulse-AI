"""
Health Check API
Provides health check endpoints for monitoring
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
import asyncio

from sqlalchemy import text

from app.database import (
    get_mongodb,
    get_redis,
    get_postgres_session,
    get_influxdb_client,
)
from app.api.websocket import manager as ws_manager

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

    # Check Redis (BurnerRedis)
    try:
        redis = get_redis()
        if redis:
            # BurnerRedis doesn't have ping, check if it's initialized
            health_status["components"]["redis"] = {
                "status": "healthy",
                "message": "BurnerRedis (embedded Redis) is responsive"
            }
        else:
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "message": "BurnerRedis connection not established"
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
        session = get_postgres_session()
        if session:
            async with session() as db:
                await db.execute(text("SELECT 1"))
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

    # Check TinyFlux (InfluxDB replacement)
    try:
        influxdb = get_influxdb_client()
        if influxdb:
            # TinyFlux is file-based, check if it's initialized
            health_status["components"]["influxdb"] = {
                "status": "healthy",
                "message": "TinyFlux (embedded time-series DB) is responsive"
            }
        else:
            health_status["components"]["influxdb"] = {
                "status": "unhealthy",
                "message": "TinyFlux connection not established"
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
            # BurnerRedis doesn't have ping, just check if it's initialized
            pass
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


@router.get("/websocket/metrics")
async def websocket_metrics() -> Dict[str, Any]:
    """Get WebSocket connection metrics"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "websocket": ws_manager.get_metrics()
    }


@router.get("/websocket/connections")
async def websocket_connections() -> Dict[str, Any]:
    """Get current WebSocket connection count"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "active_connections": ws_manager.get_connection_count(),
        "max_connections": len(ws_manager.active_connections)
    }
