"""
Backtesting API
Endpoints for running and managing backtests
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.backtesting import BacktestService
from app.database import get_mongodb, get_postgres_session
from app.config import get_settings

router = APIRouter()


class BacktestRequest(BaseModel):
    """Backtest request parameters"""
    currency_pair: Optional[str] = Field(None, description="Currency pair to backtest")
    start_date: Optional[datetime] = Field(None, description="Start date for backtest")
    end_date: Optional[datetime] = Field(None, description="End date for backtest")
    initial_capital: float = Field(default=10000.0, gt=0, description="Initial capital")
    risk_per_trade: float = Field(default=0.02, ge=0.01, le=0.1, description="Risk per trade")


class BacktestResponse(BaseModel):
    """Backtest response"""
    currency_pair: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    win_rate: float
    average_risk_reward: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    confidence_calibration: dict


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """Run a backtest with specified parameters"""
    try:
        service = BacktestService()

        result = await service.run_backtest(
            currency_pair=request.currency_pair,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            risk_per_trade=request.risk_per_trade
        )

        return {
            "status": "success",
            "result": {
                "currency_pair": result.currency_pair,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "initial_capital": result.initial_capital,
                "final_capital": result.final_capital,
                "total_return": result.total_return,
                "win_rate": result.win_rate,
                "average_risk_reward": result.average_risk_reward,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown": result.max_drawdown,
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "confidence_calibration": result.confidence_calibration
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_backtest_history(
    currency_pair: Optional[str] = Query(None, description="Filter by currency pair"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results")
):
    """Get historical backtests"""
    try:
        session = get_postgres_session()

        from sqlalchemy import select, desc
        from app.database import Base
        from sqlalchemy.orm import Session

        async with session() as db:
            # Query backtests
            query = select(Base.metadata.tables['backtest_runs'])

            if currency_pair:
                query = query.where(Base.metadata.tables['backtest_runs'].c.currency_pair == currency_pair)

            query = query.order_by(desc(Base.metadata.tables['backtest_runs'].c.created_at))
            query = query.limit(limit)

            result = await db.execute(query)
            backtests = result.fetchall()

            return {
                "status": "success",
                "count": len(backtests),
                "backtests": [
                    {
                        "id": str(backtest.id),
                        "currency_pair": backtest.currency_pair,
                        "start_date": backtest.start_date,
                        "end_date": backtest.end_date,
                        "total_return": float(backtest.total_return),
                        "win_rate": float(backtest.win_rate),
                        "sharpe_ratio": float(backtest.sharpe_ratio),
                        "total_trades": backtest.total_trades,
                        "created_at": backtest.created_at
                    }
                    for backtest in backtests
                ]
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_backtest_summary():
    """Get backtest summary statistics"""
    try:
        session = get_postgres_session()

        from sqlalchemy import select, func, desc
        from app.database import Base

        async with session() as db:
            backtest_table = Base.metadata.tables['backtest_runs']

            # Query summary view
            query = select(
                backtest_table.c.currency_pair,
                func.count(backtest_table.c.id).label('total_runs'),
                func.avg(backtest_table.c.total_return).label('avg_return'),
                func.avg(backtest_table.c.win_rate).label('avg_win_rate'),
                func.avg(backtest_table.c.sharpe_ratio).label('avg_sharpe_ratio'),
                func.max(backtest_table.c.created_at).label('last_run')
            ).group_by(backtest_table.c.currency_pair)

            result = await db.execute(query)
            summaries = result.fetchall()

            return {
                "status": "success",
                "summary": [
                    {
                        "currency_pair": summary.currency_pair,
                        "total_runs": summary.total_runs,
                        "avg_return": float(summary.avg_return) if summary.avg_return else 0.0,
                        "avg_win_rate": float(summary.avg_win_rate) if summary.avg_win_rate else 0.0,
                        "avg_sharpe_ratio": float(summary.avg_sharpe_ratio) if summary.avg_sharpe_ratio else 0.0,
                        "last_run": summary.last_run
                    }
                    for summary in summaries
                ]
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}")
async def get_backtest_details(backtest_id: str):
    """Get detailed backtest results"""
    try:
        session = get_postgres_session()

        from sqlalchemy import select
        from app.database import Base
        import uuid

        async with session() as db:
            backtest_table = Base.metadata.tables['backtest_runs']

            query = select(backtest_table).where(
                backtest_table.c.id == uuid.UUID(backtest_id)
            )

            result = await db.execute(query)
            backtest = result.fetchone()

            if not backtest:
                raise HTTPException(status_code=404, detail="Backtest not found")

            return {
                "status": "success",
                "backtest": {
                    "id": str(backtest.id),
                    "currency_pair": backtest.currency_pair,
                    "start_date": backtest.start_date,
                    "end_date": backtest.end_date,
                    "initial_capital": float(backtest.initial_capital),
                    "final_capital": float(backtest.final_capital),
                    "total_return": float(backtest.total_return),
                    "win_rate": float(backtest.win_rate),
                    "average_risk_reward": float(backtest.average_risk_reward),
                    "sharpe_ratio": float(backtest.sharpe_ratio),
                    "max_drawdown": float(backtest.max_drawdown),
                    "total_trades": backtest.total_trades,
                    "winning_trades": backtest.winning_trades,
                    "losing_trades": backtest.losing_trades,
                    "confidence_calibration": backtest.confidence_calibration,
                    "parameters": backtest.parameters,
                    "created_at": backtest.created_at
                }
            }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid backtest ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
