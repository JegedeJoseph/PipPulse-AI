"""
FinBERT Sentiment Engine
Financial sentiment classification using FinBERT model
"""

import asyncio
import torch
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import json
import hashlib

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    pipeline
)
from app.schemas import (
    ProcessedNewsItem,
    SentimentResult,
    SentimentLabel,
    SourceType
)
from app.config import get_settings


@dataclass
class SentimentBatch:
    """Batch of items for sentiment analysis"""
    items: List[ProcessedNewsItem]
    texts: List[str]
    content_hashes: List[str]


class FinBERTModel:
    """FinBERT model wrapper for sentiment analysis"""

    def __init__(self, model_name: str = "ProsusAI/finbert"):
        self.model_name = model_name
        self.settings = get_settings()
        self.device = self._get_device()
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self._load_model()

    def _get_device(self) -> str:
        """Get the best available device"""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"

    def _load_model(self):
        """Load the FinBERT model and tokenizer"""
        try:
            print(f"Loading FinBERT model: {self.model_name}")
            print(f"Using device: {self.device}")

            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)

            # Move model to device
            self.model.to(self.device)

            # Create pipeline
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True
            )

            print("FinBERT model loaded successfully")

        except Exception as e:
            print(f"Error loading FinBERT model: {e}")
            raise

    def predict(
        self,
        text: str,
        return_all_scores: bool = True
    ) -> Dict[str, Any]:
        """Predict sentiment for a single text"""
        try:
            # Truncate text if too long
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]

            # Get predictions
            results = self.pipeline(text, return_all_scores=return_all_scores)

            if return_all_scores:
                # Process all scores
                scores = {result["label"].lower(): result["score"] for result in results}

                # Find the label with highest score
                best_result = max(results, key=lambda x: x["score"])
                label = best_result["label"].lower()
                confidence = best_result["score"]

                return {
                    "label": label,
                    "confidence": confidence,
                    "probabilities": scores
                }
            else:
                return {
                    "label": results["label"].lower(),
                    "confidence": results["score"],
                    "probabilities": {}
                }

        except Exception as e:
            print(f"Error predicting sentiment: {e}")
            return {
                "label": "neutral",
                "confidence": 0.0,
                "probabilities": {}
            }

    def predict_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[Dict[str, Any]]:
        """Predict sentiment for a batch of texts"""
        results = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            try:
                batch_results = self.pipeline(
                    batch_texts,
                    return_all_scores=True
                )

                for result in batch_results:
                    scores = {r["label"].lower(): r["score"] for r in result}
                    best_result = max(result, key=lambda x: x["score"])

                    results.append({
                        "label": best_result["label"].lower(),
                        "confidence": best_result["score"],
                        "probabilities": scores
                    })

            except Exception as e:
                print(f"Error in batch prediction: {e}")
                # Add neutral results for failed predictions
                for _ in batch_texts:
                    results.append({
                        "label": "neutral",
                        "confidence": 0.0,
                        "probabilities": {}
                    })

        return results


class PairAwareSentimentMapper:
    """Map sentiment to currency pairs with awareness of base/quote polarity"""

    # Sentiment polarity for individual currencies
    CURRENCY_POLARITY = {
        "USD": {"positive": "strong", "negative": "weak"},
        "EUR": {"positive": "strong", "negative": "weak"},
        "GBP": {"positive": "strong", "negative": "weak"},
        "JPY": {"positive": "strong", "negative": "weak"},
        "CHF": {"positive": "strong", "negative": "weak"},
        "AUD": {"positive": "strong", "negative": "weak"},
        "CAD": {"positive": "strong", "negative": "weak"},
        "NZD": {"positive": "strong", "negative": "weak"},
        "SGD": {"positive": "strong", "negative": "weak"},
    }

    @staticmethod
    def map_to_pairs(
        sentiment: str,
        confidence: float,
        currency_pairs: List[str]
    ) -> Dict[str, float]:
        """Map sentiment to specific currency pairs"""
        pair_sentiment = {}

        if not currency_pairs:
            return pair_sentiment

        # Normalize sentiment label
        sentiment_value = 0.0
        if sentiment == "positive":
            sentiment_value = confidence
        elif sentiment == "negative":
            sentiment_value = -confidence
        else:
            sentiment_value = 0.0

        # Map to each currency pair
        for pair in currency_pairs:
            try:
                base, quote = pair.split("/")

                # For a currency pair, positive sentiment on the base currency
                # means positive for the pair, positive on quote means negative
                # This is a simplified approach - in production, use more sophisticated NLP

                # Default: apply sentiment to the pair
                pair_sentiment[pair] = sentiment_value

            except ValueError:
                # Invalid pair format
                continue

        return pair_sentiment


