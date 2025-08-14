#!/usr/bin/env python3
"""
Rate Limiting Smoke Test + Parity Check (Fixed Version)
Tests with environment variable overrides before app initialization.
"""

import sys
import os
import importlib

# Set environment variables BEFORE importing the app
os.environ['SETTINGS_RATE_LIMIT'] = '3/min'  
os.environ['HEALTH_RATE_LIMIT'] = '5/min'

# Now we can import after setting environment
sys.path.insert(0, '.')

# Force reload of config to pick up environment variables
if 'app.core.config' in sys.modules:
    importlib.reload(sys.modules['app.core.config'])
if 'app.main' in sys.modules:
    importlib.reload(sys.modules['app.main'])

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
import json

def test_settings_rate_limiting():
    """Test settings endpoints with 3/min rate limit."""
    print("1️⃣ TESTING SETTINGS ENDPOINTS (3/min)")
    print("=" * 50)
    
    print(f"🔧 Configured SETTINGS_RATE_LIMIT: {settings.SETTINGS_RATE_LIMIT}")
    
    client = TestClient(app)
    results = []
    headers_data = []
    
    # Send 4 quick PUT requests
    test_data = {"PROJECT_NAME": f"TestProject"}
    
    for i in range(1, 5):
        print(f"Request {i}: PUT /api/v1/settings/")
        response = client.put("/api/v1/settings/", json=test_data)
        
        status = response.status_code
        results.append(status)
        
        # Collect headers
        rate_headers = {
            'limit': response.headers.get('x-ratelimit-limit', 'NOT_FOUND'),
            'remaining': response.headers.get('x-ratelimit-remaining', 'NOT_FOUND'),
            'retry_after': response.headers.get('retry-after', 'NOT_FOUND')
        }
        headers_data.append(rate_headers)
        
        print(f"  Status: {status}")
        print(f"  Limit: {rate_headers['limit']}")
        print(f"  Remaining: {rate_headers['remaining']}")
        
        if status == 429:
            print(f"  Retry-After: {rate_headers['retry_after']}")
            try:
                body = response.json()
                print(f"  Body: {body}")
                if 'detail' in body and isinstance(body['detail'], dict):
                    detail = body['detail']
                    if detail.get('ok') is False and detail.get('reason') == 'rate_limited':
                        print("  ✅ Correct 429 response format")
                    else:
                        print("  ❌ Incorrect 429 response format")
            except:
                print("  ❌ Could not parse 429 response body")
        print()
    
    # Summary
    success_count = len([r for r in results if r == 200])
    rate_limited_count = len([r for r in results if r == 429])
    
    print(f"📊 RESULTS: {success_count} success, {rate_limited_count} rate-limited")
    expected_success = 3
    expected_rate_limited = 1
    
    if success_count == expected_success and rate_limited_count == expected_rate_limited:
        print("✅ Settings rate limiting working correctly!")
        success = True
    else:
        print(f"❌ Expected {expected_success} success + {expected_rate_limited} rate-limited")
        success = False
    
    return results, headers_data, success

def test_health_rate_limiting():
    """Test health endpoints with 5/min rate limit."""
    print("\n2️⃣ TESTING HEALTH ENDPOINTS (5/min)")
    print("=" * 50)
    
    print(f"🔧 Configured HEALTH_RATE_LIMIT: {settings.HEALTH_RATE_LIMIT}")
    
    client = TestClient(app)
    results = []
    headers_data = []
    
    # Send 6 quick GET requests
    for i in range(1, 7):
        print(f"Request {i}: GET /api/v1/health/app")
        response = client.get("/api/v1/health/app")
        
        status = response.status_code
        results.append(status)
        
        # Collect headers
        rate_headers = {
            'limit': response.headers.get('x-ratelimit-limit', 'NOT_FOUND'),
            'remaining': response.headers.get('x-ratelimit-remaining', 'NOT_FOUND'),
            'retry_after': response.headers.get('retry-after', 'NOT_FOUND')
        }
        headers_data.append(rate_headers)
        
        print(f"  Status: {status}")
        print(f"  Limit: {rate_headers['limit']}")
        print(f"  Remaining: {rate_headers['remaining']}")
        
        if status == 429:
            print(f"  Retry-After: {rate_headers['retry_after']}")
            try:
                body = response.json()
                print(f"  Body: {body}")
            except:
                print("  Could not parse response body")
        print()
    
    # Summary
    success_count = len([r for r in results if r == 200])
    rate_limited_count = len([r for r in results if r == 429])
    
    print(f"📊 RESULTS: {success_count} success, {rate_limited_count} rate-limited")
    expected_success = 5
    expected_rate_limited = 1
    
    if success_count == expected_success and rate_limited_count == expected_rate_limited:
        print("✅ Health rate limiting working correctly!")
        success = True
    else:
        print(f"❌ Expected {expected_success} success + {expected_rate_limited} rate-limited")
        success = False
    
    return results, headers_data, success

