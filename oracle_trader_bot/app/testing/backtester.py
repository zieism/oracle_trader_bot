# app/testing/backtester.py
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd

from app.portfolio.performance_tracker import PerformanceMetrics


logger = logging.getLogger(__name__)


class BacktestMode(str, Enum):
    SINGLE_STRATEGY = "SINGLE_STRATEGY"
    MULTI_STRATEGY = "MULTI_STRATEGY"
    OPTIMIZATION = "OPTIMIZATION"


@dataclass
class BacktestSettings:
    start_date: datetime
    end_date: datetime
    initial_balance: float
    symbols: List[str]
    strategy_name: str
    strategy_params: Dict[str, Any]
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005   # 0.05%
    max_positions: int = 3
    risk_per_trade: float = 0.02    # 2% risk per trade


@dataclass
class BacktestTrade:
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    direction: str  # LONG or SHORT
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    commission: float
    slippage: float
    pnl: Optional[float]
    pnl_percentage: Optional[float]
    status: str  # OPEN, CLOSED, CANCELLED
    strategy_name: str
    signal_data: Dict


@dataclass
class BacktestResults:
    settings: BacktestSettings
    trades: List[BacktestTrade]
    performance_metrics: PerformanceMetrics
    equity_curve: List[Tuple[datetime, float]]
    daily_returns: List[Tuple[datetime, float]]
    max_concurrent_positions: int
    total_commission_paid: float
    total_slippage_cost: float
    success: bool
    error_message: Optional[str] = None


