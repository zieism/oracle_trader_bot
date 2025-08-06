import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.exchanges.arbitrage import ArbitrageService, ArbitrageOpportunity
from app.exchanges.manager import ExchangeManager
from app.exchanges.base import OrderSide, OrderType


class TestArbitrageService:
    """Test the ArbitrageService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_manager = AsyncMock(spec=ExchangeManager)
        self.service = ArbitrageService(self.mock_manager)
    
    @pytest.mark.asyncio
    async def test_scan_opportunities(self):
        """Test scanning for arbitrage opportunities."""
        # Mock exchange manager to return opportunities
        self.mock_manager.find_arbitrage_opportunities.return_value = [{
            'symbol': 'BTC/USDT',
            'buy_exchange': 'binance',
            'sell_exchange': 'coinbase',
            'buy_price': 50000,
            'sell_price': 50500,
            'profit_percentage': 1.0,
            'timestamp': 1234567890
        }]
        
        # Mock max amount calculation
        with patch.object(self.service, '_calculate_max_amount', return_value=1000.0):
            opportunities = await self.service.scan_opportunities(['BTC/USDT'])
            
            assert len(opportunities) == 1
            opp = opportunities[0]
            assert isinstance(opp, ArbitrageOpportunity)
            assert opp.symbol == 'BTC/USDT'
            assert opp.profit_percentage == 1.0
            assert opp.max_amount == 1000.0
    
    @pytest.mark.asyncio
    async def test_execute_arbitrage(self):
        """Test executing an arbitrage opportunity."""
        opportunity = ArbitrageOpportunity(
            symbol='BTC/USDT',
            buy_exchange='binance',
            sell_exchange='coinbase',
            buy_price=50000,
            sell_price=50500,
            profit_percentage=1.0,
            max_amount=1000.0,
            timestamp=1234567890
        )
        
        # Mock order execution
        buy_result = {
            'id': 'buy_order_123',
            'amount': 0.02,
            'price': 50000,
            'timestamp': 1234567890
        }
        
        sell_result = {
            'id': 'sell_order_456',
            'amount': 0.02,
            'price': 50500,
            'timestamp': 1234567890
        }
        
        with patch.object(self.service, '_place_buy_order', return_value=buy_result), \
             patch.object(self.service, '_place_sell_order', return_value=sell_result):
            
            result = await self.service.execute_arbitrage(opportunity, 100.0)
            
            assert result['success'] is True
            assert result['profit_usd'] == 10.0  # (50500 - 50000) * 0.02
            assert result['buy_order']['id'] == 'buy_order_123'
            assert result['sell_order']['id'] == 'sell_order_456'
    
    @pytest.mark.asyncio
    async def test_place_buy_order(self):
        """Test placing a buy order."""
        opportunity = ArbitrageOpportunity(
            symbol='BTC/USDT',
            buy_exchange='binance',
            sell_exchange='coinbase',
            buy_price=50000,
            sell_price=50500,
            profit_percentage=1.0,
            max_amount=1000.0,
            timestamp=1234567890
        )
        
        expected_order_data = {
            "symbol": 'BTC/USDT',
            "side": OrderSide.BUY,
            "type": OrderType.MARKET,
            "amount": 0.02
        }
        
        mock_result = {'id': 'buy_order_123'}
        self.mock_manager.place_order.return_value = mock_result
        
        result = await self.service._place_buy_order(opportunity, 0.02)
        
        self.mock_manager.place_order.assert_called_once_with(
            expected_order_data, 
            'binance'
        )
        assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_place_sell_order(self):
        """Test placing a sell order."""
        opportunity = ArbitrageOpportunity(
            symbol='BTC/USDT',
            buy_exchange='binance',
            sell_exchange='coinbase',
            buy_price=50000,
            sell_price=50500,
            profit_percentage=1.0,
            max_amount=1000.0,
            timestamp=1234567890
        )
        
        expected_order_data = {
            "symbol": 'BTC/USDT',
            "side": OrderSide.SELL,
            "type": OrderType.MARKET,
            "amount": 0.02
        }
        
        mock_result = {'id': 'sell_order_456'}
        self.mock_manager.place_order.return_value = mock_result
        
        result = await self.service._place_sell_order(opportunity, 0.02)
        
        self.mock_manager.place_order.assert_called_once_with(
            expected_order_data, 
            'coinbase'
        )
        assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_calculate_max_amount(self):
        """Test calculating maximum safe trading amount."""
        opportunity = {
            'buy_exchange': 'binance',
            'sell_exchange': 'coinbase',
            'symbol': 'BTC/USDT'
        }
        
        # Mock orderbooks
        buy_orderbook = {
            'asks': [[50000, 0.1], [50100, 0.2], [50200, 0.3]]  # price, amount
        }
        
        sell_orderbook = {
            'bids': [[50500, 0.15], [50400, 0.25], [50300, 0.35]]
        }
        
        mock_buy_exchange = AsyncMock()
        mock_buy_exchange.get_orderbook.return_value = buy_orderbook
        
        mock_sell_exchange = AsyncMock()
        mock_sell_exchange.get_orderbook.return_value = sell_orderbook
        
        self.mock_manager.exchanges = {
            'binance': mock_buy_exchange,
            'coinbase': mock_sell_exchange
        }
        
        max_amount = await self.service._calculate_max_amount(opportunity)
        
        # Should calculate based on minimum depth * 0.1
        # Buy depth: 50000*0.1 + 50100*0.2 + 50200*0.3 = 30140
        # Sell depth: 50500*0.15 + 50400*0.25 + 50300*0.35 = 30250
        # Min depth: 30140, so max_amount = 30140 * 0.1 = 3014
        expected_max = min(3014.0, self.service.max_position_size)
        assert max_amount == expected_max
    
    def test_get_statistics(self):
        """Test getting arbitrage statistics."""
        self.service.opportunities_found = 10
        self.service.trades_executed = 5
        self.service.total_profit = 150.0
        
        stats = self.service.get_statistics()
        
        assert stats['opportunities_found'] == 10
        assert stats['trades_executed'] == 5
        assert stats['total_profit_usd'] == 150.0
        assert stats['average_profit_per_trade'] == 30.0
        assert stats['success_rate'] == 50.0
    
    def test_update_settings(self):
        """Test updating arbitrage settings."""
        self.service.update_settings(
            min_profit_percentage=0.8,
            max_position_size=2000.0
        )
        
        assert self.service.min_profit_percentage == 0.8
        assert self.service.max_position_size == 2000.0
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        # Mock scan_opportunities to avoid infinite loop
        with patch.object(self.service, 'scan_opportunities', return_value=[]), \
             patch('asyncio.sleep'):
            
            # Start monitoring in background
            task = asyncio.create_task(
                self.service.start_monitoring(['BTC/USDT'], 0.1)
            )
            
            # Let it run briefly
            await asyncio.sleep(0.01)
            
            # Stop monitoring
            self.service.stop_monitoring()
            
            # Wait for task to complete
            await task
            
            assert not self.service.is_running