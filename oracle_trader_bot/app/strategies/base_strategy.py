# app/strategies/base_strategy.py
"""Base strategy interface for all trading strategies."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime, timezone

from app.schemas.trading_signal import TradingSignal
from app.schemas.market_regime_schemas import MarketRegimeInfo


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.performance_metrics = {
            'signals_generated': 0,
            'trades_opened': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_trade_duration': 0,
            'last_signal_time': None,
            'creation_time': datetime.now(timezone.utc)
        }
        self.is_active = True
    
    @abstractmethod
    def generate_signal(
        self,
        symbol: str,
        df_with_indicators: pd.DataFrame,
        market_regime_info: MarketRegimeInfo,
        current_open_positions: List[str],
        **kwargs
    ) -> Optional[TradingSignal]:
        """
        Generate a trading signal based on the strategy logic.
        
        Args:
            symbol: Trading symbol
            df_with_indicators: DataFrame with technical indicators
            market_regime_info: Current market regime information
            current_open_positions: List of symbols with open positions
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            TradingSignal if conditions are met, None otherwise
        """
        pass
    
    @abstractmethod
    def validate_market_conditions(
        self,
        market_regime_info: MarketRegimeInfo,
        df_with_indicators: pd.DataFrame
    ) -> bool:
        """
        Validate if current market conditions are suitable for this strategy.
        
        Args:
            market_regime_info: Current market regime
            df_with_indicators: DataFrame with indicators
            
        Returns:
            True if conditions are suitable, False otherwise
        """
        pass
    
    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """
        Get list of required technical indicators for this strategy.
        
        Returns:
            List of required indicator names
        """
        pass
    
    @abstractmethod
    def get_minimum_data_points(self) -> int:
        """
        Get minimum number of data points required for strategy execution.
        
        Returns:
            Minimum number of candles needed
        """
        pass
    
    def update_performance(self, trade_result: Dict[str, Any]):
        """
        Update strategy performance metrics.
        
        Args:
            trade_result: Dictionary containing trade outcome information
        """
        self.performance_metrics['trades_opened'] += 1
        
        if trade_result.get('pnl', 0) > 0:
            self.performance_metrics['winning_trades'] += 1
        elif trade_result.get('pnl', 0) < 0:
            self.performance_metrics['losing_trades'] += 1
        
        self.performance_metrics['total_pnl'] += trade_result.get('pnl', 0)
        
        # Update win rate
        total_closed_trades = self.performance_metrics['winning_trades'] + self.performance_metrics['losing_trades']
        if total_closed_trades > 0:
            self.performance_metrics['win_rate'] = self.performance_metrics['winning_trades'] / total_closed_trades
    
    def record_signal_generation(self):
        """Record that a signal was generated."""
        self.performance_metrics['signals_generated'] += 1
        self.performance_metrics['last_signal_time'] = datetime.now(timezone.utc)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get strategy performance summary.
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            'strategy_name': self.name,
            'is_active': self.is_active,
            'performance': self.performance_metrics.copy(),
            'config': self.config.copy(),
            'uptime_hours': (datetime.now(timezone.utc) - self.performance_metrics['creation_time']).total_seconds() / 3600
        }
    
    def reset_performance(self):
        """Reset performance metrics."""
        self.performance_metrics = {
            'signals_generated': 0,
            'trades_opened': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_trade_duration': 0,
            'last_signal_time': None,
            'creation_time': datetime.now(timezone.utc)
        }
    
    def activate(self):
        """Activate the strategy."""
        self.is_active = True
    
    def deactivate(self):
        """Deactivate the strategy."""
        self.is_active = False
    
    def update_config(self, new_config: Dict[str, Any]):
        """
        Update strategy configuration.
        
        Args:
            new_config: New configuration parameters
        """
        self.config.update(new_config)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get basic strategy information.
        
        Returns:
            Dictionary with strategy info
        """
        return {
            'name': self.name,
            'is_active': self.is_active,
            'required_indicators': self.get_required_indicators(),
            'minimum_data_points': self.get_minimum_data_points(),
            'config': self.config.copy()
        }
    
    def calculate_position_size(
        self,
        signal: TradingSignal,
        account_balance: float,
        risk_per_trade: float = 0.02
    ) -> float:
        """
        Calculate position size based on risk management.
        
        Args:
            signal: Trading signal
            account_balance: Current account balance
            risk_per_trade: Risk percentage per trade (default 2%)
            
        Returns:
            Suggested position size
        """
        if not signal.stop_loss or not signal.entry_price:
            return 0.0
        
        # Calculate risk per unit
        risk_per_unit = abs(signal.entry_price - signal.stop_loss)
        if risk_per_unit == 0:
            return 0.0
        
        # Calculate position size
        risk_amount = account_balance * risk_per_trade
        position_size = risk_amount / risk_per_unit
        
        return position_size
    
    def validate_signal(self, signal: TradingSignal) -> bool:
        """
        Validate a generated signal for basic sanity checks.
        
        Args:
            signal: Trading signal to validate
            
        Returns:
            True if signal is valid, False otherwise
        """
        if not signal:
            return False
        
        # Basic validation
        if not signal.entry_price or signal.entry_price <= 0:
            return False
        
        if not signal.stop_loss or signal.stop_loss <= 0:
            return False
        
        if not signal.take_profit or signal.take_profit <= 0:
            return False
        
        # Validate risk/reward ratio
        if signal.direction.value.upper() == 'LONG':
            risk = signal.entry_price - signal.stop_loss
            reward = signal.take_profit - signal.entry_price
        else:  # SHORT
            risk = signal.stop_loss - signal.entry_price
            reward = signal.entry_price - signal.take_profit
        
        if risk <= 0 or reward <= 0:
            return False
        
        # Minimum risk/reward ratio of 1:1
        if reward / risk < 1.0:
            return False
        
        return True


