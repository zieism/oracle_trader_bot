# app/exchanges/kraken.py
import time
from typing import Dict, Any, List, Optional
import ccxt.async_support as ccxt
from .base import (
    BaseExchange, OrderType, OrderSide, OrderStatus,
    ExchangeError, ExchangeConnectionError, ExchangeAuthError, ExchangeInsufficientFundsError
)


class KrakenExchange(BaseExchange):
    """
    Kraken exchange implementation using CCXT.
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False, **kwargs):
        super().__init__(api_key, api_secret, **kwargs)
        self.testnet = testnet
        self.exchange = None
        
    async def connect(self) -> bool:
        """Establish connection to Kraken."""
        try:
            self.exchange = ccxt.kraken({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'sandbox': self.testnet
            })
            
            # Test connection by fetching markets
            await self.exchange.load_markets()
            self.is_connected = True
            return True
            
        except Exception as e:
            self.is_connected = False
            raise ExchangeConnectionError(f"Failed to connect to Kraken: {str(e)}")
    
    async def disconnect(self) -> None:
        """Disconnect from Kraken."""
        if self.exchange:
            await self.exchange.close()
        self.is_connected = False
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker information for a symbol."""
        try:
            normalized_symbol = self.normalize_symbol(symbol)
            ticker = await self.exchange.fetch_ticker(normalized_symbol)
            
            return {
                "symbol": symbol,
                "bid": float(ticker['bid']) if ticker['bid'] else None,
                "ask": float(ticker['ask']) if ticker['ask'] else None,
                "last": float(ticker['last']) if ticker['last'] else None,
                "volume": float(ticker['baseVolume']) if ticker['baseVolume'] else None,
                "timestamp": int(ticker['timestamp']) if ticker['timestamp'] else int(time.time() * 1000)
            }
        except Exception as e:
            raise ExchangeError(f"Failed to get ticker for {symbol}: {str(e)}")
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get order book for a symbol."""
        try:
            normalized_symbol = self.normalize_symbol(symbol)
            orderbook = await self.exchange.fetch_order_book(normalized_symbol, limit)
            
            return {
                "bids": [[float(price), float(amount)] for price, amount in orderbook['bids']],
                "asks": [[float(price), float(amount)] for price, amount in orderbook['asks']],
                "timestamp": int(orderbook['timestamp']) if orderbook['timestamp'] else int(time.time() * 1000)
            }
        except Exception as e:
            raise ExchangeError(f"Failed to get orderbook for {symbol}: {str(e)}")
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place a trading order."""
        try:
            symbol = self.normalize_symbol(order_data['symbol'])
            side = order_data['side'].value if isinstance(order_data['side'], OrderSide) else order_data['side']
            order_type = order_data['type'].value if isinstance(order_data['type'], OrderType) else order_data['type']
            amount = float(order_data['amount'])
            price = float(order_data.get('price', 0))
            
            # Convert our order types to CCXT format
            if order_type == OrderType.MARKET.value:
                order = await self.exchange.create_market_order(symbol, side, amount)
            elif order_type == OrderType.LIMIT.value:
                order = await self.exchange.create_limit_order(symbol, side, amount, price)
            else:
                raise ExchangeError(f"Unsupported order type: {order_type}")
            
            return {
                "id": str(order['id']),
                "symbol": order_data['symbol'],
                "side": side,
                "type": order_type,
                "amount": amount,
                "price": price,
                "status": self._convert_order_status(order.get('status', 'open')),
                "timestamp": int(order.get('timestamp', time.time() * 1000))
            }
            
        except ccxt.InsufficientFunds as e:
            raise ExchangeInsufficientFundsError(f"Insufficient funds: {str(e)}")
        except ccxt.AuthenticationError as e:
            raise ExchangeAuthError(f"Authentication failed: {str(e)}")
        except Exception as e:
            raise ExchangeError(f"Failed to place order: {str(e)}")
    
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an open order."""
        try:
            normalized_symbol = self.normalize_symbol(symbol)
            result = await self.exchange.cancel_order(order_id, normalized_symbol)
            
            return {
                "id": str(result['id']),
                "symbol": symbol,
                "status": "cancelled",
                "timestamp": int(time.time() * 1000)
            }
        except Exception as e:
            raise ExchangeError(f"Failed to cancel order {order_id}: {str(e)}")
    
    async def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get status of a specific order."""
        try:
            normalized_symbol = self.normalize_symbol(symbol)
            order = await self.exchange.fetch_order(order_id, normalized_symbol)
            
            return {
                "id": str(order['id']),
                "symbol": symbol,
                "side": order['side'],
                "type": order['type'],
                "amount": float(order['amount']),
                "price": float(order['price']) if order['price'] else None,
                "filled": float(order['filled']) if order['filled'] else 0,
                "remaining": float(order['remaining']) if order['remaining'] else 0,
                "status": self._convert_order_status(order['status']),
                "timestamp": int(order['timestamp']) if order['timestamp'] else None
            }
        except Exception as e:
            raise ExchangeError(f"Failed to get order status for {order_id}: {str(e)}")
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance."""
        try:
            balance = await self.exchange.fetch_balance()
            
            return {
                "free": {k: float(v) for k, v in balance['free'].items() if v > 0},
                "used": {k: float(v) for k, v in balance['used'].items() if v > 0},
                "total": {k: float(v) for k, v in balance['total'].items() if v > 0}
            }
        except Exception as e:
            raise ExchangeError(f"Failed to get balance: {str(e)}")
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions (Kraken spot doesn't support positions, return empty)."""
        return []
    
    async def get_trade_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history for a symbol."""
        try:
            normalized_symbol = self.normalize_symbol(symbol)
            trades = await self.exchange.fetch_my_trades(normalized_symbol, limit=limit)
            
            result = []
            for trade in trades:
                result.append({
                    "id": str(trade['id']),
                    "symbol": symbol,
                    "side": trade['side'],
                    "amount": float(trade['amount']),
                    "price": float(trade['price']),
                    "fee": float(trade['fee']['cost']) if trade['fee'] else 0,
                    "timestamp": int(trade['timestamp']) if trade['timestamp'] else None
                })
            
            return result
        except Exception as e:
            raise ExchangeError(f"Failed to get trade history for {symbol}: {str(e)}")
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for Kraken.
        Kraken uses different symbol naming conventions.
        """
        # Kraken symbol mapping for common pairs
        symbol_mapping = {
            'BTC/USDT': 'BTC/USDT',
            'ETH/USDT': 'ETH/USDT',
            'BTC/USD': 'XXBT/ZUSD',
            'ETH/USD': 'XETH/ZUSD'
        }
        
        return symbol_mapping.get(symbol, symbol)
    
    def _convert_order_status(self, ccxt_status: str) -> str:
        """Convert CCXT order status to our standard format."""
        status_mapping = {
            'open': OrderStatus.OPEN.value,
            'closed': OrderStatus.FILLED.value,
            'canceled': OrderStatus.CANCELLED.value,
            'cancelled': OrderStatus.CANCELLED.value,
            'rejected': OrderStatus.REJECTED.value,
            'pending': OrderStatus.PENDING.value
        }
        return status_mapping.get(ccxt_status.lower(), ccxt_status.lower())