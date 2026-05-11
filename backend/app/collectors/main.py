"""
Main Collector Runner
Orchestrates all data collectors and runs them continuously
"""

import asyncio
import logging
from typing import List
from datetime import datetime

from app.collectors.newsapi_collector import NewsAPICollector
from app.collectors.twitter_collector import TwitterCollector
from app.collectors.reddit_collector import RedditCollector
from app.collectors.telegram_collector import TelegramCollector
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CollectorRunner:
    """Main collector runner that orchestrates all collectors"""

    def __init__(self):
        self.settings = get_settings()
        self.collectors = []
        self.running = False

    def initialize_collectors(self):
        """Initialize all available collectors"""
        logger.info("Initializing collectors...")

        # NewsAPI Collector
        if self.settings.newsapi_key:
            try:
                newsapi_collector = NewsAPICollector()
                self.collectors.append(("NewsAPI", newsapi_collector))
                logger.info("NewsAPI collector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize NewsAPI collector: {e}")

        # Twitter Collector
        if self.settings.twitter_bearer_token:
            try:
                twitter_collector = TwitterCollector()
                self.collectors.append(("Twitter", twitter_collector))
                logger.info("Twitter collector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twitter collector: {e}")

        # Reddit Collector
        if self.settings.reddit_client_id:
            try:
                reddit_collector = RedditCollector()
                self.collectors.append(("Reddit", reddit_collector))
                logger.info("Reddit collector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit collector: {e}")

        # Telegram Collector
        if self.settings.telegram_api_id:
            try:
                telegram_collector = TelegramCollector()
                self.collectors.append(("Telegram", telegram_collector))
                logger.info("Telegram collector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram collector: {e}")

        logger.info(f"Initialized {len(self.collectors)} collectors")

    async def run_once(self):
        """Run all collectors once"""
        logger.info("Running collectors...")

        total_items = 0

        for name, collector in self.collectors:
            try:
                logger.info(f"Running {name} collector...")
                count = await collector.run()
                total_items += count
                logger.info(f"{name} collector collected {count} items")
            except Exception as e:
                logger.error(f"Error running {name} collector: {e}")

        logger.info(f"Total items collected: {total_items}")
        return total_items

    async def run_continuous(self, interval_minutes: int = 5):
        """Run collectors continuously at specified interval"""
        self.running = True
        logger.info(f"Starting continuous collection (interval: {interval_minutes} minutes)")

        while self.running:
            try:
                await self.run_once()
                logger.info(f"Waiting {interval_minutes} minutes until next collection...")
                await asyncio.sleep(interval_minutes * 60)
            except Exception as e:
                logger.error(f"Error in continuous collection: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    def stop(self):
        """Stop continuous collection"""
        logger.info("Stopping collectors...")
        self.running = False


async def main():
    """Main entry point"""
    logger.info("Starting PipPulse AI Collector Service...")

    # Create runner
    runner = CollectorRunner()

    # Initialize collectors
    runner.initialize_collectors()

    if not runner.collectors:
        logger.error("No collectors initialized. Please configure API keys in .env file")
        return

    # Run collectors once
    await runner.run_once()

    # Run continuously
    try:
        await runner.run_continuous(interval_minutes=5)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
