# app/portfolio/risk_manager.py
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings


logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskEvent(str, Enum):
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    POSITION_CORRELATION = "POSITION_CORRELATION"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    MARGIN_CALL = "MARGIN_CALL"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass
class RiskAlert:
    event_type: RiskEvent
    level: RiskLevel
    message: str
    timestamp: datetime
    symbol: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None
    action_required: bool = False


@dataclass
class RiskLimits:
    daily_loss_limit_pct: float = 5.0  # 5% daily loss limit
    max_position_correlation: float = 0.7
    max_portfolio_leverage: float = 10.0
    max_drawdown_pct: float = 15.0
    volatility_threshold: float = 0.08  # 8% volatility threshold
    margin_usage_limit: float = 0.8  # 80% margin usage limit


class RiskManager:
    """
    Advanced risk management system for monitoring and controlling trading risks.
    Integrates with portfolio manager and provides real-time risk assessment.
    """
    
    def __init__(self):
        self.logger = logger
        self.risk_limits = RiskLimits()
        self.daily_start_balance: Optional[float] = None
        self.daily_start_time: Optional[datetime] = None
        self.emergency_stop_active = False
        self.risk_alerts: List[RiskAlert] = []
        
    async def initialize_daily_tracking(self, account_balance: float):
        """Initialize daily risk tracking with starting balance."""
        current_time = datetime.utcnow()
        
        # Reset daily tracking if it's a new day
        if (not self.daily_start_time or 
            current_time.date() != self.daily_start_time.date()):
            
            self.daily_start_balance = account_balance
            self.daily_start_time = current_time
            self.risk_alerts.clear()  # Clear old alerts
            
            self.logger.info(f"Daily risk tracking initialized with balance: ${account_balance:.2f}")
    
    async def check_daily_loss_limit(self, current_balance: float) -> Tuple[bool, Optional[RiskAlert]]:
        """
        Check if daily loss limit has been exceeded.
        
        Returns:
            Tuple of (trading_allowed, risk_alert)
        """
        if not self.daily_start_balance:
            return True, None
        
        daily_pnl = current_balance - self.daily_start_balance
        daily_pnl_pct = (daily_pnl / self.daily_start_balance) * 100
        
        if daily_pnl_pct <= -self.risk_limits.daily_loss_limit_pct:
            alert = RiskAlert(
                event_type=RiskEvent.DAILY_LOSS_LIMIT,
                level=RiskLevel.CRITICAL,
                message=f"Daily loss limit exceeded: {daily_pnl_pct:.2f}% (limit: {self.risk_limits.daily_loss_limit_pct}%)",
                timestamp=datetime.utcnow(),
                value=daily_pnl_pct,
                threshold=self.risk_limits.daily_loss_limit_pct,
                action_required=True
            )
            
            self.risk_alerts.append(alert)
            self.logger.critical(f"DAILY LOSS LIMIT EXCEEDED: {daily_pnl_pct:.2f}%")
            
            return False, alert
        
        # Warning at 80% of limit
        warning_threshold = self.risk_limits.daily_loss_limit_pct * 0.8
        if daily_pnl_pct <= -warning_threshold:
            alert = RiskAlert(
                event_type=RiskEvent.DAILY_LOSS_LIMIT,
                level=RiskLevel.HIGH,
                message=f"Approaching daily loss limit: {daily_pnl_pct:.2f}% (80% of limit)",
                timestamp=datetime.utcnow(),
                value=daily_pnl_pct,
                threshold=warning_threshold
            )
            
            self.risk_alerts.append(alert)
            self.logger.warning(f"APPROACHING DAILY LOSS LIMIT: {daily_pnl_pct:.2f}%")
            
            return True, alert
        
        return True, None
    
    async def check_position_correlation(
        self, new_symbol: str, existing_positions: List[Dict]
    ) -> Tuple[bool, Optional[RiskAlert]]:
        """
        Check position correlation limits.
        
        Returns:
            Tuple of (trading_allowed, risk_alert)
        """
        try:
            from app.portfolio.portfolio_manager import portfolio_manager
            
            allowed, reason = await portfolio_manager.check_correlation_limits(
                new_symbol, existing_positions
            )
            
            if not allowed:
                alert = RiskAlert(
                    event_type=RiskEvent.POSITION_CORRELATION,
                    level=RiskLevel.HIGH,
                    message=f"Position correlation limit exceeded for {new_symbol}: {reason}",
                    timestamp=datetime.utcnow(),
                    symbol=new_symbol,
                    action_required=True
                )
                
                self.risk_alerts.append(alert)
                self.logger.warning(f"CORRELATION LIMIT EXCEEDED: {new_symbol} - {reason}")
                
                return False, alert
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error checking position correlation: {e}")
            return True, None  # Allow trade on error
    
    async def check_volatility_limits(
        self, symbol: str, volatility: float
    ) -> Tuple[bool, Optional[RiskAlert]]:
        """
        Check if market volatility exceeds safe trading limits.
        
        Returns:
            Tuple of (trading_allowed, risk_alert)
        """
        if volatility > self.risk_limits.volatility_threshold:
            level = RiskLevel.CRITICAL if volatility > self.risk_limits.volatility_threshold * 1.5 else RiskLevel.HIGH
            
            alert = RiskAlert(
                event_type=RiskEvent.VOLATILITY_SPIKE,
                level=level,
                message=f"High volatility detected for {symbol}: {volatility:.3f} "
                       f"(threshold: {self.risk_limits.volatility_threshold:.3f})",
                timestamp=datetime.utcnow(),
                symbol=symbol,
                value=volatility,
                threshold=self.risk_limits.volatility_threshold,
                action_required=level == RiskLevel.CRITICAL
            )
            
            self.risk_alerts.append(alert)
            self.logger.warning(f"HIGH VOLATILITY: {symbol} - {volatility:.3f}")
            
            # Stop trading on critical volatility
            return level != RiskLevel.CRITICAL, alert
        
        return True, None
    
    async def check_margin_usage(
        self, account_data: Dict
    ) -> Tuple[bool, Optional[RiskAlert]]:
        """
        Check margin usage limits.
        
        Returns:
            Tuple of (trading_allowed, risk_alert)
        """
        try:
            total_balance = account_data.get('total', 0.0)
            used_margin = account_data.get('used', 0.0)
            
            if total_balance <= 0:
                return True, None
            
            margin_usage_pct = used_margin / total_balance
            
            if margin_usage_pct > self.risk_limits.margin_usage_limit:
                alert = RiskAlert(
                    event_type=RiskEvent.MARGIN_CALL,
                    level=RiskLevel.CRITICAL,
                    message=f"Margin usage limit exceeded: {margin_usage_pct:.1%} "
                           f"(limit: {self.risk_limits.margin_usage_limit:.1%})",
                    timestamp=datetime.utcnow(),
                    value=margin_usage_pct * 100,
                    threshold=self.risk_limits.margin_usage_limit * 100,
                    action_required=True
                )
                
                self.risk_alerts.append(alert)
                self.logger.critical(f"MARGIN LIMIT EXCEEDED: {margin_usage_pct:.1%}")
                
                return False, alert
            
            # Warning at 90% of limit
            warning_threshold = self.risk_limits.margin_usage_limit * 0.9
            if margin_usage_pct > warning_threshold:
                alert = RiskAlert(
                    event_type=RiskEvent.MARGIN_CALL,
                    level=RiskLevel.HIGH,
                    message=f"High margin usage: {margin_usage_pct:.1%} "
                           f"(90% of limit: {self.risk_limits.margin_usage_limit:.1%})",
                    timestamp=datetime.utcnow(),
                    value=margin_usage_pct * 100,
                    threshold=warning_threshold * 100
                )
                
                self.risk_alerts.append(alert)
                self.logger.warning(f"HIGH MARGIN USAGE: {margin_usage_pct:.1%}")
                
                return True, alert
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error checking margin usage: {e}")
            return True, None
    
    async def evaluate_position_risk(
        self, symbol: str, entry_price: float, position_size: float,
        stop_loss: float, take_profit: float, market_volatility: float
    ) -> Dict:
        """
        Evaluate risk metrics for a specific position.
        
        Returns:
            Dictionary with risk metrics
        """
        try:
            # Calculate risk-reward ratio
            if stop_loss and take_profit:
                risk_amount = abs(entry_price - stop_loss) * position_size
                reward_amount = abs(take_profit - entry_price) * position_size
                risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
            else:
                risk_reward_ratio = 0
            
            # Calculate position risk percentage (based on volatility)
            volatility_risk = market_volatility * 100  # Convert to percentage
            
            # Determine risk level
            if risk_reward_ratio >= 2.0 and volatility_risk <= 3.0:
                risk_level = RiskLevel.LOW
            elif risk_reward_ratio >= 1.5 and volatility_risk <= 5.0:
                risk_level = RiskLevel.MEDIUM
            elif risk_reward_ratio >= 1.0 and volatility_risk <= 8.0:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.CRITICAL
            
            return {
                "symbol": symbol,
                "risk_level": risk_level.value,
                "risk_reward_ratio": risk_reward_ratio,
                "volatility_risk_pct": volatility_risk,
                "position_value": entry_price * position_size,
                "max_loss": risk_amount if 'risk_amount' in locals() else 0,
                "max_gain": reward_amount if 'reward_amount' in locals() else 0,
                "recommendation": self._get_risk_recommendation(risk_level, risk_reward_ratio)
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating position risk for {symbol}: {e}")
            return {
                "symbol": symbol,
                "risk_level": RiskLevel.CRITICAL.value,
                "error": str(e),
                "recommendation": "Skip trade due to evaluation error"
            }
    
    def _get_risk_recommendation(self, risk_level: RiskLevel, risk_reward_ratio: float) -> str:
        """Get risk-based trading recommendation."""
        if risk_level == RiskLevel.LOW:
            return "Excellent trade setup - proceed with standard position size"
        elif risk_level == RiskLevel.MEDIUM:
            return "Good trade setup - consider slightly reduced position size"
        elif risk_level == RiskLevel.HIGH:
            return "Risky trade - reduce position size significantly"
        else:
            return "Very risky trade - consider skipping or minimal position size"
    
    async def activate_emergency_stop(self, reason: str):
        """Activate emergency stop for all trading activities."""
        self.emergency_stop_active = True
        
        alert = RiskAlert(
            event_type=RiskEvent.EMERGENCY_STOP,
            level=RiskLevel.CRITICAL,
            message=f"EMERGENCY STOP ACTIVATED: {reason}",
            timestamp=datetime.utcnow(),
            action_required=True
        )
        
        self.risk_alerts.append(alert)
        self.logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}")
    
    def deactivate_emergency_stop(self):
        """Deactivate emergency stop (manual intervention required)."""
        self.emergency_stop_active = False
        self.logger.info("Emergency stop deactivated - trading resumed")
    
    def is_trading_allowed(self) -> Tuple[bool, str]:
        """Check if trading is currently allowed based on risk status."""
        if self.emergency_stop_active:
            return False, "Emergency stop is active"
        
        # Check recent critical alerts
        recent_alerts = [
            alert for alert in self.risk_alerts[-10:]  # Last 10 alerts
            if alert.level == RiskLevel.CRITICAL and alert.action_required
        ]
        
        if recent_alerts:
            return False, f"Critical risk alerts active: {len(recent_alerts)}"
        
        return True, "Trading allowed"
    
    def get_risk_summary(self) -> Dict:
        """Get comprehensive risk summary."""
        # Count alerts by level
        alert_counts = {level.value: 0 for level in RiskLevel}
        for alert in self.risk_alerts[-50:]:  # Last 50 alerts
            alert_counts[alert.level.value] += 1
        
        # Calculate daily PnL if tracking
        daily_pnl_pct = 0.0
        if self.daily_start_balance:
            # This would need current balance passed in
            pass
        
        trading_allowed, trading_status = self.is_trading_allowed()
        
        return {
            "trading_allowed": trading_allowed,
            "trading_status": trading_status,
            "emergency_stop_active": self.emergency_stop_active,
            "daily_pnl_pct": daily_pnl_pct,
            "risk_limits": {
                "daily_loss_limit": self.risk_limits.daily_loss_limit_pct,
                "volatility_threshold": self.risk_limits.volatility_threshold,
                "margin_usage_limit": self.risk_limits.margin_usage_limit
            },
            "alert_counts": alert_counts,
            "recent_alerts": [
                {
                    "type": alert.event_type.value,
                    "level": alert.level.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "symbol": alert.symbol
                }
                for alert in self.risk_alerts[-5:]  # Last 5 alerts
            ]
        }
    
    async def cleanup_old_alerts(self, max_age_hours: int = 24):
        """Clean up old risk alerts."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        initial_count = len(self.risk_alerts)
        self.risk_alerts = [
            alert for alert in self.risk_alerts
            if alert.timestamp > cutoff_time
        ]
        
        cleaned_count = initial_count - len(self.risk_alerts)
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} old risk alerts")


# Global instance
risk_manager = RiskManager()