# tests/test_rate_limiter.py
"""
Comprehensive tests for the rate limiting system.

Tests:
- Rate limit parsing and validation
- In-memory token bucket algorithm
- Redis backend (if available)
- FastAPI integration with settings/health endpoints
- Rate limit headers and responses
- Configuration override handling
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request, Response
from fastapi.testclient import TestClient

from app.utils.rate_limiter import (
    parse_rate_limit, 
    InMemoryRateLimiter, 
    RedisRateLimiter,
    RateLimiter, 
    RateLimitExceeded,
    get_rate_limiter,
    apply_rate_limit
)


class TestRateLimitParsing:
    """Test rate limit string parsing."""

    def test_parse_standard_formats(self):
        """Test parsing standard rate limit formats."""
        assert parse_rate_limit("10/min") == (10, 60)
        assert parse_rate_limit("30/sec") == (30, 1)
        assert parse_rate_limit("100/hour") == (100, 3600)
        
    def test_parse_with_multipliers(self):
        """Test parsing with time multipliers."""
        assert parse_rate_limit("5/5min") == (5, 300)  # 5 minutes
        assert parse_rate_limit("1/10sec") == (1, 10)  # 10 seconds
        assert parse_rate_limit("20/2hour") == (20, 7200)  # 2 hours
        
    def test_parse_plural_periods(self):
        """Test parsing with plural time periods."""
        assert parse_rate_limit("15/mins") == (15, 60)
        assert parse_rate_limit("45/secs") == (45, 1)
        assert parse_rate_limit("200/hours") == (200, 3600)
        
    def test_parse_case_insensitive(self):
        """Test case insensitive parsing."""
        assert parse_rate_limit("10/MIN") == (10, 60)
        assert parse_rate_limit("30/Sec") == (30, 1)
        assert parse_rate_limit("100/HOUR") == (100, 3600)
        
    def test_parse_with_whitespace(self):
        """Test parsing with whitespace."""
        assert parse_rate_limit(" 10/min ") == (10, 60)
        assert parse_rate_limit("\t30/sec\n") == (30, 1)
        
    def test_parse_invalid_formats(self):
        """Test parsing invalid formats raises ValueError."""
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            parse_rate_limit("invalid")
        
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            parse_rate_limit("10/day")  # Unsupported period
            
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            parse_rate_limit("abc/min")  # Non-numeric limit


class TestInMemoryRateLimiter:
    """Test in-memory token bucket rate limiter."""

    @pytest.fixture
    def limiter(self):
        """Create in-memory rate limiter for testing."""
        return InMemoryRateLimiter()

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self, limiter):
        """Test that requests within limit are allowed."""
        # Allow 5 requests per minute
        key = "test_ip"
        max_requests, window = 5, 60
        
        # First 5 requests should be allowed
        for i in range(5):
            allowed, metadata = await limiter.is_allowed(key, max_requests, window)
            assert allowed == True
            assert metadata["remaining"] == 4 - i
            assert metadata["limit"] == 5
            assert metadata["retry_after"] == 0

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self, limiter):
        """Test that requests over limit are blocked."""
        key = "test_ip"
        max_requests, window = 2, 60
        
        # First 2 requests allowed
        for i in range(2):
            allowed, _ = await limiter.is_allowed(key, max_requests, window)
            assert allowed == True
        
        # 3rd request blocked
        allowed, metadata = await limiter.is_allowed(key, max_requests, window)
        assert allowed == False
        assert metadata["remaining"] == 0
        assert metadata["retry_after"] > 0

    @pytest.mark.asyncio
    async def test_token_refill_over_time(self, limiter):
        """Test that tokens are refilled over time."""
        key = "test_ip"
        max_requests, window = 2, 2  # 2 requests per 2 seconds
        
        # Exhaust tokens
        for i in range(2):
            await limiter.is_allowed(key, max_requests, window)
        
        # Should be blocked initially
        allowed, _ = await limiter.is_allowed(key, max_requests, window)
        assert allowed == False
        
        # Wait for token refill (simulate time passing)
        with patch('time.time', return_value=time.time() + 1.5):
            allowed, metadata = await limiter.is_allowed(key, max_requests, window)
            assert allowed == True  # Should have ~1.5 tokens refilled

    @pytest.mark.asyncio
    async def test_different_keys_isolated(self, limiter):
        """Test that different keys have isolated limits."""
        max_requests, window = 1, 60
        
        # First key gets one request
        allowed, _ = await limiter.is_allowed("ip1", max_requests, window)
        assert allowed == True
        
        # First key blocked on second request
        allowed, _ = await limiter.is_allowed("ip1", max_requests, window)
        assert allowed == False
        
        # Second key still gets one request
        allowed, _ = await limiter.is_allowed("ip2", max_requests, window)
        assert allowed == True


class TestRedisRateLimiter:
    """Test Redis-backed rate limiter."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.pipeline.return_value.__aenter__.return_value = mock_redis
        mock_redis.pipeline.return_value.__aexit__.return_value = None
        mock_redis.execute.return_value = [None, 0]  # [zremrangebyscore_result, zcard_result]
        mock_redis.zadd.return_value = 1
        mock_redis.expire.return_value = True
        return mock_redis

    @pytest.mark.asyncio
    async def test_redis_connection_success(self, mock_redis):
        """Test successful Redis connection."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            limiter = RedisRateLimiter("redis://localhost:6379")
            redis_client = await limiter._get_redis()
            assert redis_client is not None
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_allows_requests_within_limit(self, mock_redis):
        """Test Redis rate limiter allows requests within limit."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            limiter = RedisRateLimiter("redis://localhost:6379")
            
            # Mock Redis to return 0 current requests (within limit)
            mock_redis.execute.return_value = [None, 0]
            
            allowed, metadata = await limiter.is_allowed("test_ip", 5, 60)
            
            assert allowed == True
            assert metadata["remaining"] == 4
            assert metadata["limit"] == 5
            assert metadata["retry_after"] == 0

    @pytest.mark.asyncio
    async def test_redis_blocks_requests_over_limit(self, mock_redis):
        """Test Redis rate limiter blocks requests over limit."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            limiter = RedisRateLimiter("redis://localhost:6379")
            
            # Mock Redis to return max requests (over limit)
            mock_redis.execute.return_value = [None, 5]  # 5 current requests, limit is 5
            
            allowed, metadata = await limiter.is_allowed("test_ip", 5, 60)
            
            assert allowed == False
            assert metadata["remaining"] == 0
            assert metadata["retry_after"] > 0

    @pytest.mark.asyncio
    async def test_redis_import_error(self):
        """Test handling of missing Redis package."""
        with patch('redis.asyncio', side_effect=ImportError("No module named 'redis'")):
            limiter = RedisRateLimiter("redis://localhost:6379")
            
            with pytest.raises(ImportError, match="redis package is required"):
                await limiter._get_redis()

    @pytest.mark.asyncio
    async def test_redis_connection_error(self):
        """Test handling of Redis connection errors."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            limiter = RedisRateLimiter("redis://localhost:6379")
            
            with pytest.raises(Exception, match="Connection failed"):
                await limiter._get_redis()


