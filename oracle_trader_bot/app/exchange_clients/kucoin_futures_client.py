# app/exchange_clients/kucoin_futures_client.py
import asyncio
import time 
import json
from typing import Optional, Dict, Any, List, Union

import ccxt.async_support as ccxt 
from app.core.config import settings
import aiohttp 
import pandas as pd

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
                print(f"WARNING ({self.__class__.__name__}): CCXT client for KuCoin Futures initialized with INCOMPLETE API credentials from settings. Authenticated calls will fail.")
        except Exception as e:
            print(f"ERROR ({self.__class__.__name__}): Failed to initialize CCXT KuCoin Futures client: {e}")
            raise KucoinClientException(f"Failed to initialize CCXT KuCoin Futures client: {e}")

    async def _ensure_markets_loaded(self):
        if not self.markets_loaded:
            if not hasattr(self.exchange, 'markets') or not self.exchange.markets: 
                try:
                    print(f"INFO ({self.__class__.__name__}): Loading markets for {self.exchange_id}...")
                    await self.exchange.load_markets(reload=True) 
                    self.markets_loaded = True
                    print(f"INFO ({self.__class__.__name__}): Markets loaded successfully.")
                except Exception as e:
                    await self._handle_ccxt_exception(e, "loading markets")
                    self.markets_loaded = False 
            else: 
                self.markets_loaded = True

    async def close_session(self):
        if not self.manage_session_externally and hasattr(self.exchange, 'close') and callable(self.exchange.close):
            try:
                await self.exchange.close()
                print("INFO: CCXT exchange session (internally managed by client) closed.")
            except Exception as e:
                print(f"ERROR: Exception while closing CCXT session: {e}")
    
    async def _handle_ccxt_exception(self, e: Exception, context: str, symbol: Optional[str] = None) -> None:
        log_message = f"CCXT Error during {context}"
        if symbol: log_message += f" for symbol {symbol}"
        log_message += f": {type(e).__name__} - {str(e)}"
        print(f"ERROR ({self.__class__.__name__}): {log_message}") 
        
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
                print(f"ERROR ({self.__class__.__name__}): Potential margin mode conflict. KuCoin Msg: {str(e)}")
            raise KucoinRequestError(f"Exchange error for {context}: {e}") from e
        else: 
            raise KucoinClientException(f"Unexpected CCXT error for {context}: {e}") from e

    async def get_market_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        await self._ensure_markets_loaded()
        try:
            market = self.exchange.market(symbol) 
            if market:
                return market
            else:
                print(f"ERROR ({self.__class__.__name__}): Market info not found for symbol {symbol} after loading markets.")
                return None
        except ccxt.BadSymbol: 
            print(f"ERROR ({self.__class__.__name__}): Market info not found for symbol {symbol} (BadSymbol exception from CCXT).")
            return None
        except Exception as e:
            await self._handle_ccxt_exception(e, f"fetching market info for {symbol}", symbol=symbol)
            return None

    async def get_server_time(self) -> Optional[Dict[str, Any]]:
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
            try: await self._handle_ccxt_exception(e, context)
            except KucoinClientException: pass
            return None

    # --- THIS IS THE ONLY MODIFIED FUNCTION ---
    async def get_active_contracts(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches all active, tradable USDT-margined perpetual futures contracts from KuCoin.
        """
        context = "fetching active KuCoin contracts"
        try:
            # Using fetch_markets() ensures we get the latest data directly from the exchange API
            all_markets = await self.exchange.fetch_markets()
            
            if not all_markets:
                print(f"ERROR ({self.__class__.__name__}): fetch_markets returned no data.")
                return []

            active_futures = [
                market for market in all_markets
                if market.get('active', False) and                 # The market must be active
                   market.get('type') == 'swap' and                  # It must be a perpetual contract (swap)
                   market.get('contract', False) and                 # It must be a contract
                   market.get('quote', '').upper() == 'USDT' and     # It must be quoted in USDT
                   market.get('settle', '').upper() == 'USDT'        # It must be settled in USDT
            ]
            
            print(f"INFO ({self.__class__.__name__}): Found {len(active_futures)} active USDT-margined futures contracts.")
            return active_futures
            
        except Exception as e:
            try: await self._handle_ccxt_exception(e, context)
            except KucoinClientException: pass
            return None

    async def get_account_overview(self, currency: Optional[str] = "USDT") -> Optional[Dict[str, Any]]:
        context = f"fetching KuCoin account overview (currency: {currency})"
        try:
            balance_data = await self.exchange.fetch_balance() 
            return balance_data 
        except Exception as e:
            try: await self._handle_ccxt_exception(e, context)
            except KucoinClientException: pass
            return None

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', since: Optional[int] = None, limit: Optional[int] = None) -> Optional[List[List[Any]]]:
        context = f"fetching OHLCV for {symbol} timeframe {timeframe}"
        try:
            await self._ensure_markets_loaded()
            if not self.exchange.has['fetchOHLCV']:
                raise KucoinClientException(f"Exchange {self.exchange_id} does not support fetchOHLCV.")
            
            ohlcv_data = await self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            return ohlcv_data
        except Exception as e:
            try: await self._handle_ccxt_exception(e, context, symbol=symbol)
            except KucoinClientException: pass
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
    context = f"creating {side} {order_type} order for {amount} of {symbol}"
    if order_type.lower() == 'limit' and price is None:
        print(f"ERROR ({self.__class__.__name__}): Price required for limit orders for {symbol}.")
        raise KucoinClientException("Price is required for limit orders.")
    if not all([settings.KUCOIN_API_KEY, settings.KUCOIN_API_SECRET, settings.KUCOIN_API_PASSPHRASE]):
        print(f"ERROR ({self.__class__.__name__}): API credentials not configured.")
        raise KucoinAuthError("API credentials not configured.")

    await self._ensure_markets_loaded()
    order_execution_params = params.copy() if params else {}

    if margin_mode:
        order_execution_params['marginMode'] = margin_mode.lower()
    if leverage is not None:
        order_execution_params['leverage'] = leverage

    # تنظیم TP/SL با توجه به Long یا Short
    if side.lower() == "buy":  # Long
        if stop_loss_price is not None:
            order_execution_params['stopLoss'] = {
                'triggerPrice': self.exchange.price_to_precision(symbol, stop_loss_price),
                'type': 'market'
            }
        if take_profit_price is not None:
            order_execution_params['takeProfit'] = {
                'triggerPrice': self.exchange.price_to_precision(symbol, take_profit_price),
                'type': 'market'
            }
    elif side.lower() == "sell":  # Short
        if stop_loss_price is not None:
            order_execution_params['stopLoss'] = {
                'triggerPrice': self.exchange.price_to_precision(symbol, stop_loss_price),
                'type': 'market'
            }
        if take_profit_price is not None:
            order_execution_params['takeProfit'] = {
                'triggerPrice': self.exchange.price_to_precision(symbol, take_profit_price),
                'type': 'market'
            }

    try:
        precise_amount = self.exchange.amount_to_precision(symbol, amount)
        precise_price = self.exchange.price_to_precision(symbol, price) if price is not None else None
        print(f"INFO ({self.__class__.__name__}): Attempting to create {side} {order_type} order for {symbol}, "
              f"Precise Amount: {precise_amount}, Precise Price: {precise_price}, "
              f"CCXT_Params: {order_execution_params}")
        order = await self.exchange.create_order(
            symbol=symbol,
            type=order_type.lower(),
            side=side.lower(),
            amount=float(precise_amount),
            price=float(precise_price) if precise_price is not None else None,
            params=order_execution_params
        )
        print(f"INFO ({self.__class__.__name__}): Order created successfully for {symbol}. "
              f"Order ID: {order.get('id') if order else 'N/A'}")
        return order
    except Exception as e:
        print(f"ERROR ({self.__class__.__name__}): Failed to create order for {symbol}. Error: {str(e)}")
        raise KucoinRequestError(str(e))

    async def fetch_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        context = f"fetching order ID {order_id} for symbol {symbol}"
        await self._ensure_markets_loaded()
        try:
            print(f"INFO ({self.__class__.__name__}): Fetching order {order_id} for {symbol}")
            order = await self.exchange.fetch_order(id=order_id, symbol=symbol)
            return order
        except ccxt.OrderNotFound as e: 
            print(f"INFO ({self.__class__.__name__}): Order {order_id} for {symbol} not found on exchange.")
            return {"status": "not_found", "id": order_id, "message": str(e)} 
        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None

    async def fetch_open_positions(self, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        context = "fetching open positions"
        if symbol: context += f" for symbol {symbol}"
        await self._ensure_markets_loaded()
        try:
            print(f"INFO ({self.__class__.__name__}): Fetching open positions. Symbol: {symbol if symbol else 'All'}")
            symbols_param = [symbol] if symbol else None
            all_positions = await self.exchange.fetch_positions(symbols=symbols_param) 
            open_positions = []
            if all_positions: 
                for p in all_positions:
                    current_qty_str = p.get('info', {}).get('currentQty')
                    current_qty = 0.0
                    if current_qty_str is not None:
                        try: current_qty = float(current_qty_str)
                        except ValueError: pass
                    contracts_val = p.get('contracts')
                    contracts = 0.0
                    if contracts_val is not None:
                        try: contracts = float(contracts_val)
                        except ValueError: pass
                    is_open_kucoin = p.get('info', {}).get('isOpen', False)
                    if is_open_kucoin or current_qty != 0 or contracts != 0:
                        open_positions.append(p)
            print(f"INFO ({self.__class__.__name__}): Found {len(open_positions)} actively open position(s) for {symbol if symbol else 'All'}.")
            return open_positions
        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None

    async def cancel_order_by_id(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        context = f"cancelling order ID {order_id}, symbol {symbol}"
        await self._ensure_markets_loaded()
        try:
            print(f"INFO ({self.__class__.__name__}): Cancelling order ID: {order_id}, Symbol: {symbol}")
            response = await self.exchange.cancel_order(id=order_id, symbol=symbol)
            return response
        except ccxt.OrderNotFound:
            print(f"INFO ({self.__class__.__name__}): Order {order_id} for {symbol} not found for cancellation (already closed/cancelled).")
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
        context = f"closing {current_position_side} position for {position_amount} of {symbol} with market order"
        await self._ensure_markets_loaded()
        if position_amount <= 1e-9: 
            print(f"ERROR ({self.__class__.__name__}): Position amount to close must be positive for {symbol}. Got: {position_amount}")
            raise KucoinClientException("Position amount to close must be positive and non-zero.")
        closing_order_side = 'sell' if current_position_side.lower() == 'long' else 'buy'
        close_params = {'reduceOnly': True} 
        try:
            precise_amount_to_close_str = self.exchange.amount_to_precision(symbol, position_amount)
            precise_amount_to_close = float(precise_amount_to_close_str)
            if precise_amount_to_close <= 1e-9: 
                print(f"ERROR ({self.__class__.__name__}): Precise position amount to close is zero or too small for {symbol}. Original: {position_amount}, Precise: {precise_amount_to_close}")
                raise KucoinClientException("Precise position amount to close is zero or too small.")
            print(f"INFO ({self.__class__.__name__}): Attempting to place {closing_order_side} market order to close {symbol}, Precise Amount: {precise_amount_to_close}, Params: {close_params}")
            order = await self.exchange.create_order(symbol=symbol, type='market', side=closing_order_side, amount=precise_amount_to_close, params=close_params)
            print(f"INFO ({self.__class__.__name__}): Close order placed successfully for {symbol}. Order ID: {order.get('id') if order else 'N/A'}")
            return order
        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None

    async def fetch_my_recent_trades(self, symbol: str, since: Optional[int] = None, limit: Optional[int] = 5) -> Optional[List[Dict[str, Any]]]:
        context = f"fetching my recent trades for {symbol}"
        await self._ensure_markets_loaded()
        try:
            print(f"INFO ({self.__class__.__name__}): Fetching recent trades for {symbol}. Since: {since}, Limit: {limit}")
            my_trades = await self.exchange.fetch_my_trades(symbol=symbol, since=since, limit=limit)
            return my_trades
        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None

    async def fetch_open_stop_orders_for_symbol(self, symbol: str, since: Optional[int] = None, limit: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        context = f"fetching open stop orders for symbol {symbol}"
        await self._ensure_markets_loaded()
        try:
            print(f"INFO ({self.__class__.__name__}): Fetching open stop orders for {symbol}.")
            
            if hasattr(self.exchange, 'fetch_stop_orders'): # Hypothetical
                orders = await self.exchange.fetch_stop_orders(symbol=symbol, since=since, limit=limit)
            elif hasattr(self.exchange, 'privateGetStopOrders'): # CCXT private method
                market = self.exchange.market(symbol)
                if not market:
                    raise ccxt.BadSymbol(f"Market {symbol} not found for fetching stop orders.")
                kucoin_params = {'symbol': market['id']} 
                if since: kucoin_params['startAt'] = since
                response = await self.exchange.privateGetStopOrders(kucoin_params)
                orders = response.get('data', {}).get('items', []) 
            else:
                print(f"INFO ({self.__class__.__name__}): fetch_stop_orders not available, using fetch_open_orders for {symbol} and filtering.")
                all_open_orders = await self.exchange.fetch_open_orders(symbol=symbol, since=since, limit=limit)
                orders = []
                if all_open_orders:
                    for order in all_open_orders:
                        if order.get('stopPrice') is not None and order.get('status') == 'open':
                            if order.get('reduceOnly', False) or order.get('info', {}).get('reduceOnly', False):
                                orders.append(order)
                        elif order.get('info', {}).get('stop') and order.get('info', {}).get('status') == 'active':
                                orders.append(order)

            print(f"INFO ({self.__class__.__name__}): Found {len(orders)} potential open stop/conditional order(s) for {symbol}.")
            return orders
        except Exception as e:
            await self._handle_ccxt_exception(e, context, symbol=symbol)
            return None
