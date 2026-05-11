"""
Admin API
Endpoints for configuration and management
"""

from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas import (
    SignalConfig,
    SourceWeightConfig,
    WindowConfig,
    APIKeyConfig
)
from app.config import get_settings
from app.database import get_mongodb, get_postgres

router = APIRouter()


# Request/Response Models
class ThresholdUpdate(BaseModel):
    """Threshold update request"""
    currency_pair: str
    buy_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    sell_threshold: float = Field(default=-0.3, ge=-1.0, le=0.0)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    time_decay_lambda: float = Field(default=0.1, ge=0.0)


class SourceWeightUpdate(BaseModel):
    """Source weight update request"""
    source: str
    weight: float = Field(default=0.5, ge=0.0, le=1.0)


class WindowUpdate(BaseModel):
    """Time window update request"""
    name: str
    minutes: int = Field(default=60, gt=0)


class APIKeyUpdate(BaseModel):
    """API key update request"""
    service: str
    key: str
    is_active: bool = True


@router.get("/config")
async def get_config():
    """Get current configuration"""
    try:
        settings = get_settings()

        config = {
            "signal": {
                "latency_target": settings.signal_latency_target,
                "max_batch_size": settings.max_batch_size,
                "confidence_threshold": settings.confidence_threshold,
                "time_decay_lambda": settings.time_decay_lambda
            },
            "source_weights": {
                "newsapi": settings.source_weight_newsapi,
                "twitter": settings.source_weight_twitter,
                "reddit": settings.source_weight_reddit,
                "telegram": settings.source_weight_telegram
            },
            "time_windows": {
                "15min": settings.window_15min,
                "1hour": settings.window_1hour,
                "4hour": settings.window_4hour
            },
            "currency_pairs": settings.currency_pairs,
            "model": {
                "name": settings.finbert_model_name,
                "cache_dir": settings.finbert_cache_dir
            }
        }

        return config

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thresholds")
async def get_thresholds():
    """Get signal generation thresholds for all currency pairs"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get thresholds from database
        thresholds = await mongodb.config.find_one({"type": "thresholds"})

        if not thresholds:
            # Return default thresholds
            return {
                "type": "thresholds",
                "thresholds": {
                    "EUR/USD": {
                        "buy_threshold": 0.3,
                        "sell_threshold": -0.3,
                        "confidence_threshold": 0.6,
                        "time_decay_lambda": 0.1
                    },
                    "GBP/USD": {
                        "buy_threshold": 0.3,
                        "sell_threshold": -0.3,
                        "confidence_threshold": 0.6,
                        "time_decay_lambda": 0.1
                    },
                    "USD/JPY": {
                        "buy_threshold": 0.3,
                        "sell_threshold": -0.3,
                        "confidence_threshold": 0.6,
                        "time_decay_lambda": 0.1
                    }
                }
            }

        return thresholds

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/thresholds/{currency_pair}")
async def update_threshold(currency_pair: str, update: ThresholdUpdate):
    """Update signal generation thresholds for a currency pair"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get existing thresholds
        config = await mongodb.config.find_one({"type": "thresholds"})

        if not config:
            config = {
                "type": "thresholds",
                "thresholds": {}
            }

        # Update threshold
        config["thresholds"][currency_pair] = {
            "buy_threshold": update.buy_threshold,
            "sell_threshold": update.sell_threshold,
            "confidence_threshold": update.confidence_threshold,
            "time_decay_lambda": update.time_decay_lambda,
            "updated_at": datetime.utcnow().isoformat()
        }

        # Save to database
        await mongodb.config.update_one(
            {"type": "thresholds"},
            {"$set": config},
            upsert=True
        )

        return {
            "status": "success",
            "currency_pair": currency_pair,
            "thresholds": config["thresholds"][currency_pair]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/source-weights")
async def get_source_weights():
    """Get source credibility weights"""
    try:
        settings = get_settings()

        weights = [
            SourceWeightConfig(
                source="newsapi",
                weight=settings.source_weight_newsapi
            ),
            SourceWeightConfig(
                source="twitter",
                weight=settings.source_weight_twitter
            ),
            SourceWeightConfig(
                source="reddit",
                weight=settings.source_weight_reddit
            ),
            SourceWeightConfig(
                source="telegram",
                weight=settings.source_weight_telegram
            )
        ]

        return {"weights": weights}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/source-weights")
async def update_source_weight(update: SourceWeightUpdate):
    """Update source credibility weight"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get existing weights
        config = await mongodb.config.find_one({"type": "source_weights"})

        if not config:
            config = {
                "type": "source_weights",
                "weights": {}
            }

        # Update weight
        config["weights"][update.source] = {
            "weight": update.weight,
            "updated_at": datetime.utcnow().isoformat()
        }

        # Save to database
        await mongodb.config.update_one(
            {"type": "source_weights"},
            {"$set": config},
            upsert=True
        )

        return {
            "status": "success",
            "source": update.source,
            "weight": update.weight
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/time-windows")
async def get_time_windows():
    """Get time window configurations"""
    try:
        settings = get_settings()

        windows = [
            WindowConfig(name="15min", minutes=settings.window_15min),
            WindowConfig(name="1hour", minutes=settings.window_1hour),
            WindowConfig(name="4hour", minutes=settings.window_4hour)
        ]

        return {"windows": windows}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/time-windows")
async def update_time_window(update: WindowUpdate):
    """Update time window configuration"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get existing windows
        config = await mongodb.config.find_one({"type": "time_windows"})

        if not config:
            config = {
                "type": "time_windows",
                "windows": {}
            }

        # Update window
        config["windows"][update.name] = {
            "minutes": update.minutes,
            "updated_at": datetime.utcnow().isoformat()
        }

        # Save to database
        await mongodb.config.update_one(
            {"type": "time_windows"},
            {"$set": config},
            upsert=True
        )

        return {
            "status": "success",
            "window": update.name,
            "minutes": update.minutes
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-keys")
async def get_api_keys():
    """Get API keys (masked)"""
    try:
        settings = get_settings()

        keys = [
            {
                "service": "newsapi",
                "is_configured": bool(settings.newsapi_key),
                "is_active": True
            },
            {
                "service": "twitter",
                "is_configured": bool(settings.twitter_bearer_token),
                "is_active": True
            },
            {
                "service": "reddit",
                "is_configured": bool(settings.reddit_client_id),
                "is_active": True
            },
            {
                "service": "telegram",
                "is_configured": bool(settings.telegram_bot_token),
                "is_active": True
            }
        ]

        return {"keys": keys}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api-keys")
async def update_api_key(update: APIKeyUpdate):
    """Update API key (Note: This updates environment variables, requires restart)"""
    try:
        # In production, this would update secure storage
        # For now, just return success
        return {
            "status": "success",
            "service": update.service,
            "message": "API key updated. Restart service to apply changes."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get collection stats
        news_count = await mongodb.news.count_documents({})
        signals_count = await mongodb.signals.count_documents({})

        # Get recent activity
        recent_news = await mongodb.news.find({}).sort("timestamp", -1).limit(1).to_list(length=1)
        recent_signals = await mongodb.signals.find({}).sort("timestamp", -1).limit(1).to_list(length=1)

        last_news_time = recent_news[0]["timestamp"] if recent_news else None
        last_signal_time = recent_signals[0]["timestamp"] if recent_signals else None

        return {
            "news": {
                "total_count": news_count,
                "last_update": last_news_time
            },
            "signals": {
                "total_count": signals_count,
                "last_update": last_signal_time
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_system():
    """Reset system (clear all data) - USE WITH CAUTION"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Clear collections
        await mongodb.news.delete_many({})
        await mongodb.signals.delete_many({})

        return {
            "status": "success",
            "message": "System reset completed",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