class TestRateLimiterMain:
    """Test main RateLimiter class."""

    @pytest.mark.asyncio
    async def test_defaults_to_in_memory_without_redis(self):
        """Test that rate limiter defaults to in-memory without Redis URL."""
        limiter = RateLimiter(redis_url=None)
        backend = await limiter._get_backend()
        assert isinstance(backend, InMemoryRateLimiter)

    @pytest.mark.asyncio
    async def test_uses_redis_when_available(self):
        """Test that rate limiter uses Redis when URL provided and connection succeeds."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            limiter = RateLimiter(redis_url="redis://localhost:6379")
            backend = await limiter._get_backend()
            assert isinstance(backend, RedisRateLimiter)

    @pytest.mark.asyncio
    async def test_falls_back_to_in_memory_on_redis_error(self):
        """Test that rate limiter falls back to in-memory on Redis errors."""
        with patch('redis.asyncio.from_url', side_effect=Exception("Redis unavailable")):
            limiter = RateLimiter(redis_url="redis://localhost:6379")
            backend = await limiter._get_backend()
            assert isinstance(backend, InMemoryRateLimiter)

    def test_get_client_ip_from_headers(self):
        """Test client IP extraction from various headers."""
        limiter = RateLimiter()
        
        # Mock request with X-Forwarded-For
        request = Mock()
        request.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        request.client.host = "127.0.0.1"
        assert limiter.get_client_ip(request) == "192.168.1.100"
        
        # Mock request with X-Real-IP
        request.headers = {"x-real-ip": "203.0.113.42"}
        assert limiter.get_client_ip(request) == "203.0.113.42"
        
        # Mock request with direct client IP
        request.headers = {}
        assert limiter.get_client_ip(request) == "127.0.0.1"

    def test_add_rate_limit_headers(self):
        """Test addition of rate limit headers to response."""
        limiter = RateLimiter()
        response = Mock()
        response.headers = {}
        
        metadata = {
            "limit": 10,
            "remaining": 5,
            "reset_time": 1609459200.0,  # 2021-01-01 00:00:00 UTC
            "retry_after": 30
        }
        
        limiter.add_rate_limit_headers(response, metadata)
        
        assert response.headers["X-RateLimit-Limit"] == "10"
        assert response.headers["X-RateLimit-Remaining"] == "5"
        assert response.headers["X-RateLimit-Reset"] == "1609459200"
        assert response.headers["Retry-After"] == "30"

    @pytest.mark.asyncio
    async def test_check_rate_limit_integration(self):
        """Test rate limit checking with various configurations."""
        limiter = RateLimiter(redis_url=None)  # Use in-memory
        
        # Test within limit
        allowed, metadata = await limiter.check_rate_limit("test_key", "5/min")
        assert allowed == True
        assert metadata["limit"] == 5
        assert metadata["remaining"] == 4


class TestFastAPIIntegration:
    """Test FastAPI integration with rate limiting."""

    def test_rate_limit_exceeded_exception(self):
        """Test RateLimitExceeded exception formatting."""
        exc = RateLimitExceeded(retry_after=60)
        
        assert exc.status_code == 429
        assert exc.detail == {"ok": False, "reason": "rate_limited"}
        assert exc.headers == {"Retry-After": "60"}

    @pytest.mark.asyncio
    async def test_apply_rate_limit_success(self):
        """Test successful rate limit application."""
        request = Mock()
        request.headers = {}
        request.client.host = "127.0.0.1"
        
        response = Mock()
        response.headers = {}
        
        # Should not raise exception for first request
        await apply_rate_limit(request, response, "10/min", "test_scope")
        
        # Verify headers were added
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_apply_rate_limit_exceeded(self):
        """Test rate limit exceeded scenario."""
        request = Mock()
        request.headers = {}
        request.client.host = "127.0.0.1"
        
        response = Mock()
        response.headers = {}
        
        # Exhaust the rate limit (1 request per minute)
        await apply_rate_limit(request, response, "1/min", "test_scope")
        
        # Second request should be blocked
        with pytest.raises(RateLimitExceeded) as exc_info:
            await apply_rate_limit(request, response, "1/min", "test_scope")
        
        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["reason"] == "rate_limited"

    @pytest.mark.asyncio
    async def test_apply_rate_limit_invalid_config(self):
        """Test that invalid rate limit config doesn't block requests."""
        request = Mock()
        request.headers = {}
        request.client.host = "127.0.0.1"
        
        response = Mock()
        response.headers = {}
        
        # Should not raise exception even with invalid config
        await apply_rate_limit(request, response, "invalid_format", "test_scope")

    @pytest.mark.asyncio
    async def test_apply_rate_limit_backend_error(self):
        """Test that backend errors don't block requests."""
        request = Mock()
        request.headers = {}
        request.client.host = "127.0.0.1"
        
        response = Mock()
        response.headers = {}
        
        # Mock rate limiter to raise exception
        with patch('app.utils.rate_limiter.get_rate_limiter') as mock_get_limiter:
            mock_limiter = Mock()
            mock_limiter.get_client_ip.return_value = "127.0.0.1"
            mock_limiter.check_rate_limit.side_effect = Exception("Backend error")
            mock_get_limiter.return_value = mock_limiter
            
            # Should not raise exception on backend errors
            await apply_rate_limit(request, response, "10/min", "test_scope")


