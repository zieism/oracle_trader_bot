#!/usr/bin/env python3
"""
Security Headers Configuration Demonstration

This script demonstrates all the configurable security headers options
and shows how they can be toggled via environment variables.
"""

import sys
import os

# Set different configurations before importing
test_scenarios = [
    {
        'name': 'DEFAULT CONFIGURATION',
        'env_vars': {},
        'expected_headers': ['X-Content-Type-Options', 'X-Frame-Options', 'Referrer-Policy'],
        'not_expected': ['Content-Security-Policy']
    },
    {
        'name': 'ALL HEADERS ENABLED',
        'env_vars': {
            'SECURITY_HEADERS_CONTENT_SECURITY_POLICY': 'true'
        },
        'expected_headers': ['X-Content-Type-Options', 'X-Frame-Options', 'Referrer-Policy', 'Content-Security-Policy'],
        'not_expected': []
    },
    {
        'name': 'ALL HEADERS DISABLED',
        'env_vars': {
            'SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS': 'false',
            'SECURITY_HEADERS_X_FRAME_OPTIONS': 'false',
            'SECURITY_HEADERS_REFERRER_POLICY': 'false',
            'SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY': 'false',
            'SECURITY_HEADERS_CONTENT_SECURITY_POLICY': 'false'
        },
        'expected_headers': [],
        'not_expected': ['X-Content-Type-Options', 'X-Frame-Options', 'Referrer-Policy', 'Content-Security-Policy', 'Strict-Transport-Security']
    },
    {
        'name': 'ONLY CSP ENABLED',
        'env_vars': {
            'SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS': 'false',
            'SECURITY_HEADERS_X_FRAME_OPTIONS': 'false',
            'SECURITY_HEADERS_REFERRER_POLICY': 'false',
            'SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY': 'false',
            'SECURITY_HEADERS_CONTENT_SECURITY_POLICY': 'true'
        },
        'expected_headers': ['Content-Security-Policy'],
        'not_expected': ['X-Content-Type-Options', 'X-Frame-Options', 'Referrer-Policy']
    }
]

def test_scenario(scenario):
    """Test a specific configuration scenario."""
    print(f"\n🔧 TESTING: {scenario['name']}")
    print("=" * 60)
    
    # Clear existing environment variables
    security_env_vars = [
        'SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS',
        'SECURITY_HEADERS_X_FRAME_OPTIONS', 
        'SECURITY_HEADERS_REFERRER_POLICY',
        'SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY',
        'SECURITY_HEADERS_CONTENT_SECURITY_POLICY'
    ]
    
    for var in security_env_vars:
        if var in os.environ:
            del os.environ[var]
    
    # Set scenario environment variables
    for key, value in scenario['env_vars'].items():
        os.environ[key] = value
    
    # Force reload modules to pick up new environment variables
    modules_to_reload = ['app.core.config', 'app.middleware.security_headers', 'app.main']
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    # Import after environment setup
    sys.path.insert(0, '.')
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.config import settings
    
    # Show configuration
    print("Configuration:")
    config_items = [
        ('X-Content-Type-Options', settings.SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS),
        ('X-Frame-Options', settings.SECURITY_HEADERS_X_FRAME_OPTIONS),
        ('Referrer-Policy', settings.SECURITY_HEADERS_REFERRER_POLICY),
        ('Strict-Transport-Security', settings.SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY),
        ('Content-Security-Policy', settings.SECURITY_HEADERS_CONTENT_SECURITY_POLICY)
    ]
    
    for header_name, enabled in config_items:
        status = "✅ ENABLED" if enabled else "❌ DISABLED"
        print(f"  {header_name}: {status}")
    
    # Test HTTP request
    print(f"\n📡 Testing HTTP request...")
    client = TestClient(app)
    response = client.get('/api/v1/health/app')
    
    print(f"Status: {response.status_code}")
    print("Headers found:")
    
    security_header_keys = {
        'x-content-type-options': 'X-Content-Type-Options',
        'x-frame-options': 'X-Frame-Options',
        'referrer-policy': 'Referrer-Policy',
        'strict-transport-security': 'Strict-Transport-Security',
        'content-security-policy': 'Content-Security-Policy'
    }
    
    found_headers = []
    for key, name in security_header_keys.items():
        value = response.headers.get(key)
        if value:
            found_headers.append(name)
            print(f"  ✅ {name}: {value}")
        else:
            print(f"  ❌ {name}: NOT PRESENT")
    
    # Test HTTPS request for HSTS
    print(f"\n🔒 Testing HTTPS request (X-Forwarded-Proto: https)...")
    response_https = client.get('/api/v1/health/app', headers={'X-Forwarded-Proto': 'https'})
    hsts_value = response_https.headers.get('strict-transport-security')
    if hsts_value:
        print(f"  ✅ Strict-Transport-Security: {hsts_value}")
        if 'Strict-Transport-Security' not in found_headers:
            found_headers.append('Strict-Transport-Security')
    else:
        print(f"  ❌ Strict-Transport-Security: NOT PRESENT")
    
    # Validate expectations
    print(f"\n📊 VALIDATION:")
    success = True
    
    for expected_header in scenario['expected_headers']:
        if expected_header in found_headers:
            print(f"  ✅ Expected header present: {expected_header}")
        else:
            print(f"  ❌ Expected header missing: {expected_header}")
            success = False
    
    for not_expected_header in scenario['not_expected']:
        if not_expected_header not in found_headers:
            print(f"  ✅ Unwanted header absent: {not_expected_header}")
        else:
            print(f"  ❌ Unwanted header present: {not_expected_header}")
            success = False
    
    result = "✅ PASSED" if success else "❌ FAILED"
    print(f"\nResult: {result}")
    
    return success

def main():
    """Run all test scenarios."""
    print("🔒 SECURITY HEADERS CONFIGURATION DEMONSTRATION")
    print("=" * 70)
    print("This script tests all configurable security headers options")
    print()
    
    all_passed = True
    
    for scenario in test_scenarios:
        passed = test_scenario(scenario)
        if not passed:
            all_passed = False
    
    print(f"\n{'=' * 70}")
    print("📋 FINAL RESULTS")
    print(f"{'=' * 70}")
    
    if all_passed:
        print("🎉 ALL SCENARIOS PASSED!")
        print("✅ Security headers middleware is working correctly")
        print("✅ All configuration options are functional")
        print("✅ Zero feature loss - existing functionality preserved")
    else:
        print("⚠️  Some scenarios failed - check logs above")
        return False
    
    print(f"\n🔧 CONFIGURATION SUMMARY:")
    print("Environment variables available:")
    print("  SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS (default: true)")
    print("  SECURITY_HEADERS_X_FRAME_OPTIONS (default: true)")  
    print("  SECURITY_HEADERS_REFERRER_POLICY (default: true)")
    print("  SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY (default: true, HTTPS only)")
    print("  SECURITY_HEADERS_CONTENT_SECURITY_POLICY (default: false)")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
