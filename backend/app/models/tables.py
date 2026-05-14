"""
SQLAlchemy table definitions for PostgreSQL persistence.
"""

from sqlalchemy import (
    Table,
    Column,
    String,
    DateTime,
    Integer,
    Numeric,
    Text,
    JSON,
    text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

metadata = Base.metadata


system_config = Table(
    "system_config",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")),
    Column("config_key", String(100), nullable=False, unique=True),
    Column("config_value", JSONB, nullable=False),
    Column("description", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


backtest_runs = Table(
    "backtest_runs",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")),
    Column("currency_pair", String(20), nullable=False),
    Column("start_date", DateTime(timezone=True), nullable=False),
    Column("end_date", DateTime(timezone=True), nullable=False),
    Column("initial_capital", Numeric(15, 2), nullable=False),
    Column("final_capital", Numeric(15, 2), nullable=False),
    Column("total_return", Numeric(10, 4), nullable=False),
    Column("win_rate", Numeric(5, 2), nullable=False),
    Column("average_risk_reward", Numeric(10, 4), nullable=False),
    Column("sharpe_ratio", Numeric(10, 4), nullable=False),
    Column("max_drawdown", Numeric(10, 4), nullable=False),
    Column("total_trades", Integer, nullable=False),
    Column("winning_trades", Integer, nullable=False),
    Column("losing_trades", Integer, nullable=False),
    Column("confidence_calibration", JSONB),
    Column("parameters", JSONB),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
