# backend/app/services/kucoin_futures_client.py
"""
KuCoin Futures Client Service

Professional exchange client for KuCoin Futures trading.
Handles market data, order execution, account management, and position monitoring.
"""
import asyncio
import time 
import json
import logging
from typing import Optional, Dict, Any, List, Union

import ccxt.async_support as ccxt 
from app.core.config import settings
import aiohttp 
import pandas as pd

logger = logging.getLogger(__name__)

# Custom Exceptions
class KucoinClientException(Exception):
    """Base exception for KucoinFuturesClient errors."""
    pass

class KucoinAuthError(KucoinClientException):
    """Raised for authentication errors."""
    pass

class KucoinRequestError(KucoinClientException):
    """Raised for general request errors from KuCoin."""
    pass

class KucoinFuturesClient:
    """
    Professional KuCoin Futures trading client.
    
    Provides async methods for:
    - Market data retrieval
    - Order execution and management
    - Account and position monitoring
    - Exchange connectivity health checks
    """
    
    def __init__(self, external_session: Optional[aiohttp.ClientSession] = None):
        self.exchange_id = 'kucoinfutures'
        self.exchange_config = {
            'apiKey': settings.KUCOIN_API_KEY,
            'secret': settings.KUCOIN_API_SECRET,
            'password': settings.KUCOIN_API_PASSPHRASE, 
            'options': {
                'defaultType': 'future',
            },
        }
        if external_session:
            self.exchange_config['aiohttp_session'] = external_session
            self.manage_session_externally = True 
        else:
            self.manage_session_externally = False

        try:
            self.exchange = getattr(ccxt, self.exchange_id)(self.exchange_config)
            self.markets_loaded = False 
            if not all([settings.KUCOIN_API_KEY, settings.KUCOIN_API_SECRET, settings.KUCOIN_API_PASSPHRASE]):
                logger.warning(f"KuCoin Futures client initialized with INCOMPLETE API credentials. Authenticated calls will fail.")
        except Exception as e:
            logger.error(f"Failed to initialize CCXT KuCoin Futures client: {e}")
            raise KucoinClientException(f"Failed to initialize CCXT KuCoin Futures client: {e}")

    async def _ensure_markets_loaded(self):
        """Ensure exchange markets are loaded before making requests."""
        if not self.markets_loaded:
            if not hasattr(self.exchange, 'markets') or not self.exchange.markets: 
                try:
                    logger.info(f"Loading markets for {self.exchange_id}...")
                    await self.exchange.load_markets(reload=True) 
                    self.markets_loaded = True
                    logger.info(f"Markets loaded successfully.")
                except Exception as e:
                    await self._handle_ccxt_exception(e, "loading markets")
                    self.markets_loaded = False 
            else: 
                self.markets_loaded = True

    async def close_session(self):
        """Close the exchange session if managed internally."""
        if not self.manage_session_externally and hasattr(self.exchange, 'close') and callable(self.exchange.close):
            try:
                await self.exchange.close()
                logger.info("CCXT exchange session (internally managed) closed.")
            except Exception as e:
                logger.error(f"Exception while closing CCXT session: {e}")
    
    async def _handle_ccxt_exception(self, e: Exception, context: str, symbol: Optional[str] = None) -> None:
        """Handle and re-raise CCXT exceptions with proper classification."""
        log_message = f"CCXT Error during {context}"
        if symbol: 
            log_message += f" for symbol {symbol}"
        log_message += f": {type(e).__name__} - {str(e)}"
        logger.error(log_message) 
        
        if isinstance(e, ccxt.AuthenticationError):
            raise KucoinAuthError(f"Authentication failed for {context}: {e}") from e
        elif isinstance(e, ccxt.NotSupported): 
            raise KucoinRequestError(f"Operation not supported by {self.exchange_id} for {context}: {e}") from e
        elif isinstance(e, (ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout)):
            raise KucoinRequestError(f"Network/Connectivity error for {context}: {e}") from e
        elif isinstance(e, ccxt.BadSymbol):
            raise KucoinRequestError(f"Invalid symbol for {context}: {symbol}. Error: {e}") from e
        elif isinstance(e, ccxt.InsufficientFunds): 
            raise KucoinRequestError(f"Insufficient funds for {context}: {e}") from e
        elif isinstance(e, ccxt.InvalidOrder) and "No open positions to close" in str(e):
            raise KucoinRequestError(f"No open position to close for {context}: {e}") from e
        elif isinstance(e, ccxt.ExchangeError): 
            if "marginMode" in str(e).lower() and ("isolated" in str(e).lower() or "cross" in str(e).lower()):
                logger.error(f"Potential margin mode conflict. KuCoin Msg: {str(e)}")
            raise KucoinRequestError(f"Exchange error for {context}: {e}") from e
        else: 
            raise KucoinClientException(f"Unexpected CCXT error for {context}: {e}") from e

    async def get_market_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market information for a specific symbol."""
        await self._ensure_markets_loaded()
        try:
            market = self.exchange.market(symbol) 
            if market:
                return market
            else:
                logger.error(f"Market info not found for symbol {symbol} after loading markets.")
                return None
        except ccxt.BadSymbol: 
            logger.error(f"Market info not found for symbol {symbol} (BadSymbol exception from CCXT).")
            return None
        except Exception as e:
            await self._handle_ccxt_exception(e, f"fetching market info for {symbol}", symbol=symbol)
            return None

    async def get_server_time(self) -> Optional[Dict[str, Any]]:
        """Get KuCoin server time with local time comparison."""
        context = "fetching KuCoin server time"
        try:
            server_timestamp_ms = await self.exchange.fetch_time()
            local_time_ms = int(time.time() * 1000)
            return {
                "kucoin_server_time_ms": server_timestamp_ms,
                "local_server_time_ms": local_time_ms,
                "time_difference_ms": local_time_ms - server_timestamp_ms
            }
        except Exception as e:
            try: 
                await self._handle_ccxt_exception(e, context)
            except KucoinClientException: 
                pass
            return None

    async def get_active_contracts(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch all active, tradable USDT-margined perpetual futures contracts from KuCoin.
        """
        context = "fetching active KuCoin contracts"
        try:
            # Using fetch_markets() ensures we get the latest data directly from the exchange API
            all_markets = await self.exchange.fetch_markets()
            
            if not all_markets:
                logger.error("fetch_markets returned no data.")
                return []

            active_futures = [
                market for market in all_markets
                if market.get('active', False) and                 # The market must be active
                   market.get('type') == 'swap' and               # It must be a perpetual contract (swap)
                   market.get('contract', False) and              # It must be a contract
                   market.get('quote', '').upper() == 'USDT' and  # It must be quoted in USDT
                   market.get('settle', '').upper() == 'USDT'     # It must be settled in USDT
            ]
            
            logger.info(f"Found {len(active_futures)} active USDT-margined futures contracts.")
            return active_futures
            
        except Exception as e:
            try: 
                await self._handle_ccxt_exception(e, context)
            except KucoinClientException: 
                pass
            return None

    async def get_account_overview(self, currency: Optional[str] = "USDT") -> Optional[Dict[str, Any]]:
        """Get account balance overview for specified currency."""
        context = f"fetching KuCoin account overview (currency: {currency})"
        try:
            balance_data = await self.exchange.fetch_balance() 
            return balance_data 
        except Exception as e:
            try: 
                await self._handle_ccxt_exception(e, context)
            except KucoinClientException: 
                pass
            return None

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', since: Optional[int] = None, limit: Optional[int] = None) -> Optional[List[List[Any]]]:
        """Fetch OHLCV candlestick data for a symbol."""
        context = f"fetching OHLCV for {symbol} timeframe {timeframe}"
        try:
            await self._ensure_markets_loaded()
            if not self.exchange.has['fetchOHLCV']:
                raise KucoinClientException(f"Exchange {self.exchange_id} does not support fetchOHLCV.")
            
            ohlcv_data = await self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            return ohlcv_data
        except Exception as e:
            try: 
                await self._handle_ccxt_exception(e, context, symbol=symbol)
            except KucoinClientException: 
                pass
            return None

    async def fetch_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch ticker data for a symbol."""
        context = f"fetching ticker for {symbol}"
        try:
            await self._ensure_markets_loaded()
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            try: 
                await self._handle_ccxt_exception(e, context, symbol=symbol)
            except KucoinClientException: 
                pass
            return None

    async def get_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol."""
        try:
            ticker = await self.fetch_ticker(symbol)
            if ticker:
                # Prefer mark price, fall back to last price
                return ticker.get('mark') or ticker.get('last')
            return None
        except Exception as e:
            logger.error(f"Could not fetch market price for {symbol}: {e}")
            return None

    async def create_futures_order(
        self, 
        symbol: str, 
        order_type: str, 
        side: str, 
        amount: float,
        price: Optional[float] = None,
        leverage: Optional[int] = None, 
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        margin_mode: Optional[str] = 'isolated', 
        params: Optional[Dict[str, Any]] = None 
    ) -> Optional[Dict[str, Any]]:
        """
        Create a futures order with optional stop loss and take profit.
        
        Handles proper trigger direction setup for long/short positions.
        """
        context = f"creating {side} {order_type} order for {amount} of {symbol}"

        if order_type.lower() == 'limit' and price is None:
            logger.error(f"Price required for limit orders for {symbol}.")
            raise KucoinClientException("Price is required for limit orders.")

        if not all([settings.KUCOIN_API_KEY, settings.KUCOIN_API_SECRET, settings.KUCOIN_API_PASSPHRASE]):
            logger.error("API credentials not configured.")
            raise KucoinAuthError("API credentials not configured.")

        await self._ensure_markets_loaded()
        order_execution_params = params.copy() if params else {}

        if margin_mode:
            order_execution_params['marginMode'] = margin_mode.lower()
        if leverage is not None:
            order_execution_params['leverage'] = leverage

        # Get market price for reference
        mark_price = await self.get_market_price(symbol)
        if mark_price is None:
            raise KucoinClientException("Mark price could not be determined.")

        logger.debug(f"Mark Price for {symbol} = {mark_price}")
        logger.debug(f"SL = {stop_loss_price}, TP = {take_profit_price}, Side = {side}")

        # Set up stop loss and take profit with correct trigger directions
        # For SHORT positions, the logic is inverted compared to LONG positions
        if side.lower() == 'sell':  # SHORT position
            if stop_loss_price is not None:
                order_execution_params['takeProfit'] = {
                    'triggerPrice': self.exchange.price_to_precision(symbol, stop_loss_price),
                    'triggerDirection': 1,  # Stop loss triggers when price goes up
                    'type': 'market'
                }
            if take_profit_price is not None:
                order_execution_params['stopLoss'] = {
                    'triggerPrice': self.exchange.price_to_precision(symbol, take_profit_price),
                    'triggerDirection': 2,  # Take profit triggers when price goes down
                    'type': 'market'
                }
        else:  # LONG position
            if take_profit_price is not None:
                order_execution_params['takeProfit'] = {
                    'triggerPrice': self.exchange.price_to_precision(symbol, take_profit_price),
                    'triggerDirection': 1,  # Take profit triggers when price goes up
                    'type': 'market'
                }
            if stop_loss_price is not None:
                order_execution_params['stopLoss'] = {
                    'triggerPrice': self.exchange.price_to_precision(symbol, stop_loss_price),
                    'triggerDirection': 2,  # Stop loss triggers when price goes down
                    'type': 'market'
                }

        try:
            precise_amount = self.exchange.amount_to_precision(symbol, amount)
            precise_price = self.exchange.price_to_precision(symbol, price) if price is not None else None

            logger.info(f"Creating {side} {order_type} for {symbol}, amount: {precise_amount}, price: {precise_price}, params: {order_execution_params}")

            order = await self.exchange.create_order(
                symbol=symbol,
                type=order_type.lower(),
                side=side.lower(),
                amount=float(precise_amount),
                price=float(precise_price) if precise_price is not None else None,
                params=order_execution_params
            )

            logger.info(f"Order successful for {symbol}. ID: {order.get('id') if order else 'N/A'}")
            return order

        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None

    async def fetch_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch order details by ID."""
        context = f"fetching order ID {order_id} for symbol {symbol}"
        await self._ensure_markets_loaded()
        try:
            logger.info(f"Fetching order {order_id} for {symbol}")
            order = await self.exchange.fetch_order(id=order_id, symbol=symbol)
            return order
        except ccxt.OrderNotFound as e: 
            logger.info(f"Order {order_id} for {symbol} not found on exchange.")
            return {"status": "not_found", "id": order_id, "message": str(e)} 
        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None

    async def fetch_open_positions(self, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Fetch open positions for symbol or all symbols."""
        context = "fetching open positions"
        if symbol: 
            context += f" for symbol {symbol}"
        await self._ensure_markets_loaded()
        try:
            logger.info(f"Fetching open positions. Symbol: {symbol if symbol else 'All'}")
            symbols_param = [symbol] if symbol else None
            all_positions = await self.exchange.fetch_positions(symbols=symbols_param) 
            open_positions = []
            if all_positions: 
                for p in all_positions:
                    current_qty_str = p.get('info', {}).get('currentQty')
                    current_qty = 0.0
                    if current_qty_str is not None:
                        try: 
                            current_qty = float(current_qty_str)
                        except ValueError: 
                            pass
                    contracts_val = p.get('contracts')
                    contracts = 0.0
                    if contracts_val is not None:
                        try: 
                            contracts = float(contracts_val)
                        except ValueError: 
                            pass
                    is_open_kucoin = p.get('info', {}).get('isOpen', False)
                    if is_open_kucoin or current_qty != 0 or contracts != 0:
                        open_positions.append(p)
            logger.info(f"Found {len(open_positions)} actively open position(s).")
            return open_positions
        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None

    async def cancel_order_by_id(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Cancel an order by ID."""
        context = f"cancelling order ID {order_id}, symbol {symbol}"
        await self._ensure_markets_loaded()
        try:
            logger.info(f"Cancelling order ID: {order_id}, Symbol: {symbol}")
            response = await self.exchange.cancel_order(id=order_id, symbol=symbol)
            return response
        except ccxt.OrderNotFound:
            logger.info(f"Order {order_id} for {symbol} not found for cancellation (already closed/cancelled).")
            return {"info": f"Order {order_id} not found or already processed."} 
        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None
            
    async def close_market_position(
        self, 
        symbol: str, 
        position_amount: float, 
        current_position_side: str 
    ) -> Optional[Dict[str, Any]]:
        """Close an existing market position with a reduce-only market order."""
        context = f"closing {current_position_side} position for {position_amount} of {symbol} with market order"
        await self._ensure_markets_loaded()
        if position_amount <= 1e-9: 
            logger.error(f"Position amount to close must be positive for {symbol}. Got: {position_amount}")
            raise KucoinClientException("Position amount to close must be positive and non-zero.")
        closing_order_side = 'sell' if current_position_side.lower() == 'long' else 'buy'
        close_params = {'reduceOnly': True} 
        try:
            precise_amount_to_close_str = self.exchange.amount_to_precision(symbol, position_amount)
            precise_amount_to_close = float(precise_amount_to_close_str)
            if precise_amount_to_close <= 1e-9: 
                logger.error(f"Precise position amount to close is zero or too small for {symbol}. Original: {position_amount}, Precise: {precise_amount_to_close}")
                raise KucoinClientException("Precise position amount to close is zero or too small.")
            logger.info(f"Attempting to place {closing_order_side} market order to close {symbol}, Precise Amount: {precise_amount_to_close}, Params: {close_params}")
            order = await self.exchange.create_order(symbol=symbol, type='market', side=closing_order_side, amount=precise_amount_to_close, params=close_params)
            logger.info(f"Close order placed successfully for {symbol}. Order ID: {order.get('id') if order else 'N/A'}")
            return order
        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None

    async def fetch_my_recent_trades(self, symbol: str, since: Optional[int] = None, limit: Optional[int] = 5) -> Optional[List[Dict[str, Any]]]:
        """Fetch recent trades for the account."""
        context = f"fetching my recent trades for {symbol}"
        await self._ensure_markets_loaded()
        try:
            logger.info(f"Fetching recent trades for {symbol}. Since: {since}, Limit: {limit}")
            my_trades = await self.exchange.fetch_my_trades(symbol=symbol, since=since, limit=limit)
            return my_trades
        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None
