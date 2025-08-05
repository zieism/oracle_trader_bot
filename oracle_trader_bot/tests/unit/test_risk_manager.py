# tests/unit/test_risk_manager.py
import pytest
import asyncio
from datetime import datetime

from app.portfolio.risk_manager import risk_manager, RiskLevel, RiskEvent


class TestRiskManager:
    """Unit tests for Risk Manager."""
    
    @pytest.mark.asyncio
    async def test_initialize_daily_tracking(self):
        """Test daily tracking initialization."""
        await risk_manager.initialize_daily_tracking(10000.0)
        
        assert risk_manager.daily_start_balance == 10000.0
        assert risk_manager.daily_start_time is not None
        assert isinstance(risk_manager.daily_start_time, datetime)
    
    @pytest.mark.asyncio
    async def test_check_daily_loss_limit_normal(self):
        """Test daily loss limit checking under normal conditions."""
        await risk_manager.initialize_daily_tracking(10000.0)
        
        # Test small loss (should be allowed)
        trading_allowed, alert = await risk_manager.check_daily_loss_limit(9800.0)
        
        assert trading_allowed is True
        assert alert is None
    
    @pytest.mark.asyncio
    async def test_check_daily_loss_limit_warning(self):
        """Test daily loss limit warning threshold."""
        await risk_manager.initialize_daily_tracking(10000.0)
        
        # Test loss near 80% of limit (should trigger warning)
        trading_allowed, alert = await risk_manager.check_daily_loss_limit(9600.0)
        
        assert trading_allowed is True
        assert alert is not None
        assert alert.level == RiskLevel.HIGH
        assert alert.event_type == RiskEvent.DAILY_LOSS_LIMIT
    
    @pytest.mark.asyncio
    async def test_check_daily_loss_limit_exceeded(self):
        """Test daily loss limit exceeded."""
        await risk_manager.initialize_daily_tracking(10000.0)
        
        # Test loss exceeding 5% limit
        trading_allowed, alert = await risk_manager.check_daily_loss_limit(9400.0)
        
        assert trading_allowed is False
        assert alert is not None
        assert alert.level == RiskLevel.CRITICAL
        assert alert.action_required is True
    
    @pytest.mark.asyncio
    async def test_check_volatility_limits_normal(self):
        """Test volatility limits under normal conditions."""
        trading_allowed, alert = await risk_manager.check_volatility_limits(
            "BTC/USDT:USDT", 0.03  # 3% volatility
        )
        
        assert trading_allowed is True
        assert alert is None
    
    @pytest.mark.asyncio
    async def test_check_volatility_limits_high(self):
        """Test volatility limits with high volatility."""
        trading_allowed, alert = await risk_manager.check_volatility_limits(
            "BTC/USDT:USDT", 0.10  # 10% volatility (above 8% threshold)
        )
        
        assert trading_allowed is True  # High but not critical
        assert alert is not None
        assert alert.level == RiskLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_check_volatility_limits_critical(self):
        """Test volatility limits with critical volatility."""
        trading_allowed, alert = await risk_manager.check_volatility_limits(
            "BTC/USDT:USDT", 0.15  # 15% volatility (critical)
        )
        
        assert trading_allowed is False  # Should stop trading
        assert alert is not None
        assert alert.level == RiskLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_check_margin_usage_normal(self):
        """Test margin usage checking under normal conditions."""
        account_data = {
            "total": 10000.0,
            "used": 5000.0  # 50% usage
        }
        
        trading_allowed, alert = await risk_manager.check_margin_usage(account_data)
        
        assert trading_allowed is True
        assert alert is None
    
    @pytest.mark.asyncio
    async def test_check_margin_usage_high(self):
        """Test margin usage checking with high usage."""
        account_data = {
            "total": 10000.0,
            "used": 7500.0  # 75% usage (above 72% warning threshold)
        }
        
        trading_allowed, alert = await risk_manager.check_margin_usage(account_data)
        
        assert trading_allowed is True
        assert alert is not None
        assert alert.level == RiskLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_check_margin_usage_exceeded(self):
        """Test margin usage limit exceeded."""
        account_data = {
            "total": 10000.0,
            "used": 8500.0  # 85% usage (above 80% limit)
        }
        
        trading_allowed, alert = await risk_manager.check_margin_usage(account_data)
        
        assert trading_allowed is False
        assert alert is not None
        assert alert.level == RiskLevel.CRITICAL
        assert alert.action_required is True
    
    @pytest.mark.asyncio
    async def test_evaluate_position_risk(self):
        """Test position risk evaluation."""
        risk_metrics = await risk_manager.evaluate_position_risk(
            symbol="BTC/USDT:USDT",
            entry_price=50000.0,
            position_size=0.1,
            stop_loss=49000.0,
            take_profit=52000.0,
            market_volatility=0.03
        )
        
        assert isinstance(risk_metrics, dict)
        assert "symbol" in risk_metrics
        assert "risk_level" in risk_metrics
        assert "risk_reward_ratio" in risk_metrics
        assert "recommendation" in risk_metrics
        
        # Should have good risk-reward ratio (2:1)
        assert risk_metrics["risk_reward_ratio"] == 2.0
    
    @pytest.mark.asyncio
    async def test_emergency_stop(self):
        """Test emergency stop functionality."""
        # Activate emergency stop
        await risk_manager.activate_emergency_stop("Test emergency")
        
        assert risk_manager.emergency_stop_active is True
        
        trading_allowed, reason = risk_manager.is_trading_allowed()
        assert trading_allowed is False
        assert "Emergency stop" in reason
        
        # Deactivate emergency stop
        risk_manager.deactivate_emergency_stop()
        assert risk_manager.emergency_stop_active is False
    
    def test_get_risk_summary(self):
        """Test risk summary generation."""
        summary = risk_manager.get_risk_summary()
        
        assert isinstance(summary, dict)
        assert "trading_allowed" in summary
        assert "emergency_stop_active" in summary
        assert "risk_limits" in summary
        assert "alert_counts" in summary


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(pytest.main([__file__, "-v"]))