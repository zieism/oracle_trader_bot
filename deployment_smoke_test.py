#!/usr/bin/env python3
"""
Deployment Smoke Test - Oracle Trader Bot

Tests deployment verification checklist:
- Frontend served by nginx (simulated via backend health check)
- API health endpoints return 200
- Settings endpoint returns 200 with masked secrets
- Audit endpoint accessibility
- Rate limiting headers present
- Security headers present

Usage:
    python deployment_smoke_test.py [--host localhost:8000]
"""

import asyncio
import aiohttp
import argparse
import sys
import logging
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeploymentSmokeTest:
    """Deployment smoke test runner"""
    
    def __init__(self, host: str = "localhost:8000", use_https: bool = False):
        self.protocol = "https" if use_https else "http"
        self.base_url = f"{self.protocol}://{host}"
        self.api_url = f"{self.base_url}/api/v1"
        self.use_https = use_https
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: Dict[str, Any] = {}
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(ssl=False)  # For testing with self-signed certs
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Make HTTP request with comprehensive response capture"""
        try:
            async with self.session.request(method, url, **kwargs) as response:
                content_type = response.headers.get('content-type', '')
                
                # Capture response data
                if 'application/json' in content_type:
                    try:
                        data = await response.json()
                    except:
                        data = await response.text()
                else:
                    data = await response.text()
                
                return {
                    'status': response.status,
                    'headers': dict(response.headers),
                    'data': data,
                    'success': 200 <= response.status < 300
                }
                
        except Exception as e:
            return {
                'status': 0,
                'headers': {},
                'data': {'error': str(e)},
                'success': False
            }
    
    def check_security_headers(self, headers: Dict[str, str]) -> Dict[str, bool]:
        """Check for required security headers"""
        security_checks = {
            'X-Content-Type-Options': headers.get('x-content-type-options', '').lower() == 'nosniff',
            'X-Frame-Options': headers.get('x-frame-options', '').upper() == 'DENY',
            'Referrer-Policy': headers.get('referrer-policy', '').lower() == 'no-referrer',
        }
        
        # HSTS only required for HTTPS
        if self.use_https:
            security_checks['Strict-Transport-Security'] = 'strict-transport-security' in headers
        
        return security_checks
    
    def check_rate_limit_headers(self, headers: Dict[str, str]) -> Dict[str, bool]:
        """Check for rate limiting headers"""
        rate_limit_checks = {
            'X-RateLimit-Limit': 'x-ratelimit-limit' in headers,
            'X-RateLimit-Remaining': 'x-ratelimit-remaining' in headers,
            'X-RateLimit-Reset': 'x-ratelimit-reset' in headers,
        }
        return rate_limit_checks
    
    async def test_frontend_served(self) -> Dict[str, Any]:
        """Test 1: Frontend served by nginx (root path)"""
        logger.info("🌐 Testing frontend served by nginx...")
        
        result = await self.make_request(self.base_url + "/")
        
        return {
            'test': 'Frontend Served',
            'endpoint': '/',
            'passed': result['success'],
            'status_code': result['status'],
            'details': 'Frontend accessible' if result['success'] else f"Error: {result['data']}"
        }
    
    async def test_health_app(self) -> Dict[str, Any]:
        """Test 2: Health app endpoint returns 200"""
        logger.info("🏥 Testing /api/v1/health/app...")
        
        result = await self.make_request(self.api_url + "/health/app")
        
        # Check for rate limiting and security headers
        security_headers = self.check_security_headers(result['headers'])
        rate_limit_headers = self.check_rate_limit_headers(result['headers'])
        
        return {
            'test': 'Health App Endpoint',
            'endpoint': '/api/v1/health/app',
            'passed': result['success'],
            'status_code': result['status'],
            'security_headers': security_headers,
            'rate_limit_headers': rate_limit_headers,
            'details': result['data'] if result['success'] else f"Error: {result['data']}"
        }
    
    async def test_settings_get(self) -> Dict[str, Any]:
        """Test 3: Settings endpoint returns 200 with masked secrets"""
        logger.info("⚙️  Testing /api/v1/settings/ (GET)...")
        
        result = await self.make_request(self.api_url + "/settings/")
        
        # Check for rate limiting and security headers
        security_headers = self.check_security_headers(result['headers'])
        rate_limit_headers = self.check_rate_limit_headers(result['headers'])
        
        # Check for masked secrets
        secrets_masked = False
        if result['success'] and isinstance(result['data'], dict):
            secret_fields = ['KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE', 'ADMIN_API_TOKEN']
            masked_count = 0
            for field in secret_fields:
                value = result['data'].get(field)
                if value == '***' or value == '' or value is None:
                    masked_count += 1
            secrets_masked = masked_count > 0
        
        return {
            'test': 'Settings GET Endpoint',
            'endpoint': '/api/v1/settings/',
            'passed': result['success'],
            'status_code': result['status'],
            'secrets_masked': secrets_masked,
            'security_headers': security_headers,
            'rate_limit_headers': rate_limit_headers,
            'details': f"Settings returned, secrets masked: {secrets_masked}" if result['success'] else f"Error: {result['data']}"
        }
    
    async def test_audit_endpoint(self) -> Dict[str, Any]:
        """Test 4: Audit endpoint accessibility"""
        logger.info("📋 Testing /api/v1/settings/audit...")
        
        result = await self.make_request(self.api_url + "/settings/audit")
        
        # Check for rate limiting and security headers
        security_headers = self.check_security_headers(result['headers'])
        rate_limit_headers = self.check_rate_limit_headers(result['headers'])
        
        # Audit endpoint might require admin token or be accessible without it
        audit_accessible = result['success'] or result['status'] == 401  # 401 is acceptable if auth is required
        
        return {
            'test': 'Audit Endpoint',
            'endpoint': '/api/v1/settings/audit',
            'passed': audit_accessible,
            'status_code': result['status'],
            'security_headers': security_headers,
            'rate_limit_headers': rate_limit_headers,
            'details': ('Audit accessible' if result['success'] else 
                       'Requires auth (expected)' if result['status'] == 401 else 
                       f"Error: {result['data']}")
        }
    
    async def test_rate_limiting(self) -> Dict[str, Any]:
        """Test 5: Rate limiting works (make multiple requests)"""
        logger.info("🚦 Testing rate limiting...")
        
        # Make multiple requests to settings endpoint to test rate limiting
        requests = []
        for i in range(12):  # Above the 10/min limit
            result = await self.make_request(self.api_url + "/settings/")
            requests.append({
                'request': i + 1,
                'status': result['status'],
                'rate_limit_headers': self.check_rate_limit_headers(result['headers']),
                'rate_limited': result['status'] == 429
            })
        
        # Check if any requests were rate limited
        rate_limited_requests = [r for r in requests if r['rate_limited']]
        rate_limit_working = len(rate_limited_requests) > 0
        
        return {
            'test': 'Rate Limiting',
            'endpoint': '/api/v1/settings/ (12 requests)',
            'passed': rate_limit_working,
            'rate_limited_count': len(rate_limited_requests),
            'total_requests': len(requests),
            'details': f"Rate limiting {'working' if rate_limit_working else 'not detected'} - {len(rate_limited_requests)}/{len(requests)} requests rate limited"
        }
    
    async def test_cors_headers(self) -> Dict[str, Any]:
        """Test 6: CORS headers present"""
        logger.info("🌍 Testing CORS headers...")
        
        # Make OPTIONS request to check CORS
        result = await self.make_request(
            self.api_url + "/health/app",
            method="OPTIONS",
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'GET'
            }
        )
        
        cors_headers = {
            'Access-Control-Allow-Origin': 'access-control-allow-origin' in result['headers'],
            'Access-Control-Allow-Methods': 'access-control-allow-methods' in result['headers'],
            'Access-Control-Allow-Headers': 'access-control-allow-headers' in result['headers'],
        }
        
        cors_working = any(cors_headers.values())
        
        return {
            'test': 'CORS Headers',
            'endpoint': '/api/v1/health/app (OPTIONS)',
            'passed': cors_working,
            'status_code': result['status'],
            'cors_headers': cors_headers,
            'details': f"CORS headers {'present' if cors_working else 'missing'}"
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all deployment smoke tests"""
        logger.info(f"🚀 Starting Deployment Smoke Test - {self.base_url}")
        start_time = datetime.now()
        
        tests = [
            self.test_frontend_served,
            self.test_health_app,
            self.test_settings_get,
            self.test_audit_endpoint,
            self.test_rate_limiting,
            self.test_cors_headers
        ]
        
        results = []
        for test in tests:
            try:
                result = await test()
                results.append(result)
                status = "✅ PASS" if result['passed'] else "❌ FAIL"
                logger.info(f"{status} - {result['test']}: {result['details']}")
            except Exception as e:
                logger.error(f"❌ ERROR - {test.__name__}: {e}")
                results.append({
                    'test': test.__name__,
                    'passed': False,
                    'error': str(e)
                })
        
        # Calculate summary
        passed_tests = sum(1 for r in results if r['passed'])
        total_tests = len(results)
        success_rate = (passed_tests / total_tests) * 100
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': success_rate,
                'duration_seconds': duration,
                'overall_passed': passed_tests >= (total_tests * 0.8)  # 80% pass rate
            },
            'tests': results,
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url
        }

    def print_checklist(self, results: Dict[str, Any]):
        """Print concise pass/fail checklist"""
        print("\n" + "="*60)
        print("📋 DEPLOYMENT SMOKE TEST CHECKLIST")
        print("="*60)
        
        for test in results['tests']:
            status = "✅ PASS" if test['passed'] else "❌ FAIL"
            print(f"{status} {test['test']}")
            
            # Print specific header checks if available
            if 'security_headers' in test:
                for header, present in test['security_headers'].items():
                    header_status = "✅" if present else "❌"
                    print(f"    {header_status} Security Header: {header}")
            
            if 'rate_limit_headers' in test:
                rate_headers_present = any(test['rate_limit_headers'].values())
                header_status = "✅" if rate_headers_present else "❌"
                print(f"    {header_status} Rate Limit Headers")
            
            if 'cors_headers' in test:
                cors_present = any(test['cors_headers'].values())
                header_status = "✅" if cors_present else "❌"
                print(f"    {header_status} CORS Headers")
        
        print("\n" + "-"*60)
        summary = results['summary']
        overall_status = "✅ PASSED" if summary['overall_passed'] else "❌ FAILED"
        print(f"📊 OVERALL: {overall_status}")
        print(f"📈 Success Rate: {summary['passed_tests']}/{summary['total_tests']} ({summary['success_rate']:.1f}%)")
        print(f"⏱️  Duration: {summary['duration_seconds']:.2f}s")
        print("="*60)


async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Oracle Trader Bot Deployment Smoke Test")
    parser.add_argument("--host", default="localhost:8000", help="Host and port to test (default: localhost:8000)")
    parser.add_argument("--https", action="store_true", help="Use HTTPS protocol")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    
    args = parser.parse_args()
    
    async with DeploymentSmokeTest(host=args.host, use_https=args.https) as tester:
        results = await tester.run_all_tests()
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            tester.print_checklist(results)
        
        # Return exit code based on overall success
        return 0 if results['summary']['overall_passed'] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
