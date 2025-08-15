"""
Tests for network utilities
"""
import pytest
import os
from unittest.mock import Mock, patch


def test_resolve_external_base_url_with_env():
    """Test resolution with EXTERNAL_BASE_URL environment variable"""
    from oracle_trader_bot.app.core.network import resolve_external_base_url
    
    with patch.dict(os.environ, {'EXTERNAL_BASE_URL': 'https://api.mybot.com'}):
        result = resolve_external_base_url()
        assert result == 'https://api.mybot.com'


def test_resolve_external_base_url_with_forwarded_headers():
    """Test resolution with X-Forwarded headers (reverse proxy)"""
    from oracle_trader_bot.app.core.network import resolve_external_base_url
    
    # Mock FastAPI Request object
    mock_request = Mock()
    mock_request.headers = {
        'x-forwarded-proto': 'https',
        'x-forwarded-host': 'api.example.com'
    }
    
    with patch.dict(os.environ, {}, clear=True):
        result = resolve_external_base_url(mock_request)
        assert result == 'https://api.example.com'


def test_resolve_external_base_url_with_request_url():
    """Test resolution from request URL when no headers available"""
    from oracle_trader_bot.app.core.network import resolve_external_base_url
    
    # Mock FastAPI Request object
    mock_request = Mock()
    mock_request.headers = {}
    mock_request.url = Mock()
    mock_request.url.__str__ = Mock(return_value='http://localhost:8000/api/v1/test')
    
    with patch.dict(os.environ, {}, clear=True):
        result = resolve_external_base_url(mock_request)
        assert result == 'http://localhost:8000'


def test_resolve_external_base_url_fallback():
    """Test fallback to API_INTERNAL_BASE_URL"""
    from oracle_trader_bot.app.core.network import resolve_external_base_url
    
    with patch.dict(os.environ, {'API_INTERNAL_BASE_URL': 'http://internal:8000'}, clear=True):
        result = resolve_external_base_url()
        assert result == 'http://internal:8000'


def test_resolve_external_base_url_default_fallback():
    """Test default fallback when no environment variables set"""
    from oracle_trader_bot.app.core.network import resolve_external_base_url
    
    with patch.dict(os.environ, {}, clear=True):
        result = resolve_external_base_url()
        assert result == 'http://localhost:8000'


def test_get_cors_origins():
    """Test CORS origins generation"""
    from oracle_trader_bot.app.core.network import get_cors_origins
    
    with patch.dict(os.environ, {'EXTERNAL_BASE_URL': 'https://api.mybot.com'}):
        origins = get_cors_origins()
        
        # Should include development origins + production variants
        assert 'http://localhost:5173' in origins
        assert 'https://api.mybot.com' in origins
        assert 'http://api.mybot.com' in origins


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