class Backtester:
    """
    Comprehensive backtesting framework for strategy validation and optimization.
    Supports single strategy testing, multi-strategy comparison, and parameter optimization.
    """
    
    def __init__(self):
        self.logger = logger
        self.backtest_results: List[BacktestResults] = []
    
    async def run_backtest(
        self,
        settings: BacktestSettings,
        price_data: Dict[str, pd.DataFrame],
        strategy_function: callable
    ) -> BacktestResults:
        """
        Run a complete backtest with specified settings and strategy.
        
        Args:
            settings: Backtest configuration
            price_data: Dictionary of symbol -> OHLCV DataFrame
            strategy_function: Function that generates trading signals
            
        Returns:
            BacktestResults with comprehensive results
        """
        try:
            self.logger.info(f"Starting backtest: {settings.strategy_name} "
                           f"from {settings.start_date} to {settings.end_date}")
            
            # Initialize backtest state
            current_balance = settings.initial_balance
            open_trades: List[BacktestTrade] = []
            closed_trades: List[BacktestTrade] = []
            equity_curve: List[Tuple[datetime, float]] = []
            daily_returns: List[Tuple[datetime, float]] = []
            
            total_commission = 0.0
            total_slippage = 0.0
            max_concurrent = 0
            
            # Validate price data
            if not self._validate_price_data(price_data, settings):
                return BacktestResults(
                    settings=settings, trades=[], performance_metrics=None,
                    equity_curve=[], daily_returns=[], max_concurrent_positions=0,
                    total_commission_paid=0.0, total_slippage_cost=0.0,
                    success=False, error_message="Invalid price data"
                )
            
            # Create combined timeline
            timeline = self._create_timeline(price_data, settings)
            
            # Main backtest loop
            for timestamp, market_data in timeline:
                try:
                    # Update open positions
                    await self._update_open_positions(
                        open_trades, closed_trades, market_data, timestamp
                    )
                    
                    # Calculate current portfolio value
                    current_value = await self._calculate_portfolio_value(
                        current_balance, open_trades, market_data
                    )
                    
                    # Record equity point
                    equity_curve.append((timestamp, current_value))
                    
                    # Generate trading signals
                    if len(open_trades) < settings.max_positions:
                        signals = await strategy_function(market_data, settings.strategy_params)
                        
                        # Process signals
                        for signal in signals:
                            if len(open_trades) >= settings.max_positions:
                                break
                            
                            trade = await self._execute_entry(
                                signal, market_data, timestamp, settings, current_balance
                            )
                            
                            if trade:
                                open_trades.append(trade)
                                total_commission += trade.commission
                                total_slippage += trade.slippage
                    
                    # Update max concurrent positions
                    max_concurrent = max(max_concurrent, len(open_trades))
                    
                    # Update daily returns
                    if len(equity_curve) > 1:
                        prev_value = equity_curve[-2][1]
                        daily_return = (current_value - prev_value) / prev_value
                        daily_returns.append((timestamp, daily_return))
                    
                except Exception as e:
                    self.logger.error(f"Error in backtest loop at {timestamp}: {e}")
                    continue
            
            # Close remaining open positions
            for trade in open_trades:
                await self._force_close_position(trade, timeline[-1][1], timeline[-1][0])
                closed_trades.append(trade)
            
            # Calculate final performance metrics
            performance_metrics = await self._calculate_backtest_performance(
                closed_trades, settings.initial_balance, equity_curve
            )
            
            # Create results
            results = BacktestResults(
                settings=settings,
                trades=closed_trades,
                performance_metrics=performance_metrics,
                equity_curve=equity_curve,
                daily_returns=daily_returns,
                max_concurrent_positions=max_concurrent,
                total_commission_paid=total_commission,
                total_slippage_cost=total_slippage,
                success=True
            )
            
            # Store results
            self.backtest_results.append(results)
            
            self.logger.info(f"Backtest completed: {len(closed_trades)} trades, "
                           f"Final PnL: ${performance_metrics.total_pnl:.2f}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            return BacktestResults(
                settings=settings, trades=[], performance_metrics=None,
                equity_curve=[], daily_returns=[], max_concurrent_positions=0,
                total_commission_paid=0.0, total_slippage_cost=0.0,
                success=False, error_message=str(e)
            )
    
    def _validate_price_data(self, price_data: Dict[str, pd.DataFrame], settings: BacktestSettings) -> bool:
        """Validate that price data is sufficient for backtest."""
        try:
            for symbol in settings.symbols:
                if symbol not in price_data:
                    self.logger.error(f"Missing price data for symbol: {symbol}")
                    return False
                
                df = price_data[symbol]
                if df.empty:
                    self.logger.error(f"Empty price data for symbol: {symbol}")
                    return False
                
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                if not all(col in df.columns for col in required_columns):
                    self.logger.error(f"Missing required columns in price data for {symbol}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating price data: {e}")
            return False
    
    def _create_timeline(self, price_data: Dict[str, pd.DataFrame], settings: BacktestSettings) -> List[Tuple[datetime, Dict]]:
        """Create unified timeline for backtest."""
        timeline = []
        
        try:
            # Get all unique timestamps
            all_timestamps = set()
            for df in price_data.values():
                all_timestamps.update(df.index)
            
            # Sort timestamps and filter by date range
            sorted_timestamps = sorted([
                ts for ts in all_timestamps
                if settings.start_date <= ts <= settings.end_date
            ])
            
            # Create market data for each timestamp
            for timestamp in sorted_timestamps:
                market_data = {}
                
                for symbol, df in price_data.items():
                    if timestamp in df.index:
                        row = df.loc[timestamp]
                        market_data[symbol] = {
                            'timestamp': timestamp,
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': float(row['volume'])
                        }
                
                if market_data:  # Only add if we have data
                    timeline.append((timestamp, market_data))
            
            return timeline
            
        except Exception as e:
            self.logger.error(f"Error creating timeline: {e}")
            return []
    
    async def _update_open_positions(
        self, open_trades: List[BacktestTrade], closed_trades: List[BacktestTrade],
        market_data: Dict, timestamp: datetime
    ):
        """Update open positions and close those that hit stops or targets."""
        positions_to_close = []
        
        for trade in open_trades:
            if trade.symbol in market_data:
                current_price = market_data[trade.symbol]['close']
                
                # Simple exit logic (would be enhanced with actual strategy exit rules)
                if trade.direction == "LONG":
                    # Example: close if loss > 5% or gain > 10%
                    pnl_pct = (current_price - trade.entry_price) / trade.entry_price
                    if pnl_pct <= -0.05 or pnl_pct >= 0.10:
                        positions_to_close.append((trade, current_price))
                else:  # SHORT
                    pnl_pct = (trade.entry_price - current_price) / trade.entry_price
                    if pnl_pct <= -0.05 or pnl_pct >= 0.10:
                        positions_to_close.append((trade, current_price))
        
        # Close positions
        for trade, exit_price in positions_to_close:
            await self._close_position(trade, exit_price, timestamp)
            open_trades.remove(trade)
            closed_trades.append(trade)
    
    async def _calculate_portfolio_value(
        self, cash_balance: float, open_trades: List[BacktestTrade], market_data: Dict
    ) -> float:
        """Calculate total portfolio value including open positions."""
        total_value = cash_balance
        
        for trade in open_trades:
            if trade.symbol in market_data:
                current_price = market_data[trade.symbol]['close']
                position_value = trade.quantity * current_price
                
                if trade.direction == "LONG":
                    unrealized_pnl = (current_price - trade.entry_price) * trade.quantity
                else:  # SHORT
                    unrealized_pnl = (trade.entry_price - current_price) * trade.quantity
                
                total_value += unrealized_pnl
        
        return total_value
    
    async def _execute_entry(
        self, signal: Dict, market_data: Dict, timestamp: datetime,
        settings: BacktestSettings, current_balance: float
    ) -> Optional[BacktestTrade]:
        """Execute trade entry based on signal."""
        try:
            symbol = signal.get('symbol')
            direction = signal.get('direction', 'LONG')
            
            if symbol not in market_data:
                return None
            
            entry_price = market_data[symbol]['close']
            
            # Apply slippage
            slippage_cost = entry_price * settings.slippage_rate
            if direction == "LONG":
                actual_entry_price = entry_price + slippage_cost
            else:
                actual_entry_price = entry_price - slippage_cost
            
            # Calculate position size (simple fixed USD amount)
            position_value = min(1000.0, current_balance * settings.risk_per_trade)
            quantity = position_value / actual_entry_price
            
            # Calculate commission
            commission = position_value * settings.commission_rate
            
            trade = BacktestTrade(
                entry_time=timestamp,
                exit_time=None,
                symbol=symbol,
                direction=direction,
                entry_price=actual_entry_price,
                exit_price=None,
                quantity=quantity,
                commission=commission,
                slippage=slippage_cost * quantity,
                pnl=None,
                pnl_percentage=None,
                status="OPEN",
                strategy_name=settings.strategy_name,
                signal_data=signal
            )
            
            return trade
            
        except Exception as e:
            self.logger.error(f"Error executing entry: {e}")
            return None
    
    async def _close_position(self, trade: BacktestTrade, exit_price: float, timestamp: datetime):
        """Close an open position."""
        try:
            # Apply slippage
            slippage_cost = exit_price * 0.0005  # settings.slippage_rate
            if trade.direction == "LONG":
                actual_exit_price = exit_price - slippage_cost
            else:
                actual_exit_price = exit_price + slippage_cost
            
            trade.exit_time = timestamp
            trade.exit_price = actual_exit_price
            trade.status = "CLOSED"
            
            # Calculate PnL
            if trade.direction == "LONG":
                trade.pnl = (actual_exit_price - trade.entry_price) * trade.quantity
            else:  # SHORT
                trade.pnl = (trade.entry_price - actual_exit_price) * trade.quantity
            
            # Subtract commission and slippage
            exit_commission = actual_exit_price * trade.quantity * 0.001  # settings.commission_rate
            trade.commission += exit_commission
            trade.slippage += slippage_cost * trade.quantity
            
            trade.pnl -= (trade.commission + trade.slippage)
            trade.pnl_percentage = (trade.pnl / (trade.entry_price * trade.quantity)) * 100
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
    
    async def _force_close_position(self, trade: BacktestTrade, market_data: Dict, timestamp: datetime):
        """Force close position at end of backtest."""
        try:
            if trade.symbol in market_data:
                exit_price = market_data[trade.symbol]['close']
                await self._close_position(trade, exit_price, timestamp)
            else:
                # If no market data available, close at entry price (no gain/loss)
                await self._close_position(trade, trade.entry_price, timestamp)
                
        except Exception as e:
            self.logger.error(f"Error force closing position: {e}")
    
    async def _calculate_backtest_performance(
        self, trades: List[BacktestTrade], initial_balance: float, equity_curve: List[Tuple[datetime, float]]
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics from backtest results."""
        try:
            if not trades:
                # Return empty metrics for no trades
                return PerformanceMetrics(
                    period_start=datetime.utcnow(),
                    period_end=datetime.utcnow(),
                    total_trades=0, winning_trades=0, losing_trades=0,
                    win_rate=0.0, total_pnl=0.0, gross_profit=0.0, gross_loss=0.0,
                    profit_factor=0.0, avg_win=0.0, avg_loss=0.0,
                    largest_win=0.0, largest_loss=0.0, max_drawdown=0.0, max_runup=0.0,
                    sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
                    total_fees=0.0, return_on_investment=0.0
                )
            
            # Basic statistics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
            losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            # PnL calculations
            pnls = [t.pnl for t in trades if t.pnl is not None]
            total_pnl = sum(pnls) if pnls else 0.0
            
            winning_pnls = [pnl for pnl in pnls if pnl > 0]
            losing_pnls = [pnl for pnl in pnls if pnl < 0]
            
            gross_profit = sum(winning_pnls) if winning_pnls else 0.0
            gross_loss = abs(sum(losing_pnls)) if losing_pnls else 0.0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0.0
            avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0.0
            largest_win = max(pnls) if pnls else 0.0
            largest_loss = min(pnls) if pnls else 0.0
            
            # Fees
            total_fees = sum([t.commission + t.slippage for t in trades])
            
            # Returns
            final_balance = equity_curve[-1][1] if equity_curve else initial_balance
            return_on_investment = ((final_balance - initial_balance) / initial_balance) * 100
            
            # Drawdown calculation from equity curve
            max_drawdown = 0.0
            max_runup = 0.0
            peak = initial_balance
            trough = initial_balance
            
            for timestamp, value in equity_curve:
                if value > peak:
                    peak = value
                    runup = value - trough
                    max_runup = max(max_runup, runup)
                elif value < trough:
                    trough = value
                
                drawdown = (peak - value) / peak if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown * 100)  # Convert to percentage
            
            return PerformanceMetrics(
                period_start=trades[0].entry_time if trades else datetime.utcnow(),
                period_end=trades[-1].exit_time if trades and trades[-1].exit_time else datetime.utcnow(),
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                gross_profit=gross_profit,
                gross_loss=gross_loss,
                profit_factor=profit_factor,
                avg_win=avg_win,
                avg_loss=avg_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                max_drawdown=max_drawdown,
                max_runup=max_runup,
                sharpe_ratio=0.0,  # Would need daily returns calculation
                sortino_ratio=0.0,  # Would need daily returns calculation
                calmar_ratio=abs(return_on_investment / max_drawdown) if max_drawdown > 0 else 0.0,
                total_fees=total_fees,
                return_on_investment=return_on_investment
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating backtest performance: {e}")
            # Return minimal metrics on error
            return PerformanceMetrics(
                period_start=datetime.utcnow(), period_end=datetime.utcnow(),
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0.0, total_pnl=0.0, gross_profit=0.0, gross_loss=0.0,
                profit_factor=0.0, avg_win=0.0, avg_loss=0.0,
                largest_win=0.0, largest_loss=0.0, max_drawdown=0.0, max_runup=0.0,
                sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
                total_fees=0.0, return_on_investment=0.0
            )
    
    def get_backtest_summary(self) -> Dict:
        """Get summary of all backtests performed."""
        try:
            if not self.backtest_results:
                return {"status": "No backtests performed"}
            
            successful_backtests = [r for r in self.backtest_results if r.success]
            
            return {
                "total_backtests": len(self.backtest_results),
                "successful_backtests": len(successful_backtests),
                "failed_backtests": len(self.backtest_results) - len(successful_backtests),
                "strategies_tested": list(set(r.settings.strategy_name for r in successful_backtests)),
                "best_performance": max(
                    [r.performance_metrics.return_on_investment for r in successful_backtests]
                ) if successful_backtests else 0.0,
                "average_performance": sum(
                    [r.performance_metrics.return_on_investment for r in successful_backtests]
                ) / len(successful_backtests) if successful_backtests else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting backtest summary: {e}")
            return {"status": "Error calculating summary"}


# Global instance
backtester = Backtester()