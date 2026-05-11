"""
Signal Generation Engine
Generates BUY/SELL/HOLD trading signals from sentiment analysis
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from app.schemas import (
    SentimentResult,
    ProcessedNewsItem,
    TradingSignal,
    SignalDirection,
    CurrencyPair,
    SentimentLabel
)
from app.config import get_settings


@dataclass
class TimeWindow:
    """Time window configuration"""
    name: str
    minutes: int
    decay_lambda: float = 0.1


@dataclass
class SourceWeight:
    """Source credibility weight"""
    source: str
    weight: float


@dataclass
class SignalConfig:
    """Signal generation configuration"""
    currency_pair: str
    buy_threshold: float = 0.3
    sell_threshold: float = -0.3
    confidence_threshold: float = 0.6
    time_decay_lambda: float = 0.1


class TimeDecayCalculator:
    """Calculate time-decay weighted sentiment"""

    @staticmethod
    def calculate_weight(
        age_seconds: int,
        decay_lambda: float = 0.1
    ) -> float:
        """Calculate exponential time-decay weight"""
        # Convert seconds to minutes for the decay calculation
        age_minutes = age_seconds / 60.0

        # Exponential decay: e^(-λ * t)
        weight = math.exp(-decay_lambda * age_minutes)

        return weight

    @staticmethod
    def calculate_weighted_sentiment(
        sentiments: List[Tuple[float, datetime]],
        decay_lambda: float = 0.1,
        current_time: Optional[datetime] = None
    ) -> float:
        """Calculate time-decay weighted average sentiment"""
        if not sentiments:
            return 0.0

        if current_time is None:
            current_time = datetime.utcnow()

        weighted_sum = 0.0
        total_weight = 0.0

        for sentiment, timestamp in sentiments:
            # Calculate age in seconds
            age = (current_time - timestamp).total_seconds()

            # Calculate weight
            weight = TimeDecayCalculator.calculate_weight(age, decay_lambda)

            # Add to weighted sum
            weighted_sum += sentiment * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight


class SourceCredibilityWeighter:
    """Apply source credibility weights to sentiment"""

    DEFAULT_WEIGHTS = {
        "newsapi": 0.9,
        "twitter": 0.7,
        "reddit": 0.6,
        "telegram": 0.5
    }

    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        self.weights = {**self.DEFAULT_WEIGHTS}
        if custom_weights:
            self.weights.update(custom_weights)

    def get_weight(self, source: str) -> float:
        """Get weight for a source"""
        return self.weights.get(source.lower(), 0.5)

    def apply_weight(self, sentiment: float, source: str) -> float:
        """Apply source weight to sentiment"""
        weight = self.get_weight(source)
        return sentiment * weight


class ConsensusCalculator:
    """Calculate consensus factor from multiple sources"""

    @staticmethod
    def calculate_consensus(
        sentiments: List[float]
    ) -> float:
        """Calculate consensus factor (0-1)"""
        if not sentiments:
            return 0.0

        if len(sentiments) == 1:
            return 1.0

        # Calculate standard deviation
        if len(sentiments) > 1:
            std_dev = statistics.stdev(sentiments)
        else:
            std_dev = 0.0

        # Convert to consensus (lower std dev = higher consensus)
        # Using a sigmoid-like function
        consensus = 1.0 / (1.0 + std_dev)

        return consensus

    @staticmethod
    def calculate_volume_factor(
        volume: int,
        min_volume: int = 5,
        max_volume: int = 50
    ) -> float:
        """Calculate volume factor based on number of items"""
        if volume < min_volume:
            return 0.0

        # Sigmoid-like function for volume
        normalized = (volume - min_volume) / (max_volume - min_volume)
        volume_factor = normalized / (1.0 + normalized)

        return min(volume_factor, 1.0)


class SignalStrengthCalculator:
    """Calculate signal strength from various factors"""

    @staticmethod
    def calculate(
        avg_sentiment: float,
        consensus_factor: float,
        volume_factor: float
    ) -> float:
        """Calculate signal strength (0-100)"""
        # Base strength from sentiment
        base_strength = abs(avg_sentiment) * 100

        # Apply consensus and volume factors
        adjusted_strength = base_strength * consensus_factor * volume_factor

        # Clamp to 0-100
        return max(0.0, min(100.0, adjusted_strength))

    @staticmethod
    def calculate_confidence(
        avg_confidence: float,
        consensus_factor: float,
        volume_factor: float
    ) -> float:
        """Calculate confidence score (0-100)"""
        # Base confidence from model confidence
        base_confidence = avg_confidence * 100

        # Apply consensus and volume factors
        adjusted_confidence = base_confidence * consensus_factor * volume_factor

        # Clamp to 0-100
        return max(0.0, min(100.0, adjusted_confidence))


class ExplainabilityBuilder:
    """Build explainable reasoning for signals"""

    @staticmethod
    def build_reasoning(
        direction: SignalDirection,
        strength: float,
        confidence: float,
        avg_sentiment: float,
        consensus: float,
        volume: int,
        top_headlines: List[str]
    ) -> str:
        """Build human-readable reasoning"""
        direction_text = direction.value.upper()

        reasoning_parts = [
            f"{direction_text} signal generated for this currency pair.",
            f"Overall sentiment score: {avg_sentiment:.2f}",
            f"Signal strength: {strength:.1f}/100",
            f"Confidence: {confidence:.1f}/100",
            f"Based on {volume} news items with {consensus:.1%} consensus."
        ]

        if top_headlines:
            reasoning_parts.append("\nKey supporting headlines:")
            for i, headline in enumerate(top_headlines[:3], 1):
                reasoning_parts.append(f"{i}. {headline}")

        return "\n".join(reasoning_parts)

    @staticmethod
    def extract_headlines(
        items: List[ProcessedNewsItem],
        max_count: int = 5
    ) -> List[str]:
        """Extract headlines from processed items"""
        headlines = []

        for item in items:
            if item.title:
                headlines.append(item.title)
            elif item.cleaned_content:
                # Use first 100 chars of content as headline
                headline = item.cleaned_content[:100] + "..."
                headlines.append(headline)

            if len(headlines) >= max_count:
                break

        return headlines


class SignalGenerator:
    """Main signal generation engine"""

    def __init__(self, config: Optional[SignalConfig] = None):
        self.settings = get_settings()
        self.config = config or SignalConfig(currency_pair="EUR/USD")

        # Initialize components
        self.time_decay = TimeDecayCalculator()
        self.source_weighter = SourceCredibilityWeighter()
        self.consensus = ConsensusCalculator()
        self.strength_calc = SignalStrengthCalculator()
        self.explainability = ExplainabilityBuilder()

        # Time windows
        self.time_windows = [
            TimeWindow("15min", 15, self.settings.time_decay_lambda),
            TimeWindow("1hour", 60, self.settings.time_decay_lambda),
            TimeWindow("4hour", 240, self.settings.time_decay_lambda)
        ]

    def generate_signal(
        self,
        sentiment_results: List[SentimentResult],
        processed_items: List[ProcessedNewsItem],
        currency_pair: str,
        time_window: str = "1hour"
    ) -> Optional[TradingSignal]:
        """Generate a trading signal for a currency pair"""
        if not sentiment_results or not processed_items:
            return None

        # Filter items for the specific currency pair
        pair_items = [
            item for item in processed_items
            if currency_pair in item.currency_pairs
        ]

        if not pair_items:
            return None

        # Get time window configuration
        window_config = self._get_window_config(time_window)
        if not window_config:
            return None

        # Calculate time-decay weighted sentiment
        current_time = datetime.utcnow()
        sentiments = []

        for result, item in zip(sentiment_results, processed_items):
            if currency_pair not in item.currency_pairs:
                continue

            # Get sentiment value for this pair
            sentiment_value = result.pair_sentiment.get(currency_pair, 0.0)

            # Apply source weight
            weighted_sentiment = self.source_weighter.apply_weight(
                sentiment_value,
                item.source.value
            )

            sentiments.append((weighted_sentiment, item.timestamp))

        if not sentiments:
            return None

        # Calculate weighted average sentiment
        avg_sentiment = self.time_decay.calculate_weighted_sentiment(
            sentiments,
            window_config.decay_lambda,
            current_time
        )

        # Calculate consensus
        sentiment_values = [s[0] for s in sentiments]
        consensus_factor = self.consensus.calculate_consensus(sentiment_values)

        # Calculate volume factor
        volume_factor = self.consensus.calculate_volume_factor(len(pair_items))

        # Calculate signal strength
        strength = self.strength_calc.calculate(
            avg_sentiment,
            consensus_factor,
            volume_factor
        )

        # Calculate confidence
        avg_confidence = statistics.mean([
            r.confidence for r in sentiment_results
            if currency_pair in processed_items[sentiment_results.index(r)].currency_pairs
        ]) if sentiment_results else 0.0

        confidence = self.strength_calc.calculate_confidence(
            avg_confidence,
            consensus_factor,
            volume_factor
        )

        # Determine direction
        direction = self._determine_direction(avg_sentiment, confidence)

        # Extract supporting headlines
        headlines = self.explainability.extract_headlines(pair_items)

        # Build reasoning
        reasoning = self.explainability.build_reasoning(
            direction,
            strength,
            confidence,
            avg_sentiment,
            consensus_factor,
            len(pair_items),
            headlines
        )

        # Create signal
        signal = TradingSignal(
            currency_pair=currency_pair,
            direction=direction,
            strength=strength,
            confidence=confidence,
            timestamp=current_time,
            time_window=time_window,
            reasoning=reasoning,
            sentiment_score=avg_sentiment,
            volume=len(pair_items),
            consensus_factor=consensus_factor,
            supporting_headlines=headlines
        )

        return signal

    def generate_signals_for_all_pairs(
        self,
        sentiment_results: List[SentimentResult],
        processed_items: List[ProcessedNewsItem],
        time_window: str = "1hour"
    ) -> List[TradingSignal]:
        """Generate signals for all currency pairs"""
        signals = []

        # Get all unique currency pairs
        all_pairs = set()
        for item in processed_items:
            all_pairs.update(item.currency_pairs)

        # Generate signal for each pair
        for pair in all_pairs:
            signal = self.generate_signal(
                sentiment_results,
                processed_items,
                pair,
                time_window
            )

            if signal:
                signals.append(signal)

        return signals

    def _determine_direction(
        self,
        sentiment: float,
        confidence: float
    ) -> SignalDirection:
        """Determine signal direction from sentiment and confidence"""
        # Convert confidence to 0-1 range
        confidence_normalized = confidence / 100.0

        # Check if confidence meets threshold
        if confidence_normalized < self.config.confidence_threshold:
            return SignalDirection.HOLD

        # Determine direction based on sentiment
        if sentiment >= self.config.buy_threshold:
            return SignalDirection.BUY
        elif sentiment <= self.config.sell_threshold:
            return SignalDirection.SELL
        else:
            return SignalDirection.HOLD

    def _get_window_config(self, window_name: str) -> Optional[TimeWindow]:
        """Get time window configuration by name"""
        for window in self.time_windows:
            if window.name == window_name:
                return window
        return None

    def update_config(self, config: SignalConfig):
        """Update signal generation configuration"""
        self.config = config


class SignalAggregator:
    """Aggregate signals across multiple time windows"""

    def __init__(self):
        self.generator = SignalGenerator()

    def aggregate_signals(
        self,
        sentiment_results: List[SentimentResult],
        processed_items: List[ProcessedNewsItem],
        currency_pair: str
    ) -> Dict[str, TradingSignal]:
        """Aggregate signals across all time windows"""
        signals = {}

        windows = ["15min", "1hour", "4hour"]

        for window in windows:
            signal = self.generator.generate_signal(
                sentiment_results,
                processed_items,
                currency_pair,
                window
            )

            if signal:
                signals[window] = signal

        return signals

    def get_consensus_signal(
        self,
        signals: Dict[str, TradingSignal]
    ) -> Optional[TradingSignal]:
        """Get consensus signal from multiple time windows"""
        if not signals:
            return None

        # Count directions
        direction_counts = defaultdict(int)
        for signal in signals.values():
            direction_counts[signal.direction] += 1

        # Find most common direction
        most_common = max(direction_counts, key=direction_counts.get)

        # If there's a tie, prefer the longer time window
        if list(direction_counts.values()).count(direction_counts[most_common]) > 1:
            # Prefer 4hour, then 1hour, then 15min
            window_priority = ["4hour", "1hour", "15min"]
            for window in window_priority:
                if window in signals and signals[window].direction == most_common:
                    return signals[window]

        # Return signal with most common direction
        for signal in signals.values():
            if signal.direction == most_common:
                return signal

        return None