def test_parity_checks():
    """Test parity - OpenAPI and basic functionality."""
    print("\n3️⃣ PARITY CHECKS")
    print("=" * 50)
    
    client = TestClient(app)
    
    # Test 1: OpenAPI endpoint
    print("Testing /openapi.json accessibility...")
    try:
        response = client.get("/openapi.json")
        if response.status_code == 200:
            openapi_data = response.json()
            paths = openapi_data.get('paths', {})
            endpoint_count = len(paths)
            print(f"✅ /openapi.json reachable")
            print(f"📈 Current endpoint count: {endpoint_count}")
            
            # Show some key endpoints
            key_endpoints = [ep for ep in paths.keys() if any(key in ep for key in ['/settings', '/health', '/trading'])]
            if key_endpoints:
                print(f"🔍 Key endpoints found: {len(key_endpoints)}")
                for ep in key_endpoints[:5]:  # Show first 5
                    print(f"   - {ep}")
                if len(key_endpoints) > 5:
                    print(f"   ... and {len(key_endpoints) - 5} more")
            
            openapi_success = True
        else:
            print(f"❌ /openapi.json not accessible (status: {response.status_code})")
            endpoint_count = 0
            openapi_success = False
            
    except Exception as e:
        print(f"❌ Error accessing /openapi.json: {e}")
        endpoint_count = 0
        openapi_success = False
    
    # Test 2: Basic functionality without rate limits
    print("\nTesting basic endpoint functionality...")
    basic_tests = [
        ("/api/v1/health/app", "GET", "Health App"),
        ("/api/v1/health/", "GET", "Health Root"),
        ("/api/v1/settings/", "GET", "Settings Get"),
    ]
    
    basic_results = []
    for endpoint, method, name in basic_tests:
        try:
            if method == "GET":
                resp = client.get(endpoint)
            else:
                resp = client.request(method, endpoint)
            
            status = resp.status_code
            basic_results.append((name, status, status in [200, 307]))  # 307 is redirect, also OK
            print(f"  {name}: {status} {'✅' if status in [200, 307] else '❌'}")
            
        except Exception as e:
            basic_results.append((name, 0, False))
            print(f"  {name}: Error - {e} ❌")
    
    # Summary
    working_endpoints = len([r for r in basic_results if r[2]])
    total_endpoints = len(basic_results)
    
    print(f"\n📊 Basic functionality: {working_endpoints}/{total_endpoints} endpoints working")
    
    functionality_success = working_endpoints == total_endpoints
    
    return openapi_success, endpoint_count, functionality_success

def run_full_tests():
    """Run pytest and report results."""
    print("\n4️⃣ RUNNING FULL TESTS")
    print("=" * 50)
    
    # Run pytest on core functionality
    import subprocess
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/test_rate_limiter.py', 
            '-v', '--tb=short'
        ], 
        capture_output=True, 
        text=True, 
        cwd='.',
        timeout=60
        )
        
        print("Full test output (last 20 lines):")
        output_lines = result.stdout.split('\n')
        for line in output_lines[-20:]:
            if line.strip():
                print(f"  {line}")
        
        if result.stderr:
            print("Errors:")
            error_lines = result.stderr.split('\n')
            for line in error_lines[-10:]:
                if line.strip():
                    print(f"  {line}")
        
        test_success = result.returncode == 0
        print(f"\n📊 Full tests: {'✅ PASSED' if test_success else '❌ FAILED'}")
        
        return test_success
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def main():
    """Run all smoke tests."""
    print("🚀 RATE LIMITING SMOKE TEST + PARITY CHECK (FIXED)")
    print("=" * 60)
    print()
    
    try:
        # Test 1: Settings rate limiting
        settings_results, settings_headers, settings_success = test_settings_rate_limiting()
        
        # Test 2: Health rate limiting  
        health_results, health_headers, health_success = test_health_rate_limiting()
        
        # Test 3: Parity checks
        openapi_ok, endpoint_count, functionality_ok = test_parity_checks()
        
        # Test 4: Full test suite
        full_tests_ok = run_full_tests()
        
        # Final Summary
        print("\n" + "=" * 60)
        print("📋 FINAL SUMMARY")
        print("=" * 60)
        
        # Settings summary
        settings_429 = [i+1 for i, r in enumerate(settings_results) if r == 429]
        settings_headers_found = any(h['limit'] != 'NOT_FOUND' for h in settings_headers)
        print(f"Settings (3/min): Requests {settings_429} hit 429, Headers present: {settings_headers_found}")
        
        # Health summary  
        health_429 = [i+1 for i, r in enumerate(health_results) if r == 429]
        health_headers_found = any(h['limit'] != 'NOT_FOUND' for h in health_headers)
        print(f"Health (5/min): Requests {health_429} hit 429, Headers present: {health_headers_found}")
        
        # Parity summary
        print(f"OpenAPI: {'✅ Reachable' if openapi_ok else '❌ Failed'}, Endpoints: {endpoint_count}")
        print(f"Basic functionality: {'✅ Working' if functionality_ok else '❌ Failed'}")
        print(f"Full test suite: {'✅ PASSED' if full_tests_ok else '❌ FAILED'}")
        
        # Overall status
        all_good = (
            settings_success and health_success and
            openapi_ok and functionality_ok and
            full_tests_ok
        )
        
        if all_good:
            print("\n🎉 ALL TESTS PASSED - Rate limiting system working perfectly!")
        else:
            print("\n⚠️  Some tests failed - see details above")
            
            # Show what failed
            if not settings_success:
                print("   - Settings rate limiting not working as expected")
            if not health_success:
                print("   - Health rate limiting not working as expected") 
            if not openapi_ok:
                print("   - OpenAPI endpoint not accessible")
            if not functionality_ok:
                print("   - Basic functionality issues")
            if not full_tests_ok:
                print("   - Full test suite failed")
        
        return all_good
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
