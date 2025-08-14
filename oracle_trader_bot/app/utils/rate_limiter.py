# app/utils/rate_limiter.py
"""
Lightweight, configurable rate limiting with Redis or in-memory backend support.

Features:
- Configurable rate limits (e.g., "10/min", "30/sec")
- Redis backend for distributed rate limiting (optional)
- In-memory token bucket fallback for single-process/dev environments
- Standard rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After
- FastAPI dependency integration
- Zero feature loss - only enforces limits when exceeded
"""

import asyncio
import time
import re
from typing import Dict, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field
from fastapi import HTTPException, Request, Response
from fastapi.security.utils import get_authorization_scheme_param
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limit information for a specific key."""
    tokens: float
    last_refill: float
    window_start: float = field(default_factory=time.time)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=429,
            detail={"ok": False, "reason": "rate_limited"},
            headers={"Retry-After": str(retry_after)}
        )


def parse_rate_limit(rate_string: str) -> Tuple[int, int]:
    """
    Parse rate limit string into (max_requests, window_seconds).
    
    Examples:
        "10/min" -> (10, 60)
        "30/sec" -> (30, 1)  
        "100/hour" -> (100, 3600)
        "5/5min" -> (5, 300)
    
    Args:
        rate_string: Rate limit string in format "N/period"
        
    Returns:
        Tuple of (max_requests, window_seconds)
        
    Raises:
        ValueError: If rate string format is invalid
    """
    pattern = r'^(\d+)/(\d*)?(sec|min|hour)s?$'
    match = re.match(pattern, rate_string.strip().lower())
    
    if not match:
        raise ValueError(f"Invalid rate limit format: {rate_string}. Expected format: 'N/period' (e.g., '10/min', '30/sec')")
    
    max_requests = int(match.group(1))
    multiplier = int(match.group(2) or 1)
    period = match.group(3)
    
    # Convert period to seconds
    if period == "sec":
        window_seconds = 1 * multiplier
    elif period == "min":
        window_seconds = 60 * multiplier
    elif period == "hour":
        window_seconds = 3600 * multiplier
    else:
        raise ValueError(f"Unsupported time period: {period}")
    
    return max_requests, window_seconds


class InMemoryRateLimiter:
    """
    In-memory token bucket rate limiter for single-process environments.
    Uses token bucket algorithm with automatic token refill.
    """
    
    def __init__(self):
        self._buckets: Dict[str, RateLimitInfo] = {}
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Rate limit key (e.g., IP address)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (allowed, metadata) where metadata contains:
            - remaining: Remaining requests
            - reset_time: When the bucket resets
            - retry_after: Seconds to wait if blocked
        """
        async with self._lock:
            now = time.time()
            
            # Get or create bucket for this key
            if key not in self._buckets:
                self._buckets[key] = RateLimitInfo(
                    tokens=max_requests,
                    last_refill=now,
                    window_start=now
                )
            
            bucket = self._buckets[key]
            
            # Calculate tokens to add based on time elapsed
            time_elapsed = now - bucket.last_refill
            tokens_to_add = (time_elapsed / window_seconds) * max_requests
            
            # Refill tokens, but don't exceed max capacity
            bucket.tokens = min(max_requests, bucket.tokens + tokens_to_add)
            bucket.last_refill = now
            
            # Check if we have tokens available
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                allowed = True
                remaining = int(bucket.tokens)
                retry_after = 0
            else:
                allowed = False
                remaining = 0
                # Calculate time needed to get one token
                retry_after = max(1, int(window_seconds / max_requests))
            
            # Calculate reset time (when bucket will be full again)
            tokens_needed = max_requests - bucket.tokens
            reset_time = now + (tokens_needed / max_requests) * window_seconds
            
            metadata = {
                "remaining": remaining,
                "reset_time": reset_time,
                "retry_after": retry_after,
                "limit": max_requests,
                "window": window_seconds
            }
            
            return allowed, metadata


