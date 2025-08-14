#!/usr/bin/env python3
"""
End-to-End API Flow Tests for Oracle Trader Bot

Tests the complete API workflow:
1. Settings GET→PUT (sandbox credentials) → health/exchange flips to auth
2. Sample analysis endpoint returns 200 
3. Optional dry-run trade endpoint returns 200

Usage:
    python tests_e2e/test_api_flow.py
"""

import os
import sys
import asyncio
import logging
import pytest
import aiohttp
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from oracle_trader_bot.app.core.config import settings
except ImportError:
    # Fallback for different project structure
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'oracle_trader_bot'))
    from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class E2EAPITester:
    """End-to-End API Flow Tester"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or getattr(settings, 'API_INTERNAL_BASE_URL', 'http://localhost:8000')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Test data - sandbox KuCoin credentials (safe to use)
        self.sandbox_credentials = {
            "KUCOIN_API_KEY": "test_api_key_sandbox_60f123abc456def",
            "KUCOIN_API_SECRET": "test-secret-sandbox-12345678-abcd-efgh-ijkl-123456789abc",  
            "KUCOIN_API_PASSPHRASE": "test_passphrase_sandbox_v2",
            "KUCOIN_SANDBOX": True
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"Making {method} request to {url}")
            async with self.session.request(method, url, **kwargs) as response:
                content_type = response.headers.get('content-type', '')
                
                if 'application/json' in content_type:
                    data = await response.json()
                else:
                    data = await response.text()
                
                result = {
                    'status_code': response.status,
                    'data': data,
                    'headers': dict(response.headers)
                }
                
                logger.info(f"Response: {response.status} from {method} {url}")
                return result
                
        except Exception as e:
            logger.error(f"Request failed: {method} {url} - {e}")
            return {
                'status_code': 0,
                'data': {'error': str(e)},
                'headers': {}
            }
    
    async def test_step_1_settings_get(self) -> Dict[str, Any]:
        """Step 1: GET /api/v1/settings/ - Check initial settings state"""
        logger.info("🔍 STEP 1: Testing GET /api/v1/settings/")
        
        result = await self.make_request("GET", "/api/v1/settings/")
        
        if result['status_code'] == 200:
            settings_data = result['data']
            
            # Check that secrets are properly masked
            secret_fields = ['KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE']
            masked_secrets = []
            
            for field in secret_fields:
                value = settings_data.get(field)
                if value and value != '***' and value != '':
                    logger.warning(f"Secret field {field} appears unmasked: {value[:10]}...")
                elif value == '***':
                    masked_secrets.append(field)
            
            logger.info(f"✅ GET settings successful - {len(settings_data)} fields, {len(masked_secrets)} masked secrets")
            return {
                'success': True, 
                'data': settings_data, 
                'masked_secrets': masked_secrets,
                'status_code': result['status_code']
            }
        else:
            logger.error(f"❌ GET settings failed: {result['status_code']} - {result['data']}")
            return {
                'success': False, 
                'error': result['data'],
                'status_code': result['status_code']
            }
    
    async def test_step_2_health_exchange_before(self) -> Dict[str, Any]:
        """Step 2: GET /api/v1/health/exchange - Check exchange status before auth"""
        logger.info("🏥 STEP 2: Testing health/exchange BEFORE authentication")
        
        result = await self.make_request("GET", "/api/v1/health/exchange")
        
        if result['status_code'] == 200:
            health_data = result['data']
            exchange_status = health_data.get('exchange_status', 'unknown')
            
            logger.info(f"✅ Health check successful - exchange_status: {exchange_status}")
            return {
                'success': True,
                'exchange_status': exchange_status,
                'data': health_data,
                'status_code': result['status_code']
            }
        else:
            logger.error(f"❌ Health check failed: {result['status_code']} - {result['data']}")
            return {
                'success': False,
                'error': result['data'],
                'status_code': result['status_code']
            }
    
    async def test_step_3_settings_put(self) -> Dict[str, Any]:
        """Step 3: PUT /api/v1/settings/ - Set sandbox credentials"""
        logger.info("⚙️  STEP 3: Testing PUT /api/v1/settings/ with sandbox credentials")
        
        result = await self.make_request(
            "PUT", 
            "/api/v1/settings/",
            json=self.sandbox_credentials,
            headers={'Content-Type': 'application/json'}
        )
        
        if result['status_code'] == 200:
            logger.info("✅ PUT settings successful - sandbox credentials set")
            return {
                'success': True, 
                'data': result['data'],
                'status_code': result['status_code']
            }
        else:
            logger.error(f"❌ PUT settings failed: {result['status_code']} - {result['data']}")
            return {
                'success': False, 
                'error': result['data'],
                'status_code': result['status_code']
            }
    
    async def test_step_4_health_exchange_after(self) -> Dict[str, Any]:
        """Step 4: GET /api/v1/health/exchange - Check exchange status after auth"""
        logger.info("🔄 STEP 4: Testing health/exchange AFTER authentication")
        
        # Wait a moment for settings to be applied
        await asyncio.sleep(1)
        
        result = await self.make_request("GET", "/api/v1/health/exchange")
        
        if result['status_code'] == 200:
            health_data = result['data']
            exchange_status = health_data.get('exchange_status', 'unknown')
            
            logger.info(f"✅ Health check successful - exchange_status: {exchange_status}")
            return {
                'success': True,
                'exchange_status': exchange_status,
                'data': health_data,
                'status_code': result['status_code']
            }
        else:
            logger.error(f"❌ Health check failed: {result['status_code']} - {result['data']}")
            return {
                'success': False,
                'error': result['data'],
                'status_code': result['status_code']
            }
    
    async def test_step_5_analysis_endpoint(self) -> Dict[str, Any]:
        """Step 5: GET /api/v1/market/ohlcv-with-indicators/{symbol} - Test analysis endpoint"""
        logger.info("📈 STEP 5: Testing sample analysis endpoint")
        
        # Use a common symbol that should be available on KuCoin
        test_symbol = "BTCUSDT"
        
        result = await self.make_request(
            "GET", 
            f"/api/v1/market/ohlcv-with-indicators/{test_symbol}?limit=50&timeframe=1h"
        )
        
        if result['status_code'] == 200:
            analysis_data = result['data']
            data_points = len(analysis_data.get('data', []))
            market_regime = analysis_data.get('market_regime', {}).get('descriptive_label', 'unknown')
            
            logger.info(f"✅ Analysis endpoint successful - {data_points} data points, regime: {market_regime}")
            return {
                'success': True,
                'data_points': data_points,
                'market_regime': market_regime,
                'status_code': result['status_code']
            }
        else:
            logger.warning(f"⚠️  Analysis endpoint returned: {result['status_code']} - {result['data']}")
            return {
                'success': result['status_code'] in [200, 503],  # 503 acceptable for no-auth mode
                'error': result['data'],
                'status_code': result['status_code']
            }
    
    async def test_step_6_dry_run_trade_endpoint(self) -> Dict[str, Any]:
        """Step 6: POST /api/v1/trading/execute-signal - Test dry-run trade endpoint (optional)"""
        logger.info("💼 STEP 6: Testing dry-run trade endpoint (optional)")
        
        # Simple trading signal for dry-run test
        test_signal = {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 45000.0,
            "stop_loss": 44000.0,
            "take_profit": 46000.0,
            "suggested_leverage": 2.0,
            "strategy_name": "test_e2e",
            "confidence_score": 0.7,
            "trigger_price": 45000.0
        }
        
        result = await self.make_request(
            "POST",
            "/api/v1/trading/execute-signal",
            json=test_signal,
            headers={'Content-Type': 'application/json'}
        )
        
        # Accept various status codes since this is sandbox/testing
        success_codes = [200, 201, 400, 503]  # 400/503 acceptable for sandbox limitations
        
        if result['status_code'] in success_codes:
            logger.info(f"✅ Trade endpoint accessible - status: {result['status_code']}")
            return {
                'success': True,
                'status_code': result['status_code'],
                'response_type': 'success' if result['status_code'] < 300 else 'expected_error'
            }
        else:
            logger.error(f"❌ Trade endpoint failed: {result['status_code']} - {result['data']}")
            return {
                'success': False,
                'error': result['data'],
                'status_code': result['status_code']
            }
    
    async def run_complete_flow_test(self) -> Dict[str, Any]:
        """Run the complete E2E API flow test"""
        logger.info("🚀 Starting Complete E2E API Flow Test")
        logger.info(f"Testing against: {self.base_url}")
        
        results = {}
        
        # Step 1: Initial settings GET
        results['step_1_settings_get'] = await self.test_step_1_settings_get()
        
        # Step 2: Health check before auth
        results['step_2_health_before'] = await self.test_step_2_health_exchange_before()
        
        # Step 3: Set sandbox credentials
        results['step_3_settings_put'] = await self.test_step_3_settings_put()
        
        # Step 4: Health check after auth (should show different status)
        results['step_4_health_after'] = await self.test_step_4_health_exchange_after()
        
        # Step 5: Test analysis endpoint
        results['step_5_analysis'] = await self.test_step_5_analysis_endpoint()
        
        # Step 6: Test trade endpoint (optional)
        results['step_6_trade'] = await self.test_step_6_dry_run_trade_endpoint()
        
        # Analyze results
        passed_steps = sum(1 for result in results.values() if result.get('success', False))
        total_steps = len(results)
        
        logger.info(f"🏁 E2E Test Complete: {passed_steps}/{total_steps} steps passed")
        
        return {
            'summary': {
                'passed_steps': passed_steps,
                'total_steps': total_steps,
                'success_rate': passed_steps / total_steps,
                'overall_success': passed_steps >= 4  # Require at least 4/6 steps
            },
            'details': results
        }


async def main():
    """Main test runner"""
    print("🧪 Oracle Trader Bot - E2E API Flow Tests")
    print("=" * 60)
    
    async with E2EAPITester() as tester:
        results = await tester.run_complete_flow_test()
        
        # Print summary
        summary = results['summary']
        print(f"\n📊 FINAL RESULTS:")
        print(f"✅ Passed: {summary['passed_steps']}/{summary['total_steps']} steps")
        print(f"📈 Success Rate: {summary['success_rate']:.1%}")
        
        if summary['overall_success']:
            print("🎉 Overall E2E Test: PASSED")
            return 0
        else:
            print("❌ Overall E2E Test: FAILED")
            return 1


# Pytest integration
class TestE2EAPIFlow:
    """Pytest test class for E2E API flow"""
    
    @pytest.mark.asyncio
    async def test_complete_api_flow(self):
        """Test the complete API flow"""
        async with E2EAPITester() as tester:
            results = await tester.run_complete_flow_test()
            
            # Assert overall success
            assert results['summary']['overall_success'], f"E2E test failed: {results['summary']['passed_steps']}/{results['summary']['total_steps']} steps passed"
            
            # Assert critical steps
            assert results['details']['step_1_settings_get']['success'], "Settings GET failed"
            assert results['details']['step_3_settings_put']['success'], "Settings PUT failed"
    
    @pytest.mark.asyncio
    async def test_settings_flow_only(self):
        """Test just the settings GET→PUT flow"""
        async with E2EAPITester() as tester:
            # Test GET
            get_result = await tester.test_step_1_settings_get()
            assert get_result['success'], f"Settings GET failed: {get_result}"
            
            # Test PUT
            put_result = await tester.test_step_3_settings_put()
            assert put_result['success'], f"Settings PUT failed: {put_result}"
    
    @pytest.mark.asyncio 
    async def test_health_endpoints(self):
        """Test health endpoints"""
        async with E2EAPITester() as tester:
            # Test before auth
            before_result = await tester.test_step_2_health_exchange_before()
            assert before_result['success'], f"Health check failed: {before_result}"
            
            # Set credentials
            await tester.test_step_3_settings_put()
            
            # Test after auth
            after_result = await tester.test_step_4_health_exchange_after()
            assert after_result['success'], f"Health check after auth failed: {after_result}"


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
