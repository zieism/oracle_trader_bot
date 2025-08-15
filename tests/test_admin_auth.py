# tests/test_admin_auth.py
"""
Tests for Optional Admin Authentication System

Comprehensive tests covering:
- Token authentication when enabled
- No authentication when disabled
- Proper error responses
- Logging without token exposure
- All protected endpoints
"""

import os
import tempfile
from unittest.mock import patch, Mock
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.security.admin_auth import AdminAuthGuard
from app.main import app


class TestAdminAuthGuard:
    """Test suite for the AdminAuthGuard class"""

    def test_disabled_when_no_token_set(self):
        """Test that guard is disabled when ADMIN_API_TOKEN is not set"""
        with patch.dict(os.environ, {}, clear=False):
            # Remove token if it exists
            if 'ADMIN_API_TOKEN' in os.environ:
                del os.environ['ADMIN_API_TOKEN']
            
            guard = AdminAuthGuard()
            assert guard.is_enabled is False
            assert guard.admin_token == ""

    def test_disabled_when_empty_token_set(self):
        """Test that guard is disabled when ADMIN_API_TOKEN is empty"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': ''}):
            guard = AdminAuthGuard()
            assert guard.is_enabled is False

    def test_disabled_when_whitespace_token_set(self):
        """Test that guard is disabled when ADMIN_API_TOKEN is only whitespace"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': '   '}):
            guard = AdminAuthGuard()
            assert guard.is_enabled is False

    def test_enabled_when_token_set(self):
        """Test that guard is enabled when ADMIN_API_TOKEN has value"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'test-token-123'}):
            guard = AdminAuthGuard()
            assert guard.is_enabled is True
            assert guard.admin_token == "test-token-123"

    def test_no_verification_when_disabled(self):
        """Test that no verification occurs when guard is disabled"""
        with patch.dict(os.environ, {}, clear=False):
            if 'ADMIN_API_TOKEN' in os.environ:
                del os.environ['ADMIN_API_TOKEN']
            
            guard = AdminAuthGuard()
            mock_request = Mock(spec=Request)
            
            # Should not raise any exception
            try:
                guard.verify_admin_token(mock_request)
            except Exception as e:
                pytest.fail(f"verify_admin_token should not raise when disabled, but raised: {e}")

    def test_missing_token_header_when_enabled(self):
        """Test 401 response when token header is missing and guard is enabled"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'test-token-123'}):
            guard = AdminAuthGuard()
            
            mock_request = Mock(spec=Request)
            mock_request.headers = {}
            mock_request.client = Mock()
            mock_request.client.host = "127.0.0.1"
            
            with pytest.raises(Exception) as exc_info:
                guard.verify_admin_token(mock_request)
            
            # Should be HTTPException with 401 status
            assert hasattr(exc_info.value, 'status_code')
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == {"ok": False, "reason": "unauthorized"}

    def test_invalid_token_when_enabled(self):
        """Test 401 response when token header is wrong and guard is enabled"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'correct-token'}):
            guard = AdminAuthGuard()
            
            mock_request = Mock(spec=Request)
            mock_request.headers = {"X-Admin-Token": "wrong-token"}
            mock_request.client = Mock()
            mock_request.client.host = "127.0.0.1"
            
            with pytest.raises(Exception) as exc_info:
                guard.verify_admin_token(mock_request)
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == {"ok": False, "reason": "unauthorized"}

    def test_valid_token_when_enabled(self):
        """Test successful verification when correct token provided"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'correct-token'}):
            guard = AdminAuthGuard()
            
            mock_request = Mock(spec=Request)
            mock_request.headers = {"X-Admin-Token": "correct-token"}
            mock_request.client = Mock()
            mock_request.client.host = "127.0.0.1"
            
            # Should not raise any exception
            try:
                guard.verify_admin_token(mock_request)
            except Exception as e:
                pytest.fail(f"verify_admin_token should not raise with valid token, but raised: {e}")

    def test_token_extraction_with_whitespace(self):
        """Test that tokens with surrounding whitespace are handled correctly"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'test-token'}):
            guard = AdminAuthGuard()
            
            mock_request = Mock(spec=Request)
            mock_request.headers = {"X-Admin-Token": "  test-token  "}
            mock_request.client = Mock()
            mock_request.client.host = "127.0.0.1"
            
            # Should not raise - whitespace should be stripped
            guard.verify_admin_token(mock_request)

    def test_client_ip_extraction_from_proxy_headers(self):
        """Test that client IP is correctly extracted from proxy headers"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'test-token'}):
            guard = AdminAuthGuard()
            
            # Test with X-Forwarded-For header
            mock_request = Mock(spec=Request)
            mock_request.headers = {
                "X-Admin-Token": "wrong-token",
                "x-forwarded-for": "203.0.113.1, 192.168.1.1"
            }
            mock_request.client = None
            
            with patch('app.security.admin_auth.logger') as mock_logger:
                with pytest.raises(Exception):
                    guard.verify_admin_token(mock_request)
                
                # Check that IP was extracted from X-Forwarded-For
                mock_logger.warning.assert_called_once()
                log_call = mock_logger.warning.call_args[0][0]
                assert "IP: 203.0.113.1" in log_call

    def test_logging_does_not_expose_tokens(self):
        """Test that authentication logs never expose actual token values"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'secret-token-123'}):
            guard = AdminAuthGuard()
            
            mock_request = Mock(spec=Request)
            mock_request.headers = {"X-Admin-Token": "wrong-secret-token"}
            mock_request.client = Mock()
            mock_request.client.host = "192.168.1.100"
            
            with patch('app.security.admin_auth.logger') as mock_logger:
                with pytest.raises(Exception):
                    guard.verify_admin_token(mock_request)
                
                # Check that no token values appear in log messages
                for call in mock_logger.warning.call_args_list:
                    log_message = call[0][0]
                    assert "secret-token-123" not in log_message
                    assert "wrong-secret-token" not in log_message


class TestAdminAuthAPI:
    """Test suite for API endpoints with admin authentication"""

    def test_settings_update_without_token_when_disabled(self):
        """Test PUT /settings works without token when auth is disabled"""
        # Ensure no admin token is set
        with patch.dict(os.environ, {}, clear=False):
            if 'ADMIN_API_TOKEN' in os.environ:
                del os.environ['ADMIN_API_TOKEN']
            
            # Force reload of admin auth
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    response = client.put("/api/v1/settings", json={
                        "PROJECT_NAME": "Test No Auth"
                    })
                    
                    assert response.status_code == 200

    def test_settings_update_without_token_when_enabled(self):
        """Test PUT /settings returns 401 without token when auth is enabled"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'test-admin-token'}):
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('oracle_trader_bot.app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    response = client.put("/api/v1/settings", json={
                        "PROJECT_NAME": "Test With Auth"
                    })
                    
                    assert response.status_code == 401
                    data = response.json()["detail"]
                    assert data["ok"] is False
                    assert data["reason"] == "unauthorized"

    def test_settings_update_with_wrong_token_when_enabled(self):
        """Test PUT /settings returns 401 with wrong token when auth is enabled"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'correct-token'}):
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('oracle_trader_bot.app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    response = client.put("/api/v1/settings", 
                        json={"PROJECT_NAME": "Test Wrong Token"},
                        headers={"X-Admin-Token": "wrong-token"}
                    )
                    
                    assert response.status_code == 401
                    data = response.json()["detail"]
                    assert data["ok"] is False
                    assert data["reason"] == "unauthorized"

    def test_settings_update_with_correct_token_when_enabled(self):
        """Test PUT /settings works with correct token when auth is enabled"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'correct-token'}):
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    response = client.put("/api/v1/settings", 
                        json={"PROJECT_NAME": "Test Correct Token"},
                        headers={"X-Admin-Token": "correct-token"}
                    )
                    
                    assert response.status_code == 200

    def test_audit_endpoint_without_token_when_disabled(self):
        """Test GET /settings/audit works without token when auth is disabled"""
        with patch.dict(os.environ, {}, clear=False):
            if 'ADMIN_API_TOKEN' in os.environ:
                del os.environ['ADMIN_API_TOKEN']
            
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    response = client.get("/api/v1/settings/audit")
                    
                    assert response.status_code == 200

    def test_audit_endpoint_without_token_when_enabled(self):
        """Test GET /settings/audit returns 401 without token when auth is enabled"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'audit-token'}):
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('oracle_trader_bot.app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    response = client.get("/api/v1/settings/audit")
                    
                    assert response.status_code == 401

    def test_audit_endpoint_with_correct_token_when_enabled(self):
        """Test GET /settings/audit works with correct token when auth is enabled"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'audit-token'}):
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('oracle_trader_bot.app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    response = client.get("/api/v1/settings/audit",
                        headers={"X-Admin-Token": "audit-token"}
                    )
                    
                    assert response.status_code == 200

    def test_reset_endpoint_without_token_when_disabled(self):
        """Test POST /settings/reset works without token when auth is disabled"""
        with patch.dict(os.environ, {}, clear=False):
            if 'ADMIN_API_TOKEN' in os.environ:
                del os.environ['ADMIN_API_TOKEN']
            
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    response = client.post("/api/v1/settings/reset")
                    
                    assert response.status_code == 200

    def test_reset_endpoint_without_token_when_enabled(self):
        """Test POST /settings/reset returns 401 without token when auth is enabled"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'reset-token'}):
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('oracle_trader_bot.app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    response = client.post("/api/v1/settings/reset")
                    
                    assert response.status_code == 401

    def test_reset_endpoint_with_correct_token_when_enabled(self):
        """Test POST /settings/reset works with correct token when auth is enabled"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'reset-token'}):
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('oracle_trader_bot.app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    response = client.post("/api/v1/settings/reset",
                        headers={"X-Admin-Token": "reset-token"}
                    )
                    
                    assert response.status_code == 200

    def test_get_settings_not_protected(self):
        """Test GET /settings is not protected even when auth is enabled"""
        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'some-token'}):
            from app.security.admin_auth import AdminAuthGuard
            test_guard = AdminAuthGuard()
            
            with patch('oracle_trader_bot.app.security.admin_auth.admin_auth', test_guard):
                with TestClient(app) as client:
                    # Should work without token - GET is not protected
                    response = client.get("/api/v1/settings")
                    
                    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