class TestSettingsAPIRateLimiting:
    """Test rate limiting integration with settings API."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        from app.main import app
        return app

    @pytest.fixture 
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_settings_get_rate_limited(self, client):
        """Test that settings GET endpoint respects rate limits."""
        # Override rate limit for testing
        with patch('app.core.config.settings.SETTINGS_RATE_LIMIT', "2/min"):
            # First 2 requests should succeed
            for i in range(2):
                response = client.get("/api/v1/settings")
                assert response.status_code == 200
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
            
            # Third request should be rate limited
            response = client.get("/api/v1/settings")
            assert response.status_code == 429
            assert response.json()["detail"]["reason"] == "rate_limited"
            assert "Retry-After" in response.headers

    def test_settings_put_rate_limited(self, client):
        """Test that settings PUT endpoint respects rate limits."""
        with patch('app.core.config.settings.SETTINGS_RATE_LIMIT', "1/min"):
            # First request should succeed  
            response = client.put("/api/v1/settings", json={"PROJECT_NAME": "Test"})
            # Note: might be 401 due to admin auth, but should include rate limit headers
            assert "X-RateLimit-Limit" in response.headers
            
            # Second request should be rate limited
            response = client.put("/api/v1/settings", json={"PROJECT_NAME": "Test2"})
            assert response.status_code == 429

    def test_settings_audit_rate_limited(self, client):
        """Test that settings audit endpoint respects rate limits."""
        with patch('app.core.config.settings.SETTINGS_RATE_LIMIT', "1/min"):
            # First request
            response = client.get("/api/v1/settings/audit")
            assert "X-RateLimit-Limit" in response.headers
            
            # Second request should be rate limited
            response = client.get("/api/v1/settings/audit")
            assert response.status_code == 429

    def test_settings_reset_rate_limited(self, client):
        """Test that settings reset endpoint respects rate limits."""
        with patch('app.core.config.settings.SETTINGS_RATE_LIMIT', "1/min"):
            # First request
            response = client.post("/api/v1/settings/reset")
            assert "X-RateLimit-Limit" in response.headers
            
            # Second request should be rate limited
            response = client.post("/api/v1/settings/reset")
            assert response.status_code == 429


class TestHealthAPIRateLimiting:
    """Test rate limiting integration with health API."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        from app.main import app
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoints_rate_limited(self, client):
        """Test that health endpoints respect rate limits."""
        endpoints = ["/api/v1/health/app", "/api/v1/health/db", "/api/v1/health/exchange", "/api/v1/health"]
        
        with patch('app.core.config.settings.HEALTH_RATE_LIMIT', "2/min"):
            for endpoint in endpoints:
                # Reset rate limiter for each endpoint test
                with patch('app.utils.rate_limiter._global_rate_limiter', None):
                    # First 2 requests should succeed
                    for i in range(2):
                        response = client.get(endpoint)
                        assert response.status_code == 200
                        assert "X-RateLimit-Limit" in response.headers
                        assert response.headers["X-RateLimit-Limit"] == "2"
                    
                    # Third request should be rate limited
                    response = client.get(endpoint)
                    assert response.status_code == 429
                    assert response.json()["detail"]["reason"] == "rate_limited"

    def test_different_scope_isolation(self, client):
        """Test that settings and health endpoints have separate rate limits."""
        with patch('app.core.config.settings.SETTINGS_RATE_LIMIT', "1/min"), \
             patch('app.core.config.settings.HEALTH_RATE_LIMIT', "1/min"):
            
            # Use settings endpoint
            response = client.get("/api/v1/settings")
            assert response.status_code == 200
            
            # Settings endpoint should be rate limited
            response = client.get("/api/v1/settings")  
            assert response.status_code == 429
            
            # But health endpoint should still work (different scope)
            response = client.get("/api/v1/health/app")
            assert response.status_code == 200
            
            # Now health should be rate limited too
            response = client.get("/api/v1/health/app")
            assert response.status_code == 429


