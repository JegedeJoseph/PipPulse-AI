"""
News API
Endpoints for news items and sentiment
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta

from app.schemas import (
    NewsItemResponse,
    SourceType,
    SentimentLabel,
    SentimentTrend
)
from app.database import get_mongodb

router = APIRouter()


@router.get("/", response_model=List[NewsItemResponse])
async def get_news(
    source: Optional[SourceType] = Query(None, description="Filter by source"),
    currency_pair: Optional[str] = Query(None, description="Filter by currency pair"),
    sentiment: Optional[SentimentLabel] = Query(None, description="Filter by sentiment"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items"),
    hours: int = Query(24, ge=1, le=168, description="Hours of news to fetch")
):
    """Get recent news items"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Build query
        query = {}

        if source:
            query["source"] = source.value

        if currency_pair:
            query["currency_pairs"] = currency_pair

        if sentiment:
            query["sentiment.label"] = sentiment.value

        # Time filter
        start_time = datetime.utcnow() - timedelta(hours=hours)
        query["timestamp"] = {"$gte": start_time}

        # Get news items
        items = await mongodb.news.find(query).sort("timestamp", -1).limit(limit).to_list(length=limit)

        # Convert to response format
        responses = []
        for item in items:
            sentiment_data = item.get("sentiment")
            sentiment_result = None

            if sentiment_data:
                from app.schemas import SentimentResult
                sentiment_result = SentimentResult(
                    content_hash=sentiment_data.get("content_hash", ""),
                    label=SentimentLabel(sentiment_data.get("label", "neutral")),
                    confidence=sentiment_data.get("confidence", 0.0),
                    probabilities=sentiment_data.get("probabilities", {}),
                    timestamp=sentiment_data.get("timestamp", datetime.utcnow()),
                    model_name=sentiment_data.get("model_name", ""),
                    pair_sentiment=sentiment_data.get("pair_sentiment", {})
                )

            responses.append(NewsItemResponse(
                source=SourceType(item["source"]),
                title=item.get("title"),
                content=item["content"],
                url=item.get("url"),
                timestamp=item["timestamp"],
                currency_pairs=item.get("currency_pairs", []),
                sentiment=sentiment_result
            ))

        return responses

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_news(
    limit: int = Query(20, ge=1, le=50, description="Maximum number of items")
):
    """Get the latest news items"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get latest news
        items = await mongodb.news.find({}).sort("timestamp", -1).limit(limit).to_list(length=limit)

        # Convert to response format
        responses = []
        for item in items:
            responses.append({
                "source": item["source"],
                "title": item.get("title"),
                "content": item["content"][:200] + "..." if len(item.get("content", "")) > 200 else item.get("content", ""),
                "url": item.get("url"),
                "timestamp": item["timestamp"],
                "currency_pairs": item.get("currency_pairs", []),
                "sentiment": item.get("sentiment", {}).get("label", "neutral")
            })

        return {
            "count": len(responses),
            "items": responses
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/trend/{currency_pair}")
async def get_sentiment_trend(
    currency_pair: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of data"),
    interval: str = Query("1hour", description="Interval (15min, 1hour, 4hour)")
):
    """Get sentiment trend for a currency pair"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Calculate start time
        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Get news items with sentiment for this pair
        items = await mongodb.news.find({
            "currency_pairs": currency_pair,
            "timestamp": {"$gte": start_time},
            "sentiment": {"$exists": True}
        }).sort("timestamp", 1).to_list(length=None)

        # Aggregate sentiment by time interval
        interval_minutes = {
            "15min": 15,
            "1hour": 60,
            "4hour": 240
        }.get(interval, 60)

        # Group by time intervals
        time_groups = {}
        for item in items:
            timestamp = item["timestamp"]
            # Round down to interval
            interval_start = timestamp.replace(
                minute=0,
                second=0,
                microsecond=0
            )

            if interval == "15min":
                interval_start = interval_start.replace(
                    minute=(timestamp.minute // 15) * 15
                )
            elif interval == "4hour":
                interval_start = interval_start.replace(
                    hour=(timestamp.hour // 4) * 4
                )

            interval_key = interval_start.isoformat()

            if interval_key not in time_groups:
                time_groups[interval_key] = {
                    "sentiments": [],
                    "count": 0
                }

            sentiment = item.get("sentiment", {})
            pair_sentiment = sentiment.get("pair_sentiment", {}).get(currency_pair, 0)

            time_groups[interval_key]["sentiments"].append(pair_sentiment)
            time_groups[interval_key]["count"] += 1

        # Calculate averages
        timestamps = []
        sentiment_scores = []
        signal_counts = []

        for interval_key in sorted(time_groups.keys()):
            group = time_groups[interval_key]
            avg_sentiment = sum(group["sentiments"]) / len(group["sentiments"]) if group["sentiments"] else 0

            timestamps.append(interval_key)
            sentiment_scores.append(avg_sentiment)
            signal_counts.append(group["count"])

        return SentimentTrend(
            currency_pair=currency_pair,
            timestamps=timestamps,
            sentiment_scores=sentiment_scores,
            signal_counts=signal_counts
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_news_sources():
    """Get available news sources"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get distinct sources
        sources = await mongodb.news.distinct("source")

        # Get counts for each source
        source_counts = {}
        for source in sources:
            count = await mongodb.news.count_documents({"source": source})
            source_counts[source] = count

        return {
            "sources": source_counts,
            "total": sum(source_counts.values())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_news(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results")
):
    """Search news items"""
    try:
        mongodb = get_mongodb()
        if not mongodb:
            raise HTTPException(status_code=503, detail="Database not available")

        # Text search
        items = await mongodb.news.find({
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"content": {"$regex": query, "$options": "i"}}
            ]
        }).sort("timestamp", -1).limit(limit).to_list(length=limit)

        # Convert to response format
        responses = []
        for item in items:
            responses.append({
                "source": item["source"],
                "title": item.get("title"),
                "content": item["content"][:200] + "..." if len(item.get("content", "")) > 200 else item.get("content", ""),
                "url": item.get("url"),
                "timestamp": item["timestamp"],
                "currency_pairs": item.get("currency_pairs", []),
                "sentiment": item.get("sentiment", {}).get("label", "neutral")
            })

        return {
            "query": query,
            "count": len(responses),
            "items": responses
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
