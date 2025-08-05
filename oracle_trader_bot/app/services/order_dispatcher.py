# app/services/order_dispatcher.py
"""Order dispatching and execution service."""
import logging
from typing import Dict, Any, Optional
import pandas as pd

from app.schemas.trading_signal import TradingSignal, TradeDirection
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient
from app.models.bot_settings import BotSettings as BotSettingsModel, TradeAmountMode
from app.core.config import settings

logger = logging.getLogger(__name__)


class OrderDispatcher:
    """Handles order creation and execution."""
    
    def __init__(self, kucoin_client: KucoinFuturesClient):
        self.kucoin_client = kucoin_client
    
    async def calculate_trade_amount(
        self, 
        bot_config: BotSettingsModel,
        symbol: str
    ) -> float:
        """
        Calculates the margin amount to use for trading based on bot configuration.
        
        Returns:
            Margin amount in USD
        """
        if bot_config.trade_amount_mode == TradeAmountMode.FIXED_USD.value:
            margin_to_use = bot_config.fixed_trade_amount_usd
            logger.info(f"OrderDispatcher: Using FIXED_USD amount: {margin_to_use} USD")
            return margin_to_use
            
        elif bot_config.trade_amount_mode == TradeAmountMode.PERCENTAGE_BALANCE.value:
            available_balance = await self._get_current_usdt_balance()
            if available_balance > 0 and bot_config.percentage_trade_amount > 0:
                margin_to_use = (bot_config.percentage_trade_amount / 100.0) * available_balance
                logger.info(f"OrderDispatcher: Using PERCENTAGE_BALANCE: {bot_config.percentage_trade_amount}% of {available_balance:.2f} USD = {margin_to_use:.2f} USD")
                return margin_to_use
            else:
                logger.warning(f"OrderDispatcher: Cannot use PERCENTAGE_BALANCE (Balance: {available_balance}, Perc: {bot_config.percentage_trade_amount}). Falling back to env default: {settings.FIXED_USD_AMOUNT_PER_TRADE}")
                return settings.FIXED_USD_AMOUNT_PER_TRADE
        else:
            logger.warning(f"OrderDispatcher: Unknown trade_amount_mode '{bot_config.trade_amount_mode}'. Using env default: {settings.FIXED_USD_AMOUNT_PER_TRADE}")
            return settings.FIXED_USD_AMOUNT_PER_TRADE
    
    async def _get_current_usdt_balance(self) -> float:
        """Gets current USDT balance from exchange."""
        try:
            overview = await self.kucoin_client.get_account_overview()
            if overview:
                if 'USDT' in overview and isinstance(overview['USDT'], dict) and overview['USDT'].get('free') is not None:
                    return float(overview['USDT']['free'])
                elif overview.get('info', {}).get('data', {}).get('availableBalance') is not None:
                    try:
                        return float(overview['info']['data']['availableBalance'])
                    except (TypeError, ValueError, KeyError) as e:
                        logger.warning(f"OrderDispatcher: Could not parse 'availableBalance': {e}")
                else:
                    usdt_balance = overview.get('free', {}).get('USDT')
                    if usdt_balance is not None:
                        return float(usdt_balance)
            
            logger.warning("OrderDispatcher: Could not determine USDT balance")
            return 0.0
        except Exception as e:
            logger.error(f"OrderDispatcher: Error getting USDT balance: {e}", exc_info=True)
            return 0.0
    
    async def calculate_order_amount(
        self,
        trading_signal: TradingSignal,
        margin_usd: float,
        symbol: str
    ) -> Optional[float]:
        """
        Calculates the order amount in base currency.
        
        Returns:
            Order amount in base currency, None if calculation fails
        """
        try:
            leverage = trading_signal.suggested_leverage
            effective_entry_price = trading_signal.entry_price or trading_signal.trigger_price
            
            if not effective_entry_price or effective_entry_price <= 0:
                logger.error(f"OrderDispatcher: Invalid entry price for {symbol}")
                return None
            
            position_value_usd = margin_usd * leverage
            
            # Get market info for precision and limits
            market_info = await self.kucoin_client.get_market_info(symbol)
            if not market_info:
                logger.error(f"OrderDispatcher: Market info missing for {symbol}")
                return None
            
            amount_precision = market_info.get('precision', {}).get('amount')
            min_amount = market_info.get('limits', {}).get('amount', {}).get('min')
            contract_size = market_info.get('contractSize', 1.0)
            
            # Calculate amount based on contract type
            if market_info.get('linear', True):
                # Linear contract
                calculated_amount = position_value_usd / effective_entry_price
            elif market_info.get('inverse'):
                # Inverse contract
                if contract_size > 0:
                    calculated_amount = position_value_usd / contract_size
                else:
                    logger.error(f"OrderDispatcher: Invalid contract size for {symbol}")
                    return None
            else:
                # Assume linear as fallback
                calculated_amount = position_value_usd / effective_entry_price
                logger.warning(f"OrderDispatcher: Assuming linear contract for {symbol}")
            
            # Apply precision
            if amount_precision is not None:
                order_amount = float(self.kucoin_client.exchange.amount_to_precision(symbol, calculated_amount))
            else:
                order_amount = calculated_amount
            
            # Check minimum amount
            if min_amount is not None and order_amount < min_amount:
                logger.warning(f"OrderDispatcher: Amount {order_amount} < minimum {min_amount} for {symbol}")
                return None
            
            logger.info(f"OrderDispatcher: Calculated order amount for {symbol}: {order_amount:.8f} (Margin: {margin_usd:.2f} USD, Leverage: {leverage}x)")
            return order_amount
            
        except Exception as e:
            logger.error(f"OrderDispatcher: Error calculating order amount for {symbol}: {e}", exc_info=True)
            return None
    
    async def execute_order(
        self,
        trading_signal: TradingSignal,
        order_amount: float,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Executes the trading order on the exchange.
        
        Returns:
            Order information if successful, None if failed
        """
        try:
            # Determine order side
            if trading_signal.direction == TradeDirection.LONG:
                order_side = 'buy'
            elif trading_signal.direction == TradeDirection.SHORT:
                order_side = 'sell'
            else:
                logger.error(f"OrderDispatcher: Invalid trade direction for {symbol}")
                return None
            
            logger.info(f"OrderDispatcher: Placing {order_side} order for {symbol}: Amount={order_amount:.8f}, Leverage={trading_signal.suggested_leverage}x")
            
            # Create futures order
            order_info = await self.kucoin_client.create_futures_order(
                symbol=symbol,
                order_type='market',
                side=order_side,
                amount=order_amount,
                leverage=trading_signal.suggested_leverage,
                stop_loss_price=trading_signal.stop_loss,
                take_profit_price=trading_signal.take_profit,
                margin_mode='isolated'
            )
            
            if order_info and order_info.get('id'):
                logger.info(f"OrderDispatcher: Order placed successfully for {symbol}. Order ID: {order_info.get('id')}")
                return order_info
            else:
                logger.error(f"OrderDispatcher: Order placement failed for {symbol} - no order ID returned")
                return None
                
        except Exception as e:
            logger.error(f"OrderDispatcher: Error executing order for {symbol}: {e}", exc_info=True)
            return None
    
    async def validate_order_parameters(
        self,
        trading_signal: TradingSignal,
        symbol: str
    ) -> bool:
        """
        Validates order parameters before execution.
        
        Returns:
            True if parameters are valid, False otherwise
        """
        try:
            # Check basic signal validity
            if not trading_signal.entry_price or trading_signal.entry_price <= 0:
                logger.warning(f"OrderDispatcher: Invalid entry price for {symbol}")
                return False
            
            if not trading_signal.stop_loss or not trading_signal.take_profit:
                logger.warning(f"OrderDispatcher: Missing SL/TP for {symbol}")
                return False
            
            if trading_signal.suggested_leverage <= 0:
                logger.warning(f"OrderDispatcher: Invalid leverage for {symbol}")
                return False
            
            # Validate risk/reward ratio
            if trading_signal.direction == TradeDirection.LONG:
                risk = trading_signal.entry_price - trading_signal.stop_loss
                reward = trading_signal.take_profit - trading_signal.entry_price
            else:
                risk = trading_signal.stop_loss - trading_signal.entry_price
                reward = trading_signal.entry_price - trading_signal.take_profit
            
            if risk <= 0 or reward <= 0:
                logger.warning(f"OrderDispatcher: Invalid risk/reward for {symbol}: risk={risk}, reward={reward}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"OrderDispatcher: Error validating order parameters for {symbol}: {e}", exc_info=True)
            return False