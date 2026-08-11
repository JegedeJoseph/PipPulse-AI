"""
Signals API
Endpoints for trading signals
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta

from app.schemas import (
    TradingSignal,
    SignalResponse,
    SignalDirection,
    CurrencyPair
)
from app.signal import SignalGenerator, SignalAggregator
from app.database import get_mongodb, get_influxdb

router = APIRouter()


@router.get("", response_model=List[SignalResponse])
async def get_signals(
    currency_pair: Optional[str] = Query(None, description="Filter by currency pair"),
    direction: Optional[SignalDirection] = Query(None, description="Filter by direction"),
    time_window: Optional[str] = Query("1hour", description="Time window (15min, 1hour, 4hour)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of signals to return")
):
    """Get recent trading signals"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Build query
        query = {}

        if currency_pair:
            query["currency_pair"] = currency_pair

        if direction:
            query["direction"] = direction.value

        if time_window:
            query["time_window"] = time_window

        # Get signals from database
        signals = await mongodb.signals.find(query).sort("timestamp", -1).limit(limit).to_list(length=limit)

        # Convert to response format
        responses = []
        for signal in signals:
            responses.append(SignalResponse(
                currency_pair=signal["currency_pair"],
                direction=SignalDirection(signal["direction"]),
                strength=signal["strength"],
                confidence=signal["confidence"],
                timestamp=signal["timestamp"],
                time_window=signal["time_window"],
                reasoning=signal.get("reasoning", ""),
                supporting_headlines=signal.get("supporting_headlines", []),
                sentiment_score=signal.get("sentiment_score", 0.0),
                volume=signal.get("volume", 0),
                consensus_factor=signal.get("consensus_factor", 0.0)
            ))

        return responses

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest", response_model=List[SignalResponse])
async def get_latest_signals(
    currency_pairs: Optional[List[str]] = Query(None, description="List of currency pairs"),
    time_window: str = Query("1hour", description="Time window")
):
    """Get the latest signals for specified currency pairs"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Default currency pairs
        if not currency_pairs:
            currency_pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD"]

        # Get latest signal for each pair
        signals = []

        for pair in currency_pairs:
            signal = await mongodb.signals.find_one(
                {"currency_pair": pair, "time_window": time_window},
                sort=[("timestamp", -1)]
            )

            if signal:
                signals.append(SignalResponse(
                    currency_pair=signal["currency_pair"],
                    direction=SignalDirection(signal["direction"]),
                    strength=signal["strength"],
                    confidence=signal["confidence"],
                    timestamp=signal["timestamp"],
                    time_window=signal["time_window"],
                    reasoning=signal.get("reasoning", ""),
                    supporting_headlines=signal.get("supporting_headlines", []),
                    sentiment_score=signal.get("sentiment_score", 0.0),
                    volume=signal.get("volume", 0),
                    consensus_factor=signal.get("consensus_factor", 0.0)
                ))

        return signals

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aggregate/{currency_pair}")
async def get_aggregated_signals(
    currency_pair: str,
    time_window: str = Query("1hour", description="Base time window")
):
    """Get aggregated signals across all time windows for a currency pair"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get signals for all time windows
        windows = ["15min", "1hour", "4hour"]
        signals = {}

        for window in windows:
            signal = await mongodb.signals.find_one(
                {"currency_pair": currency_pair, "time_window": window},
                sort=[("timestamp", -1)]
            )

            if signal:
                signals[window] = {
                    "direction": signal["direction"],
                    "strength": signal["strength"],
                    "confidence": signal["confidence"],
                    "timestamp": signal["timestamp"],
                    "sentiment_score": signal.get("sentiment_score", 0),
                    "volume": signal.get("volume", 0),
                    "consensus_factor": signal.get("consensus_factor", 0)
                }

        # Calculate consensus
        if signals:
            direction_counts = {}
            for window, signal in signals.items():
                direction = signal["direction"]
                direction_counts[direction] = direction_counts.get(direction, 0) + 1

            consensus_direction = max(direction_counts, key=direction_counts.get)

            return {
                "currency_pair": currency_pair,
                "consensus_direction": consensus_direction,
                "signals": signals,
                "timestamp": datetime.utcnow().isoformat()
            }

        return {
            "currency_pair": currency_pair,
            "consensus_direction": "hold",
            "signals": {},
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{currency_pair}")
async def get_signal_history(
    currency_pair: str,
    hours: int = Query(24, ge=1, le=168, description="Number of hours of history"),
    time_window: str = Query("1hour", description="Time window")
):
    """Get historical signals for a currency pair"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Calculate start time
        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Get signals
        signals = await mongodb.signals.find({
            "currency_pair": currency_pair,
            "time_window": time_window,
            "timestamp": {"$gte": start_time}
        }).sort("timestamp", 1).to_list(length=None)

        # Format response
        history = []
        for signal in signals:
            history.append({
                "timestamp": signal["timestamp"],
                "direction": signal["direction"],
                "strength": signal["strength"],
                "confidence": signal["confidence"],
                "sentiment_score": signal.get("sentiment_score", 0)
            })

        return {
            "currency_pair": currency_pair,
            "time_window": time_window,
            "start_time": start_time.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "count": len(history),
            "history": history
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pairs")
async def get_available_pairs():
    """Get list of available currency pairs"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get distinct currency pairs
        pairs = await mongodb.signals.distinct("currency_pair")

        # Sort pairs
        pairs.sort()

        return {
            "pairs": pairs,
            "count": len(pairs)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
