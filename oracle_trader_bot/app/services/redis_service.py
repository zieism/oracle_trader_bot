# app/services/redis_service.py
import asyncio
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RedisService:
    """
    Redis service for caching and pub/sub messaging.
    
    Graceful fallback implementation when Redis is not available.
    """
    
    def __init__(self):
        self.redis = None
        self.is_connected = False
        self.cache = {}  # In-memory fallback cache
        
    async def connect(self) -> bool:
        """Connect to Redis with fallback to in-memory cache."""
        try:
            # Try to import and connect to Redis
            import redis.asyncio as redis_async
            from app.core.config import settings
            
            self.redis = redis_async.from_url(settings.REDIS_URL, decode_responses=True)
            await self.redis.ping()
            self.is_connected = True
            logger.info("Connected to Redis")
            return True
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self.redis = None
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            try:
                await self.redis.close()
            except Exception:
                pass
            self.is_connected = False
            logger.info("Disconnected from Redis")
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value with optional TTL."""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if self.redis:
                if ttl:
                    await self.redis.setex(key, ttl, value)
                else:
                    await self.redis.set(key, value)
            else:
                # Fallback to in-memory cache
                self.cache[key] = value
                if ttl:
                    # Schedule removal after TTL (simplified)
                    asyncio.create_task(self._expire_key(key, ttl))
            
            return True
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value."""
        try:
            if self.redis:
                value = await self.redis.get(key)
                if value is None:
                    return default
            else:
                # Fallback to in-memory cache
                value = self.cache.get(key)
                if value is None:
                    return default
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return default
    
    async def cache_ticker(self, exchange: str, symbol: str, ticker_data: Dict[str, Any], ttl: int = 10):
        """Cache ticker data with TTL."""
        key = f"ticker:{exchange}:{symbol}"
        await self.set(key, ticker_data, ttl)
    
    async def get_cached_ticker(self, exchange: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached ticker data."""
        key = f"ticker:{exchange}:{symbol}"
        return await self.get(key)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            if not self.redis:
                return {
                    "status": "fallback", 
                    "mode": "in-memory",
                    "connected": False
                }
            
            start_time = asyncio.get_event_loop().time()
            await self.redis.ping()
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "mode": "redis",
                "latency_ms": latency,
                "connected": self.is_connected
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False
            }
    
    async def _expire_key(self, key: str, ttl: int):
        """Remove key after TTL (simplified implementation)."""
        await asyncio.sleep(ttl)
        self.cache.pop(key, None)


# Global Redis service instance
redis_service = RedisService()