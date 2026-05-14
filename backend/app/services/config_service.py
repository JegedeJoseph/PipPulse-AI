"""
Configuration service for storing and retrieving system settings in PostgreSQL.
"""

from typing import Dict, Any, Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

from app.config import get_settings
from app.database import get_postgres_session
from app.models.tables import system_config


DEFAULT_CONFIG_KEYS = {
    "signal_thresholds": "Signal generation thresholds per currency pair",
    "source_weights": "Source credibility weights",
    "time_windows": "Time window configurations in minutes",
    "signal_params": "Signal generation parameters",
}


def _default_thresholds(settings) -> Dict[str, Any]:
    return {
        pair: {
            "buy_threshold": 0.3,
            "sell_threshold": -0.3,
            "confidence_threshold": settings.confidence_threshold,
            "time_decay_lambda": settings.time_decay_lambda,
        }
        for pair in settings.currency_pairs
    }


def _default_source_weights(settings) -> Dict[str, float]:
    return {
        "newsapi": settings.source_weight_newsapi,
        "twitter": settings.source_weight_twitter,
        "reddit": settings.source_weight_reddit,
        "telegram": settings.source_weight_telegram,
    }


def _default_time_windows(settings) -> Dict[str, int]:
    return {
        "15min": settings.window_15min,
        "1hour": settings.window_1hour,
        "4hour": settings.window_4hour,
    }


def _default_signal_params(settings) -> Dict[str, Any]:
    return {
        "latency_target": settings.signal_latency_target,
        "max_batch_size": settings.max_batch_size,
        "confidence_threshold": settings.confidence_threshold,
        "time_decay_lambda": settings.time_decay_lambda,
    }


async def _upsert_config(config_key: str, config_value: Dict[str, Any], description: Optional[str] = None) -> None:
    session = get_postgres_session()
    if session is None:
        raise RuntimeError("PostgreSQL session not available")

    async with session() as db:
        stmt = insert(system_config).values(
            config_key=config_key,
            config_value=config_value,
            description=description or DEFAULT_CONFIG_KEYS.get(config_key),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[system_config.c.config_key],
            set_={
                "config_value": config_value,
                "description": description or DEFAULT_CONFIG_KEYS.get(config_key),
                "updated_at": func.now(),
            },
        )
        await db.execute(stmt)
        await db.commit()


async def get_system_config() -> Dict[str, Any]:
    settings = get_settings()
    session = get_postgres_session()
    if session is None:
        raise RuntimeError("PostgreSQL session not available")

    async with session() as db:
        result = await db.execute(select(system_config.c.config_key, system_config.c.config_value))
        rows = result.fetchall()

    config_map = {row.config_key: row.config_value for row in rows}

    thresholds = _default_thresholds(settings)
    thresholds.update(config_map.get("signal_thresholds", {}))

    source_weights = _default_source_weights(settings)
    source_weights.update(config_map.get("source_weights", {}))

    time_windows = _default_time_windows(settings)
    time_windows.update(config_map.get("time_windows", {}))

    signal_params = _default_signal_params(settings)
    signal_params.update(config_map.get("signal_params", {}))

    return {
        "signal": {
            **signal_params,
            "thresholds": thresholds,
        },
        "source_weights": source_weights,
        "time_windows": time_windows,
        "currency_pairs": settings.currency_pairs,
        "model": {
            "name": settings.finbert_model_name,
            "cache_dir": settings.finbert_cache_dir,
        },
    }


async def update_signal_params(params: Dict[str, Any]) -> None:
    await _upsert_config("signal_params", params)


async def update_thresholds(thresholds: Dict[str, Any]) -> None:
    await _upsert_config("signal_thresholds", thresholds)


async def update_source_weights(weights: Dict[str, Any]) -> None:
    await _upsert_config("source_weights", weights)


async def update_time_windows(windows: Dict[str, Any]) -> None:
    await _upsert_config("time_windows", windows)
