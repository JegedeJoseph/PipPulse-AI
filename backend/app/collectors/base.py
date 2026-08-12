"""
Base Collector Module
Defines the interface and common functionality for all data collectors
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import json

from app.schemas import RawNewsItem, SourceType
from app.database import get_redis
from app.config import get_settings


class BaseCollector(ABC):
    """Base class for all data collectors"""

    def __init__(self, source_type: SourceType):
        self.source_type = source_type
        self.redis = get_redis()
        self.settings = get_settings()
        self.stream_key = self.settings.redis_stream_key

    @abstractmethod
    async def collect(self) -> List[RawNewsItem]:
        """Collect raw news items from the source"""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the source API"""
        pass

    def generate_content_hash(self, content: str, source_id: str) -> str:
        """Generate a unique hash for content deduplication"""
        hash_input = f"{self.source_type.value}:{source_id}:{content}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    async def publish_to_stream(self, item: RawNewsItem) -> bool:
        """Publish item to Redis stream"""
        try:
            if self.redis:
                await self.redis.xadd(
                    self.stream_key,
                    {
                        "source": item.source.value,
                        "source_id": item.source_id,
                        "content": item.content,
                        "title": item.title or "",
                        "author": item.author or "",
                        "url": str(item.url) if item.url else "",
                        "timestamp": item.timestamp.isoformat(),
                        "currency_pairs": json.dumps(item.currency_pairs),
                        "metadata": json.dumps(item.metadata),
                        "content_hash": item.content_hash or ""
                    }
                )
                return True
        except Exception as e:
            print(f"Error publishing to stream: {e}")
        return False

    async def check_duplicate(self, content_hash: str) -> bool:
        """Check if item already exists in Redis"""
        try:
            if self.redis:
                exists = await self.redis.exists(f"news:{content_hash}")
                return exists > 0
        except Exception as e:
            print(f"Error checking duplicate: {e}")
        return False

    async def mark_processed(self, content_hash: str) -> bool:
        """Mark item as processed in Redis"""
        try:
            if self.redis:
                await self.redis.setex(
                    f"news:{content_hash}",
                    86400,  # 24 hours TTL
                    "1"
                )
                return True
        except Exception as e:
            print(f"Error marking processed: {e}")
        return False

    def extract_currency_pairs(self, text: str) -> List[str]:
        """Extract currency pairs from text (basic implementation)"""
        # This is a simple implementation - can be enhanced with NLP
        currency_pairs = [
            "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF",
            "AUD/USD", "USD/CAD", "NZD/USD", "USD/SGD"
        ]

        found_pairs = []
        text_upper = text.upper()

        for pair in currency_pairs:
            if pair.replace("/", "") in text_upper.replace("/", ""):
                found_pairs.append(pair)

        return found_pairs

    def normalize_text(self, text: str) -> str:
        """Normalize text for processing"""
        # Basic normalization
        text = text.strip()
        text = " ".join(text.split())  # Remove extra whitespace
        return text

    async def run(self) -> int:
        """Run the collector and return count of items collected"""
        try:
            items = await self.collect()
            count = 0

            # Fallback to mock data if API fails or returns no items
            if not items and getattr(self.settings, 'use_mock_fallback', False):
                print(f"Fallback to mock data for {self.source_type.value}")
                from app.collectors.mock_data import generate_mock_news
                items = generate_mock_news(self.source_type, count=6)

            for item in items:
                # Generate content hash
                item.content_hash = self.generate_content_hash(
                    item.content,
                    item.source_id
                )

                # Check for duplicates
                if await self.check_duplicate(item.content_hash):
                    continue

                # Publish to stream
                if await self.publish_to_stream(item):
                    await self.mark_processed(item.content_hash)
                    count += 1

            return count

        except Exception as e:
            print(f"Error in collector run: {e}")
            return 0
