# app/exchanges/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
import asyncio


class OrderType(Enum):
    """Order types supported across exchanges."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderSide(Enum):
    """Order sides supported across exchanges."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order statuses supported across exchanges."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class ExchangeError(Exception):
    """Base exception for exchange-related errors."""
    pass


class ExchangeConnectionError(ExchangeError):
    """Raised when exchange connection fails."""
    pass


class ExchangeAuthError(ExchangeError):
    """Raised when exchange authentication fails."""
    pass


class ExchangeInsufficientFundsError(ExchangeError):
    """Raised when insufficient funds for trade."""
    pass


class BaseExchange(ABC):
    """
    Abstract base class for exchange implementations.
    
    This provides a unified interface for all exchange integrations,
    ensuring consistent behavior across different trading platforms.
    """
    
    def __init__(self, api_key: str, api_secret: str, **kwargs):
        self.api_key = api_key
        self.api_secret = api_secret
        self.is_connected = False
        self.exchange_name = self.__class__.__name__.replace('Exchange', '').lower()
        
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the exchange.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange."""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dict containing ticker data with standardized keys:
            - symbol: str
            - bid: float
            - ask: float
            - last: float
            - volume: float
            - timestamp: int (Unix timestamp)
        """
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get order book for a symbol.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of orders to fetch on each side
            
        Returns:
            Dict containing:
            - bids: List[List[float, float]] (price, amount)
            - asks: List[List[float, float]] (price, amount)
            - timestamp: int
        """
        pass
    
    @abstractmethod
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place a trading order.
        
        Args:
            order_data: Dict containing:
            - symbol: str
            - side: OrderSide
            - type: OrderType  
            - amount: float
            - price: float (optional for market orders)
            - stop_price: float (optional for stop orders)
            
        Returns:
            Dict containing:
            - id: str (order ID)
            - symbol: str
            - side: str
            - type: str
            - amount: float
            - price: float
            - status: OrderStatus
            - timestamp: int
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancel an open order.
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading pair symbol
            
        Returns:
            Dict containing cancellation status
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Get status of a specific order.
        
        Args:
            order_id: Order ID to check
            symbol: Trading pair symbol
            
        Returns:
            Dict containing order details and current status
        """
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance.
        
        Returns:
            Dict containing:
            - free: Dict[str, float] (available balances by currency)
            - used: Dict[str, float] (locked balances by currency)
            - total: Dict[str, float] (total balances by currency)
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get open positions (for futures/margin trading).
        
        Returns:
            List of position dicts containing:
            - symbol: str
            - side: str ('long' or 'short')
            - size: float
            - entry_price: float
            - mark_price: float
            - unrealized_pnl: float
            - percentage: float
        """
        pass
    
    @abstractmethod
    async def get_trade_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get trade history for a symbol.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of trades to fetch
            
        Returns:
            List of trade dicts containing:
            - id: str
            - symbol: str
            - side: str
            - amount: float
            - price: float
            - fee: float
            - timestamp: int
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check exchange connectivity and status.
        
        Returns:
            Dict containing health status information
        """
        try:
            # Try to fetch a common trading pair ticker as health check
            ticker = await self.get_ticker("BTC/USDT")
            return {
                "status": "healthy",
                "exchange": self.exchange_name,
                "connected": self.is_connected,
                "last_check": ticker.get("timestamp"),
                "latency_ms": None  # Can be implemented by subclasses
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "exchange": self.exchange_name,
                "connected": False,
                "error": str(e),
                "last_check": None
            }
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for the specific exchange.
        Override in subclasses if needed.
        
        Args:
            symbol: Symbol in standard format (e.g., 'BTC/USDT')
            
        Returns:
            Symbol in exchange-specific format
        """
        return symbol
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()