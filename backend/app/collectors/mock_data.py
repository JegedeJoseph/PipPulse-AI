"""
Mock Data Generator
Generates fallback forex news data when APIs fail or return no data.
"""
import random
from datetime import datetime, timedelta
from typing import List

from app.schemas import RawNewsItem, SourceType

def generate_mock_news(source_type: SourceType, count: int = 6) -> List[RawNewsItem]:
    """Generate realistic mock forex news items"""
    items = []
    
    # Pre-defined templates for headlines/content categorized by rough sentiment
    templates = {
        "neutral": [
            "Forex trading volumes for {pair} remain steady ahead of market open.",
            "Central bank officials scheduled to speak today regarding {pair} economic outlook.",
            "Technical analysis shows {pair} consolidating near key resistance levels.",
            "Market participants await upcoming inflation data affecting {pair}.",
            "Quiet session expected for {pair} as major markets close for holiday."
        ],
        "positive": [
            "Stronger than expected economic data boosts {pair} outlook.",
            "Bullish momentum building for {pair} following recent policy announcements.",
            "Investors shift to risk-on sentiment, driving {pair} higher.",
            "Positive retail sales figures support upward trend for {pair}."
        ],
        "negative": [
            "Unexpected inflation spike puts downward pressure on {pair}.",
            "Dovish central bank comments weigh heavily on {pair}.",
            "Market uncertainty drives sell-off in {pair} during early trading.",
            "Disappointing employment data leads to sharp drop in {pair}."
        ]
    }
    
    currency_pairs = [
        "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF",
        "AUD/USD", "USD/CAD", "NZD/USD", "USD/SGD"
    ]
    
    # We want mostly neutral (60%), with some positive (20%) and negative (20%)
    weights = ["neutral", "neutral", "neutral", "positive", "negative"]
    
    for i in range(count):
        # Pick a sentiment category based on weights to ensure a mix
        sentiment = random.choice(weights)
        template = random.choice(templates[sentiment])
        pair = random.choice(currency_pairs)
        
        content = template.format(pair=pair)
        title = content if source_type != SourceType.TWITTER and source_type != SourceType.TELEGRAM else None
        
        # Add a random time offset within the last hour
        time_offset = timedelta(minutes=random.randint(0, 59))
        timestamp = datetime.utcnow() - time_offset
        
        # Create a deterministic mock ID
        mock_id = f"mock_{source_type.value}_{int(timestamp.timestamp())}_{i}"
        
        item = RawNewsItem(
            source=source_type,
            source_id=mock_id,
            content=content,
            title=title,
            author="System_Mock_Generator",
            url=f"https://mockdata.local/{mock_id}",
            timestamp=timestamp,
            currency_pairs=[pair],
            metadata={
                "is_mock_data": True,
                "intended_sentiment": sentiment
            }
        )
        items.append(item)
        
    return items
