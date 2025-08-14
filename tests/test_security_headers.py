"""
Tests for Security Headers Middleware.

Tests that security headers are correctly added or omitted based on configuration.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'oracle_trader_bot'))

from app.main import app
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.core.config import settings


class TestSecurityHeadersMiddleware:
    """Test security headers middleware functionality."""

    def test_default_security_headers_enabled(self):
        """Test that default security headers are present when enabled."""
        client = TestClient(app)
        
        response = client.get("/api/v1/health/app")
        
        # Default headers should be present
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("referrer-policy") == "no-referrer"
        
        # CSP should NOT be present by default (disabled)
        assert "content-security-policy" not in response.headers

    def test_strict_transport_security_https_only(self):
        """Test that HSTS header is only added for HTTPS requests."""
        client = TestClient(app)
        
        # HTTP request - HSTS should not be present
        response = client.get("/api/v1/health/app")
        assert "strict-transport-security" not in response.headers
        
        # Simulate HTTPS request via X-Forwarded-Proto header
        response = client.get("/api/v1/health/app", headers={"X-Forwarded-Proto": "https"})
        assert response.headers.get("strict-transport-security") == "max-age=15552000"

    def test_content_security_policy_when_enabled(self):
        """Test CSP header when enabled via settings."""
        with patch.object(settings, 'SECURITY_HEADERS_CONTENT_SECURITY_POLICY', True):
            client = TestClient(app)
            response = client.get("/api/v1/health/app")
            
            assert response.headers.get("content-security-policy") == "default-src 'self'"

    def test_x_content_type_options_when_disabled(self):
        """Test X-Content-Type-Options header when disabled."""
        with patch.object(settings, 'SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS', False):
            client = TestClient(app)
            response = client.get("/api/v1/health/app")
            
            assert "x-content-type-options" not in response.headers

    def test_x_frame_options_when_disabled(self):
        """Test X-Frame-Options header when disabled."""
        with patch.object(settings, 'SECURITY_HEADERS_X_FRAME_OPTIONS', False):
            client = TestClient(app)
            response = client.get("/api/v1/health/app")
            
            assert "x-frame-options" not in response.headers

    def test_referrer_policy_when_disabled(self):
        """Test Referrer-Policy header when disabled."""
        with patch.object(settings, 'SECURITY_HEADERS_REFERRER_POLICY', False):
            client = TestClient(app)
            response = client.get("/api/v1/health/app")
            
            assert "referrer-policy" not in response.headers

    def test_strict_transport_security_when_disabled(self):
        """Test HSTS header when disabled."""
        with patch.object(settings, 'SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY', False):
            client = TestClient(app)
            
            # Even with HTTPS, HSTS should not be present when disabled
            response = client.get("/api/v1/health/app", headers={"X-Forwarded-Proto": "https"})
            assert "strict-transport-security" not in response.headers

    def test_all_headers_disabled(self):
        """Test that no security headers are present when all disabled."""
        with patch.object(settings, 'SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS', False), \
             patch.object(settings, 'SECURITY_HEADERS_X_FRAME_OPTIONS', False), \
             patch.object(settings, 'SECURITY_HEADERS_REFERRER_POLICY', False), \
             patch.object(settings, 'SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY', False), \
             patch.object(settings, 'SECURITY_HEADERS_CONTENT_SECURITY_POLICY', False):
            
            client = TestClient(app)
            response = client.get("/api/v1/health/app", headers={"X-Forwarded-Proto": "https"})
            
            # No security headers should be present
            assert "x-content-type-options" not in response.headers
            assert "x-frame-options" not in response.headers
            assert "referrer-policy" not in response.headers
            assert "strict-transport-security" not in response.headers
            assert "content-security-policy" not in response.headers

    def test_all_headers_enabled(self):
        """Test that all security headers are present when all enabled."""
        with patch.object(settings, 'SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS', True), \
             patch.object(settings, 'SECURITY_HEADERS_X_FRAME_OPTIONS', True), \
             patch.object(settings, 'SECURITY_HEADERS_REFERRER_POLICY', True), \
             patch.object(settings, 'SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY', True), \
             patch.object(settings, 'SECURITY_HEADERS_CONTENT_SECURITY_POLICY', True):
            
            client = TestClient(app)
            response = client.get("/api/v1/health/app", headers={"X-Forwarded-Proto": "https"})
            
            # All security headers should be present
            assert response.headers.get("x-content-type-options") == "nosniff"
            assert response.headers.get("x-frame-options") == "DENY"
            assert response.headers.get("referrer-policy") == "no-referrer"
            assert response.headers.get("strict-transport-security") == "max-age=15552000"
            assert response.headers.get("content-security-policy") == "default-src 'self'"

    def test_headers_on_different_endpoints(self):
        """Test that security headers are applied to different endpoints."""
        client = TestClient(app)
        
        endpoints_to_test = [
            "/api/v1/health/app",
            "/api/v1/health/",
            "/api/v1/settings/",
            "/openapi.json"
        ]
        
        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            
            # Basic security headers should be present regardless of endpoint
            if response.status_code == 200:  # Only check successful responses
                assert response.headers.get("x-content-type-options") == "nosniff"
                assert response.headers.get("x-frame-options") == "DENY"
                assert response.headers.get("referrer-policy") == "no-referrer"

    def test_https_detection_methods(self):
        """Test different methods of HTTPS detection."""
        client = TestClient(app)
        
        # Test X-Forwarded-Proto
        response = client.get("/api/v1/health/app", headers={"X-Forwarded-Proto": "https"})
        assert response.headers.get("strict-transport-security") == "max-age=15552000"
        
        # Test X-Forwarded-Protocol (alternative)
        response = client.get("/api/v1/health/app", headers={"X-Forwarded-Protocol": "https"})
        assert response.headers.get("strict-transport-security") == "max-age=15552000"
        
        # Test case insensitive
        response = client.get("/api/v1/health/app", headers={"X-Forwarded-Proto": "HTTPS"})
        assert response.headers.get("strict-transport-security") == "max-age=15552000"

    def test_compatibility_with_existing_middleware(self):
        """Test that security headers don't interfere with CORS and rate limiting."""
        client = TestClient(app)
        
        # Test CORS headers still present
        response = client.options("/api/v1/health/app", headers={"Origin": "http://localhost:3000"})
        assert "access-control-allow-origin" in response.headers
        
        # Test rate limiting headers still present (make a request to trigger rate limiting)
        response = client.get("/api/v1/health/app")
        # Should have both security headers and rate limit headers
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert "x-ratelimit-limit" in response.headers  # From rate limiting middleware

    def test_security_headers_on_error_responses(self):
        """Test that security headers are added even to error responses."""
        client = TestClient(app)
        
        # Test 404 response
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("referrer-policy") == "no-referrer"


