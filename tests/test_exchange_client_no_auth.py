"""
Test exchange client no-auth mode functionality
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.exchange_clients.kucoin_futures_client import (
    KucoinFuturesClient,
    KucoinAuthError,
    KucoinClientException
)
from app.core.config import settings


class TestExchangeClientNoAuth:
    """Test exchange client graceful degradation without credentials."""
    
    @patch.object(settings, 'has_exchange_credentials', return_value=False)
    @patch.object(settings, 'is_sandbox', return_value=False)
    def test_client_initialization_no_auth_mode(self):
        """Test client initializes correctly in no-auth mode."""
        client = KucoinFuturesClient()
        
        assert client.auth_mode == 'no-auth'
        assert client.has_credentials is False
        assert client.is_sandbox is False
        
        status = client.get_client_status()
        expected_status = {
            'ok': False,
            'sandbox': False,
            'mode': 'no-auth', 
            'reason': 'missing_credentials'
        }
        assert status == expected_status

    @patch.object(settings, 'has_exchange_credentials', return_value=True)
    @patch.object(settings, 'is_sandbox', return_value=True)
    def test_client_initialization_auth_mode(self):
        """Test client initializes correctly in auth mode with sandbox."""
        client = KucoinFuturesClient()
        
        assert client.auth_mode == 'auth'
        assert client.has_credentials is True
        assert client.is_sandbox is True
        
        status = client.get_client_status()
        expected_status = {
            'ok': True,
            'sandbox': True,
            'mode': 'auth',
            'reason': None
        }
        assert status == expected_status

    @patch.object(settings, 'has_exchange_credentials', return_value=False)
    def test_require_credentials_raises_auth_error(self):
        """Test that private operations raise KucoinAuthError without credentials."""
        client = KucoinFuturesClient()
        
        with pytest.raises(KucoinAuthError, match="Missing credentials for test operation"):
            client._require_credentials("test operation")

    @patch.object(settings, 'has_exchange_credentials', return_value=False)
    @pytest.mark.asyncio
    async def test_private_methods_raise_auth_error(self):
        """Test that private methods raise authentication errors without credentials."""
        client = KucoinFuturesClient()
        
        # Test account overview
        with pytest.raises(KucoinAuthError):
            await client.get_account_overview()
            
        # Test order creation 
        with pytest.raises(KucoinAuthError):
            await client.create_futures_order("BTC/USDT:USDT", "market", "buy", 0.1)
            
        # Test order fetching
        with pytest.raises(KucoinAuthError):
            await client.fetch_order("test-order-id", "BTC/USDT:USDT")
            
        # Test positions
        with pytest.raises(KucoinAuthError):
            await client.fetch_open_positions()
            
        # Test order cancellation
        with pytest.raises(KucoinAuthError):
            await client.cancel_order_by_id("test-order-id", "BTC/USDT:USDT")

    @patch.object(settings, 'has_exchange_credentials', return_value=False) 
    @pytest.mark.asyncio
    async def test_public_methods_work_without_credentials(self):
        """Test that public methods work without credentials."""
        with patch('app.exchange_clients.kucoin_futures_client.ccxt') as mock_ccxt:
            # Mock the exchange
            mock_exchange = AsyncMock()
            mock_exchange.fetch_time.return_value = 1640995200000
            mock_exchange.load_markets.return_value = True
            mock_exchange.markets = {"BTC/USDT:USDT": {"active": True}}
            
            mock_ccxt.kucoinfutures.return_value = mock_exchange
            
            client = KucoinFuturesClient()
            client.exchange = mock_exchange
            
            # Test server time (public)
            time_result = await client.get_server_time()
            assert time_result is not None
            assert "kucoin_server_time_ms" in time_result
            
            # Test market loading (public)
            await client._ensure_markets_loaded()
            assert client.markets_loaded is True
