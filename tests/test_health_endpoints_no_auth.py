"""
Test health endpoints with no-credentials mode
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


class TestHealthEndpointsNoAuth:
    """Test health endpoints handle missing credentials gracefully."""
    
    @patch.object(settings, 'has_exchange_credentials', return_value=False)
    @patch.object(settings, 'is_sandbox', return_value=False)
    def test_exchange_health_no_credentials(self):
        """Test /api/v1/health/exchange returns 200 with ok=false when no credentials."""
        with TestClient(app) as client:
            with patch('oracle_trader_bot.app.exchange_clients.kucoin_futures_client.KucoinFuturesClient') as mock_client_class:
                # Mock client instance
                mock_client = Mock()
                mock_client.get_client_status.return_value = {
                    'ok': False,
                    'sandbox': False, 
                    'mode': 'no-auth',
                    'reason': 'missing_credentials'
                }
                mock_client._ensure_markets_loaded = AsyncMock()
                mock_client_class.return_value = mock_client
                
                response = client.get("/api/v1/health/exchange")
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["ok"] is False
                assert data["exchange"] == "kucoinfutures"
                assert data["credentials_configured"] is False
                assert data["details"]["mode"] == "no-auth"
                assert data["details"]["sandbox"] is False
                assert data["details"]["reason"] == "missing_credentials"

    @patch.object(settings, 'has_exchange_credentials', return_value=True)
    @patch.object(settings, 'is_sandbox', return_value=True)
    def test_exchange_health_with_credentials(self):
        """Test /api/v1/health/exchange returns 200 with ok=true when credentials available."""
        with TestClient(app) as client:
            with patch('oracle_trader_bot.app.exchange_clients.kucoin_futures_client.KucoinFuturesClient') as mock_client_class:
                # Mock client instance
                mock_client = Mock()
                mock_client.get_client_status.return_value = {
                    'ok': True,
                    'sandbox': True,
                    'mode': 'auth',
                    'reason': None
                }
                mock_client._ensure_markets_loaded = AsyncMock()
                mock_client_class.return_value = mock_client
                
                response = client.get("/api/v1/health/exchange")
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["ok"] is True
                assert data["exchange"] == "kucoinfutures"
                assert data["credentials_configured"] is True
                assert data["details"]["mode"] == "auth"
                assert data["details"]["sandbox"] is True
                assert data["details"]["reason"] is None

    @patch.object(settings, 'has_exchange_credentials', return_value=False)
    def test_account_overview_returns_503_no_credentials(self):
        """Test /api/v1/exchange/kucoin/account-overview returns 503 when no credentials."""
        with TestClient(app) as client:
            with patch('app.api.dependencies.get_kucoin_client') as mock_get_client:
                from app.exchange_clients.kucoin_futures_client import KucoinAuthError
                
                # Mock client that raises auth error
                mock_client = Mock()
                mock_client.get_account_overview.side_effect = KucoinAuthError("Missing credentials for fetching account overview")
                mock_get_client.return_value = mock_client
                
                response = client.get("/api/v1/exchange/kucoin/account-overview")
                
                assert response.status_code == 503
                data = response.json()
                
                assert "detail" in data
                detail = data["detail"]
                assert detail["ok"] is False
                assert detail["reason"] == "missing_credentials"

    @patch.object(settings, 'has_exchange_credentials', return_value=False) 
    def test_symbols_endpoint_works_no_credentials(self):
        """Test /api/v1/exchange/symbols works without credentials (public endpoint)."""
        with TestClient(app) as client:
            with patch('app.api.dependencies.get_kucoin_client') as mock_get_client:
                # Mock client for public endpoint
                mock_client = Mock()
                mock_client.get_active_contracts = AsyncMock(return_value=[
                    {"symbol": "BTC/USDT:USDT", "active": True},
                    {"symbol": "ETH/USDT:USDT", "active": True}
                ])
                mock_get_client.return_value = mock_client
                
                response = client.get("/api/v1/exchange/symbols")
                
                # Should work fine - public endpoint
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["symbol"] == "BTC/USDT:USDT"

    @patch.object(settings, 'has_exchange_credentials', return_value=False)
    def test_order_status_returns_503_no_credentials(self):
        """Test order status endpoint returns 503 when no credentials."""
        with TestClient(app) as client:
            with patch('app.api.dependencies.get_kucoin_client') as mock_get_client:
                from app.exchange_clients.kucoin_futures_client import KucoinAuthError
                
                # Mock client that raises auth error
                mock_client = Mock()
                mock_client.fetch_order.side_effect = KucoinAuthError("Missing credentials for fetching order information")
                mock_get_client.return_value = mock_client
                
                response = client.get("/api/v1/orders/status/BTC%2FUSDT%3AUSDT/test-order-id")
                
                assert response.status_code == 503
                data = response.json()
                
                assert "detail" in data
                detail = data["detail"]
                assert detail["ok"] is False
                assert detail["reason"] == "missing_credentials"
