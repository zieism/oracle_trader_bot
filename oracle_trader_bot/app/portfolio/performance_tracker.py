# app/portfolio/performance_tracker.py
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics

from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    period_start: datetime
    period_end: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    max_drawdown: float
    max_runup: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    total_fees: float
    return_on_investment: float


@dataclass
class DailyPerformance:
    date: datetime
    starting_balance: float
    ending_balance: float
    daily_pnl: float
    daily_return: float
    trades_count: int
    fees_paid: float
    max_balance: float
    min_balance: float


@dataclass
class StrategyPerformance:
    strategy_name: str
    trades_count: int
    win_rate: float
    total_pnl: float
    avg_pnl_per_trade: float
    profit_factor: float
    max_drawdown: float


class PerformanceTracker:
    """
    Tracks and analyzes trading performance with comprehensive metrics.
    Provides real-time performance monitoring and historical analysis.
    """
    
    def __init__(self):
        self.logger = logger
        self.daily_performance: List[DailyPerformance] = []
        self.trade_history: List[Dict] = []
        self.balance_history: List[Tuple[datetime, float]] = []
        self.current_balance: float = 0.0
        self.peak_balance: float = 0.0
        self.starting_balance: Optional[float] = None
        
    async def initialize_tracking(self, initial_balance: float):
        """Initialize performance tracking with starting balance."""
        self.starting_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        
        # Add initial balance point
        self.balance_history.append((datetime.utcnow(), initial_balance))
        
        self.logger.info(f"Performance tracking initialized with balance: ${initial_balance:.2f}")
    
    async def update_balance(self, new_balance: float):
        """Update current balance and track performance."""
        if new_balance <= 0:
            return
        
        self.current_balance = new_balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
        
        # Record balance point
        self.balance_history.append((datetime.utcnow(), new_balance))
        
        # Limit balance history to prevent memory issues
        if len(self.balance_history) > 10000:
            self.balance_history = self.balance_history[-5000:]
    
    async def record_trade(self, trade_data: Dict):
        """Record a completed trade for performance analysis."""
        try:
            # Validate required fields
            required_fields = ['pnl', 'entry_price', 'exit_price', 'quantity', 'direction', 'timestamp_closed']
            if not all(field in trade_data for field in required_fields):
                self.logger.warning("Trade data missing required fields for performance tracking")
                return
            
            # Enhance trade data with calculated metrics
            enhanced_trade = trade_data.copy()
            enhanced_trade['return_percentage'] = self._calculate_trade_return(trade_data)
            enhanced_trade['duration_minutes'] = self._calculate_trade_duration(trade_data)
            enhanced_trade['recorded_at'] = datetime.utcnow()
            
            self.trade_history.append(enhanced_trade)
            
            # Limit trade history size
            if len(self.trade_history) > 5000:
                self.trade_history = self.trade_history[-2500:]
            
            self.logger.info(f"Trade recorded: {trade_data.get('symbol')} "
                           f"PnL: ${trade_data.get('pnl', 0):.2f}")
            
        except Exception as e:
            self.logger.error(f"Error recording trade for performance tracking: {e}")
    
    def _calculate_trade_return(self, trade_data: Dict) -> float:
        """Calculate trade return percentage."""
        try:
            entry_price = trade_data.get('entry_price', 0)
            exit_price = trade_data.get('exit_price', 0)
            direction = trade_data.get('direction', 'LONG')
            
            if entry_price <= 0:
                return 0.0
            
            if direction.upper() == 'LONG':
                return ((exit_price - entry_price) / entry_price) * 100
            else:  # SHORT
                return ((entry_price - exit_price) / entry_price) * 100
                
        except Exception:
            return 0.0
    
    def _calculate_trade_duration(self, trade_data: Dict) -> float:
        """Calculate trade duration in minutes."""
        try:
            start_time = trade_data.get('timestamp_opened')
            end_time = trade_data.get('timestamp_closed')
            
            if start_time and end_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                
                duration = end_time - start_time
                return duration.total_seconds() / 60
            
            return 0.0
            
        except Exception:
            return 0.0
    
    async def calculate_performance_metrics(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics for specified period."""
        try:
            # Filter trades by date if specified
            if start_date or end_date:
                filtered_trades = []
                for trade in self.trade_history:
                    trade_date = trade.get('timestamp_closed')
                    if isinstance(trade_date, str):
                        trade_date = datetime.fromisoformat(trade_date.replace('Z', '+00:00'))
                    
                    if start_date and trade_date < start_date:
                        continue
                    if end_date and trade_date > end_date:
                        continue
                    
                    filtered_trades.append(trade)
            else:
                filtered_trades = self.trade_history
                start_date = datetime.utcnow() - timedelta(days=30)  # Default to last 30 days
                end_date = datetime.utcnow()
            
            if not filtered_trades:
                return self._empty_performance_metrics(start_date, end_date)
            
            # Basic trade statistics
            total_trades = len(filtered_trades)
            pnls = [trade.get('pnl', 0) for trade in filtered_trades]
            winning_trades = len([pnl for pnl in pnls if pnl > 0])
            losing_trades = len([pnl for pnl in pnls if pnl < 0])
            
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            # PnL calculations
            total_pnl = sum(pnls)
            gross_profit = sum([pnl for pnl in pnls if pnl > 0])
            gross_loss = abs(sum([pnl for pnl in pnls if pnl < 0]))
            
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Average calculations
            winning_pnls = [pnl for pnl in pnls if pnl > 0]
            losing_pnls = [pnl for pnl in pnls if pnl < 0]
            
            avg_win = statistics.mean(winning_pnls) if winning_pnls else 0
            avg_loss = statistics.mean(losing_pnls) if losing_pnls else 0
            largest_win = max(pnls) if pnls else 0
            largest_loss = min(pnls) if pnls else 0
            
            # Risk metrics
            max_drawdown = await self._calculate_max_drawdown(filtered_trades)
            max_runup = await self._calculate_max_runup(filtered_trades)
            
            # Advanced ratios
            sharpe_ratio = await self._calculate_sharpe_ratio(pnls)
            sortino_ratio = await self._calculate_sortino_ratio(pnls)
            calmar_ratio = abs(total_pnl / max_drawdown) if max_drawdown != 0 else 0
            
            # Total fees
            total_fees = sum([
                trade.get('entry_fee', 0) + trade.get('exit_fee', 0)
                for trade in filtered_trades
            ])
            
            # ROI calculation
            initial_balance = self.starting_balance or 10000  # Fallback
            return_on_investment = (total_pnl / initial_balance) * 100 if initial_balance > 0 else 0
            
            return PerformanceMetrics(
                period_start=start_date,
                period_end=end_date,
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
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                total_fees=total_fees,
                return_on_investment=return_on_investment
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return self._empty_performance_metrics(start_date or datetime.utcnow(), end_date or datetime.utcnow())
    
    def _empty_performance_metrics(self, start_date: datetime, end_date: datetime) -> PerformanceMetrics:
        """Return empty performance metrics structure."""
        return PerformanceMetrics(
            period_start=start_date,
            period_end=end_date,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            profit_factor=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            max_drawdown=0.0,
            max_runup=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            total_fees=0.0,
            return_on_investment=0.0
        )
    
    async def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """Calculate maximum drawdown from trade sequence."""
        if not trades:
            return 0.0
        
        try:
            # Create cumulative PnL series
            cumulative_pnl = 0
            peak = 0
            max_dd = 0
            
            for trade in sorted(trades, key=lambda x: x.get('timestamp_closed', datetime.min)):
                cumulative_pnl += trade.get('pnl', 0)
                
                if cumulative_pnl > peak:
                    peak = cumulative_pnl
                
                drawdown = peak - cumulative_pnl
                if drawdown > max_dd:
                    max_dd = drawdown
            
            return max_dd
            
        except Exception as e:
            self.logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    async def _calculate_max_runup(self, trades: List[Dict]) -> float:
        """Calculate maximum runup from trade sequence."""
        if not trades:
            return 0.0
        
        try:
            cumulative_pnl = 0
            trough = 0
            max_runup = 0
            
            for trade in sorted(trades, key=lambda x: x.get('timestamp_closed', datetime.min)):
                cumulative_pnl += trade.get('pnl', 0)
                
                if cumulative_pnl < trough:
                    trough = cumulative_pnl
                
                runup = cumulative_pnl - trough
                if runup > max_runup:
                    max_runup = runup
            
            return max_runup
            
        except Exception as e:
            self.logger.error(f"Error calculating max runup: {e}")
            return 0.0
    
    async def _calculate_sharpe_ratio(self, pnls: List[float]) -> float:
        """Calculate Sharpe ratio from PnL series."""
        if len(pnls) < 2:
            return 0.0
        
        try:
            mean_return = statistics.mean(pnls)
            return_std = statistics.stdev(pnls)
            
            if return_std == 0:
                return 0.0
            
            # Assuming risk-free rate of 0 for simplicity
            return mean_return / return_std
            
        except Exception:
            return 0.0
    
    async def _calculate_sortino_ratio(self, pnls: List[float]) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if len(pnls) < 2:
            return 0.0
        
        try:
            mean_return = statistics.mean(pnls)
            negative_returns = [pnl for pnl in pnls if pnl < 0]
            
            if not negative_returns:
                return float('inf')
            
            downside_std = statistics.stdev(negative_returns)
            return mean_return / downside_std if downside_std > 0 else 0.0
            
        except Exception:
            return 0.0
    
    async def analyze_strategy_performance(self) -> List[StrategyPerformance]:
        """Analyze performance by trading strategy."""
        try:
            strategy_stats = defaultdict(list)
            
            # Group trades by strategy
            for trade in self.trade_history:
                strategy = trade.get('strategy_name', 'Unknown')
                strategy_stats[strategy].append(trade)
            
            strategy_performances = []
            
            for strategy_name, trades in strategy_stats.items():
                if not trades:
                    continue
                
                pnls = [trade.get('pnl', 0) for trade in trades]
                winning_trades = len([pnl for pnl in pnls if pnl > 0])
                
                total_pnl = sum(pnls)
                win_rate = (winning_trades / len(trades)) * 100
                avg_pnl = total_pnl / len(trades)
                
                gross_profit = sum([pnl for pnl in pnls if pnl > 0])
                gross_loss = abs(sum([pnl for pnl in pnls if pnl < 0]))
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                
                max_drawdown = await self._calculate_max_drawdown(trades)
                
                strategy_performances.append(StrategyPerformance(
                    strategy_name=strategy_name,
                    trades_count=len(trades),
                    win_rate=win_rate,
                    total_pnl=total_pnl,
                    avg_pnl_per_trade=avg_pnl,
                    profit_factor=profit_factor,
                    max_drawdown=max_drawdown
                ))
            
            return sorted(strategy_performances, key=lambda x: x.total_pnl, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error analyzing strategy performance: {e}")
            return []
    
    def get_daily_performance(self, days: int = 30) -> List[Dict]:
        """Get daily performance for the last N days."""
        try:
            # Group trades by day
            daily_trades = defaultdict(list)
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            for trade in self.trade_history:
                trade_date = trade.get('timestamp_closed')
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date.replace('Z', '+00:00'))
                
                if trade_date and trade_date >= cutoff_date:
                    day_key = trade_date.date()
                    daily_trades[day_key].append(trade)
            
            daily_performance = []
            
            for date, trades in sorted(daily_trades.items()):
                daily_pnl = sum([trade.get('pnl', 0) for trade in trades])
                total_fees = sum([
                    trade.get('entry_fee', 0) + trade.get('exit_fee', 0)
                    for trade in trades
                ])
                
                daily_performance.append({
                    'date': date.isoformat(),
                    'trades_count': len(trades),
                    'daily_pnl': daily_pnl,
                    'fees_paid': total_fees,
                    'net_pnl': daily_pnl - total_fees
                })
            
            return daily_performance
            
        except Exception as e:
            self.logger.error(f"Error getting daily performance: {e}")
            return []
    
    def get_performance_summary(self) -> Dict:
        """Get current performance summary."""
        try:
            if not self.trade_history:
                return {
                    "status": "No trades recorded",
                    "current_balance": self.current_balance,
                    "starting_balance": self.starting_balance
                }
            
            # Calculate recent performance (last 7 days)
            recent_trades = []
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            for trade in self.trade_history:
                trade_date = trade.get('timestamp_closed')
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date.replace('Z', '+00:00'))
                
                if trade_date and trade_date >= cutoff_date:
                    recent_trades.append(trade)
            
            recent_pnl = sum([trade.get('pnl', 0) for trade in recent_trades])
            total_pnl = sum([trade.get('pnl', 0) for trade in self.trade_history])
            
            # Current drawdown
            current_drawdown = self.peak_balance - self.current_balance
            
            return {
                "current_balance": self.current_balance,
                "starting_balance": self.starting_balance,
                "peak_balance": self.peak_balance,
                "total_pnl": total_pnl,
                "recent_pnl_7d": recent_pnl,
                "current_drawdown": current_drawdown,
                "total_trades": len(self.trade_history),
                "recent_trades_7d": len(recent_trades),
                "roi_percent": ((self.current_balance - self.starting_balance) / self.starting_balance * 100) if self.starting_balance else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance summary: {e}")
            return {"status": "Error calculating performance"}


# Global instance
performance_tracker = PerformanceTracker()