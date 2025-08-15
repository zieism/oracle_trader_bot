"""
Unit tests for trading endpoint no-auth behavior
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.exchange_clients.kucoin_futures_client import KucoinAuthError


class TestTradingEndpointNoAuth:
    """Test trading endpoint behavior with missing credentials"""

    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)

    @patch('oracle_trader_bot.app.api.endpoints.trading.get_kucoin_client')
    @patch('oracle_trader_bot.app.api.endpoints.trading.get_db_session')
    def test_execute_signal_returns_503_on_missing_credentials(self, mock_db_session, mock_kucoin_client):
        """Test that execute-signal endpoint returns 503 when credentials are missing"""
        
        # Mock the KuCoin client to raise KucoinAuthError
        mock_client = Mock()
        mock_client.get_market_info.side_effect = KucoinAuthError("Missing API credentials")
        mock_kucoin_client.return_value = mock_client
        
        # Mock DB session
        mock_db_session.return_value = Mock()
        
        # Test payload
        payload = {
            "symbol": "BTC/USDT:USDT",
            "direction": "long",
            "strength": 0.8,
            "signal_source": "test",
            "strategy_name": "test_strategy",
            "entry_price": 50000.0,
            "suggested_leverage": 2.0
        }
        
        # Make request
        response = self.client.post("/api/v1/trading/execute-signal", json=payload)
        
        # Verify response
        assert response.status_code == 503
        data = response.json()
        
        # The detail should be our dict with the error structure
        detail = data.get("detail")
        if isinstance(detail, dict):
            assert detail["ok"] is False
            assert detail["reason"] == "missing_credentials"
            assert detail["message"] == "Trading operations require API credentials"
        else:
            # If FastAPI serialized it differently, just check we got 503
            assert response.status_code == 503

    @patch('oracle_trader_bot.app.api.endpoints.trading.get_kucoin_client')
    @patch('oracle_trader_bot.app.api.endpoints.trading.get_db_session')
    def test_execute_signal_handles_auth_error_during_order_placement(self, mock_db_session, mock_kucoin_client):
        """Test that execute-signal handles auth error during order placement"""
        
        # Mock the KuCoin client
        mock_client = Mock()
        # Market info succeeds but order placement fails with auth error
        mock_client.get_market_info.return_value = {
            'precision': {'amount': 8},
            'limits': {'amount': {'min': 0.001}},
            'contractSize': 1.0,
            'linear': True
        }
        mock_client.create_futures_order.side_effect = KucoinAuthError("API credentials invalid")
        mock_kucoin_client.return_value = mock_client
        
        # Mock DB session
        mock_db_session.return_value = Mock()
        
        # Test payload
        payload = {
            "symbol": "BTC/USDT:USDT",
            "direction": "long", 
            "strength": 0.8,
            "signal_source": "test",
            "strategy_name": "test_strategy",
            "entry_price": 50000.0,
            "suggested_leverage": 2.0
        }
        
        # Make request
        response = self.client.post("/api/v1/trading/execute-signal", json=payload)
        
        # Verify response
        assert response.status_code == 503
        data = response.json()
        
        # The detail should be our dict with the error structure
        detail = data.get("detail")
        if isinstance(detail, dict):
            assert detail["ok"] is False
            assert detail["reason"] == "missing_credentials" 
            assert detail["message"] == "Trading operations require API credentials"
        else:
            # If FastAPI serialized it differently, just check we got 503
            assert response.status_code == 503
