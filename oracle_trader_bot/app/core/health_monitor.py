# app/core/health_monitor.py
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import aiohttp
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


@dataclass
class HealthMetrics:
    """Health metrics for system monitoring."""
    timestamp: str
    overall_status: str
    database_status: str
    exchange_status: str
    api_latency_ms: Optional[float]
    bot_engine_status: str
    websocket_status: str
    memory_usage_mb: Optional[float]
    uptime_seconds: Optional[float]
    last_trade_timestamp: Optional[str]
    error_count_last_hour: int
    warnings: List[str]


class HealthMonitor:
    """
    System health monitoring for the Oracle Trader Bot.
    Monitors database, exchange connectivity, API performance, and bot status.
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.error_count = 0
        self.last_error_reset = time.time()
        self.api_response_times: List[float] = []
        self.max_response_time_samples = 100
        
    def record_api_call(self, response_time_ms: float):
        """Record API call response time for monitoring."""
        self.api_response_times.append(response_time_ms)
        if len(self.api_response_times) > self.max_response_time_samples:
            self.api_response_times.pop(0)
            
    def record_error(self):
        """Record an error occurrence."""
        current_time = time.time()
        # Reset error count every hour
        if current_time - self.last_error_reset > 3600:
            self.error_count = 0
            self.last_error_reset = current_time
        self.error_count += 1
        
    def get_average_api_latency(self) -> Optional[float]:
        """Get average API response time in milliseconds."""
        if not self.api_response_times:
            return None
        return sum(self.api_response_times) / len(self.api_response_times)
        
    async def check_database_health(self, async_engine) -> tuple[str, Optional[str]]:
        """Check database connectivity and response time."""
        try:
            start_time = time.time()
            async with async_engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            response_time = (time.time() - start_time) * 1000
            
            if response_time > 1000:  # > 1 second
                return "slow", f"Database response time: {response_time:.1f}ms"
            elif response_time > 500:  # > 500ms
                return "degraded", f"Database response time: {response_time:.1f}ms"
            else:
                return "healthy", None
                
        except Exception as e:
            logger.error(f"HealthMonitor: Database health check failed: {e}")
            return "unhealthy", str(e)
            
    async def check_exchange_connectivity(self, kucoin_client) -> tuple[str, Optional[str]]:
        """Check exchange connectivity and API responsiveness."""
        if not kucoin_client:
            return "unavailable", "KuCoin client not initialized"
            
        try:
            start_time = time.time()
            # Try to get server time as a lightweight health check
            await kucoin_client.exchange.fetch_time()
            response_time = (time.time() - start_time) * 1000
            self.record_api_call(response_time)
            
            if response_time > 2000:  # > 2 seconds
                return "slow", f"Exchange API response time: {response_time:.1f}ms"
            elif response_time > 1000:  # > 1 second
                return "degraded", f"Exchange API response time: {response_time:.1f}ms"
            else:
                return "healthy", None
                
        except Exception as e:
            logger.error(f"HealthMonitor: Exchange health check failed: {e}")
            self.record_error()
            return "unhealthy", str(e)
            
    def check_bot_engine_status(self, bot_process_manager) -> tuple[str, Optional[str]]:
        """Check bot engine process status."""
        try:
            status_str, pid = bot_process_manager.get_bot_process_status()
            
            if status_str == "running" and pid:
                return "running", None
            elif status_str == "stopped":
                return "stopped", "Bot engine is not running"
            elif status_str == "stopped_stale_pid":
                return "error", "Stale PID file detected"
            else:
                return "unknown", f"Unknown status: {status_str}"
                
        except Exception as e:
            logger.error(f"HealthMonitor: Bot process check failed: {e}")
            return "error", str(e)
            
    def get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except ImportError:
            logger.debug("HealthMonitor: psutil not available for memory monitoring")
            return None
        except Exception as e:
            logger.error(f"HealthMonitor: Memory usage check failed: {e}")
            return None
            
    async def get_last_trade_timestamp(self, async_engine) -> Optional[str]:
        """Get timestamp of the last trade."""
        try:
            async with async_engine.connect() as connection:
                result = await connection.execute(
                    text("SELECT MAX(timestamp_created) FROM trades")
                )
                last_trade = result.scalar()
                return last_trade.isoformat() if last_trade else None
        except Exception as e:
            logger.error(f"HealthMonitor: Last trade timestamp check failed: {e}")
            return None
            
    async def generate_health_report(self, async_engine, kucoin_client, bot_process_manager) -> HealthMetrics:
        """Generate comprehensive health report."""
        warnings = []
        
        # Check database health
        db_status, db_warning = await self.check_database_health(async_engine)
        if db_warning:
            warnings.append(f"Database: {db_warning}")
            
        # Check exchange connectivity  
        exchange_status, exchange_warning = await self.check_exchange_connectivity(kucoin_client)
        if exchange_warning:
            warnings.append(f"Exchange: {exchange_warning}")
            
        # Check bot engine status
        bot_status, bot_warning = self.check_bot_engine_status(bot_process_manager)
        if bot_warning:
            warnings.append(f"Bot Engine: {bot_warning}")
            
        # Determine overall status
        if any(status in ["unhealthy", "error"] for status in [db_status, exchange_status, bot_status]):
            overall_status = "unhealthy"
        elif any(status in ["slow", "degraded"] for status in [db_status, exchange_status]):
            overall_status = "degraded"
        elif bot_status != "running":
            overall_status = "partial"  # System healthy but bot not running
        else:
            overall_status = "healthy"
            
        # Get additional metrics
        memory_usage = self.get_memory_usage()
        uptime = time.time() - self.start_time
        api_latency = self.get_average_api_latency()
        last_trade = await self.get_last_trade_timestamp(async_engine)
        
        # Error count warnings
        if self.error_count > 10:
            warnings.append(f"High error rate: {self.error_count} errors in last hour")
            
        return HealthMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_status=overall_status,
            database_status=db_status,
            exchange_status=exchange_status,
            api_latency_ms=api_latency,
            bot_engine_status=bot_status,
            websocket_status="not_implemented",  # TODO: Implement WebSocket monitoring
            memory_usage_mb=memory_usage,
            uptime_seconds=uptime,
            last_trade_timestamp=last_trade,
            error_count_last_hour=self.error_count,
            warnings=warnings
        )
        
    def to_dict(self, health_metrics: HealthMetrics) -> Dict[str, Any]:
        """Convert health metrics to dictionary."""
        return asdict(health_metrics)


# Global health monitor instance
health_monitor = HealthMonitor()