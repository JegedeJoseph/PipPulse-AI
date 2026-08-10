"""
Application Configuration Module
Handles environment variables and application settings
"""

from typing import List, Optional, Any
from pydantic_settings import BaseSettings
from pydantic import Field, computed_field
import os
import json


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
    mongodb_client_id: Optional[str] = Field(default=None, env="MONGODB_CLIENT_ID")
    mongodb_client_secret: Optional[str] = Field(default=None, env="MONGODB_CLIENT_SECRET")

    # Redis Configuration
    redis_uri: str = Field(default="redis://localhost:6379/0", env="REDIS_URI")
    redis_stream_key: str = Field(default="news_stream", env="REDIS_STREAM_KEY")

    # PostgreSQL Configuration
    postgres_uri: str = Field(
        default="postgresql+asyncpg://pippulse:pippulse123@localhost:5432/pippulse",
        env="POSTGRES_URI"
    )
    postgres_db: str = Field(default="pippulse", env="POSTGRES_DB")

    # InfluxDB Configuration
    influxdb_url: str = Field(default="http://localhost:8086", env="INFLUXDB_URL")
    influxdb_token: str = Field(
        default="pippulse-super-secret-token-change-in-production",
        env="INFLUXDB_TOKEN"
    )
    influxdb_org: str = Field(default="pippulse", env="INFLUXDB_ORG")
    influxdb_bucket: str = Field(default="signals", env="INFLUXDB_BUCKET")
    influxdb_price_bucket: str = Field(default="forex_prices", env="INFLUXDB_PRICE_BUCKET")

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
    currency_pairs_raw: str = Field(
        default="EUR/USD,GBP/USD,USD/JPY,USD/CHF,AUD/USD,USD/CAD",
        env="CURRENCY_PAIRS"
    )

    @computed_field
    @property
    def currency_pairs(self) -> List[str]:
        return _parse_list(self.currency_pairs_raw)

    # Subreddits
    reddit_subreddits_raw: str = Field(
        default="Forex,CurrencyTrading,ForexStrategy,Daytrading",
        env="REDDIT_SUBREDDITS"
    )

    @computed_field
    @property
    def reddit_subreddits(self) -> List[str]:
        return _parse_list(self.reddit_subreddits_raw)

    # Telegram Channels
    telegram_channels_raw: str = Field(
        default="forex_signals,forex_trading",
        env="TELEGRAM_CHANNELS"
    )

    @computed_field
    @property
    def telegram_channels(self) -> List[str]:
        return _parse_list(self.telegram_channels_raw)

    # News Categories
    news_categories_raw: str = Field(
        default="business,general",
        env="NEWS_CATEGORIES"
    )

    @computed_field
    @property
    def news_categories(self) -> List[str]:
        return _parse_list(self.news_categories_raw)

    # News Languages
    news_languages_raw: str = Field(default="en", env="NEWS_LANGUAGES")

    @computed_field
    @property
    def news_languages(self) -> List[str]:
        return _parse_list(self.news_languages_raw)

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
    cors_origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        env="CORS_ORIGINS"
    )

    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        return _parse_list(self.cors_origins_raw)

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="pippulse-jwt-secret-key-change-in-production",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=1440, env="JWT_EXPIRATION_MINUTES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def _parse_list(val: str) -> List[str]:
    if not val:
        return []
    if val.startswith('[') and val.endswith(']'):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            pass
    return [x.strip() for x in val.split(',')]

# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
