"""
Backtesting Engine
Validate trading signals against historical price data
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque
import statistics
import httpx
import logging
from time import time

from app.schemas import (
    TradingSignal,
    BacktestResult,
    SignalDirection,
    CurrencyPair
)
from app.database import (
    get_mongodb,
    get_influxdb_query_api,
    get_influxdb_write_api,
    get_influxdb_price_client,
    get_postgres_session,
)
from app.config import get_settings
from tinyflux import Point
from app.models.tables import backtest_runs
from sqlalchemy import insert

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    exit_time: Optional[datetime]
    currency_pair: str
    direction: SignalDirection
    entry_price: float
    exit_price: Optional[float]
    pnl: Optional[float]
    pnl_percentage: Optional[float]
    holding_period: Optional[timedelta]
    signal_strength: float
    signal_confidence: float
    reasoning: str


@dataclass
class PriceData:
    """OHLCV price data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class RateLimiter:
    """Simple rate limiter for API requests (token bucket algorithm)"""
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    async def acquire(self):
        """Wait until a request can be made within rate limit"""
        now = time()
        
        # Remove old requests outside the time window
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()
        
        # If at capacity, wait until oldest request is outside window
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0]) + 0.1
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Waiting {sleep_time:.2f}s before next request")
                await asyncio.sleep(sleep_time)
                # Recursively check again after sleep
                return await self.acquire()
        
        self.requests.append(now)