class StrategyManager:
    """Manages multiple trading strategies."""
    
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.strategy_rankings = {}
    
    def register_strategy(self, strategy: BaseStrategy):
        """
        Register a new strategy.
        
        Args:
            strategy: Strategy instance to register
        """
        self.strategies[strategy.name] = strategy
    
    def unregister_strategy(self, strategy_name: str):
        """
        Unregister a strategy.
        
        Args:
            strategy_name: Name of strategy to unregister
        """
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
    
    def get_active_strategies(self) -> List[BaseStrategy]:
        """Get list of active strategies."""
        return [strategy for strategy in self.strategies.values() if strategy.is_active]
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Get strategy by name."""
        return self.strategies.get(name)
    
    def get_best_strategy_for_market(
        self,
        market_regime_info: MarketRegimeInfo,
        df_with_indicators: pd.DataFrame
    ) -> Optional[BaseStrategy]:
        """
        Get the best strategy for current market conditions.
        
        Args:
            market_regime_info: Current market regime
            df_with_indicators: DataFrame with indicators
            
        Returns:
            Best strategy for conditions, None if none suitable
        """
        suitable_strategies = []
        
        for strategy in self.get_active_strategies():
            if strategy.validate_market_conditions(market_regime_info, df_with_indicators):
                suitable_strategies.append(strategy)
        
        if not suitable_strategies:
            return None
        
        # Rank strategies by performance
        ranked_strategies = sorted(
            suitable_strategies,
            key=lambda s: s.performance_metrics['win_rate'],
            reverse=True
        )
        
        return ranked_strategies[0]
    
    def get_all_strategies_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance summary for all strategies."""
        return {
            name: strategy.get_performance_summary()
            for name, strategy in self.strategies.items()
        }
    
    def reset_all_performance(self):
        """Reset performance metrics for all strategies."""
        for strategy in self.strategies.values():
            strategy.reset_performance()
    
    def update_strategy_rankings(self):
        """Update strategy rankings based on performance."""
        strategies_with_trades = [
            (name, strategy) for name, strategy in self.strategies.items()
            if strategy.performance_metrics['trades_opened'] > 0
        ]
        
        # Rank by win rate, then by total PnL
        ranked = sorted(
            strategies_with_trades,
            key=lambda x: (x[1].performance_metrics['win_rate'], x[1].performance_metrics['total_pnl']),
            reverse=True
        )
        
        self.strategy_rankings = {
            name: rank + 1 for rank, (name, _) in enumerate(ranked)
        }
    
    def get_strategy_rankings(self) -> Dict[str, int]:
        """Get current strategy rankings."""
        return self.strategy_rankings.copy()