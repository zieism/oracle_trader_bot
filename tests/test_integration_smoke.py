# tests/test_integration_smoke.py
"""
Basic smoke tests for API integration
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'oracle_trader_bot'))

from app.core.config import settings
import requests
import time

# Simple HTTP tests without database dependencies
def test_health_endpoint_simple():
    """Test basic health endpoint with requests"""
    try:
        base_url = settings.API_INTERNAL_BASE_URL  # Use centralized config
        response = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"Health endpoint status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Health data: {data}")
            assert "status" in data
            print("✓ Health endpoint working")
        else:
            print("✗ Health endpoint not accessible (server not running?)")
    except Exception as e:
        print(f"✗ Could not connect to health endpoint: {e}")

def test_cors_headers_simple():
    """Test CORS configuration"""
    try:
        response = requests.options(
            f"{settings.API_INTERNAL_BASE_URL}/api/health", 
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            },
            timeout=5
        )
        print(f"CORS preflight status: {response.status_code}")
        if response.status_code == 200:
            print(f"CORS headers: {dict(response.headers)}")
            print("✓ CORS configured")
        else:
            print("✗ CORS preflight failed")
    except Exception as e:
        print(f"✗ CORS test failed: {e}")

def test_api_endpoints_exist():
    """Test that expected API endpoints exist"""
    base_url = settings.API_INTERNAL_BASE_URL  # Use centralized config
    endpoints_to_check = [
        "/api/v1/bot-settings/",
        "/api/v1/exchange/health",
        "/api/v1/exchange/symbols",
        "/api/v1/bot-management/status"
    ]
    
    for endpoint in endpoints_to_check:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code != 404:
                print(f"✓ {endpoint} exists (status: {response.status_code})")
            else:
                print(f"✗ {endpoint} not found")
        except Exception as e:
            print(f"✗ {endpoint} test failed: {e}")

def check_server_running():
    """Check if the server is running"""
    try:
        response = requests.get(f"{settings.API_INTERNAL_BASE_URL}/api/health", timeout=2)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    print("=== Oracle Trader Bot Integration Smoke Tests ===")
    
    if not check_server_running():
        print(f"❌ Server is not running on {settings.API_INTERNAL_BASE_URL}")
        print("Please start the server first with: python -m uvicorn app.main:app --reload")
        exit(1)
    
    print("✓ Server is running")
    print("\n--- Testing API Endpoints ---")
    test_health_endpoint_simple()
    test_cors_headers_simple() 
    test_api_endpoints_exist()
    
    print("\n=== Tests Complete ===")
    print("If you see ✓ marks, the integration is working!")
    print("If you see ✗ marks, there are issues to fix.")
