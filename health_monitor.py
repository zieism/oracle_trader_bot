#!/usr/bin/env python3
"""
Health Monitor Script for Oracle Trader Bot

Monitors critical application endpoints and exits with non-zero code on failures.
Designed to run as a cron job or in CI/CD pipelines for continuous health monitoring.

Usage:
    python health_monitor.py [--url BASE_URL] [--timeout SECONDS] [--verbose]
    
Examples:
    python health_monitor.py --url http://localhost:8000
    python health_monitor.py --url https://api.oracletrader.app --timeout 30
"""

import asyncio
import aiohttp
import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import argparse
import logging
from dataclasses import dataclass


@dataclass
class HealthCheck:
    """Health check configuration"""
    name: str
    endpoint: str
    required: bool = True
    timeout: int = 10
    expected_status: int = 200


@dataclass
class HealthResult:
    """Health check result"""
    name: str
    endpoint: str
    success: bool
    status_code: int
    response_time_ms: int
    error: Optional[str] = None
    details: Optional[Dict] = None


class HealthMonitor:
    """Health monitoring system for Oracle Trader Bot"""
    
    def __init__(self, base_url: str, global_timeout: int = 30, verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.global_timeout = global_timeout
        self.verbose = verbose
        
        # Configure logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
        # Define health checks to monitor
        self.health_checks = [
            HealthCheck(
                name="Application Health",
                endpoint="/api/v1/health/app",
                required=True,
                timeout=10
            ),
            HealthCheck(
                name="Database Health", 
                endpoint="/api/v1/health/db",
                required=False,  # DB can be optional in lite mode
                timeout=15
            ),
            HealthCheck(
                name="Exchange Health",
                endpoint="/api/v1/health/exchange",
                required=False,  # Exchange can be in no-auth mode
                timeout=15
            ),
            HealthCheck(
                name="Legacy Health",
                endpoint="/api/v1/health",
                required=True,
                timeout=10
            )
        ]
    
    async def check_endpoint(self, session: aiohttp.ClientSession, check: HealthCheck) -> HealthResult:
        """Perform a single health check"""
        url = f"{self.base_url}{check.endpoint}"
        start_time = time.time()
        
        try:
            self.logger.debug(f"Checking {check.name}: {url}")
            
            async with session.get(
                url, 
                timeout=aiohttp.ClientTimeout(total=check.timeout)
            ) as response:
                response_time_ms = int((time.time() - start_time) * 1000)
                
                # Try to parse JSON response
                try:
                    response_data = await response.json()
                except:
                    response_data = {"raw": await response.text()}
                
                success = response.status == check.expected_status
                
                # Additional validation for health endpoints
                if success and "ok" in response_data:
                    # For health endpoints, also check the "ok" field
                    success = response_data.get("ok", False)
                
                result = HealthResult(
                    name=check.name,
                    endpoint=check.endpoint,
                    success=success,
                    status_code=response.status,
                    response_time_ms=response_time_ms,
                    details=response_data
                )
                
                if success:
                    self.logger.info(f"✅ {check.name}: OK ({response_time_ms}ms)")
                else:
                    error_msg = f"HTTP {response.status}"
                    if not response_data.get("ok", True):
                        error_msg += f" - {response_data.get('error', 'Health check failed')}"
                    result.error = error_msg
                    self.logger.warning(f"❌ {check.name}: {error_msg} ({response_time_ms}ms)")
                
                return result
                
        except asyncio.TimeoutError:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Timeout after {check.timeout}s"
            self.logger.error(f"⏱️  {check.name}: {error_msg}")
            
            return HealthResult(
                name=check.name,
                endpoint=check.endpoint,
                success=False,
                status_code=0,
                response_time_ms=response_time_ms,
                error=error_msg
            )
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Connection error: {str(e)}"
            self.logger.error(f"🔌 {check.name}: {error_msg}")
            
            return HealthResult(
                name=check.name,
                endpoint=check.endpoint,
                success=False,
                status_code=0,
                response_time_ms=response_time_ms,
                error=error_msg
            )
    
    async def run_health_checks(self) -> Tuple[List[HealthResult], bool]:
        """Run all health checks and return results"""
        self.logger.info(f"🔍 Starting health monitoring for {self.base_url}")
        start_time = datetime.now(timezone.utc)
        
        # Create aiohttp session with appropriate timeout
        timeout = aiohttp.ClientTimeout(total=self.global_timeout)
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        results = []
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # Run health checks concurrently
            tasks = [
                self.check_endpoint(session, check) 
                for check in self.health_checks
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions from gather
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    check = self.health_checks[i]
                    final_results.append(HealthResult(
                        name=check.name,
                        endpoint=check.endpoint,
                        success=False,
                        status_code=0,
                        response_time_ms=0,
                        error=f"Task exception: {str(result)}"
                    ))
                else:
                    final_results.append(result)
            
            results = final_results
        
        # Analyze results
        total_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        successful_checks = sum(1 for r in results if r.success)
        required_failures = sum(
            1 for i, r in enumerate(results) 
            if not r.success and self.health_checks[i].required
        )
        
        overall_success = required_failures == 0
        
        # Log summary
        self.logger.info(f"📊 Health check summary:")
        self.logger.info(f"   Total checks: {len(results)}")
        self.logger.info(f"   Successful: {successful_checks}")
        self.logger.info(f"   Failed: {len(results) - successful_checks}")
        self.logger.info(f"   Required failures: {required_failures}")
        self.logger.info(f"   Total time: {total_time:.2f}s")
        self.logger.info(f"   Overall status: {'✅ HEALTHY' if overall_success else '❌ UNHEALTHY'}")
        
        return results, overall_success
    
    def generate_report(self, results: List[HealthResult], overall_success: bool) -> Dict:
        """Generate a detailed health report"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        report = {
            "timestamp": timestamp,
            "base_url": self.base_url,
            "overall_success": overall_success,
            "summary": {
                "total_checks": len(results),
                "successful": sum(1 for r in results if r.success),
                "failed": sum(1 for r in results if not r.success),
                "required_failures": sum(
                    1 for i, r in enumerate(results)
                    if not r.success and self.health_checks[i].required
                )
            },
            "checks": []
        }
        
        for i, result in enumerate(results):
            check_config = self.health_checks[i]
            check_report = {
                "name": result.name,
                "endpoint": result.endpoint,
                "required": check_config.required,
                "success": result.success,
                "status_code": result.status_code,
                "response_time_ms": result.response_time_ms,
                "error": result.error,
                "details": result.details
            }
            report["checks"].append(check_report)
        
        return report
    
    def print_report(self, results: List[HealthResult], overall_success: bool):
        """Print a human-readable health report"""
        print("\n" + "="*80)
        print("🏥 ORACLE TRADER BOT - HEALTH MONITOR REPORT")
        print("="*80)
        print(f"📍 Target: {self.base_url}")
        print(f"⏰ Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"🎯 Overall Status: {'✅ HEALTHY' if overall_success else '❌ UNHEALTHY'}")
        print()
        
        # Print individual check results
        for i, result in enumerate(results):
            check_config = self.health_checks[i]
            status_icon = "✅" if result.success else "❌"
            required_badge = "[REQ]" if check_config.required else "[OPT]"
            
            print(f"{status_icon} {required_badge} {result.name}")
            print(f"   Endpoint: {result.endpoint}")
            print(f"   Status: {result.status_code} ({result.response_time_ms}ms)")
            
            if result.error:
                print(f"   Error: {result.error}")
            elif result.details and self.verbose:
                print(f"   Response: {json.dumps(result.details, indent=6)}")
            
            print()
        
        # Summary statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        required_failures = sum(
            1 for i, r in enumerate(results)
            if not r.success and self.health_checks[i].required
        )
        
        print("📊 SUMMARY")
        print(f"   Total checks: {len(results)}")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   🚨 Required failures: {required_failures}")
        print()
        
        if not overall_success:
            print("❌ HEALTH CHECK FAILED - Required services are not responding properly")
            print("   Please investigate the failed endpoints immediately.")
        else:
            print("✅ HEALTH CHECK PASSED - All required services are healthy")
        
        print("="*80)


async def main():
    """Main health monitor function"""
    parser = argparse.ArgumentParser(
        description="Oracle Trader Bot Health Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python health_monitor.py --url http://localhost:8000
    python health_monitor.py --url https://api.oracletrader.app --timeout 30 --verbose
    python health_monitor.py --url http://localhost:8000 --json > health_report.json
        """
    )
    
    parser.add_argument(
        '--url', 
        default='http://localhost:8000',
        help='Base URL of the Oracle Trader Bot API (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Global timeout in seconds for all checks (default: 30)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging and detailed output'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format instead of human-readable'
    )
    parser.add_argument(
        '--interval',
        type=int,
        help='Run continuously with specified interval in seconds'
    )
    
    args = parser.parse_args()
    
    # Initialize health monitor
    monitor = HealthMonitor(
        base_url=args.url,
        global_timeout=args.timeout,
        verbose=args.verbose
    )
    
    if args.interval:
        # Continuous monitoring mode
        print(f"🔄 Starting continuous health monitoring (interval: {args.interval}s)")
        print(f"📍 Target: {args.url}")
        print("Press Ctrl+C to stop...")
        print()
        
        try:
            while True:
                results, overall_success = await monitor.run_health_checks()
                
                if args.json:
                    report = monitor.generate_report(results, overall_success)
                    print(json.dumps(report, indent=2))
                else:
                    monitor.print_report(results, overall_success)
                
                if not overall_success:
                    print(f"⚠️  Health check failed, waiting {args.interval}s before retry...")
                
                await asyncio.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            return 0
    else:
        # Single check mode
        results, overall_success = await monitor.run_health_checks()
        
        if args.json:
            report = monitor.generate_report(results, overall_success)
            print(json.dumps(report, indent=2))
        else:
            monitor.print_report(results, overall_success)
        
        # Exit with appropriate code
        return 0 if overall_success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Health monitor interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Health monitor failed: {e}")
        sys.exit(1)
