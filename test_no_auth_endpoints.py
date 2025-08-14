#!/usr/bin/env python3
"""
Quick test script to validate no-auth endpoint functionality
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'oracle_trader_bot'))

from app.core.config import settings
import asyncio
import aiohttp
import json

async def test_health_endpoint():
    """Test the /api/v1/health/exchange endpoint with no credentials"""
    print("Testing /api/v1/health/exchange endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f'{settings.API_INTERNAL_BASE_URL}/api/v1/health/exchange') as response:
                status = response.status
                content = await response.json()
                
                print(f"✅ Health endpoint - Status: {status}")
                print(f"Response: {json.dumps(content, indent=2)}")
                
                # Validate expected structure
                if status == 200 and 'ok' in content and 'mode' in content:
                    print("✅ Health endpoint returned expected structure")
                else:
                    print("❌ Health endpoint response unexpected")
                    
        except Exception as e:
            print(f"❌ Health endpoint failed: {e}")

async def test_private_endpoint():
    """Test a private endpoint that should return 503 with no credentials"""
    print("\nTesting /api/v1/orders/positions endpoint (should return 503)...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f'{settings.API_INTERNAL_BASE_URL}/api/v1/orders/positions') as response:
                status = response.status
                content = await response.json()
                
                print(f"Status: {status}")
                print(f"Response: {json.dumps(content, indent=2)}")
                
                # Validate expected 503 error response
                if status == 503 and 'detail' in content:
                    print("✅ Private endpoint correctly returned 503 with no credentials")
                else:
                    print("❌ Private endpoint response unexpected")
                    
        except Exception as e:
            print(f"❌ Private endpoint test failed: {e}")

async def test_account_overview():
    """Test account overview endpoint that should return 503"""
    print("\nTesting /api/v1/exchange/account/overview endpoint (should return 503)...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f'{settings.API_INTERNAL_BASE_URL}/api/v1/exchange/account/overview') as response:
                status = response.status
                content = await response.json()
                
                print(f"Status: {status}")
                print(f"Response: {json.dumps(content, indent=2)}")
                
                if status == 503 and 'detail' in content:
                    print("✅ Account overview correctly returned 503 with no credentials")
                else:
                    print("❌ Account overview response unexpected")
                    
        except Exception as e:
            print(f"❌ Account overview test failed: {e}")

async def main():
    """Run all tests"""
    print("🔍 Testing No-Auth Mode Endpoints")
    print("=" * 50)
    
    await test_health_endpoint()
    await test_private_endpoint()
    await test_account_overview()
    
    print("\n" + "=" * 50)
    print("✅ No-auth endpoint testing complete!")

if __name__ == "__main__":
    asyncio.run(main())
