#!/usr/bin/env python3
"""
Quick integration test for rate limiting functionality.
Tests the rate limiter against actual FastAPI endpoints.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from unittest.mock import patch

def test_rate_limiting_integration():
    """Test that rate limiting works with actual endpoints."""
    print("🧪 Testing Rate Limiting Integration")
    
    # Import after setting up path
    from app.main import app
    
    with TestClient(app) as client:
        # Test with very restrictive rate limit
        with patch('app.core.config.settings.SETTINGS_RATE_LIMIT', '1/min'):
            print("\n📊 Testing /api/v1/settings with 1/min rate limit...")
            
            # First request should succeed
            response1 = client.get("/api/v1/settings")
            print(f"Request 1: status={response1.status_code}")
            
            # Check rate limit headers
            if "X-RateLimit-Limit" in response1.headers:
                limit = response1.headers["X-RateLimit-Limit"]
                remaining = response1.headers["X-RateLimit-Remaining"]
                print(f"✅ Rate limit headers: Limit={limit}, Remaining={remaining}")
            else:
                print("❌ Rate limit headers missing")
                return False
            
            # Second request should be rate limited
            response2 = client.get("/api/v1/settings")
            print(f"Request 2: status={response2.status_code}")
            
            if response2.status_code == 429:
                print("✅ Rate limiting works! Second request blocked with 429")
                data = response2.json()
                if data.get("detail", {}).get("reason") == "rate_limited":
                    print("✅ Rate limit response format correct")
                    
                if "Retry-After" in response2.headers:
                    retry_after = response2.headers["Retry-After"]
                    print(f"✅ Retry-After header present: {retry_after}")
                else:
                    print("❌ Retry-After header missing")
                    
                return True
            else:
                print(f"❌ Expected 429 but got {response2.status_code}")
                return False

def test_health_rate_limiting():
    """Test rate limiting on health endpoints."""
    print("\n🏥 Testing Health endpoint rate limiting")
    
    from app.main import app
    
    with TestClient(app) as client:
        with patch('app.core.config.settings.HEALTH_RATE_LIMIT', '2/min'):
            print("Testing /api/v1/health/app with 2/min rate limit...")
            
            # First 2 requests should succeed
            success_count = 0
            for i in range(2):
                response = client.get("/api/v1/health/app")
                print(f"Request {i+1}: status={response.status_code}")
                if response.status_code == 200:
                    success_count += 1
                    if "X-RateLimit-Limit" in response.headers:
                        remaining = response.headers.get("X-RateLimit-Remaining")
                        print(f"  Remaining: {remaining}")
            
            # Third request should be blocked
            response = client.get("/api/v1/health/app")
            print(f"Request 3: status={response.status_code}")
            
            if response.status_code == 429 and success_count == 2:
                print("✅ Health endpoint rate limiting works!")
                return True
            else:
                print(f"❌ Expected 2 success + 1 blocked, got {success_count} success, final status {response.status_code}")
                return False

def test_scope_isolation():
    """Test that different scopes have isolated rate limits."""
    print("\n🔒 Testing scope isolation (settings vs health)")
    
    from app.main import app
    
    with TestClient(app) as client:
        with patch('app.core.config.settings.SETTINGS_RATE_LIMIT', '1/min'), \
             patch('app.core.config.settings.HEALTH_RATE_LIMIT', '1/min'):
            
            # Use up settings rate limit
            response1 = client.get("/api/v1/settings")
            response2 = client.get("/api/v1/settings")
            
            print(f"Settings request 1: {response1.status_code}")
            print(f"Settings request 2: {response2.status_code}")
            
            # Settings should be blocked
            if response2.status_code != 429:
                print("❌ Settings rate limit not working")
                return False
            
            # But health should still work (different scope)
            health_response = client.get("/api/v1/health/app")
            print(f"Health request: {health_response.status_code}")
            
            if health_response.status_code == 200:
                print("✅ Scope isolation works! Health not affected by settings rate limit")
                return True
            else:
                print("❌ Scope isolation failed - health blocked by settings limit")
                return False

def main():
    """Run integration tests."""
    print("🚀 Rate Limiting Integration Tests")
    print("=" * 50)
    
    tests = [
        test_rate_limiting_integration,
        test_health_rate_limiting,
        test_scope_isolation
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
                print("✅ PASSED\n")
            else:
                print("❌ FAILED\n")
        except Exception as e:
            print(f"💥 ERROR: {e}\n")
    
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All rate limiting tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
