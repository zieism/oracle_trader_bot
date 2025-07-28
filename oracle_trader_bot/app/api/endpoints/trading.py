# app/api/endpoints/trading.py
from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import Optional, Dict, Any
import logging
import ccxt
from datetime import datetime, timezone # Ensure timezone is imported

from app.core.config import settings 
from app.api.dependencies import get_kucoin_client # get_kucoin_client is correctly here
from app.db.session import get_db_session # <--- CORRECTED IMPORT PATH for get_db_session
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient, KucoinAuthError, KucoinRequestError
from app.schemas.trading_signal import TradingSignal, TradeDirection
from app.schemas.trade import TradeCreate as TradeCreateSchema 
from app.models.trade import TradeStatus # Import TradeStatus enum for default status
from app.crud import crud_trade 
from sqlalchemy.ext.asyncio import AsyncSession 

router = APIRouter()
logger = logging.getLogger(__name__)
# Set logger level if you want more detailed logs from this specific module
# logger.setLevel(logging.INFO) 

@router.post(
    "/execute-signal", 
    response_model=Dict[str, Any], 
    summary="Execute Trading Signal and Log Trade"
)
async def execute_trading_signal(
    signal: TradingSignal = Body(...), 
    db: AsyncSession = Depends(get_db_session), # DB session dependency
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    logger.info(f"ExecuteSignal: Received for {signal.symbol}, Dir: {signal.direction.value}, Strat: {signal.strategy_name}, Entry: {signal.entry_price}, SL: {signal.stop_loss}, TP: {signal.take_profit}, Lev: {signal.suggested_leverage}")

    # Validate signal parameters
    if not signal.symbol:
        logger.error("ExecuteSignal: Symbol is missing in the trading signal.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol is required in the signal.")
    
    effective_entry_price = signal.entry_price
    if signal.entry_price is None or signal.entry_price <= 0:
        logger.warning(f"ExecuteSignal: Entry price missing/invalid ({signal.entry_price}) for {signal.symbol}. Using trigger_price: {signal.trigger_price} as fallback.")
        effective_entry_price = signal.trigger_price 
    
    if effective_entry_price is None or effective_entry_price <= 0:
        logger.error(f"ExecuteSignal: Valid entry_price or trigger_price required for {signal.symbol} for amount calculation.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid entry_price or trigger_price required in signal for amount calculation.")

    if signal.suggested_leverage <= 0:
        logger.error(f"ExecuteSignal: Suggested leverage ({signal.suggested_leverage}) is invalid for {signal.symbol}.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Suggested leverage must be positive.")

    # Fetch market info for precision and limits
    ccxt_market_id = signal.symbol 
    market_info = await kucoin_client.get_market_info(ccxt_market_id)
    if not market_info:
        logger.error(f"ExecuteSignal: Could not retrieve market info for symbol {ccxt_market_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Market info not found for symbol {ccxt_market_id}. Ensure it's a valid CCXT futures symbol.")

    amount_precision = market_info.get('precision', {}).get('amount')
    min_amount_limit = market_info.get('limits', {}).get('amount', {}).get('min')
    contract_size = market_info.get('contractSize', 1.0) # Default to 1 for linear contracts
    
    # Calculate order amount
    fixed_usd_per_trade_as_margin = settings.FIXED_USD_AMOUNT_PER_TRADE
    leverage_for_sizing = signal.suggested_leverage
    position_value_usd = fixed_usd_per_trade_as_margin * leverage_for_sizing
    order_amount_in_base_currency: float = 0.0
    
    if effective_entry_price > 0:
        calculated_amount = 0.0
        # Differentiate between linear and inverse contracts for amount calculation
        if market_info.get('linear', True): # Assume linear if 'linear' is True or not specified
            calculated_amount = position_value_usd / effective_entry_price
        elif market_info.get('inverse'):
            if contract_size > 0:
                 calculated_amount = position_value_usd / contract_size # Amount is number of contracts
            else:
                logger.error(f"ExecuteSignal: Contract size is zero or invalid for inverse contract {ccxt_market_id}.")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid contract size for inverse contract.")
        else: 
            logger.warning(f"ExecuteSignal: Contract type for {ccxt_market_id} is not explicitly linear or inverse. Assuming linear for amount calculation.")
            calculated_amount = position_value_usd / effective_entry_price


        if amount_precision is not None:
            order_amount_in_base_currency = float(kucoin_client.exchange.amount_to_precision(ccxt_market_id, calculated_amount))
        else: 
            order_amount_in_base_currency = calculated_amount
            logger.warning(f"ExecuteSignal: Amount precision not found for {ccxt_market_id}. Using raw calculated amount: {order_amount_in_base_currency}")

        if min_amount_limit is not None and order_amount_in_base_currency < min_amount_limit:
            logger.error(f"ExecuteSignal: Calculated order amount {order_amount_in_base_currency} for {ccxt_market_id} is below minimum exchange limit {min_amount_limit}.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Calculated order amount {order_amount_in_base_currency} is below minimum {min_amount_limit} for {ccxt_market_id}.")
    else:
        logger.error(f"ExecuteSignal: Cannot calculate order amount due to invalid effective_entry_price ({effective_entry_price}) for {ccxt_market_id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid effective_entry_price for amount calculation.")
    
    logger.info(f"ExecuteSignal: Final Precise Order Amount for {ccxt_market_id}: {order_amount_in_base_currency:.8f} "
                f"(Desired Margin: {fixed_usd_per_trade_as_margin} USD, Intended Leverage for Sizing: {leverage_for_sizing}x)")

    # Prepare order parameters
    ccxt_order_type = 'market' 
    ccxt_side = 'buy' if signal.direction == TradeDirection.LONG else 'sell'
    
    order_execution_params = {'marginMode': 'isolated'} # Assuming isolated margin
    if signal.stop_loss:
        order_execution_params['stopLoss'] = {'triggerPrice': signal.stop_loss, 'type': 'market'}
    if signal.take_profit:
        order_execution_params['takeProfit'] = {'triggerPrice': signal.take_profit, 'type': 'market'}
    
    # If only marginMode is set and no SL/TP, CCXT might not need it explicitly if it's the default.
    # However, being explicit about 'isolated' is generally safer if that's the intent.
    # if len(order_execution_params) == 1 and 'marginMode' in order_execution_params:
    #     order_execution_params = None # Or keep it if 'isolated' must always be sent

    created_order_info: Optional[Dict[str, Any]] = None
    db_trade_id: Optional[int] = None

    try:
        logger.info(f"ExecuteSignal: Placing {ccxt_side} {ccxt_order_type} order for {ccxt_market_id}, "
                    f"Amount: {order_amount_in_base_currency}, Leverage: {leverage_for_sizing}, Params: {order_execution_params}")
        
        created_order_info = await kucoin_client.create_futures_order(
            symbol=ccxt_market_id,
            order_type=ccxt_order_type,
            side=ccxt_side,
            amount=order_amount_in_base_currency,
            price=None, 
            leverage=leverage_for_sizing, 
            stop_loss_price=signal.stop_loss, # Passed to client method
            take_profit_price=signal.take_profit, # Passed to client method
            margin_mode='isolated', 
            params=None # Other specific params not covered by direct args
        )

        if created_order_info and created_order_info.get('id'):
            logger.info(f"ExecuteSignal: Order successfully placed with Exchange. Order ID: {created_order_info.get('id')}")
            
            try:
                actual_entry_price = created_order_info.get('average') or effective_entry_price
                actual_quantity_filled = created_order_info.get('filled') if created_order_info.get('filled') is not None else order_amount_in_base_currency
                
                # Prepare data for TradeCreateSchema
                trade_db_entry = TradeCreateSchema(
                    symbol=created_order_info.get('symbol', ccxt_market_id), 
                    entry_order_id=str(created_order_info.get('id')),
                    direction=signal.direction,
                    entry_price=float(actual_entry_price),
                    quantity=float(actual_quantity_filled),
                    margin_used_initial=float(fixed_usd_per_trade_as_margin),
                    leverage_applied=int(leverage_for_sizing),
                    status=TradeStatus.OPEN, 
                    timestamp_opened=datetime.fromtimestamp(created_order_info.get('timestamp') / 1000, tz=timezone.utc) if created_order_info.get('timestamp') else datetime.now(timezone.utc),
                    strategy_used=signal.strategy_name,
                    # market_regime_at_entry: # TODO: Pass this from signal generation or re-evaluate
                    stop_loss_initial=signal.stop_loss,
                    take_profit_initial=signal.take_profit
                )
                
                db_trade = await crud_trade.create_trade(db=db, trade_in=trade_db_entry)
                db_trade_id = db_trade.id
                logger.info(f"ExecuteSignal: Trade logged to DB with ID: {db_trade_id}")

            except Exception as db_exc:
                logger.error(f"ExecuteSignal: Failed to log trade to database for order {created_order_info.get('id')}: {db_exc}", exc_info=True)
                return {
                    "status": "success_order_placed_db_log_failed",
                    "message": "Market order placed, but DB logging failed. Check server logs.",
                    "order_details_from_exchange": created_order_info,
                    "db_error": str(db_exc)
                }

            return {
                "status": "success", 
                "message": "Market order placed and logged to DB. SL/TP info (if sent) in order_details.",
                "order_details_from_exchange": created_order_info,
                "db_trade_id": db_trade_id, 
            }
        else:
            logger.error(f"ExecuteSignal: Order placement failed for {ccxt_market_id} (client returned None or no ID).")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Order placement failed (client error or no order ID).")

    except KucoinAuthError as e:
        logger.error(f"ExecuteSignal: Auth error for {ccxt_market_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"KuCoin Auth Error: {str(e)}")
    except KucoinRequestError as e: 
        logger.error(f"ExecuteSignal: KuCoin request error for {ccxt_market_id}: {e}", exc_info=True)
        original_ccxt_error = e.__cause__ or e.__context__
        if isinstance(original_ccxt_error, ccxt.InsufficientFunds):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient funds: {str(original_ccxt_error)}. Ensure sufficient balance and that ISOLATED MARGIN LEVERAGE for {ccxt_market_id} is set correctly on KuCoin exchange to match bot's intended leverage ({leverage_for_sizing}x).")
        elif isinstance(original_ccxt_error, ccxt.BadSymbol):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid symbol '{ccxt_market_id}': {str(original_ccxt_error)}")
        elif isinstance(original_ccxt_error, ccxt.ExchangeError) and "you should use either triggerPrice or stopLossPrice or takeProfitPrice" in str(original_ccxt_error):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"KuCoin order structure error (SL/TP with market order): {str(original_ccxt_error)}")
        elif isinstance(original_ccxt_error, ccxt.ExchangeError) and ("margin mode" in str(original_ccxt_error).lower() or "leverage" in str(original_ccxt_error).lower()):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Margin/Leverage mode error: {str(original_ccxt_error)}. Ensure symbol is configured for isolated margin with the correct leverage on KuCoin.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"KuCoin Request Error: {str(e)}")
    except Exception as e: 
        logger.error(f"ExecuteSignal: Unexpected error placing order for {ccxt_market_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected server error: {str(e)}")