class TestConfigurationOverrides:
    """Test rate limiting configuration overrides."""

    def test_settings_rate_limit_override(self):
        """Test that SETTINGS_RATE_LIMIT can be overridden."""
        with patch.dict('os.environ', {'SETTINGS_RATE_LIMIT': '5/min'}):
            from app.core.config import Settings
            settings = Settings()
            assert settings.SETTINGS_RATE_LIMIT == "5/min"

    def test_health_rate_limit_override(self):
        """Test that HEALTH_RATE_LIMIT can be overridden."""
        with patch.dict('os.environ', {'HEALTH_RATE_LIMIT': '60/min'}):
            from app.core.config import Settings
            settings = Settings()
            assert settings.HEALTH_RATE_LIMIT == "60/min"

    def test_redis_url_override(self):
        """Test that REDIS_URL can be overridden."""
        with patch.dict('os.environ', {'REDIS_URL': 'redis://custom:6379/1'}):
            from app.core.config import Settings
            settings = Settings()
            assert settings.REDIS_URL == "redis://custom:6379/1"

    def test_default_values(self):
        """Test default rate limiting values."""
        from app.core.config import Settings
        settings = Settings()
        assert settings.SETTINGS_RATE_LIMIT == "10/min"
        assert settings.HEALTH_RATE_LIMIT == "30/min" 
        assert settings.REDIS_URL is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