class RedisRateLimiter:
    """
    Redis-backed distributed rate limiter using sliding window algorithm.
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None
    
    async def _get_redis(self):
        """Lazy Redis connection initialization."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                await self._redis.ping()
                logger.info(f"Redis rate limiter connected to {self.redis_url}")
            except ImportError:
                raise ImportError("redis package is required for Redis rate limiting. Install with: pip install redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis at {self.redis_url}: {e}")
                raise
        return self._redis
    
    async def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed using Redis sliding window.
        
        Uses Redis sorted sets to implement sliding window rate limiting.
        """
        redis_client = await self._get_redis()
        now = time.time()
        window_start = now - window_seconds
        
        # Redis key for this rate limit bucket
        redis_key = f"rate_limit:{key}"
        
        async with redis_client.pipeline() as pipe:
            # Remove expired entries
            await pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests in window
            await pipe.zcard(redis_key)
            
            # Execute pipeline
            results = await pipe.execute()
            current_requests = results[1]
            
            if current_requests < max_requests:
                # Add current request timestamp
                await redis_client.zadd(redis_key, {str(now): now})
                await redis_client.expire(redis_key, window_seconds + 1)  # Cleanup key
                
                allowed = True
                remaining = max_requests - current_requests - 1
                retry_after = 0
            else:
                allowed = False
                remaining = 0
                retry_after = max(1, int(window_seconds / max_requests))
            
            reset_time = now + window_seconds
            
            metadata = {
                "remaining": remaining,
                "reset_time": reset_time,
                "retry_after": retry_after,
                "limit": max_requests,
                "window": window_seconds
            }
            
            return allowed, metadata


class RateLimiter:
    """
    Main rate limiter class that automatically selects Redis or in-memory backend.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self._backend = None
    
    async def _get_backend(self):
        """Initialize and return appropriate rate limiting backend."""
        if self._backend is None:
            if self.redis_url:
                try:
                    self._backend = RedisRateLimiter(self.redis_url)
                    # Test the connection
                    await self._backend._get_redis()
                    logger.info("Using Redis backend for rate limiting")
                except Exception as e:
                    logger.warning(f"Redis backend failed, falling back to in-memory: {e}")
                    self._backend = InMemoryRateLimiter()
            else:
                self._backend = InMemoryRateLimiter()
                logger.info("Using in-memory backend for rate limiting")
        
        return self._backend
    
    async def check_rate_limit(self, key: str, rate_string: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limit.
        
        Args:
            key: Rate limit identifier (usually IP address)
            rate_string: Rate limit specification (e.g., "10/min")
            
        Returns:
            Tuple of (allowed, metadata)
        """
        max_requests, window_seconds = parse_rate_limit(rate_string)
        backend = await self._get_backend()
        return await backend.is_allowed(key, max_requests, window_seconds)
    
    def get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request, considering proxy headers.
        """
        # Check for proxy headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client IP
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    def add_rate_limit_headers(self, response: Response, metadata: Dict[str, Any]) -> None:
        """
        Add standard rate limit headers to response.
        """
        response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
        
        # Add reset time as Unix timestamp
        response.headers["X-RateLimit-Reset"] = str(int(metadata["reset_time"]))
        
        if metadata["retry_after"] > 0:
            response.headers["Retry-After"] = str(metadata["retry_after"])


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get or create global rate limiter instance.
    """
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        from app.core.config import settings
        _global_rate_limiter = RateLimiter(redis_url=settings.REDIS_URL)
    
    return _global_rate_limiter


async def apply_rate_limit(request: Request, response: Response, rate_string: str, scope: str = "default") -> None:
    """
    Apply rate limiting to a request.
    
    Args:
        request: FastAPI request object
        response: FastAPI response object  
        rate_string: Rate limit specification (e.g., "10/min")
        scope: Rate limit scope for key generation
        
    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    limiter = get_rate_limiter()
    client_ip = limiter.get_client_ip(request)
    
    # Create scoped key for rate limiting
    rate_key = f"{scope}:{client_ip}"
    
    try:
        allowed, metadata = await limiter.check_rate_limit(rate_key, rate_string)
        
        # Always add rate limit headers
        limiter.add_rate_limit_headers(response, metadata)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_ip} on {scope}: {rate_string}")
            raise RateLimitExceeded(retry_after=metadata["retry_after"])
            
    except RateLimitExceeded:
        # Re-raise rate limit exceptions
        raise
    except ValueError as e:
        logger.error(f"Invalid rate limit configuration '{rate_string}': {e}")
        # Don't block request on configuration errors
    except Exception as e:
        logger.error(f"Rate limiting error for {client_ip}: {e}")
        # Don't block request on rate limiter failures


def rate_limit(rate_string: str, scope: str = "default"):
    """
    FastAPI dependency factory for rate limiting.
    
    Usage:
        @router.get("/api/v1/settings")
        async def get_settings(
            request: Request,
            response: Response,
            _: None = Depends(rate_limit("10/min", "settings"))
        ):
            ...
    
    Args:
        rate_string: Rate limit specification (e.g., "10/min")
        scope: Rate limit scope identifier
        
    Returns:
        FastAPI dependency function
    """
    async def dependency(request: Request, response: Response) -> None:
        await apply_rate_limit(request, response, rate_string, scope)
    
    return dependency
