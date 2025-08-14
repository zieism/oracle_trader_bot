"""
End-to-End Tests for Oracle Trader Bot

This package contains E2E tests for the complete Oracle Trader Bot system:

- test_api_flow.py: Backend API flow tests (settings, health, analysis, trading)  
- test_ui_minimal.py: Basic frontend UI tests with Playwright

Usage:
    # Run API E2E tests
    python tests_e2e/test_api_flow.py
    
    # Run UI E2E tests (requires playwright)
    pip install playwright pytest-playwright
    playwright install
    python tests_e2e/test_ui_minimal.py
    
    # Run with pytest
    pytest tests_e2e/ -v
"""

__version__ = "1.0.0"
__author__ = "Oracle Trader Bot Team"
