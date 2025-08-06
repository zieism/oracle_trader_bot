import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.exchanges.manager import ExchangeManager
from app.exchanges.binance import BinanceExchange
from app.exchanges.coinbase import CoinbaseExchange
from app.exchanges.kraken import KrakenExchange


class TestExchangeManager:
    """Test the ExchangeManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ExchangeManager()
    
    def test_register_exchange(self):
        """Test exchange registration."""
        config = {
            'api_key': 'test_key',
            'api_secret': 'test_secret'
        }
        
        self.manager.register_exchange(
            'binance', 
            BinanceExchange, 
            config, 
            is_primary=True
        )
        
        assert 'binance' in self.manager.exchange_configs
        assert self.manager.primary_exchange == 'binance'
        assert self.manager.exchange_configs['binance']['class'] == BinanceExchange
    
    @pytest.mark.asyncio
    async def test_connect_all_success(self):
        """Test successful connection to all exchanges."""
        # Mock exchange instances
        mock_binance = AsyncMock()
        mock_binance.connect.return_value = True
        
        mock_coinbase = AsyncMock()
        mock_coinbase.connect.return_value = True
        
        # Patch exchange classes
        with patch.object(BinanceExchange, '__new__', return_value=mock_binance), \
             patch.object(CoinbaseExchange, '__new__', return_value=mock_coinbase):
            
            # Register exchanges
            self.manager.register_exchange('binance', BinanceExchange, {
                'api_key': 'test_key',
                'api_secret': 'test_secret'
            }, is_primary=True)
            
            self.manager.register_exchange('coinbase', CoinbaseExchange, {
                'api_key': 'test_key',
                'api_secret': 'test_secret',
                'passphrase': 'test_passphrase'
            })
            
            # Test connection
            results = await self.manager.connect_all()
            
            assert results['binance'] is True
            assert results['coinbase'] is True
            assert len(self.manager.exchanges) == 2
    
    @pytest.mark.asyncio
    async def test_get_ticker_with_failover(self):
        """Test ticker retrieval with failover."""
        # Mock exchanges
        mock_primary = AsyncMock()
        mock_primary.get_ticker.side_effect = Exception("Primary failed")
        mock_primary.is_connected = True
        
        mock_secondary = AsyncMock()
        mock_secondary.get_ticker.return_value = {
            'symbol': 'BTC/USDT',
            'bid': 50000,
            'ask': 50100,
            'last': 50050
        }
        mock_secondary.is_connected = True
        
        # Set up manager with mock exchanges
        self.manager.exchanges = {
            'binance': mock_primary,
            'coinbase': mock_secondary
        }
        self.manager.primary_exchange = 'binance'
        
        # Test failover
        result = await self.manager.get_ticker('BTC/USDT')
        
        assert result['symbol'] == 'BTC/USDT'
        assert result['exchange'] == 'coinbase'
        assert mock_primary.get_ticker.called
        assert mock_secondary.get_ticker.called
    
    @pytest.mark.asyncio
    async def test_find_arbitrage_opportunities(self):
        """Test arbitrage opportunity detection."""
        # Mock exchanges with different prices
        mock_binance = AsyncMock()
        mock_binance.get_ticker.return_value = {
            'symbol': 'BTC/USDT',
            'bid': 50000,
            'ask': 50100,
            'timestamp': 1234567890
        }
        
        mock_coinbase = AsyncMock()
        mock_coinbase.get_ticker.return_value = {
            'symbol': 'BTC/USDT',
            'bid': 50200,  # Higher bid price
            'ask': 50300,
            'timestamp': 1234567890
        }
        
        self.manager.exchanges = {
            'binance': mock_binance,
            'coinbase': mock_coinbase
        }
        
        # Find arbitrage opportunities
        opportunities = await self.manager.find_arbitrage_opportunities('BTC/USDT', 0.1)
        
        assert len(opportunities) > 0
        # Should find opportunity to buy on Binance and sell on Coinbase
        opp = opportunities[0]
        assert opp['buy_exchange'] == 'binance'
        assert opp['sell_exchange'] == 'coinbase'
        assert opp['profit_percentage'] > 0.1
    
    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check for all exchanges."""
        mock_binance = AsyncMock()
        mock_binance.health_check.return_value = {
            'status': 'healthy',
            'exchange': 'binance',
            'connected': True
        }
        
        mock_coinbase = AsyncMock()
        mock_coinbase.health_check.return_value = {
            'status': 'unhealthy',
            'exchange': 'coinbase',
            'connected': False,
            'error': 'Connection timeout'
        }
        
        self.manager.exchanges = {
            'binance': mock_binance,
            'coinbase': mock_coinbase
        }
        
        health_results = await self.manager.health_check_all()
        
        assert health_results['binance']['status'] == 'healthy'
        assert health_results['coinbase']['status'] == 'unhealthy'
    
    def test_get_available_exchanges(self):
        """Test getting available exchanges."""
        mock_exchange = AsyncMock()
        self.manager.exchanges = {'binance': mock_exchange}
        
        available = self.manager.get_available_exchanges()
        assert available == ['binance']
    
    def test_is_exchange_available(self):
        """Test checking if exchange is available."""
        mock_exchange = AsyncMock()
        mock_exchange.is_connected = True
        self.manager.exchanges = {'binance': mock_exchange}
        
        assert self.manager.is_exchange_available('binance') is True
        assert self.manager.is_exchange_available('coinbase') is False