class SentimentEngine:
    """Main sentiment analysis engine"""

    def __init__(self, model_name: Optional[str] = None):
        self.settings = get_settings()
        model_name = model_name or self.settings.finbert_model_name

        self.model = FinBERTModel(model_name)
        self.mapper = PairAwareSentimentMapper()
        self.cache = {}  # Simple in-memory cache

    def analyze(
        self,
        item: ProcessedNewsItem,
        use_cache: bool = True
    ) -> Optional[SentimentResult]:
        """Analyze sentiment for a single item"""
        # Check cache
        if use_cache and item.content_hash in self.cache:
            return self.cache[item.content_hash]

        # Get prediction
        prediction = self.model.predict(item.cleaned_content)

        # Map to currency pairs
        pair_sentiment = self.mapper.map_to_pairs(
            prediction["label"],
            prediction["confidence"],
            item.currency_pairs
        )

        # Create result
        result = SentimentResult(
            content_hash=item.content_hash,
            label=SentimentLabel(prediction["label"]),
            confidence=prediction["confidence"],
            probabilities=prediction["probabilities"],
            timestamp=datetime.utcnow(),
            model_name=self.model.model_name,
            pair_sentiment=pair_sentiment
        )

        # Cache result
        if use_cache:
            self.cache[item.content_hash] = result

        return result

    def analyze_batch(
        self,
        items: List[ProcessedNewsItem],
        batch_size: int = 32
    ) -> List[Optional[SentimentResult]]:
        """Analyze sentiment for a batch of items"""
        if not items:
            return []

        # Extract texts
        texts = [item.cleaned_content for item in items]

        # Get batch predictions
        predictions = self.model.predict_batch(texts, batch_size)

        # Create results
        results = []
        for item, prediction in zip(items, predictions):
            # Map to currency pairs
            pair_sentiment = self.mapper.map_to_pairs(
                prediction["label"],
                prediction["confidence"],
                item.currency_pairs
            )

            # Create result
            result = SentimentResult(
                content_hash=item.content_hash,
                label=SentimentLabel(prediction["label"]),
                confidence=prediction["confidence"],
                probabilities=prediction["probabilities"],
                timestamp=datetime.utcnow(),
                model_name=self.model.model_name,
                pair_sentiment=pair_sentiment
            )

            # Cache result
            self.cache[item.content_hash] = result

            results.append(result)

        return results

    def clear_cache(self):
        """Clear the sentiment cache"""
        self.cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "keys": list(self.cache.keys())[:10]  # First 10 keys
        }


class SentimentService:
    """Service for sentiment analysis with async support"""

    def __init__(self, model_name: Optional[str] = None):
        self.engine = SentimentEngine(model_name)
        self.executor = None

    async def analyze(
        self,
        item: ProcessedNewsItem
    ) -> Optional[SentimentResult]:
        """Analyze sentiment asynchronously"""
        loop = asyncio.get_event_loop()

        # Run in thread pool to avoid blocking
        result = await loop.run_in_executor(
            None,
            self.engine.analyze,
            item
        )

        return result

    async def analyze_batch(
        self,
        items: List[ProcessedNewsItem],
        batch_size: int = 32
    ) -> List[Optional[SentimentResult]]:
        """Analyze sentiment for a batch asynchronously"""
        loop = asyncio.get_event_loop()

        # Run in thread pool to avoid blocking
        results = await loop.run_in_executor(
            None,
            self.engine.analyze_batch,
            items,
            batch_size
        )

        return results

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        return {
            "model_name": self.engine.model.model_name,
            "device": self.engine.model.device,
            "cache_size": len(self.engine.cache)
        }
