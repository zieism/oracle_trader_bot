# app/monitoring/dashboard.py
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from app.portfolio.portfolio_manager import portfolio_manager
from app.portfolio.risk_manager import risk_manager
from app.portfolio.performance_tracker import performance_tracker
from app.monitoring.alerting import alerting_manager
from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    response_time_ms: float


@dataclass
class TradingMetrics:
    timestamp: datetime
    active_positions: int
    daily_pnl: float
    total_pnl: float
    win_rate: float
    current_balance: float
    margin_usage: float
    risk_level: str


class PerformanceDashboard:
    """
    Real-time performance dashboard for monitoring system health,
    trading performance, and risk metrics.
    """
    
    def __init__(self):
        self.logger = logger
        self.system_metrics_history: List[SystemMetrics] = []
        self.trading_metrics_history: List[TradingMetrics] = []
        self.dashboard_data: Dict[str, Any] = {}
        
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics."""
        try:
            import psutil
            
            # Get CPU and memory usage
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get active connections (simplified)
            connections = len(psutil.net_connections())
            
            # Response time placeholder (would measure actual API response time)
            response_time_ms = 50.0  # Placeholder
            
            metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                active_connections=connections,
                response_time_ms=response_time_ms
            )
            
            # Store metrics
            self.system_metrics_history.append(metrics)
            
            # Limit history size
            if len(self.system_metrics_history) > 1440:  # 24 hours at 1 minute intervals
                self.system_metrics_history = self.system_metrics_history[-720:]  # Keep 12 hours
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                active_connections=0,
                response_time_ms=0.0
            )
    
    async def collect_trading_metrics(self, balance_data: Dict, positions_data: List[Dict]) -> TradingMetrics:
        """Collect current trading performance metrics."""
        try:
            # Update portfolio metrics
            portfolio_metrics = await portfolio_manager.update_portfolio_metrics(
                balance_data, positions_data
            )
            
            # Get performance summary
            performance_summary = performance_tracker.get_performance_summary()
            
            # Get risk summary
            risk_summary = risk_manager.get_risk_summary()
            
            # Calculate win rate from recent trades
            recent_performance = await performance_tracker.calculate_performance_metrics(
                start_date=datetime.utcnow() - timedelta(days=7)
            )
            
            metrics = TradingMetrics(
                timestamp=datetime.utcnow(),
                active_positions=portfolio_metrics.open_positions,
                daily_pnl=portfolio_metrics.daily_pnl,
                total_pnl=performance_summary.get("total_pnl", 0.0),
                win_rate=recent_performance.win_rate,
                current_balance=portfolio_metrics.total_balance,
                margin_usage=portfolio_metrics.used_margin / portfolio_metrics.total_balance * 100 if portfolio_metrics.total_balance > 0 else 0,
                risk_level=risk_summary.get("trading_status", "unknown")
            )
            
            # Store metrics
            self.trading_metrics_history.append(metrics)
            
            # Limit history size
            if len(self.trading_metrics_history) > 1440:  # 24 hours
                self.trading_metrics_history = self.trading_metrics_history[-720:]  # Keep 12 hours
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting trading metrics: {e}")
            return TradingMetrics(
                timestamp=datetime.utcnow(),
                active_positions=0,
                daily_pnl=0.0,
                total_pnl=0.0,
                win_rate=0.0,
                current_balance=0.0,
                margin_usage=0.0,
                risk_level="error"
            )
    
    async def update_dashboard_data(
        self, 
        balance_data: Optional[Dict] = None,
        positions_data: Optional[List[Dict]] = None
    ):
        """Update all dashboard data."""
        try:
            # Collect metrics
            system_metrics = await self.collect_system_metrics()
            
            if balance_data and positions_data:
                trading_metrics = await self.collect_trading_metrics(balance_data, positions_data)
            else:
                # Use placeholder data if not provided
                trading_metrics = TradingMetrics(
                    timestamp=datetime.utcnow(),
                    active_positions=0, daily_pnl=0.0, total_pnl=0.0,
                    win_rate=0.0, current_balance=0.0, margin_usage=0.0,
                    risk_level="no_data"
                )
            
            # Get additional data
            portfolio_summary = portfolio_manager.get_portfolio_summary()
            risk_summary = risk_manager.get_risk_summary()
            performance_summary = performance_tracker.get_performance_summary()
            alert_summary = alerting_manager.get_alert_summary()
            
            # Update dashboard data
            self.dashboard_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "system_metrics": asdict(system_metrics),
                "trading_metrics": asdict(trading_metrics),
                "portfolio_summary": portfolio_summary,
                "risk_summary": risk_summary,
                "performance_summary": performance_summary,
                "alert_summary": alert_summary,
                "historical_data": {
                    "system_metrics_1h": self._get_recent_system_metrics(60),
                    "trading_metrics_1h": self._get_recent_trading_metrics(60),
                    "system_metrics_24h": self._get_recent_system_metrics(1440),
                    "trading_metrics_24h": self._get_recent_trading_metrics(1440)
                }
            }
            
            # Check for alerts based on current metrics
            await self._check_dashboard_alerts(system_metrics, trading_metrics)
            
        except Exception as e:
            self.logger.error(f"Error updating dashboard data: {e}")
    
    def _get_recent_system_metrics(self, minutes: int) -> List[Dict]:
        """Get recent system metrics for specified time period."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            recent_metrics = [
                asdict(metric) for metric in self.system_metrics_history
                if metric.timestamp >= cutoff_time
            ]
            
            # Convert datetime to string for JSON serialization
            for metric in recent_metrics:
                metric["timestamp"] = metric["timestamp"].isoformat()
            
            return recent_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting recent system metrics: {e}")
            return []
    
    def _get_recent_trading_metrics(self, minutes: int) -> List[Dict]:
        """Get recent trading metrics for specified time period."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            recent_metrics = [
                asdict(metric) for metric in self.trading_metrics_history
                if metric.timestamp >= cutoff_time
            ]
            
            # Convert datetime to string for JSON serialization
            for metric in recent_metrics:
                metric["timestamp"] = metric["timestamp"].isoformat()
            
            return recent_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting recent trading metrics: {e}")
            return []
    
    async def _check_dashboard_alerts(self, system_metrics: SystemMetrics, trading_metrics: TradingMetrics):
        """Check metrics against alert thresholds."""
        try:
            # System alerts
            if system_metrics.cpu_usage > 80:
                await alerting_manager.send_alert(
                    title="High CPU Usage",
                    message=f"CPU usage is {system_metrics.cpu_usage:.1f}%",
                    severity=alerting_manager.AlertSeverity.WARNING,
                    source="dashboard",
                    data={"cpu_usage": system_metrics.cpu_usage}
                )
            
            if system_metrics.memory_usage > 85:
                await alerting_manager.send_alert(
                    title="High Memory Usage",
                    message=f"Memory usage is {system_metrics.memory_usage:.1f}%",
                    severity=alerting_manager.AlertSeverity.WARNING,
                    source="dashboard",
                    data={"memory_usage": system_metrics.memory_usage}
                )
            
            # Trading alerts
            if trading_metrics.margin_usage > 80:
                await alerting_manager.send_alert(
                    title="High Margin Usage",
                    message=f"Margin usage is {trading_metrics.margin_usage:.1f}%",
                    severity=alerting_manager.AlertSeverity.ERROR,
                    source="dashboard",
                    data={"margin_usage": trading_metrics.margin_usage}
                )
            
            if trading_metrics.daily_pnl < -500:  # Example threshold
                await alerting_manager.send_alert(
                    title="Significant Daily Loss",
                    message=f"Daily PnL is ${trading_metrics.daily_pnl:.2f}",
                    severity=alerting_manager.AlertSeverity.WARNING,
                    source="dashboard",
                    data={"daily_pnl": trading_metrics.daily_pnl}
                )
                
        except Exception as e:
            self.logger.error(f"Error checking dashboard alerts: {e}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data."""
        return self.dashboard_data.copy()
    
    def get_health_status(self) -> Dict[str, str]:
        """Get overall system health status."""
        try:
            if not self.system_metrics_history or not self.trading_metrics_history:
                return {"status": "initializing", "message": "Collecting initial metrics"}
            
            latest_system = self.system_metrics_history[-1]
            latest_trading = self.trading_metrics_history[-1]
            
            # Determine overall health
            issues = []
            
            if latest_system.cpu_usage > 90:
                issues.append("High CPU usage")
            if latest_system.memory_usage > 90:
                issues.append("High memory usage")
            if latest_trading.margin_usage > 90:
                issues.append("Critical margin usage")
            if latest_trading.risk_level == "critical":
                issues.append("Critical risk level")
            
            if issues:
                status = "unhealthy"
                message = "; ".join(issues)
            elif latest_system.cpu_usage > 70 or latest_system.memory_usage > 70:
                status = "warning"
                message = "System resources under pressure"
            elif latest_trading.margin_usage > 70:
                status = "warning"
                message = "Trading margin usage high"
            else:
                status = "healthy"
                message = "All systems operational"
            
            return {
                "status": status,
                "message": message,
                "last_update": latest_system.timestamp.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return {"status": "error", "message": "Error determining health status"}


# Global instance
performance_dashboard = PerformanceDashboard()