class TestSecurityHeadersMiddlewareUnit:
    """Unit tests for SecurityHeadersMiddleware class methods."""

    def test_is_https_request_with_https_scheme(self):
        """Test HTTPS detection with https:// scheme."""
        from starlette.requests import Request
        from starlette.datastructures import URL
        
        middleware = SecurityHeadersMiddleware(app=None)
        
        # Mock request with HTTPS scheme
        request = Request({
            "type": "http",
            "method": "GET", 
            "url": URL("https://example.com/test"),
            "headers": [],
            "query_string": b"",
            "path_info": "/test"
        })
        
        assert middleware._is_https_request(request) is True

    def test_is_https_request_with_http_scheme(self):
        """Test HTTPS detection with http:// scheme."""
        from starlette.requests import Request
        from starlette.datastructures import URL
        
        middleware = SecurityHeadersMiddleware(app=None)
        
        # Mock request with HTTP scheme
        request = Request({
            "type": "http",
            "method": "GET",
            "url": URL("http://example.com/test"),
            "headers": [],
            "query_string": b"",
            "path_info": "/test"
        })
        
        assert middleware._is_https_request(request) is False

    def test_is_https_request_with_forwarded_headers(self):
        """Test HTTPS detection with forwarded headers."""
        from starlette.requests import Request
        from starlette.datastructures import URL, Headers
        
        middleware = SecurityHeadersMiddleware(app=None)
        
        # Test X-Forwarded-Proto
        request = Request({
            "type": "http",
            "method": "GET",
            "url": URL("http://example.com/test"),
            "headers": Headers([("x-forwarded-proto", "https")]).raw,
            "query_string": b"",
            "path_info": "/test"
        })
        
        assert middleware._is_https_request(request) is True
        
        # Test X-Forwarded-Protocol
        request = Request({
            "type": "http",
            "method": "GET",
            "url": URL("http://example.com/test"),
            "headers": Headers([("x-forwarded-protocol", "https")]).raw,
            "query_string": b"",
            "path_info": "/test"
        })
        
        assert middleware._is_https_request(request) is True
