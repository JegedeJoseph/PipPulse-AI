"""
Application Configuration Module
Handles environment variables and application settings
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):

    """Application settings loaded from environment variables"""

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    # MongoDB Configuration
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017/pippulse",
        env="MONGODB_URI"
    )
    mongodb_database: str = Field(default="pippulse", env="MONGO_DATABASE")

    # Redis Configuration (BurnerRedis - embedded replacement)
    redis_uri: str = Field(default="redis://localhost:6379/0", env="REDIS_URI")
    redis_stream_key: str = Field(default="news_stream", env="REDIS_STREAM_KEY")
    redis_persistence_path: str = Field(default="redis_data.dat", env="REDIS_PERSISTENCE_PATH")

    # PostgreSQL Configuration
    postgres_uri: str = Field(
        default="postgresql+asyncpg://pippulse:pippulse123@localhost:5432/pippulse",
        env="POSTGRES_URI"
    )
    postgres_db: str = Field(default="pippulse", env="POSTGRES_DB")

    # TinyFlux Configuration (embedded time-series database replacement)
    tinyflux_signals_path: str = Field(default="tinyflux_signals.csv", env="TINYFLUX_SIGNALS_PATH")
    tinyflux_prices_path: str = Field(default="tinyflux_prices.csv", env="TINYFLUX_PRICES_PATH")

    # API Keys
    newsapi_key: Optional[str] = Field(default=None, env="NEWSAPI_KEY")
    alphavantage_api_key: Optional[str] = Field(default=None, env="ALPHAVANTAGE_API_KEY")

    twitter_bearer_token: Optional[str] = Field(default=None, env="TWITTER_BEARER_TOKEN")
    twitter_api_key: Optional[str] = Field(default=None, env="TWITTER_API_KEY")
    twitter_api_secret: Optional[str] = Field(default=None, env="TWITTER_API_SECRET")
    twitter_access_token: Optional[str] = Field(default=None, env="TWITTER_ACCESS_TOKEN")
    twitter_access_secret: Optional[str] = Field(default=None, env="TWITTER_ACCESS_SECRET")

    reddit_client_id: Optional[str] = Field(default=None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(default=None, env="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(default="PipPulse/1.0", env="REDDIT_USER_AGENT")

    telegram_api_id: Optional[str] = Field(default=None, env="TELEGRAM_API_ID")
    telegram_api_hash: Optional[str] = Field(default=None, env="TELEGRAM_API_HASH")
    telegram_bot_token: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN")

    # Model Configuration
    finbert_model_name: str = Field(default="ProsusAI/finbert", env="FINBERT_MODEL_NAME")
    finbert_cache_dir: str = Field(default="./models/finbert", env="FINBERT_CACHE_DIR")

    # Signal Generation Parameters
    signal_latency_target: int = Field(default=5, env="SIGNAL_LATENCY_TARGET")
    max_batch_size: int = Field(default=32, env="MAX_BATCH_SIZE")
    confidence_threshold: float = Field(default=0.6, env="CONFIDENCE_THRESHOLD")
    time_decay_lambda: float = Field(default=0.1, env="TIME_DECAY_LAMBDA")

    # Source Credibility Weights
    source_weight_newsapi: float = Field(default=0.9, env="SOURCE_WEIGHT_NEWSAPI")
    source_weight_twitter: float = Field(default=0.7, env="SOURCE_WEIGHT_TWITTER")
    source_weight_reddit: float = Field(default=0.6, env="SOURCE_WEIGHT_REDDIT")
    source_weight_telegram: float = Field(default=0.5, env="SOURCE_WEIGHT_TELEGRAM")

    # Time Windows (in minutes)
    window_15min: int = Field(default=15, env="WINDOW_15MIN")
    window_1hour: int = Field(default=60, env="WINDOW_1HOUR")
    window_4hour: int = Field(default=240, env="WINDOW_4HOUR")

    # Currency Pairs
    currency_pairs: List[str] = Field(
        default=["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD"],
        env="CURRENCY_PAIRS"
    )

    # Subreddits
    reddit_subreddits: List[str] = Field(
        default=["Forex", "CurrencyTrading", "ForexStrategy", "Daytrading"],
        env="REDDIT_SUBREDDITS"
    )

    # Telegram Channels
    telegram_channels: List[str] = Field(
        default=["forex_signals", "forex_trading"],
        env="TELEGRAM_CHANNELS"
    )

    # News Categories
    news_categories: List[str] = Field(
        default=["business", "general"],
        env="NEWS_CATEGORIES"
    )

    # News Languages
    news_languages: List[str] = Field(default=["en"], env="NEWS_LANGUAGES")

    # Rate Limits (requests per minute)
    rate_limit_newsapi: int = Field(default=100, env="RATE_LIMIT_NEWSAPI")
    rate_limit_twitter: int = Field(default=450, env="RATE_LIMIT_TWITTER")
    rate_limit_reddit: int = Field(default=60, env="RATE_LIMIT_REDDIT")
    rate_limit_telegram: int = Field(default=30, env="RATE_LIMIT_TELEGRAM")

    # Backtesting Configuration
    backtest_start_date: str = Field(default="2024-01-01", env="BACKTEST_START_DATE")
    backtest_end_date: str = Field(default="2024-12-31", env="BACKTEST_END_DATE")
    backtest_initial_capital: float = Field(default=10000.0, env="BACKTEST_INITIAL_CAPITAL")
    backtest_risk_per_trade: float = Field(default=0.02, env="BACKTEST_RISK_PER_TRADE")

    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=1440, env="JWT_EXPIRATION_MINUTES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
