"""
Signal Engine Runner
Orchestrates sentiment analysis and signal generation
"""

import asyncio
import logging
import json
from typing import List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.preprocessing import PreprocessingPipeline
from app.sentiment import SentimentService
from app.signal import SignalGenerator, SignalAggregator
from app.database import (
    connect_mongodb,
    connect_redis,
    connect_postgres,
    disconnect_mongodb,
    disconnect_redis,
    disconnect_postgres,
    get_mongodb,
    get_redis,
    get_influxdb_write_api,
)
from app.config import get_settings
from app.services.config_service import get_system_config
from tinyflux import Point

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SignalEngineRunner:
    """Main signal engine that processes news and generates signals"""

    def __init__(self):
        self.settings = get_settings()
        self.preprocessing_pipeline = PreprocessingPipeline()
        self.sentiment_service = None
        self.signal_generator = None
        self.signal_aggregator = None
        self.running = False
        self.last_stream_id = "0-0"
        self.config_last_refresh: Optional[datetime] = None
        self.cached_config = None

    async def initialize(self):
        """Initialize the signal engine components"""
        logger.info("Initializing signal engine...")

        await connect_mongodb()
        await connect_redis()
        # TinyFlux is file-based, no explicit connection needed
        await connect_postgres()

        # Initialize sentiment service
        try:
            self.sentiment_service = SentimentService(
                model_name=self.settings.finbert_model_name
            )
            logger.info("Sentiment service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize sentiment service: {e}")
            raise

        # Initialize signal generator
        try:
            self.signal_generator = SignalGenerator()
            logger.info("Signal generator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize signal generator: {e}")
            raise

        # Initialize signal aggregator
        try:
            self.signal_aggregator = SignalAggregator()
            logger.info("Signal aggregator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize signal aggregator: {e}")
            raise

        await self.refresh_config(force=True)
        logger.info("Signal engine initialized successfully")

    async def refresh_config(self, force: bool = False):
        """Refresh configuration from persistent storage"""
        now = datetime.utcnow()
        if not force and self.config_last_refresh and (now - self.config_last_refresh) < timedelta(minutes=5):
            return

        try:
            config = await get_system_config()
            self.cached_config = config
            if self.signal_generator:
                self.signal_generator.update_from_config(config)
            if self.signal_aggregator:
                self.signal_aggregator.generator.update_from_config(config)
            self.config_last_refresh = now
            logger.info("Signal engine configuration refreshed")
        except Exception as e:
            logger.error(f"Failed to refresh configuration: {e}")

    async def process_news_stream(self):
        """Process news from Redis stream"""
        logger.info("Processing news stream...")

        redis = get_redis()
        if not redis:
            logger.error("Redis not available")
            return

        mongodb = get_mongodb()
        if not mongodb:
            logger.error("MongoDB not available")
            return

        stream_key = self.settings.redis_stream_key

        # Restore last processed ID if available
        stored_id = await redis.get(f"{stream_key}:last_id")
        if stored_id:
            self.last_stream_id = stored_id

        while self.running:
            try:
                # Read from stream
                messages = await redis.xread(
                    {stream_key: self.last_stream_id},
                    count=10,
                    block=5000  # 5 second timeout
                )

                if not messages:
                    continue

                for stream, items in messages:
                    for item_id, fields in items:
                        try:
                            # Process item
                            await self.process_news_item(fields, mongodb)
                            self.last_stream_id = item_id
                            await redis.set(f"{stream_key}:last_id", item_id)
                        except Exception as e:
                            logger.error(f"Error processing news item: {e}")

            except Exception as e:
                logger.error(f"Error reading from stream: {e}")
                await asyncio.sleep(5)

    async def process_news_item(self, fields: dict, mongodb):
        """Process a single news item"""
        try:
            def _decode(value):
                if value is None:
                    return ""
                if isinstance(value, bytes):
                    return value.decode()
                return str(value)

            # Extract fields
            source = _decode(fields.get("source") or fields.get(b"source"))
            source_id = _decode(fields.get("source_id") or fields.get(b"source_id"))
            content = _decode(fields.get("content") or fields.get(b"content"))
            title = _decode(fields.get("title") or fields.get(b"title")) or None
            author = _decode(fields.get("author") or fields.get(b"author")) or None
            url = _decode(fields.get("url") or fields.get(b"url")) or None
            timestamp_str = _decode(fields.get("timestamp") or fields.get(b"timestamp"))
            currency_pairs_str = _decode(fields.get("currency_pairs") or fields.get(b"currency_pairs"))
            metadata_str = _decode(fields.get("metadata") or fields.get(b"metadata"))
            content_hash = _decode(fields.get("content_hash") or fields.get(b"content_hash"))

            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str)

            # Parse currency pairs
            currency_pairs = json.loads(currency_pairs_str) if currency_pairs_str else []

            # Parse metadata
            metadata = json.loads(metadata_str) if metadata_str else {}

            # Create raw item
            from app.schemas import RawNewsItem, SourceType
            raw_item = RawNewsItem(
                source=SourceType(source),
                source_id=source_id,
                content=content,
                title=title,
                author=author,
                url=url,
                timestamp=timestamp,
                currency_pairs=currency_pairs,
                metadata=metadata,
                content_hash=content_hash
            )

            # Store raw item
            await mongodb.raw_news.update_one(
                {"content_hash": raw_item.content_hash},
                {
                    "$set": {
                        "source": raw_item.source.value,
                        "source_id": raw_item.source_id,
                        "content": raw_item.content,
                        "title": raw_item.title,
                        "author": raw_item.author,
                        "url": str(raw_item.url) if raw_item.url else None,
                        "timestamp": raw_item.timestamp,
                        "currency_pairs": raw_item.currency_pairs,
                        "metadata": raw_item.metadata,
                        "content_hash": raw_item.content_hash,
                    }
                },
                upsert=True
            )

            # Preprocess
            processed_item = self.preprocessing_pipeline.process(raw_item)
            if not processed_item:
                logger.debug(f"Item filtered out during preprocessing: {source_id}")
                return

            # Analyze sentiment
            sentiment_result = await self.sentiment_service.analyze(processed_item)
            if not sentiment_result:
                logger.debug(f"Sentiment analysis failed for item: {source_id}")
                return

            # Store processed item with sentiment
            await mongodb.news.update_one(
                {"content_hash": processed_item.content_hash},
                {
                    "$set": {
                        "source": processed_item.source.value,
                        "source_id": processed_item.source_id,
                        "content": processed_item.original_content,
                        "cleaned_content": processed_item.cleaned_content,
                        "title": processed_item.title,
                        "author": processed_item.author,
                        "url": str(processed_item.url) if processed_item.url else None,
                        "timestamp": processed_item.timestamp,
                        "currency_pairs": processed_item.currency_pairs,
                        "language": processed_item.language,
                        "is_spam": processed_item.is_spam,
                        "is_bot": processed_item.is_bot,
                        "metadata": processed_item.metadata,
                        "content_hash": processed_item.content_hash,
                        "sentiment": {
                            "content_hash": sentiment_result.content_hash,
                            "label": sentiment_result.label.value,
                            "confidence": sentiment_result.confidence,
                            "probabilities": sentiment_result.probabilities,
                            "timestamp": sentiment_result.timestamp,
                            "model_name": sentiment_result.model_name,
                            "pair_sentiment": sentiment_result.pair_sentiment
                        }
                    }
                },
                upsert=True
            )

            logger.debug(f"Processed item: {source_id} - {sentiment_result.label.value}")

            # Publish to realtime channel
            redis = get_redis()
            if redis:
                payload = {
                    "source": processed_item.source.value,
                    "title": processed_item.title,
                    "content": processed_item.original_content,
                    "url": str(processed_item.url) if processed_item.url else None,
                    "timestamp": processed_item.timestamp.isoformat(),
                    "currency_pairs": processed_item.currency_pairs,
                    "sentiment": {
                        "label": sentiment_result.label.value,
                        "confidence": sentiment_result.confidence,
                        "probabilities": sentiment_result.probabilities,
                        "timestamp": sentiment_result.timestamp.isoformat(),
                        "model_name": sentiment_result.model_name,
                        "pair_sentiment": sentiment_result.pair_sentiment
                    }
                }
                await redis.publish("news", json.dumps(payload))

        except Exception as e:
            logger.error(f"Error processing news item: {e}")

    async def generate_signals(self):
        """Generate trading signals from processed news"""
        logger.info("Generating signals...")

        mongodb = get_mongodb()
        if not mongodb:
            logger.error("MongoDB not available")
            return

        while self.running:
            try:
                await self.refresh_config()

                # Get recent news items with sentiment
                start_time = datetime.utcnow() - timedelta(hours=4)

                items = await mongodb.news.find({
                    "timestamp": {"$gte": start_time},
                    "sentiment": {"$exists": True}
                }).sort("timestamp", -1).limit(100).to_list(length=100)

                if not items:
                    logger.debug("No recent news items found")
                    await asyncio.sleep(60)
                    continue

                # Convert to processed items
                from app.schemas import ProcessedNewsItem, SourceType, SentimentResult, SentimentLabel
                processed_items = []
                sentiment_results = []

                for item in items:
                    processed_item = ProcessedNewsItem(
                        source=SourceType(item["source"]),
                        source_id=item["source_id"],
                        original_content=item["content"],
                        cleaned_content=item.get("cleaned_content", item["content"]),
                        title=item.get("title"),
                        author=item.get("author"),
                        url=item.get("url"),
                        timestamp=item["timestamp"],
                        currency_pairs=item.get("currency_pairs", []),
                        language=item.get("language", "en"),
                        is_spam=item.get("is_spam", False),
                        is_bot=item.get("is_bot", False),
                        metadata=item.get("metadata", {}),
                        content_hash=item["content_hash"]
                    )

                    sentiment_data = item.get("sentiment", {})
                    sentiment_result = SentimentResult(
                        content_hash=sentiment_data.get("content_hash", ""),
                        label=SentimentLabel(sentiment_data.get("label", "neutral")),
                        confidence=sentiment_data.get("confidence", 0.0),
                        probabilities=sentiment_data.get("probabilities", {}),
                        timestamp=sentiment_data.get("timestamp", datetime.utcnow()),
                        model_name=sentiment_data.get("model_name", ""),
                        pair_sentiment=sentiment_data.get("pair_sentiment", {})
                    )

                    processed_items.append(processed_item)
                    sentiment_results.append(sentiment_result)

                # Generate signals for all currency pairs and windows
                signals = []
                for window in ["15min", "1hour", "4hour"]:
                    signals.extend(
                        self.signal_generator.generate_signals_for_all_pairs(
                            sentiment_results,
                            processed_items,
                            time_window=window
                        )
                    )

                # Store signals
                for signal in signals:
                    await mongodb.signals.update_one(
                        {
                            "currency_pair": signal.currency_pair,
                            "time_window": signal.time_window,
                            "timestamp": {"$gte": datetime.utcnow() - timedelta(minutes=15)}
                        },
                        {
                            "$set": {
                                "currency_pair": signal.currency_pair,
                                "direction": signal.direction.value,
                                "strength": signal.strength,
                                "confidence": signal.confidence,
                                "timestamp": signal.timestamp,
                                "time_window": signal.time_window,
                                "reasoning": signal.reasoning,
                                "sentiment_score": signal.sentiment_score,
                                "volume": signal.volume,
                                "consensus_factor": signal.consensus_factor,
                                "supporting_headlines": signal.supporting_headlines
                            }
                        },
                        upsert=True
                    )

                    # Write to TinyFlux
                    write_api = get_influxdb_write_api()
                    if write_api:
                        point = Point(
                            time=signal.timestamp,
                            measurement="signals",
                            tags={
                                "currency_pair": signal.currency_pair,
                                "time_window": signal.time_window,
                                "direction": signal.direction.value
                            },
                            fields={
                                "strength": float(signal.strength),
                                "confidence": float(signal.confidence),
                                "sentiment_score": float(signal.sentiment_score),
                                "volume": int(signal.volume),
                                "consensus_factor": float(signal.consensus_factor)
                            }
                        )
                        write_api.insert(point)

                    # Publish to realtime channel
                    redis = get_redis()
                    if redis:
                        payload = {
                            "currency_pair": signal.currency_pair,
                            "direction": signal.direction.value,
                            "strength": signal.strength,
                            "confidence": signal.confidence,
                            "timestamp": signal.timestamp.isoformat(),
                            "time_window": signal.time_window,
                            "reasoning": signal.reasoning,
                            "sentiment_score": signal.sentiment_score,
                            "volume": signal.volume,
                            "consensus_factor": signal.consensus_factor,
                            "supporting_headlines": signal.supporting_headlines,
                        }
                        await redis.publish("signals", json.dumps(payload))

                    logger.info(f"Generated signal: {signal.currency_pair} - {signal.direction.value} (strength: {signal.strength:.1f}, confidence: {signal.confidence:.1f})")

                # Wait before next signal generation
                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f"Error generating signals: {e}")
                await asyncio.sleep(60)

    async def run(self):
        """Run the signal engine"""
        logger.info("Starting signal engine...")

        self.running = True

        # Run both tasks concurrently
        try:
            await asyncio.gather(
                self.process_news_stream(),
                self.generate_signals()
            )
        except Exception as e:
            logger.error(f"Error in signal engine: {e}")
        finally:
            self.running = False
            await disconnect_mongodb()
            await disconnect_redis()
            # TinyFlux is file-based, no explicit disconnection needed
            await disconnect_postgres()

    def stop(self):
        """Stop the signal engine"""
        logger.info("Stopping signal engine...")
        self.running = False


async def main():
    """Main entry point"""
    logger.info("Starting PipPulse AI Signal Engine...")

    # Create engine
    engine = SignalEngineRunner()

    # Initialize
    await engine.initialize()

    # Run
    try:
        await engine.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
