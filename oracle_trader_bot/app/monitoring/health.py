# app/monitoring/health.py
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status data structure."""
    service: str
    status: str  # healthy, unhealthy, degraded
    timestamp: int
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthMonitor:
    """
    Centralized health monitoring for all services.
    
    Features:
    - Database connectivity checks
    - Exchange connectivity monitoring
    - Redis connectivity checks
    - Service dependency health
    """
    
    def __init__(self):
        self.health_checks = {}
        self.last_check_time = {}
        self.check_interval = 30  # seconds
        
    def register_health_check(self, service_name: str, check_function):
        """
        Register a health check function for a service.
        
        Args:
            service_name: Name of the service
            check_function: Async function that returns HealthStatus
        """
        self.health_checks[service_name] = check_function
        logger.info(f"Registered health check for {service_name}")
    
    async def check_database_health(self) -> HealthStatus:
        """Check database connectivity."""
        start_time = time.time()
        
        try:
            import asyncpg
            
            conn = await asyncpg.connect(settings.ASYNC_DATABASE_URL)
            await conn.execute("SELECT 1")
            await conn.close()
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthStatus(
                service="database",
                status="healthy",
                timestamp=int(time.time()),
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                service="database",
                status="unhealthy",
                timestamp=int(time.time()),
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def check_redis_health(self) -> HealthStatus:
        """Check Redis connectivity."""
        start_time = time.time()
        
        try:
            import aioredis
            
            redis = aioredis.from_url(settings.REDIS_URL)
            await redis.ping()
            await redis.close()
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthStatus(
                service="redis",
                status="healthy",
                timestamp=int(time.time()),
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                service="redis",
                status="unhealthy",
                timestamp=int(time.time()),
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def check_exchanges_health(self) -> HealthStatus:
        """Check exchange connectivity."""
        start_time = time.time()
        
        try:
            from app.exchanges.manager import ExchangeManager
            
            # This would be injected in a real implementation
            exchange_manager = getattr(self, '_exchange_manager', None)
            if not exchange_manager:
                return HealthStatus(
                    service="exchanges",
                    status="degraded",
                    timestamp=int(time.time()),
                    error="Exchange manager not initialized"
                )
            
            health_results = await exchange_manager.health_check_all()
            
            # Determine overall status
            healthy_count = sum(1 for result in health_results.values() 
                              if result.get('status') == 'healthy')
            total_count = len(health_results)
            
            if healthy_count == total_count:
                status = "healthy"
            elif healthy_count > 0:
                status = "degraded"
            else:
                status = "unhealthy"
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthStatus(
                service="exchanges",
                status=status,
                timestamp=int(time.time()),
                response_time_ms=response_time,
                details={
                    "healthy_exchanges": healthy_count,
                    "total_exchanges": total_count,
                    "exchange_status": health_results
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                service="exchanges",
                status="unhealthy",
                timestamp=int(time.time()),
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def check_all_health(self) -> Dict[str, HealthStatus]:
        """Check health of all registered services."""
        results = {}
        
        # Built-in health checks
        built_in_checks = {
            "database": self.check_database_health,
            "redis": self.check_redis_health,
            "exchanges": self.check_exchanges_health
        }
        
        # Combine with registered checks
        all_checks = {**built_in_checks, **self.health_checks}
        
        # Run all checks concurrently
        check_tasks = []
        for service_name, check_function in all_checks.items():
            check_tasks.append(check_function())
        
        check_results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        for i, (service_name, _) in enumerate(all_checks.items()):
            result = check_results[i]
            
            if isinstance(result, Exception):
                results[service_name] = HealthStatus(
                    service=service_name,
                    status="unhealthy",
                    timestamp=int(time.time()),
                    error=str(result)
                )
            else:
                results[service_name] = result
        
        return results
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        health_results = await self.check_all_health()
        
        # Calculate overall status
        statuses = [result.status for result in health_results.values()]
        
        if all(status == "healthy" for status in statuses):
            overall_status = "healthy"
        elif any(status == "healthy" for status in statuses):
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        # Calculate response times
        response_times = [result.response_time_ms for result in health_results.values() 
                         if result.response_time_ms is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            "status": overall_status,
            "timestamp": int(time.time()),
            "services": {name: asdict(status) for name, status in health_results.items()},
            "summary": {
                "total_services": len(health_results),
                "healthy_services": sum(1 for s in statuses if s == "healthy"),
                "degraded_services": sum(1 for s in statuses if s == "degraded"),
                "unhealthy_services": sum(1 for s in statuses if s == "unhealthy"),
                "average_response_time_ms": avg_response_time
            }
        }
    
    def set_exchange_manager(self, exchange_manager):
        """Set the exchange manager for health checks."""
        self._exchange_manager = exchange_manager


# Global health monitor instance
health_monitor = HealthMonitor()