class PriceDataFetcher:
    """Fetch historical price data for backtesting"""

    # Class-level rate limiter (shared across all instances)
    _rate_limiter = RateLimiter(max_requests=5, time_window=60)

    def __init__(self):
        self.settings = get_settings()
        logger.debug(f"Initialized PriceDataFetcher with AlphaVantage key: {bool(self.settings.alphavantage_api_key)}")

    async def fetch_price_data(
        self,
        currency_pair: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1h"
    ) -> List[PriceData]:
        """Fetch historical price data for a currency pair"""
        try:
            # Try to get from TinyFlux first
            influxdb = get_influxdb_price_client()
            if influxdb:
                cached = await self._fetch_from_influxdb(
                    influxdb,
                    currency_pair,
                    start_date,
                    end_date,
                    interval
                )
                if cached:
                    return cached

            # Fetch from Alpha Vantage
            return await self._fetch_from_alpha_vantage(
                currency_pair,
                start_date,
                end_date,
                interval
            )

            # No data available
            return []

        except Exception as e:
            logger.error(f"Error fetching price data: {e}")
            return []

    async def _fetch_from_influxdb(
        self,
        influxdb,
        currency_pair: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> List[PriceData]:
        """Fetch price data from TinyFlux cache"""
        try:
            from tinyflux import TimeQuery
            
            # Create time range query
            query = TimeQuery(start=start_date, end=end_date)
            
            # Query for specific currency pair
            price_data = []
            for point in influxdb.search(query):
                # Check if this point matches our currency pair
                if point.tags.get("pair") == currency_pair:
                    price_data.append(PriceData(
                        timestamp=point.time,
                        open=point.fields.get("open", 0),
                        high=point.fields.get("high", 0),
                        low=point.fields.get("low", 0),
                        close=point.fields.get("close", 0),
                        volume=point.fields.get("volume", 0)
                    ))

            if price_data:
                logger.info(f"Retrieved {len(price_data)} cached price records for {currency_pair} from TinyFlux")
            return price_data

        except Exception as e:
            logger.warning(f"Error fetching from TinyFlux cache for {currency_pair}: {e}")
            return []

    async def _fetch_from_alpha_vantage(
        self,
        currency_pair: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> List[PriceData]:
        """Fetch price data from Alpha Vantage with rate limiting"""
        if not self.settings.alphavantage_api_key:
            logger.error("ALPHAVANTAGE_API_KEY not configured")
            raise Exception("ALPHAVANTAGE_API_KEY not configured")

        try:
            base, quote = currency_pair.split("/")
        except ValueError:
            logger.error(f"Invalid currency pair format: {currency_pair}")
            raise Exception(f"Invalid currency pair format: {currency_pair}")
        
        interval_map = {
            "15min": "15min",
            "1h": "60min",
            "4h": "60min",
        }
        av_interval = interval_map.get(interval, "60min")

        params = {
            "function": "FX_INTRADAY",
            "from_symbol": base,
            "to_symbol": quote,
            "interval": av_interval,
            "outputsize": "full",
            "apikey": self.settings.alphavantage_api_key,
        }

        # Apply rate limiting before making request
        await self._rate_limiter.acquire()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Fetching price data for {currency_pair} from Alpha Vantage")
                response = await client.get("https://www.alphavantage.co/query", params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching data for {currency_pair} from Alpha Vantage")
            raise Exception(f"Alpha Vantage request timeout for {currency_pair}")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching data for {currency_pair}: {e}")
            raise Exception(f"Alpha Vantage HTTP error: {e}")

        series_key = f"Time Series FX ({av_interval})"
        if series_key not in data:
            error_msg = data.get('Note') or data.get('Error Message') or "Unknown error"
            logger.error(f"Alpha Vantage response error for {currency_pair}: {error_msg}")
            raise Exception(f"Alpha Vantage response missing series: {error_msg}")

        series = data[series_key]
        price_data = []
        
        for timestamp_str, values in series.items():
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                logger.warning(f"Invalid timestamp format: {timestamp_str}")
                continue
            
            if not (start_date <= timestamp <= end_date):
                continue

            try:
                price_data.append(PriceData(
                    timestamp=timestamp,
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=0.0
                ))
            except (KeyError, ValueError) as e:
                logger.warning(f"Error parsing price data for {timestamp_str}: {e}")
                continue

        price_data.sort(key=lambda p: p.timestamp)
        logger.info(f"Fetched {len(price_data)} price records for {currency_pair}")

        if interval == "4h":
            price_data = self._aggregate_prices(price_data, hours=4)

        # Store in InfluxDB for caching
        try:
            await self._write_to_influxdb(currency_pair, price_data)
        except Exception as e:
            logger.warning(f"Failed to write to InfluxDB for {currency_pair}: {e}")
            # Don't fail if InfluxDB write fails, just log and continue
        
        return price_data

    async def _write_to_influxdb(self, currency_pair: str, price_data: List[PriceData]) -> None:
        """Persist price data to TinyFlux for caching"""
        price_db = get_influxdb_price_client()
        if not price_db or not price_data:
            logger.debug(f"Skipping TinyFlux write: price_db={bool(price_db)}, data_points={len(price_data)}")
            return

        try:
            points = []
            for item in price_data:
                point = Point(
                    time=item.timestamp,
                    measurement="forex_prices",
                    tags={"pair": currency_pair, "timeframe": "intraday"},
                    fields={
                        "open": float(item.open),
                        "high": float(item.high),
                        "low": float(item.low),
                        "close": float(item.close),
                        "volume": float(item.volume)
                    }
                )
                points.append(point)

            # Insert all points
            price_db.insert_multiple(points)
            logger.info(f"Successfully wrote {len(points)} price records for {currency_pair} to TinyFlux")
        except Exception as e:
            logger.error(f"Error writing to TinyFlux for {currency_pair}: {e}")

    @staticmethod
    def _aggregate_prices(price_data: List[PriceData], hours: int) -> List[PriceData]:
        """Aggregate price data into larger windows"""
        if not price_data:
            return []

        aggregated = []
        bucket = []
        current_bucket_start = None

        for item in price_data:
            bucket_start = item.timestamp.replace(minute=0, second=0, microsecond=0)
            bucket_start = bucket_start.replace(hour=(bucket_start.hour // hours) * hours)
            if current_bucket_start is None:
                current_bucket_start = bucket_start

            if bucket_start != current_bucket_start:
                aggregated.append(PriceData(
                    timestamp=current_bucket_start,
                    open=bucket[0].open,
                    high=max(p.high for p in bucket),
                    low=min(p.low for p in bucket),
                    close=bucket[-1].close,
                    volume=sum(p.volume for p in bucket),
                ))
                bucket = []
                current_bucket_start = bucket_start

            bucket.append(item)

        if bucket:
            aggregated.append(PriceData(
                timestamp=current_bucket_start,
                open=bucket[0].open,
                high=max(p.high for p in bucket),
                low=min(p.low for p in bucket),
                close=bucket[-1].close,
                volume=sum(p.volume for p in bucket),
            ))

        return aggregated


class TradeExecutor:
    """Execute trades based on signals"""

    def __init__(self, risk_per_trade: float = 0.02):
        self.risk_per_trade = risk_per_trade

    def execute_trade(
        self,
        signal: TradingSignal,
        entry_price: float,
        initial_capital: float
    ) -> Trade:
        """Execute a trade based on a signal"""
        return Trade(
            entry_time=signal.timestamp,
            exit_time=None,
            currency_pair=signal.currency_pair,
            direction=signal.direction,
            entry_price=entry_price,
            exit_price=None,
            pnl=None,
            pnl_percentage=None,
            holding_period=None,
            signal_strength=signal.strength,
            signal_confidence=signal.confidence,
            reasoning=signal.reasoning
        )

    def close_trade(
        self,
        trade: Trade,
        exit_price: float,
        exit_time: datetime
    ) -> Trade:
        """Close a trade and calculate P&L"""
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.holding_period = exit_time - trade.entry_time

        # Calculate P&L
        if trade.direction == SignalDirection.BUY:
            price_change = exit_price - trade.entry_price
        else:  # SELL
            price_change = trade.entry_price - exit_price

        trade.pnl = price_change
        trade.pnl_percentage = (price_change / trade.entry_price) * 100

        return trade


class BacktestEngine:
    """Main backtesting engine"""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        risk_per_trade: float = 0.02,
        max_holding_period: timedelta = timedelta(hours=24)
    ):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.max_holding_period = max_holding_period

        self.price_fetcher = PriceDataFetcher()
        self.trade_executor = TradeExecutor(risk_per_trade)

    async def run_backtest(
        self,
        signals: List[TradingSignal],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1h"
    ) -> BacktestResult:
        """Run a backtest on a list of signals"""
        if not signals:
            return self._empty_result(start_date, end_date)

        # Group signals by currency pair
        signals_by_pair = defaultdict(list)
        for signal in signals:
            signals_by_pair[signal.currency_pair].append(signal)

        # Run backtest for each pair
        all_trades = []
        capital = self.initial_capital

        for currency_pair, pair_signals in signals_by_pair.items():
            # Fetch price data
            price_data = await self.price_fetcher.fetch_price_data(
                currency_pair,
                start_date,
                end_date,
                interval
            )

            if not price_data:
                continue

            # Create price lookup
            price_lookup = {pd.timestamp: pd for pd in price_data}

            # Execute trades
            pair_trades = await self._execute_trades_for_pair(
                pair_signals,
                price_lookup,
                capital
            )

            all_trades.extend(pair_trades)

        # Calculate results
        return self._calculate_results(
            all_trades,
            start_date,
            end_date,
            capital
        )

    async def _execute_trades_for_pair(
        self,
        signals: List[TradingSignal],
        price_lookup: Dict[datetime, PriceData],
        capital: float
    ) -> List[Trade]:
        """Execute trades for a specific currency pair"""
        trades = []
        open_trades = []

        # Sort signals by timestamp
        signals.sort(key=lambda s: s.timestamp)

        for signal in signals:
            # Skip HOLD signals
            if signal.direction == SignalDirection.HOLD:
                continue

            # Find entry price
            entry_price = self._find_price_at_time(
                price_lookup,
                signal.timestamp
            )

            if entry_price is None:
                continue

            # Execute trade
            trade = self.trade_executor.execute_trade(
                signal,
                entry_price,
                capital
            )

            open_trades.append(trade)

            # Close existing trades that have exceeded max holding period
            for open_trade in open_trades[:]:
                if (signal.timestamp - open_trade.entry_time) > self.max_holding_period:
                    exit_price = self._find_price_at_time(
                        price_lookup,
                        signal.timestamp
                    )

                    if exit_price:
                        closed_trade = self.trade_executor.close_trade(
                            open_trade,
                            exit_price,
                            signal.timestamp
                        )
                        trades.append(closed_trade)
                        open_trades.remove(open_trade)

        # Close remaining open trades
        last_timestamp = max(price_lookup.keys()) if price_lookup else datetime.utcnow()

        for open_trade in open_trades:
            exit_price = self._find_price_at_time(
                price_lookup,
                last_timestamp
            )

            if exit_price:
                closed_trade = self.trade_executor.close_trade(
                    open_trade,
                    exit_price,
                    last_timestamp
                )
                trades.append(closed_trade)

        return trades

    def _find_price_at_time(
        self,
        price_lookup: Dict[datetime, PriceData],
        target_time: datetime
    ) -> Optional[float]:
        """Find the price at or closest to a given time"""
        # Find the closest price data point
        closest_time = min(
            price_lookup.keys(),
            key=lambda t: abs((t - target_time).total_seconds())
        )

        # Only use if within 1 hour
        if abs((closest_time - target_time).total_seconds()) <= 3600:
            return price_lookup[closest_time].close

        return None

    def _calculate_results(
        self,
        trades: List[Trade],
        start_date: datetime,
        end_date: datetime,
        initial_capital: float
    ) -> BacktestResult:
        """Calculate backtest results"""
        if not trades:
            return self._empty_result(start_date, end_date)

        # Separate winning and losing trades
        winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl < 0]

        # Calculate total return
        total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
        total_return = (total_pnl / initial_capital) * 100

        # Calculate win rate
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0

        # Calculate average risk-reward ratio
        avg_win = statistics.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = statistics.mean([abs(t.pnl) for t in losing_trades]) if losing_trades else 0
        avg_risk_reward = avg_win / avg_loss if avg_loss > 0 else 0

        # Calculate Sharpe ratio (simplified)
        returns = [t.pnl_percentage for t in trades if t.pnl_percentage is not None]
        sharpe_ratio = 0
        if returns and len(returns) > 1:
            avg_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0

        # Calculate maximum drawdown
        cumulative_returns = []
        running_capital = initial_capital

        for trade in trades:
            if trade.pnl is not None:
                running_capital += trade.pnl
                cumulative_returns.append((running_capital - initial_capital) / initial_capital)

        max_drawdown = 0
        peak = 0

        for ret in cumulative_returns:
            if ret > peak:
                peak = ret
            drawdown = peak - ret
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Calculate confidence calibration
        confidence_calibration = self._calculate_confidence_calibration(trades)

        return BacktestResult(
            currency_pair="Multiple",
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=initial_capital + total_pnl,
            total_return=total_return,
            win_rate=win_rate,
            average_risk_reward=avg_risk_reward,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            confidence_calibration=confidence_calibration
        )

    def _calculate_confidence_calibration(
        self,
        trades: List[Trade]
    ) -> Dict[str, float]:
        """Calculate confidence calibration metrics"""
        if not trades:
            return {}

        # Group trades by confidence ranges
        confidence_ranges = {
            "0-20": [],
            "20-40": [],
            "40-60": [],
            "60-80": [],
            "80-100": []
        }

        for trade in trades:
            confidence = trade.signal_confidence
            if confidence <= 20:
                confidence_ranges["0-20"].append(trade)
            elif confidence <= 40:
                confidence_ranges["20-40"].append(trade)
            elif confidence <= 60:
                confidence_ranges["40-60"].append(trade)
            elif confidence <= 80:
                confidence_ranges["60-80"].append(trade)
            else:
                confidence_ranges["80-100"].append(trade)

        # Calculate win rate for each range
        calibration = {}

        for range_name, range_trades in confidence_ranges.items():
            if range_trades:
                winning = sum(1 for t in range_trades if t.pnl and t.pnl > 0)
                win_rate = winning / len(range_trades) * 100
                calibration[range_name] = win_rate

        return calibration

    def _empty_result(self, start_date: datetime, end_date: datetime) -> BacktestResult:
        """Return empty backtest result"""
        return BacktestResult(
            currency_pair="N/A",
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            total_return=0.0,
            win_rate=0.0,
            average_risk_reward=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            confidence_calibration={}
        )


class BacktestService:
    """Service for running backtests"""

    def __init__(self):
        self.engine = BacktestEngine()

    async def run_backtest(
        self,
        currency_pair: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_capital: float = 10000.0,
        risk_per_trade: float = 0.02
    ) -> BacktestResult:
        """Run a backtest with specified parameters"""
        # Set default dates
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)

        if not end_date:
            end_date = datetime.utcnow()

        # Get signals from database
        mongodb = get_mongodb()
        if not mongodb:
            raise Exception("Database not available")

        # Build query
        query = {
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }

        if currency_pair:
            query["currency_pair"] = currency_pair

        # Get signals
        signals_data = await mongodb.signals.find(query).to_list(length=None)

        # Convert to TradingSignal objects
        signals = []
        for signal_data in signals_data:
            signals.append(TradingSignal(
                currency_pair=signal_data["currency_pair"],
                direction=SignalDirection(signal_data["direction"]),
                strength=signal_data["strength"],
                confidence=signal_data["confidence"],
                timestamp=signal_data["timestamp"],
                time_window=signal_data["time_window"],
                reasoning=signal_data.get("reasoning", ""),
                sentiment_score=signal_data.get("sentiment_score", 0),
                volume=signal_data.get("volume", 0),
                consensus_factor=signal_data.get("consensus_factor", 0),
                supporting_headlines=signal_data.get("supporting_headlines", [])
            ))

        # Run backtest
        engine = BacktestEngine(initial_capital, risk_per_trade)
        result = await engine.run_backtest(signals, start_date, end_date)

        # Store backtest result in PostgreSQL
        session = get_postgres_session()
        if session:
            async with session() as db:
                await db.execute(
                    insert(backtest_runs).values(
                        currency_pair=result.currency_pair,
                        start_date=result.start_date,
                        end_date=result.end_date,
                        initial_capital=result.initial_capital,
                        final_capital=result.final_capital,
                        total_return=result.total_return,
                        win_rate=result.win_rate,
                        average_risk_reward=result.average_risk_reward,
                        sharpe_ratio=result.sharpe_ratio,
                        max_drawdown=result.max_drawdown,
                        total_trades=result.total_trades,
                        winning_trades=result.winning_trades,
                        losing_trades=result.losing_trades,
                        confidence_calibration=result.confidence_calibration,
                        parameters={
                            "currency_pair": currency_pair,
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                            "initial_capital": initial_capital,
                            "risk_per_trade": risk_per_trade,
                        },
                    )
                )
                await db.commit()

        return result
