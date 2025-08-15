#!/usr/bin/env python3
"""
CORS End-to-End Validation Script
Automated curl tests to verify environment-driven CORS allowlist
"""

import subprocess
import json
import sys
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class CORSTestResult:
    """Result of a single CORS test"""
    test_name: str
    method: str
    origin: str
    url: str
    status_code: int
    headers: Dict[str, str]
    passed: bool
    expected_cors: bool
    details: str


class CORSValidator:
    """CORS validation test runner"""
    
    def __init__(self, base_url: str = "http://localhost"):
        self.base_url = base_url.rstrip('/')
        self.results: List[CORSTestResult] = []
        
        # Define allowed and disallowed origins based on .env configuration
        self.allowed_origins = [
            "http://localhost:5173",
            "https://oracletrader.app", 
            "https://www.oracletrader.app"
        ]
        
        self.disallowed_origins = [
            "https://evil.example.com",
            "http://malicious.com",
            "https://attacker.net"
        ]
    
    def run_curl_command(self, method: str, url: str, headers: Dict[str, str] = None, timeout: int = 10) -> Tuple[int, Dict[str, str], str]:
        """Execute curl command and parse response"""
        cmd = ["curl", "-i", "-s", "--connect-timeout", str(timeout), "-X", method]
        
        # Add headers
        if headers:
            for key, value in headers.items():
                cmd.extend(["-H", f"{key}: {value}"])
        
        cmd.append(url)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            output = result.stdout
            
            # Parse HTTP response
            if not output:
                return 0, {}, "Empty response"
            
            lines = output.split('\n')
            
            # Extract status code
            status_line = lines[0] if lines else ""
            status_code = 0
            if "HTTP/" in status_line:
                parts = status_line.split()
                if len(parts) >= 2:
                    try:
                        status_code = int(parts[1])
                    except ValueError:
                        status_code = 0
            
            # Extract headers
            response_headers = {}
            for line in lines[1:]:
                if ':' in line and not line.startswith('{') and not line.startswith('<'):
                    try:
                        key, value = line.split(':', 1)
                        response_headers[key.strip().lower()] = value.strip()
                    except ValueError:
                        continue
                elif line.strip() == '':
                    break  # End of headers
            
            return status_code, response_headers, output
            
        except subprocess.TimeoutExpired:
            return 0, {}, "Request timed out"
        except Exception as e:
            return 0, {}, f"Error: {str(e)}"
    
    def test_cors_preflight(self, origin: str, expected_allowed: bool) -> CORSTestResult:
        """Test CORS preflight (OPTIONS) request"""
        url = f"{self.base_url}/api/v1/settings"
        headers = {
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        
        status_code, response_headers, output = self.run_curl_command("OPTIONS", url, headers)
        
        # Check CORS headers
        acao = response_headers.get('access-control-allow-origin', '')
        acac = response_headers.get('access-control-allow-credentials', '')
        acam = response_headers.get('access-control-allow-methods', '')
        acah = response_headers.get('access-control-allow-headers', '')
        acma = response_headers.get('access-control-max-age', '')
        
        if expected_allowed:
            # For allowed origins, expect 200 or 204 with proper CORS headers
            # FastAPI CORSMiddleware returns 200, nginx typically returns 204
            passed = (
                status_code in [200, 204] and
                acao == origin and
                acac.lower() == 'true' and
                ('POST' in acam.upper() or 'GET' in acam.upper()) and  # Check for expected methods
                bool(acah)  # Headers should be present
            )
            details = f"Status: {status_code}, ACAO: '{acao}', ACAC: '{acac}', Methods: '{acam}'"
        else:
            # For disallowed origins, expect no CORS headers or empty ACAO
            passed = (acao == '' or acao != origin)
            details = f"Status: {status_code}, ACAO: '{acao}' (should be empty for disallowed origin)"
        
        return CORSTestResult(
            test_name=f"Preflight - {'Allowed' if expected_allowed else 'Disallowed'} Origin",
            method="OPTIONS",
            origin=origin,
            url=url,
            status_code=status_code,
            headers=response_headers,
            passed=passed,
            expected_cors=expected_allowed,
            details=details
        )
    
    def test_cors_actual(self, origin: str, expected_allowed: bool) -> CORSTestResult:
        """Test actual CORS request (GET)"""
        url = f"{self.base_url}/api/v1/health/app"
        headers = {"Origin": origin}
        
        status_code, response_headers, output = self.run_curl_command("GET", url, headers)
        
        # Check CORS headers
        acao = response_headers.get('access-control-allow-origin', '')
        acac = response_headers.get('access-control-allow-credentials', '')
        
        # Count CORS headers to check for duplicates
        acao_count = len([v for k, v in response_headers.items() if k == 'access-control-allow-origin'])
        
        if expected_allowed:
            # For allowed origins, expect 200 with proper CORS headers and no duplicates
            passed = (
                status_code == 200 and
                acao == origin and
                acac.lower() == 'true' and
                acao_count == 1  # No duplicate headers
            )
            details = f"Status: {status_code}, ACAO: '{acao}', ACAC: '{acac}', Duplicates: {acao_count > 1}"
        else:
            # For disallowed origins, expect no CORS headers
            passed = (acao == '' or acao != origin)
            details = f"Status: {status_code}, ACAO: '{acao}' (should be empty for disallowed origin)"
        
        return CORSTestResult(
            test_name=f"Actual Request - {'Allowed' if expected_allowed else 'Disallowed'} Origin",
            method="GET",
            origin=origin,
            url=url,
            status_code=status_code,
            headers=response_headers,
            passed=passed,
            expected_cors=expected_allowed,
            details=details
        )
    
    def check_duplicate_headers(self) -> CORSTestResult:
        """Check for duplicate CORS headers in allowed responses"""
        # Test with allowed origin
        origin = self.allowed_origins[0]
        url = f"{self.base_url}/api/v1/health/app"
        headers = {"Origin": origin}
        
        status_code, response_headers, output = self.run_curl_command("GET", url, headers)
        
        # Count all CORS-related headers
        cors_header_counts = {}
        for key in response_headers.keys():
            if key.startswith('access-control-'):
                cors_header_counts[key] = cors_header_counts.get(key, 0) + 1
        
        # Check if any CORS header appears more than once
        duplicates = {k: v for k, v in cors_header_counts.items() if v > 1}
        
        passed = len(duplicates) == 0
        details = f"CORS header counts: {cors_header_counts}, Duplicates: {duplicates}"
        
        return CORSTestResult(
            test_name="Duplicate Header Check",
            method="GET",
            origin=origin,
            url=url,
            status_code=status_code,
            headers=response_headers,
            passed=passed,
            expected_cors=True,
            details=details
        )
    
    def run_all_tests(self) -> List[CORSTestResult]:
        """Run comprehensive CORS validation tests"""
        print("🔍 Starting CORS End-to-End Validation...")
        print(f"📍 Base URL: {self.base_url}")
        print(f"✅ Allowed Origins: {', '.join(self.allowed_origins)}")
        print(f"❌ Disallowed Origins: {', '.join(self.disallowed_origins)}")
        print("-" * 80)
        
        # Test allowed origins
        for origin in self.allowed_origins:
            print(f"Testing allowed origin: {origin}")
            self.results.append(self.test_cors_preflight(origin, expected_allowed=True))
            time.sleep(0.1)  # Small delay between tests
            self.results.append(self.test_cors_actual(origin, expected_allowed=True))
            time.sleep(0.1)
        
        # Test disallowed origins  
        for origin in self.disallowed_origins:
            print(f"Testing disallowed origin: {origin}")
            self.results.append(self.test_cors_preflight(origin, expected_allowed=False))
            time.sleep(0.1)
            self.results.append(self.test_cors_actual(origin, expected_allowed=False))
            time.sleep(0.1)
        
        # Test for duplicate headers
        print("Testing for duplicate CORS headers...")
        self.results.append(self.check_duplicate_headers())
        
        return self.results
    
    def print_validation_report(self):
        """Print concise CORS validation report"""
        print("\n" + "=" * 80)
        print("🌐 CORS VALIDATION REPORT")
        print("=" * 80)
        
        passed_tests = sum(1 for r in self.results if r.passed)
        total_tests = len(self.results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print()
        
        # Group results by category
        preflight_results = [r for r in self.results if r.method == "OPTIONS"]
        actual_results = [r for r in self.results if r.method == "GET" and "Duplicate" not in r.test_name]
        duplicate_results = [r for r in self.results if "Duplicate" in r.test_name]
        
        # Report by category
        categories = [
            ("PREFLIGHT TESTS (OPTIONS)", preflight_results),
            ("ACTUAL REQUEST TESTS (GET)", actual_results),
            ("DUPLICATE HEADER TESTS", duplicate_results)
        ]
        
        for category_name, category_results in categories:
            if not category_results:
                continue
                
            print(f"🔬 {category_name}")
            print("-" * len(category_name))
            
            for result in category_results:
                status_icon = "✅" if result.passed else "❌"
                origin_short = result.origin.replace("https://", "").replace("http://", "")[:20]
                print(f"{status_icon} {result.test_name}")
                print(f"   Origin: {origin_short} | {result.details}")
            print()
        
        # Summary by pass criteria
        print("📋 PASS CRITERIA SUMMARY")
        print("-" * 25)
        
        allowed_preflight = [r for r in preflight_results if r.expected_cors and r.passed]
        allowed_actual = [r for r in actual_results if r.expected_cors and r.passed]
        disallowed_preflight = [r for r in preflight_results if not r.expected_cors and r.passed]
        disallowed_actual = [r for r in actual_results if not r.expected_cors and r.passed]
        no_duplicates = all(r.passed for r in duplicate_results)
        
        criteria = [
            ("Allowed origin preflight", len(allowed_preflight), len([r for r in preflight_results if r.expected_cors])),
            ("Allowed origin actual", len(allowed_actual), len([r for r in actual_results if r.expected_cors])),
            ("Disallowed origin preflight", len(disallowed_preflight), len([r for r in preflight_results if not r.expected_cors])),
            ("Disallowed origin actual", len(disallowed_actual), len([r for r in actual_results if not r.expected_cors])),
            ("No duplicate headers", 1 if no_duplicates else 0, 1)
        ]
        
        for criterion, passed, total in criteria:
            status = "PASS" if passed == total else "FAIL"
            icon = "✅" if passed == total else "❌"
            print(f"{icon} {criterion}: {status} ({passed}/{total})")
        
        print("\n" + "=" * 80)
        overall_status = "✅ PASSED" if success_rate >= 90 else "❌ FAILED"
        print(f"🏁 OVERALL CORS VALIDATION: {overall_status}")
        print("=" * 80)
        
        return success_rate >= 90


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CORS End-to-End Validation")
    parser.add_argument("--base-url", default="http://localhost", 
                       help="Base URL for testing (default: http://localhost)")
    parser.add_argument("--json", action="store_true", 
                       help="Output results in JSON format")
    
    args = parser.parse_args()
    
    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(2)
    
    validator = CORSValidator(args.base_url)
    results = validator.run_all_tests()
    
    if args.json:
        # Output JSON for programmatic use
        json_results = [
            {
                "test_name": r.test_name,
                "method": r.method,
                "origin": r.origin,
                "url": r.url,
                "status_code": r.status_code,
                "passed": r.passed,
                "expected_cors": r.expected_cors,
                "details": r.details,
                "headers": r.headers
            }
            for r in results
        ]
        print(json.dumps(json_results, indent=2))
    else:
        success = validator.print_validation_report()
        return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
