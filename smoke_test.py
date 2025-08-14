#!/usr/bin/env python3
"""
Quick smoke test for no-auth mode functionality
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'oracle_trader_bot'))

from app.core.config import settings
import asyncio
import aiohttp
import json

async def smoke_test():
    """Run smoke tests for no-auth endpoints"""
    print("🧪 No-Auth Mode Smoke Test")
    print("=" * 50)
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Health endpoint
        print("1. Testing GET /api/v1/health/exchange (expect 200, ok=false, mode='no-auth')")
        try:
            async with session.get(f'{settings.API_INTERNAL_BASE_URL}/api/v1/health/exchange') as response:
                status = response.status
                content = await response.json()
                
                print(f"   Status: {status}")
                print(f"   Content: {json.dumps(content, indent=4)}")
                
                # Validate expectations
                if status == 200:
                    if content.get('ok') == False and content.get('details', {}).get('mode') == 'no-auth':
                        print("   ✅ PASS - Correct health response")
                        results.append(("health", True, f"200 OK, mode=no-auth"))
                    else:
                        print("   ❌ FAIL - Unexpected content structure")
                        results.append(("health", False, f"Wrong content: ok={content.get('ok')}, mode={content.get('details', {}).get('mode')}"))
                else:
                    print(f"   ❌ FAIL - Expected 200, got {status}")
                    results.append(("health", False, f"Status {status}"))
        except Exception as e:
            print(f"   ❌ ERROR - {e}")
            results.append(("health", False, f"Exception: {e}"))
        
        print()
        
        # Test 2: Public symbols endpoint
        print("2. Testing GET /api/v1/exchange/symbols (expect 200 with list - public data)")
        try:
            async with session.get(f'{settings.API_INTERNAL_BASE_URL}/api/v1/exchange/symbols') as response:
                status = response.status
                content = await response.json()
                
                print(f"   Status: {status}")
                if isinstance(content, list) and len(content) > 0:
                    print(f"   Content: List with {len(content)} symbols (showing first 3)")
                    for i, symbol in enumerate(content[:3]):
                        print(f"     [{i}]: {symbol}")
                else:
                    print(f"   Content: {content}")
                
                if status == 200 and isinstance(content, list) and len(content) > 0:
                    print("   ✅ PASS - Public symbols data available")
                    results.append(("symbols", True, f"200 OK, {len(content)} symbols"))
                else:
                    print(f"   ❌ FAIL - Expected 200 with symbol list")
                    results.append(("symbols", False, f"Status {status}, content type: {type(content)}"))
        except Exception as e:
            print(f"   ❌ ERROR - {e}")
            results.append(("symbols", False, f"Exception: {e}"))
            
        print()
        
        # Test 3: Private trading endpoint
        print("3. Testing POST /api/v1/trading/execute-signal (expect 503 with missing_credentials)")
        try:
            payload = {
                "symbol": "BTC/USDT:USDT",
                "direction": "long",
                "strength": 0.8,
                "signal_source": "test",
                "quantity": 0.01
            }
            
            async with session.post(f'{settings.API_INTERNAL_BASE_URL}/api/v1/trading/execute-signal', json=payload) as response:
                status = response.status
                content = await response.json()
                
                print(f"   Status: {status}")
                print(f"   Content: {json.dumps(content, indent=4)}")
                
                if status == 503:
                    detail = content.get('detail', {})
                    if isinstance(detail, dict) and detail.get('reason') == 'missing_credentials':
                        print("   ✅ PASS - Correct 503 error with missing_credentials")
                        results.append(("trading", True, "503 with missing_credentials"))
                    else:
                        print("   ❌ FAIL - 503 but wrong error structure")
                        results.append(("trading", False, f"503 but detail: {detail}"))
                else:
                    print(f"   ❌ FAIL - Expected 503, got {status}")
                    results.append(("trading", False, f"Status {status}"))
        except Exception as e:
            print(f"   ❌ ERROR - {e}")
            results.append(("trading", False, f"Exception: {e}"))
    
    print()
    print("=" * 50)
    print("📊 SMOKE TEST RESULTS")
    print("=" * 50)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, details in results:
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {test_name.upper()}: {details}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All smoke tests PASSED!")
    else:
        print("🚨 Some smoke tests FAILED - check details above")
    
    return results

if __name__ == "__main__":
    asyncio.run(smoke_test())
