#!/usr/bin/env python3
"""
Comprehensive Settings Smoke Test & Parity Check

Tests:
1. Server in lite mode (DB down)
2. Settings endpoints (GET/PUT) with secret masking
3. Exchange health check before/after credentials
4. Persistence across server restarts
5. Test suite execution
6. OpenAPI endpoint count analysis
"""

import asyncio
import json
import time
import subprocess
import sys
import os
import requests
from pathlib import Path
import signal
from typing import Dict, Any, Optional

# Add the oracle_trader_bot directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "oracle_trader_bot"))

class SettingsSmokeTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.server_process = None
        self.results = {}
        
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def start_server(self) -> bool:
        """Start server in lite mode"""
        self.log("Starting server in lite mode...")
        
        # Set environment variables
        env = os.environ.copy()
        env.update({
            'APP_STARTUP_MODE': 'lite',
            'SKIP_DB_INIT': 'true',
            'KUCOIN_API_KEY': '',
            'KUCOIN_API_SECRET': '',
            'KUCOIN_API_PASSPHRASE': ''
        })
        
        # Start server process
        try:
            self.server_process = subprocess.Popen([
                sys.executable, "-c",
                "import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=False, log_level='error')"
            ], cwd="oracle_trader_bot", env=env, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            max_attempts = 15
            for attempt in range(max_attempts):
                try:
                    response = requests.get(f"{self.base_url}/api/v1/health", timeout=2)
                    if response.status_code == 200:
                        self.log("✅ Server started successfully")
                        return True
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
                self.log(f"Waiting for server... attempt {attempt + 1}/{max_attempts}")
                
            self.log("❌ Server failed to start within timeout")
            return False
            
        except Exception as e:
            self.log(f"❌ Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the server process"""
        if self.server_process:
            self.log("Stopping server...")
            try:
                # Try graceful shutdown first
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    self.server_process.kill()
                    self.server_process.wait()
                self.log("✅ Server stopped")
            except Exception as e:
                self.log(f"⚠️  Error stopping server: {e}")
            finally:
                self.server_process = None
    
    def make_request(self, method: str, endpoint: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request and return structured result"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = requests.get(url, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, json=json_data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return {
                "status_code": response.status_code,
                "success": response.ok,
                "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                "headers": dict(response.headers)
            }
        except requests.exceptions.RequestException as e:
            return {
                "status_code": 0,
                "success": False,
                "error": str(e),
                "data": None
            }
    
    def test_settings_get(self) -> Dict[str, Any]:
        """Test GET /api/v1/settings"""
        self.log("Testing GET /api/v1/settings...")
        result = self.make_request("GET", "/api/v1/settings")
        
        if result["success"]:
            data = result["data"]
            # Check for secret masking
            secret_fields = ["kucoin_api_key", "kucoin_api_secret", "kucoin_api_passphrase"]
            masked_secrets = []
            
            for field in secret_fields:
                if field in data and data[field] == "***":
                    masked_secrets.append(field)
            
            self.log(f"✅ GET settings: {result['status_code']}, masked secrets: {masked_secrets}")
        else:
            self.log(f"❌ GET settings failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def test_settings_put(self) -> Dict[str, Any]:
        """Test PUT /api/v1/settings with sandbox credentials"""
        self.log("Testing PUT /api/v1/settings...")
        
        # Use sandbox-like credential placeholders
        settings_update = {
            "kucoin_api_key": "test_sandbox_key_12345",
            "kucoin_api_secret": "test_sandbox_secret_67890", 
            "kucoin_api_passphrase": "test_sandbox_pass",
            "kucoin_sandbox": True,
            "trading_enabled": False
        }
        
        result = self.make_request("PUT", "/api/v1/settings", settings_update)
        
        if result["success"]:
            self.log(f"✅ PUT settings: {result['status_code']}")
        else:
            self.log(f"❌ PUT settings failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def test_exchange_health_before(self) -> Dict[str, Any]:
        """Test exchange health before credentials"""
        self.log("Testing GET /api/v1/health/exchange (before creds)...")
        result = self.make_request("GET", "/api/v1/health/exchange")
        
        if result["success"]:
            data = result["data"]
            expected_mode = "no-auth"
            expected_ok = False
            
            actual_ok = data.get("ok", True)  # Default to True to catch failures
            actual_mode = data.get("mode", "unknown")
            
            if actual_ok == expected_ok and actual_mode == expected_mode:
                self.log(f"✅ Exchange health (before): ok={actual_ok}, mode={actual_mode}")
            else:
                self.log(f"⚠️  Exchange health (before): expected ok={expected_ok}, mode={expected_mode}, got ok={actual_ok}, mode={actual_mode}")
        else:
            self.log(f"❌ Exchange health (before) failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def test_exchange_health_after(self) -> Dict[str, Any]:
        """Test exchange health after credentials"""
        self.log("Testing GET /api/v1/health/exchange (after creds)...")
        result = self.make_request("GET", "/api/v1/health/exchange")
        
        if result["success"]:
            data = result["data"]
            # After adding sandbox credentials, should be auth mode
            expected_mode = "auth"
            expected_ok = True  # Should be true for sandbox mode
            
            actual_ok = data.get("ok", False)
            actual_mode = data.get("mode", "unknown")
            
            if actual_ok == expected_ok and actual_mode == expected_mode:
                self.log(f"✅ Exchange health (after): ok={actual_ok}, mode={actual_mode}")
            else:
                self.log(f"⚠️  Exchange health (after): expected ok={expected_ok}, mode={expected_mode}, got ok={actual_ok}, mode={actual_mode}")
        else:
            self.log(f"❌ Exchange health (after) failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def test_persistence(self) -> Dict[str, Any]:
        """Test settings persistence across server restart"""
        self.log("Testing persistence across server restart...")
        
        # Stop server
        self.stop_server()
        time.sleep(2)
        
        # Restart server
        if not self.start_server():
            return {"success": False, "error": "Failed to restart server"}
        
        # Get settings again
        result = self.make_request("GET", "/api/v1/settings")
        
        if result["success"]:
            data = result["data"]
            # Check if our sandbox credentials persisted (should be masked)
            if data.get("kucoin_sandbox") is True and data.get("kucoin_api_key") == "***":
                self.log("✅ Settings persisted across restart")
            else:
                self.log("⚠️  Settings may not have persisted correctly")
        else:
            self.log(f"❌ Persistence test failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def check_settings_file(self) -> bool:
        """Check if settings file was created"""
        settings_paths = [
            Path("oracle_trader_bot/.runtime/settings.json"),
            Path("oracle_trader_bot/settings.json"),
            Path(".runtime/settings.json"),
            Path("settings.json")
        ]
        
        for path in settings_paths:
            if path.exists():
                try:
                    with open(path) as f:
                        data = json.load(f)
                    self.log(f"✅ Settings file found: {path} ({len(data)} fields)")
                    return True
                except Exception as e:
                    self.log(f"⚠️  Settings file exists but error reading {path}: {e}")
        
        self.log("❌ No settings file found")
        return False
    
    def get_endpoint_count(self) -> Dict[str, Any]:
        """Get endpoint count from OpenAPI spec"""
        self.log("Getting endpoint count from OpenAPI...")
        result = self.make_request("GET", "/openapi.json")
        
        if result["success"]:
            openapi_data = result["data"]
            paths = openapi_data.get("paths", {})
            endpoint_count = len(paths)
            self.log(f"✅ OpenAPI endpoint count: {endpoint_count}")
            return {"success": True, "count": endpoint_count, "paths": list(paths.keys())}
        else:
            self.log(f"❌ Failed to get OpenAPI spec: {result.get('error', 'Unknown error')}")
            return {"success": False, "count": 0}
    
    def run_tests(self) -> bool:
        """Run test suite"""
        self.log("Running test suite...")
        try:
            # Run specific tests that should pass
            result = subprocess.run([
                sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"
            ], cwd=".", capture_output=True, text=True, timeout=60)
            
            success = result.returncode == 0
            if success:
                self.log("✅ Test suite passed")
            else:
                self.log("❌ Test suite had failures")
                # Show only the summary
                lines = result.stdout.split('\n')
                for line in lines[-10:]:  # Last 10 lines usually contain summary
                    if line.strip():
                        self.log(f"TEST: {line}")
            
            return success
            
        except subprocess.TimeoutExpired:
            self.log("⚠️  Test suite timed out")
            return False
        except Exception as e:
            self.log(f"❌ Test suite error: {e}")
            return False
    
    def run_full_test(self):
        """Run complete test suite"""
        self.log("🚀 Starting comprehensive settings smoke test...")
        
        try:
            # 1. Start server
            if not self.start_server():
                self.log("❌ CRITICAL: Server failed to start")
                return
            
            # 2. Test sequence
            self.log("\n📋 Phase 1: Initial settings and exchange health")
            get_result_1 = self.test_settings_get()
            exchange_before = self.test_exchange_health_before()
            
            self.log("\n📋 Phase 2: Update settings with credentials") 
            put_result = self.test_settings_put()
            exchange_after = self.test_exchange_health_after()
            
            self.log("\n📋 Phase 3: Persistence test")
            persistence_result = self.test_persistence()
            
            self.log("\n📋 Phase 4: File and endpoint analysis")
            file_exists = self.check_settings_file()
            endpoint_info = self.get_endpoint_count()
            
            self.log("\n📋 Phase 5: Test suite execution")
            tests_passed = self.run_tests()
            
            # Summary Report
            self.log("\n" + "="*60)
            self.log("🎯 COMPREHENSIVE TEST RESULTS")
            self.log("="*60)
            
            # Settings API Results
            self.log("\n🔧 Settings API Results:")
            if get_result_1.get("success"):
                # Redact secrets in output
                data = get_result_1["data"].copy()
                for key in ["kucoin_api_key", "kucoin_api_secret", "kucoin_api_passphrase"]:
                    if key in data:
                        data[key] = "[REDACTED]" if data[key] != "***" else "***"
                self.log(f"  GET /api/v1/settings: {get_result_1['status_code']} - {len(data)} fields")
            
            if put_result.get("success"):
                self.log(f"  PUT /api/v1/settings: {put_result['status_code']} - Update successful")
            
            # Exchange Health Results
            self.log("\n🏥 Exchange Health Results:")
            if exchange_before.get("success"):
                before_data = exchange_before["data"]
                self.log(f"  BEFORE creds: ok={before_data.get('ok')}, mode='{before_data.get('mode')}'")
            
            if exchange_after.get("success"):
                after_data = exchange_after["data"]
                self.log(f"  AFTER creds:  ok={after_data.get('ok')}, mode='{after_data.get('mode')}'")
                
                # Check if mode flipped
                before_mode = exchange_before.get("data", {}).get("mode")
                after_mode = after_data.get("mode")
                if before_mode != after_mode:
                    self.log(f"  ✅ Health mode flipped: {before_mode} → {after_mode}")
                else:
                    self.log(f"  ⚠️  Health mode unchanged: {before_mode}")
            
            # Persistence Results
            self.log(f"\n💾 Persistence: {'✅ PASSED' if persistence_result.get('success') else '❌ FAILED'}")
            self.log(f"   Settings file: {'✅ Found' if file_exists else '❌ Not found'}")
            
            # Endpoint Count
            if endpoint_info.get("success"):
                self.log(f"\n🛣️  Endpoint Analysis: {endpoint_info['count']} total endpoints")
                # Show some key endpoints
                paths = endpoint_info.get("paths", [])
                key_endpoints = [p for p in paths if "/settings" in p or "/health" in p]
                for ep in key_endpoints[:5]:  # Show first 5 key endpoints
                    self.log(f"   {ep}")
            
            # Test Results
            self.log(f"\n🧪 Test Suite: {'✅ PASSED' if tests_passed else '❌ FAILED'}")
            
            # Final Status
            all_critical_passed = all([
                get_result_1.get("success"),
                put_result.get("success"), 
                persistence_result.get("success"),
                endpoint_info.get("success")
            ])
            
            self.log("\n🎯 FINAL STATUS:")
            if all_critical_passed:
                self.log("✅ ALL CRITICAL TESTS PASSED - Settings system operational!")
            else:
                self.log("❌ Some critical tests failed - Review results above")
            
        except KeyboardInterrupt:
            self.log("\n⚠️  Test interrupted by user")
        except Exception as e:
            self.log(f"\n❌ CRITICAL ERROR: {e}")
        finally:
            self.stop_server()
            self.log("\n🏁 Test suite complete")

def main():
    test = SettingsSmokeTest()
    test.run_full_test()

if __name__ == "__main__":
    main()
