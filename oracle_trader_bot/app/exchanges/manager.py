# app/exchanges/manager.py
import asyncio
import logging
from typing import Dict, Any, List, Optional, Type
from .base import BaseExchange, ExchangeError, ExchangeConnectionError
from .binance import BinanceExchange
from .coinbase import CoinbaseExchange
from .kraken import KrakenExchange


logger = logging.getLogger(__name__)


class ExchangeManager:
    """
    Manages multiple exchange connections and provides unified access.
    
    Features:
    - Multi-exchange coordination
    - Automatic failover
    - Load balancing
    - Health monitoring
    """
    
    def __init__(self):
        self.exchanges: Dict[str, BaseExchange] = {}
        self.exchange_configs: Dict[str, Dict[str, Any]] = {}
        self.primary_exchange: Optional[str] = None
        self.failover_enabled = True
        
    def register_exchange(self, name: str, exchange_class: Type[BaseExchange], config: Dict[str, Any], is_primary: bool = False):
        """
        Register an exchange with the manager.
        
        Args:
            name: Exchange identifier
            exchange_class: Exchange implementation class
            config: Exchange configuration (API keys, etc.)
            is_primary: Whether this is the primary exchange
        """
        self.exchange_configs[name] = {
            'class': exchange_class,
            'config': config
        }
        
        if is_primary:
            self.primary_exchange = name
            
        logger.info(f"Registered exchange: {name} (primary: {is_primary})")
    
    async def connect_all(self) -> Dict[str, bool]:
        """
        Connect to all registered exchanges.
        
        Returns:
            Dict mapping exchange names to connection success status
        """
        results = {}
        
        for name, config in self.exchange_configs.items():
            try:
                exchange = config['class'](**config['config'])
                success = await exchange.connect()
                
                if success:
                    self.exchanges[name] = exchange
                    results[name] = True
                    logger.info(f"Connected to {name}")
                else:
                    results[name] = False
                    logger.error(f"Failed to connect to {name}")
                    
            except Exception as e:
                results[name] = False
                logger.error(f"Error connecting to {name}: {str(e)}")
        
        return results
    
    async def disconnect_all(self):
        """Disconnect from all exchanges."""
        for name, exchange in self.exchanges.items():
            try:
                await exchange.disconnect()
                logger.info(f"Disconnected from {name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {name}: {str(e)}")
        
        self.exchanges.clear()
    
    async def get_ticker(self, symbol: str, exchange_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get ticker from specified exchange or primary exchange with failover.
        
        Args:
            symbol: Trading pair symbol
            exchange_name: Specific exchange to use (optional)
            
        Returns:
            Ticker data with exchange name added
        """
        if exchange_name:
            # Use specific exchange
            if exchange_name not in self.exchanges:
                raise ExchangeError(f"Exchange {exchange_name} not available")
            
            exchange = self.exchanges[exchange_name]
            ticker = await exchange.get_ticker(symbol)
            ticker['exchange'] = exchange_name
            return ticker
        
        # Try primary exchange first, then failover
        exchanges_to_try = []
        if self.primary_exchange and self.primary_exchange in self.exchanges:
            exchanges_to_try.append(self.primary_exchange)
        
        # Add other exchanges for failover
        for name in self.exchanges:
            if name != self.primary_exchange:
                exchanges_to_try.append(name)
        
        last_error = None
        for exchange_name in exchanges_to_try:
            try:
                exchange = self.exchanges[exchange_name]
                ticker = await exchange.get_ticker(symbol)
                ticker['exchange'] = exchange_name
                return ticker
            except Exception as e:
                last_error = e
                logger.warning(f"Failed to get ticker from {exchange_name}: {str(e)}")
                continue
        
        raise ExchangeError(f"Failed to get ticker from all exchanges. Last error: {str(last_error)}")
    
    async def place_order(self, order_data: Dict[str, Any], exchange_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Place order on specified exchange or primary exchange.
        
        Args:
            order_data: Order details
            exchange_name: Specific exchange to use (optional)
            
        Returns:
            Order result with exchange name added
        """
        target_exchange = exchange_name or self.primary_exchange
        
        if not target_exchange or target_exchange not in self.exchanges:
            raise ExchangeError(f"Exchange {target_exchange} not available")
        
        exchange = self.exchanges[target_exchange]
        result = await exchange.place_order(order_data)
        result['exchange'] = target_exchange
        
        logger.info(f"Order placed on {target_exchange}: {result['id']}")
        return result
    
    async def get_balance(self, exchange_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get balance from specific exchange or all exchanges.
        
        Args:
            exchange_name: Specific exchange (optional, if None returns all)
            
        Returns:
            Balance data with exchange names
        """
        if exchange_name:
            if exchange_name not in self.exchanges:
                raise ExchangeError(f"Exchange {exchange_name} not available")
            
            exchange = self.exchanges[exchange_name]
            balance = await exchange.get_balance()
            return {exchange_name: balance}
        
        # Get balances from all exchanges
        balances = {}
        for name, exchange in self.exchanges.items():
            try:
                balance = await exchange.get_balance()
                balances[name] = balance
            except Exception as e:
                logger.error(f"Failed to get balance from {name}: {str(e)}")
                balances[name] = {"error": str(e)}
        
        return balances
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all exchanges.
        
        Returns:
            Dict mapping exchange names to health status
        """
        health_results = {}
        
        for name, exchange in self.exchanges.items():
            try:
                health = await exchange.health_check()
                health_results[name] = health
            except Exception as e:
                health_results[name] = {
                    "status": "unhealthy",
                    "exchange": name,
                    "connected": False,
                    "error": str(e)
                }
        
        return health_results
    
    async def find_arbitrage_opportunities(self, symbol: str, min_profit_percentage: float = 0.1) -> List[Dict[str, Any]]:
        """
        Find arbitrage opportunities across exchanges.
        
        Args:
            symbol: Trading pair to check
            min_profit_percentage: Minimum profit percentage to consider
            
        Returns:
            List of arbitrage opportunities
        """
        if len(self.exchanges) < 2:
            return []
        
        # Get tickers from all exchanges
        tickers = {}
        for name, exchange in self.exchanges.items():
            try:
                ticker = await exchange.get_ticker(symbol)
                tickers[name] = ticker
            except Exception as e:
                logger.warning(f"Failed to get ticker from {name}: {str(e)}")
                continue
        
        if len(tickers) < 2:
            return []
        
        # Find arbitrage opportunities
        opportunities = []
        exchange_names = list(tickers.keys())
        
        for i in range(len(exchange_names)):
            for j in range(i + 1, len(exchange_names)):
                exchange_a = exchange_names[i]
                exchange_b = exchange_names[j]
                
                ticker_a = tickers[exchange_a]
                ticker_b = tickers[exchange_b]
                
                # Check if we can buy on A and sell on B
                if ticker_a['ask'] and ticker_b['bid']:
                    profit_percentage = ((ticker_b['bid'] - ticker_a['ask']) / ticker_a['ask']) * 100
                    
                    if profit_percentage >= min_profit_percentage:
                        opportunities.append({
                            "symbol": symbol,
                            "buy_exchange": exchange_a,
                            "sell_exchange": exchange_b,
                            "buy_price": ticker_a['ask'],
                            "sell_price": ticker_b['bid'],
                            "profit_percentage": profit_percentage,
                            "timestamp": max(ticker_a.get('timestamp', 0), ticker_b.get('timestamp', 0))
                        })
                
                # Check if we can buy on B and sell on A
                if ticker_b['ask'] and ticker_a['bid']:
                    profit_percentage = ((ticker_a['bid'] - ticker_b['ask']) / ticker_b['ask']) * 100
                    
                    if profit_percentage >= min_profit_percentage:
                        opportunities.append({
                            "symbol": symbol,
                            "buy_exchange": exchange_b,
                            "sell_exchange": exchange_a,
                            "buy_price": ticker_b['ask'],
                            "sell_price": ticker_a['bid'],
                            "profit_percentage": profit_percentage,
                            "timestamp": max(ticker_a.get('timestamp', 0), ticker_b.get('timestamp', 0))
                        })
        
        # Sort by profit percentage
        opportunities.sort(key=lambda x: x['profit_percentage'], reverse=True)
        return opportunities
    
    def get_available_exchanges(self) -> List[str]:
        """Get list of connected exchanges."""
        return list(self.exchanges.keys())
    
    def is_exchange_available(self, exchange_name: str) -> bool:
        """Check if specific exchange is available."""
        return exchange_name in self.exchanges and self.exchanges[exchange_name].is_connected
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect_all()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect_all()