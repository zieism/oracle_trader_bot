# tests/unit/test_portfolio_manager.py
import pytest
import asyncio
from datetime import datetime

from app.portfolio.portfolio_manager import portfolio_manager, PositionSizeMode, PositionSizeResult


class TestPortfolioManager:
    """Unit tests for Portfolio Manager."""
    
    @pytest.mark.asyncio
    async def test_calculate_position_size_basic(self):
        """Test basic position size calculation."""
        result = await portfolio_manager.calculate_position_size(
            symbol="BTC/USDT:USDT",
            entry_price=50000.0,
            market_volatility=0.03,
            strategy_signal_strength=0.7,
            account_balance=10000.0,
            current_positions=1,
            max_positions=3,
            risk_tolerance=0.02
        )
        
        assert isinstance(result, PositionSizeResult)
        assert result.size_usd > 0
        assert result.size_base > 0
        assert result.leverage > 0
        assert result.margin_required > 0
        assert result.risk_percentage <= 2.0  # Should respect risk tolerance
    
    @pytest.mark.asyncio
    async def test_calculate_position_size_high_volatility(self):
        """Test position size calculation with high volatility."""
        result = await portfolio_manager.calculate_position_size(
            symbol="BTC/USDT:USDT",
            entry_price=50000.0,
            market_volatility=0.15,  # High volatility
            strategy_signal_strength=0.5,
            account_balance=10000.0,
            current_positions=0,
            max_positions=3
        )
        
        # Should reduce position size due to high volatility
        assert result.size_usd > 0
        assert result.reason is not None
    
    @pytest.mark.asyncio
    async def test_calculate_position_size_max_positions(self):
        """Test position size calculation near max positions."""
        result = await portfolio_manager.calculate_position_size(
            symbol="BTC/USDT:USDT",
            entry_price=50000.0,
            market_volatility=0.03,
            strategy_signal_strength=0.7,
            account_balance=10000.0,
            current_positions=2,  # Near max
            max_positions=3
        )
        
        # Should reduce size as we approach max positions
        assert result.size_usd > 0
        assert result.size_usd <= 10000.0 * 0.1  # Max 10% per position
    
    @pytest.mark.asyncio
    async def test_check_correlation_limits(self):
        """Test position correlation checking."""
        existing_positions = [
            {"symbol": "BTC/USDT:USDT"},
            {"symbol": "ETH/USDT:USDT"}
        ]
        
        # Test adding correlated position (same base currency)
        allowed, reason = await portfolio_manager.check_correlation_limits(
            "BTC/BUSD:BUSD", existing_positions
        )
        
        assert isinstance(allowed, bool)
        assert isinstance(reason, str)
    
    @pytest.mark.asyncio
    async def test_update_portfolio_metrics(self):
        """Test portfolio metrics calculation."""
        balance_data = {
            "total": 10000.0,
            "free": 8000.0,
            "used": 2000.0
        }
        
        positions_data = [
            {"contracts": 0.1, "markPrice": 50000.0, "unrealizedPnl": 100.0},
            {"contracts": 0.05, "markPrice": 3000.0, "unrealizedPnl": -50.0}
        ]
        
        metrics = await portfolio_manager.update_portfolio_metrics(
            balance_data, positions_data
        )
        
        assert metrics.total_balance == 10000.0
        assert metrics.available_balance == 8000.0
        assert metrics.used_margin == 2000.0
        assert metrics.open_positions == 2
        assert metrics.daily_pnl == 50.0  # 100 - 50
    
    def test_get_portfolio_summary(self):
        """Test portfolio summary generation."""
        summary = portfolio_manager.get_portfolio_summary()
        
        assert isinstance(summary, dict)
        assert "status" in summary


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(pytest.main([__file__, "-v"]))