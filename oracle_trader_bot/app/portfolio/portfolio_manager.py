# app/portfolio/portfolio_manager.py
import logging
import math
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings


logger = logging.getLogger(__name__)


class PositionSizeMode(str, Enum):
    FIXED_USD = "FIXED_USD"
    PERCENTAGE_BALANCE = "PERCENTAGE_BALANCE"
    VOLATILITY_ADJUSTED = "VOLATILITY_ADJUSTED"
    RISK_PARITY = "RISK_PARITY"


@dataclass
class PositionSizeResult:
    size_usd: float
    size_base: float
    leverage: int
    margin_required: float
    risk_percentage: float
    reason: str


@dataclass
class PortfolioMetrics:
    total_balance: float
    available_balance: float
    used_margin: float
    open_positions: int
    daily_pnl: float
    total_pnl: float
    max_drawdown: float
    risk_exposure: float


class PortfolioManager:
    """
    Manages portfolio-wide position sizing, risk allocation, and performance tracking.
    Integrates with existing bot settings and risk management systems.
    """
    
    def __init__(self):
        self.logger = logger
        self._portfolio_metrics: Optional[PortfolioMetrics] = None
        
    async def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        market_volatility: float,
        strategy_signal_strength: float,
        account_balance: float,
        current_positions: int,
        max_positions: int,
        risk_tolerance: float = 0.02  # 2% risk per trade
    ) -> PositionSizeResult:
        """
        Calculate optimal position size based on multiple factors.
        
        Args:
            symbol: Trading symbol
            entry_price: Planned entry price
            market_volatility: Current market volatility (ATR or similar)
            strategy_signal_strength: Signal strength (0.0 to 1.0)
            account_balance: Available account balance
            current_positions: Number of current open positions
            max_positions: Maximum allowed concurrent positions
            risk_tolerance: Risk per trade as percentage of balance
            
        Returns:
            PositionSizeResult with calculated size and metadata
        """
        try:
            # Base position size calculation
            base_size_usd = await self._calculate_base_size(
                account_balance, current_positions, max_positions
            )
            
            # Apply volatility adjustment
            volatility_adjustment = await self._calculate_volatility_adjustment(
                market_volatility, symbol
            )
            
            # Apply signal strength multiplier
            signal_multiplier = await self._calculate_signal_multiplier(
                strategy_signal_strength
            )
            
            # Calculate final size
            adjusted_size_usd = base_size_usd * volatility_adjustment * signal_multiplier
            
            # Ensure size doesn't exceed risk limits
            max_risk_size = account_balance * risk_tolerance
            final_size_usd = min(adjusted_size_usd, max_risk_size)
            
            # Calculate leverage based on size and signal strength
            leverage = await self._calculate_optimal_leverage(
                strategy_signal_strength, market_volatility
            )
            
            # Convert to base currency size
            size_base = final_size_usd / entry_price
            margin_required = final_size_usd / leverage
            
            # Calculate risk percentage
            risk_percentage = (final_size_usd / account_balance) * 100
            
            reason = f"Base: ${base_size_usd:.2f}, Vol: {volatility_adjustment:.2f}x, Signal: {signal_multiplier:.2f}x"
            
            result = PositionSizeResult(
                size_usd=final_size_usd,
                size_base=size_base,
                leverage=leverage,
                margin_required=margin_required,
                risk_percentage=risk_percentage,
                reason=reason
            )
            
            self.logger.info(f"Position size calculated for {symbol}: ${final_size_usd:.2f} "
                           f"({risk_percentage:.2f}% risk) with {leverage}x leverage")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating position size for {symbol}: {e}")
            # Return conservative fallback
            fallback_size = min(settings.FIXED_USD_AMOUNT_PER_TRADE, account_balance * 0.01)
            return PositionSizeResult(
                size_usd=fallback_size,
                size_base=fallback_size / entry_price,
                leverage=settings.BOT_DEFAULT_LEVERAGE,
                margin_required=fallback_size / settings.BOT_DEFAULT_LEVERAGE,
                risk_percentage=(fallback_size / account_balance) * 100,
                reason="Fallback due to calculation error"
            )
    
    async def _calculate_base_size(
        self, account_balance: float, current_positions: int, max_positions: int
    ) -> float:
        """Calculate base position size considering position limits."""
        # Reduce size as we approach position limits
        position_factor = 1.0 - (current_positions / max_positions) * 0.3
        
        # Base size from settings
        base_size = settings.FIXED_USD_AMOUNT_PER_TRADE * position_factor
        
        # Ensure we don't exceed reasonable balance percentage
        max_base_size = account_balance * 0.1  # Max 10% per position
        
        return min(base_size, max_base_size)
    
    async def _calculate_volatility_adjustment(
        self, market_volatility: float, symbol: str
    ) -> float:
        """Adjust position size based on market volatility."""
        # Normalize volatility (assuming ATR as percentage)
        normalized_vol = min(market_volatility, 0.1)  # Cap at 10%
        
        # Inverse relationship: higher volatility = smaller position
        # Scale from 0.5x to 1.5x based on volatility
        volatility_factor = 1.5 - (normalized_vol / 0.1)
        
        return max(0.5, min(1.5, volatility_factor))
    
    async def _calculate_signal_multiplier(self, signal_strength: float) -> float:
        """Calculate position size multiplier based on signal strength."""
        # Scale signal strength (0.0 to 1.0) to multiplier (0.5 to 1.5)
        multiplier = 0.5 + signal_strength
        return max(0.5, min(1.5, multiplier))
    
    async def _calculate_optimal_leverage(
        self, signal_strength: float, market_volatility: float
    ) -> int:
        """Calculate optimal leverage based on signal strength and volatility."""
        # Base leverage from settings
        base_leverage = settings.BOT_DEFAULT_LEVERAGE
        
        # Adjust based on signal strength (stronger signal = higher leverage)
        signal_adjustment = 1.0 + (signal_strength - 0.5) * 0.5
        
        # Adjust based on volatility (higher volatility = lower leverage)
        volatility_adjustment = 1.0 - min(market_volatility, 0.05) * 10
        
        adjusted_leverage = base_leverage * signal_adjustment * volatility_adjustment
        
        # Clamp to reasonable range
        return max(1, min(20, int(adjusted_leverage)))
    
    async def check_correlation_limits(
        self, new_symbol: str, existing_positions: List[Dict]
    ) -> Tuple[bool, str]:
        """
        Check if new position would violate correlation limits.
        
        Args:
            new_symbol: Symbol for new position
            existing_positions: List of existing position data
            
        Returns:
            Tuple of (allowed, reason)
        """
        try:
            # Simple correlation check based on symbol similarity
            correlation_threshold = 0.7
            max_correlated_positions = 2
            
            correlated_count = 0
            
            for position in existing_positions:
                correlation = await self._calculate_symbol_correlation(
                    new_symbol, position.get('symbol', '')
                )
                
                if correlation > correlation_threshold:
                    correlated_count += 1
            
            if correlated_count >= max_correlated_positions:
                return False, f"Too many correlated positions ({correlated_count})"
            
            return True, "Correlation check passed"
            
        except Exception as e:
            self.logger.error(f"Error checking correlation limits: {e}")
            return True, "Correlation check failed - allowing trade"
    
    async def _calculate_symbol_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate simple correlation between two symbols."""
        # Simple heuristic-based correlation
        if symbol1 == symbol2:
            return 1.0
        
        # Extract base currencies
        base1 = symbol1.split('/')[0] if '/' in symbol1 else symbol1[:3]
        base2 = symbol2.split('/')[0] if '/' in symbol2 else symbol2[:3]
        
        # High correlation for same base currency
        if base1 == base2:
            return 0.9
        
        # Medium correlation for related crypto pairs
        crypto_groups = [
            ['BTC', 'ETH'],  # Major cryptos
            ['BNB', 'MATIC', 'ADA'],  # Alt coins
            ['USDT', 'USDC', 'BUSD']  # Stablecoins
        ]
        
        for group in crypto_groups:
            if base1 in group and base2 in group:
                return 0.6
        
        # Low correlation otherwise
        return 0.2
    
    async def update_portfolio_metrics(
        self, balance_data: Dict, positions_data: List[Dict]
    ) -> PortfolioMetrics:
        """Update and return current portfolio metrics."""
        try:
            total_balance = balance_data.get('total', 0.0)
            available_balance = balance_data.get('free', 0.0)
            used_margin = balance_data.get('used', 0.0)
            
            # Calculate daily PnL from positions
            daily_pnl = sum(pos.get('unrealizedPnl', 0.0) for pos in positions_data)
            
            # Calculate risk exposure
            total_position_value = sum(
                abs(pos.get('contracts', 0.0) * pos.get('markPrice', 0.0))
                for pos in positions_data
            )
            risk_exposure = (total_position_value / total_balance) if total_balance > 0 else 0.0
            
            self._portfolio_metrics = PortfolioMetrics(
                total_balance=total_balance,
                available_balance=available_balance,
                used_margin=used_margin,
                open_positions=len(positions_data),
                daily_pnl=daily_pnl,
                total_pnl=0.0,  # Would need historical data
                max_drawdown=0.0,  # Would need historical data
                risk_exposure=risk_exposure
            )
            
            return self._portfolio_metrics
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio metrics: {e}")
            return PortfolioMetrics(
                total_balance=0.0, available_balance=0.0, used_margin=0.0,
                open_positions=0, daily_pnl=0.0, total_pnl=0.0,
                max_drawdown=0.0, risk_exposure=0.0
            )
    
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio summary."""
        if not self._portfolio_metrics:
            return {"status": "No metrics available"}
        
        metrics = self._portfolio_metrics
        return {
            "total_balance": metrics.total_balance,
            "available_balance": metrics.available_balance,
            "used_margin": metrics.used_margin,
            "margin_usage_percent": (metrics.used_margin / metrics.total_balance * 100) if metrics.total_balance > 0 else 0,
            "open_positions": metrics.open_positions,
            "daily_pnl": metrics.daily_pnl,
            "risk_exposure_percent": metrics.risk_exposure * 100,
            "status": "healthy" if metrics.risk_exposure < 0.8 else "high_risk"
        }


# Global instance
portfolio_manager = PortfolioManager()