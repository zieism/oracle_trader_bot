#!/usr/bin/env python3
"""
Direct Settings Test - Manual approach for smoke testing
"""

import requests
import json
import time
import subprocess
import sys
import os
from pathlib import Path

def log(message, level="INFO"):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_settings_endpoints():
    """Test settings endpoints directly"""
    base_url = "http://localhost:8000"
    
    log("Testing settings endpoints...")
    
    try:
        # Test GET /api/v1/settings
        log("Testing GET /api/v1/settings")
        response = requests.get(f"{base_url}/api/v1/settings", timeout=5)
        log(f"GET settings: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log(f"✅ GET settings successful - {len(data)} fields received")
            
            # Check secret masking
            secret_fields = ["kucoin_api_key", "kucoin_api_secret", "kucoin_api_passphrase"]
            masked_count = sum(1 for field in secret_fields if data.get(field) == "***")
            log(f"   Secret masking: {masked_count}/{len(secret_fields)} fields masked")
            
            # Show sample of data (redacted)
            sample_fields = ["trading_enabled", "kucoin_sandbox", "position_size_percent"]
            sample_data = {k: data.get(k) for k in sample_fields if k in data}
            log(f"   Sample data: {sample_data}")
            
        else:
            log(f"❌ GET settings failed: {response.status_code} - {response.text}")
            return False
        
        # Test exchange health before credentials
        log("Testing GET /api/v1/health/exchange (before creds)")
        response = requests.get(f"{base_url}/api/v1/health/exchange", timeout=5)
        log(f"Exchange health (before): {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Exchange health (before): ok={data.get('ok')}, mode='{data.get('mode')}'")
            before_mode = data.get('mode')
        else:
            log(f"❌ Exchange health (before) failed: {response.status_code}")
            before_mode = None
        
        # Test PUT /api/v1/settings with sandbox credentials
        log("Testing PUT /api/v1/settings with sandbox credentials")
        settings_update = {
            "kucoin_api_key": "test_sandbox_key_12345",
            "kucoin_api_secret": "test_sandbox_secret_67890",
            "kucoin_api_passphrase": "test_sandbox_pass",
            "kucoin_sandbox": True,
            "trading_enabled": False
        }
        
        response = requests.put(f"{base_url}/api/v1/settings", json=settings_update, timeout=10)
        log(f"PUT settings: {response.status_code}")
        
        if response.status_code == 200:
            log("✅ PUT settings successful")
        else:
            log(f"❌ PUT settings failed: {response.status_code} - {response.text}")
            return False
        
        # Test exchange health after credentials
        log("Testing GET /api/v1/health/exchange (after creds)")
        response = requests.get(f"{base_url}/api/v1/health/exchange", timeout=5)
        log(f"Exchange health (after): {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            after_mode = data.get('mode')
            log(f"✅ Exchange health (after): ok={data.get('ok')}, mode='{after_mode}'")
            
            # Check if mode changed
            if before_mode and after_mode and before_mode != after_mode:
                log(f"✅ Mode changed: {before_mode} → {after_mode}")
            else:
                log(f"⚠️  Mode unchanged: {before_mode} → {after_mode}")
        else:
            log(f"❌ Exchange health (after) failed: {response.status_code}")
        
        # Test GET settings again to verify persistence
        log("Testing GET /api/v1/settings (verify update)")
        response = requests.get(f"{base_url}/api/v1/settings", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            sandbox_mode = data.get("kucoin_sandbox")
            masked_key = data.get("kucoin_api_key")
            log(f"✅ Settings updated: sandbox={sandbox_mode}, key_masked={'***' == masked_key}")
        else:
            log(f"❌ Settings verification failed: {response.status_code}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        log(f"❌ Connection error: {e}")
        return False

def check_settings_file():
    """Check if settings file exists"""
    log("Checking for settings file...")
    
    possible_paths = [
        "oracle_trader_bot/.runtime/settings.json",
        ".runtime/settings.json", 
        "oracle_trader_bot/settings.json",
        "settings.json"
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                log(f"✅ Settings file found: {path} ({len(data)} fields)")
                
                # Check if our test credentials are there
                if data.get("kucoin_sandbox") is True:
                    log("✅ Test credentials persisted to file")
                else:
                    log("⚠️  Test credentials not found in file")
                
                return True
            except Exception as e:
                log(f"⚠️  Error reading {path}: {e}")
    
    log("❌ No settings file found")
    return False

def get_openapi_count():
    """Get OpenAPI endpoint count"""
    log("Getting OpenAPI endpoint count...")
    
    try:
        response = requests.get("http://localhost:8000/openapi.json", timeout=5)
        if response.status_code == 200:
            data = response.json()
            paths = data.get("paths", {})
            count = len(paths)
            log(f"✅ OpenAPI endpoint count: {count}")
            
            # Show settings-related endpoints
            settings_endpoints = [path for path in paths.keys() if "settings" in path]
            log(f"   Settings endpoints: {settings_endpoints}")
            
            return count
        else:
            log(f"❌ OpenAPI request failed: {response.status_code}")
            return 0
    except Exception as e:
        log(f"❌ OpenAPI error: {e}")
        return 0

def run_tests():
    """Run basic tests"""
    log("Running test suite...")
    
    try:
        # Try to run a simple test
        result = subprocess.run([
            sys.executable, "-c", 
            "import sys; sys.path.insert(0, 'oracle_trader_bot'); from app.core.config import settings; print('Config test passed')"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            log("✅ Basic config test passed")
            return True
        else:
            log(f"❌ Config test failed: {result.stderr}")
            return False
            
    except Exception as e:
        log(f"❌ Test error: {e}")
        return False

def main():
    log("🚀 Starting Direct Settings Smoke Test")
    log("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=2)
        if response.status_code == 200:
            log("✅ Server is running")
        else:
            log("❌ Server not responding correctly")
            return
    except:
        log("❌ Server not running - please start server first")
        log("   Run: cd oracle_trader_bot && $env:APP_STARTUP_MODE='lite'; $env:SKIP_DB_INIT='true'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return
    
    # Run tests
    log("\n📋 Phase 1: Settings API Testing")
    settings_ok = test_settings_endpoints()
    
    log("\n📋 Phase 2: File Persistence Check")
    file_ok = check_settings_file()
    
    log("\n📋 Phase 3: OpenAPI Analysis")
    endpoint_count = get_openapi_count()
    
    log("\n📋 Phase 4: Basic Tests")
    tests_ok = run_tests()
    
    # Summary
    log("\n" + "=" * 50)
    log("🎯 TEST RESULTS SUMMARY")
    log("=" * 50)
    
    log(f"Settings API:      {'✅ PASSED' if settings_ok else '❌ FAILED'}")
    log(f"File Persistence:  {'✅ PASSED' if file_ok else '❌ FAILED'}")
    log(f"OpenAPI Endpoints: {endpoint_count} total")
    log(f"Basic Tests:       {'✅ PASSED' if tests_ok else '❌ FAILED'}")
    
    overall_status = all([settings_ok, file_ok, tests_ok, endpoint_count > 0])
    log(f"\n🏁 OVERALL STATUS: {'✅ PASSED' if overall_status else '❌ SOME ISSUES'}")

if __name__ == "__main__":
    main()
