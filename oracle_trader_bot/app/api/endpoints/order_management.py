# app/api/endpoints/order_management.py
from fastapi import APIRouter, Depends, HTTPException, status, Path, Body, Query 
from typing import List, Dict, Any, Optional
import logging
import ccxt 
from datetime import datetime, timezone

from app.api.dependencies import get_kucoin_client 
from app.db.session import get_db_session 
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient, KucoinRequestError, KucoinAuthError
from app.core.config import settings 
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession 
from app.crud import crud_trade 
from app.models.trade import TradeStatus, TradeDirection, Trade as TradeModel 
from app.schemas.trade import TradeUpdate as TradeUpdateSchema

router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Ensure logging level allows INFO and DEBUG messages

class SetSLTPPayload(BaseModel): 
    position_side: str 
    position_amount: float
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None

class ClosePositionPayload(BaseModel): 
    symbol: str 

@router.get(
    "/status/{symbol}/{order_id}", 
    response_model=Dict[str, Any],
    summary="Get Order Status by ID"
)
async def get_order_status_endpoint( 
    symbol: str = Path(..., description="CCXT market symbol (e.g., BTC/USDT:USDT)"),
    order_id: str = Path(..., description="The exchange order ID"),
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    logger.info(f"OrderManagement: Request to fetch status for order ID '{order_id}', symbol '{symbol}'")
    try:
        order = await kucoin_client.fetch_order(order_id=order_id, symbol=symbol)
        if order is None:
            logger.warning(f"OrderManagement: Order ID '{order_id}' for symbol '{symbol}' not found or client returned None.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Order with ID '{order_id}' for symbol '{symbol}' not found or error fetching."
            )
        logger.info(f"OrderManagement: Successfully fetched status for order ID '{order_id}'. Status: {order.get('status')}")
        return order
    except KucoinAuthError as e:
        logger.warning(f"OrderManagement: No credentials available for order status check: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"ok": False, "reason": "missing_credentials", "message": "Order status requires API credentials"}
        )
    except KucoinRequestError as e:
        logger.error(f"OrderManagement: KucoinRequestError fetching order {order_id} for {symbol}: {e}", exc_info=True)
        original_error = e.__cause__ or e.__context__
        if isinstance(original_error, ccxt.OrderNotFound) or "order not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except KucoinAuthError as e:
        logger.error(f"OrderManagement: KucoinAuthError fetching order {order_id} for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"OrderManagement: Unexpected error fetching order {order_id} for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


@router.delete(
    "/cancel/{symbol}/{order_id}", 
    response_model=Dict[str, Any],
    summary="Cancel Order by ID"
)
async def cancel_order_endpoint( 
    symbol: str = Path(..., description="CCXT market symbol"),
    order_id: str = Path(..., description="The exchange order ID to cancel"),
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    logger.info(f"OrderManagement: Request to cancel order ID '{order_id}', symbol '{symbol}'")
    try:
        response = await kucoin_client.cancel_order_by_id(order_id=order_id, symbol=symbol)
        if response is None: 
            logger.warning(f"OrderManagement: Failed to cancel order {order_id} for {symbol} (client returned None).")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Failed to cancel order {order_id} for {symbol}, or no specific response from client."
            )
        
        if isinstance(response.get("info"), str) and "not found" in response.get("info", "").lower():
             logger.info(f"OrderManagement: Order {order_id} for {symbol} not found for cancellation (already processed). Response: {response}")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.get("info"))
        
        logger.info(f"OrderManagement: Cancellation attempt for order ID '{order_id}' processed. Response: {response}")
        return response
    except KucoinAuthError as e:
        logger.warning(f"OrderManagement: No credentials available for order cancellation: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"ok": False, "reason": "missing_credentials", "message": "Order cancellation requires API credentials"}
        )
    except KucoinRequestError as e:
        logger.error(f"OrderManagement: KucoinRequestError cancelling order {order_id} for {symbol}: {e}", exc_info=True)
        original_error = e.__cause__ or e.__context__
        if isinstance(original_error, ccxt.OrderNotFound) or \
           (isinstance(original_error, ccxt.InvalidOrder) and "cannot be canceled" in str(original_error)) or \
           "100004" in str(e): 
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except KucoinAuthError as e:
        logger.error(f"OrderManagement: KucoinAuthError cancelling order {order_id} for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"OrderManagement: Unexpected error cancelling order {order_id} for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


@router.get(
    "/positions", 
    response_model=List[Dict[str, Any]],
    summary="Get Open Positions (All or by Symbol)"
)
async def get_open_positions_endpoint( 
    symbol: Optional[str] = Query(None, description="Optional: CCXT market symbol (e.g., SUI/USDT:USDT) to filter positions"), 
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client),
    db: AsyncSession = Depends(get_db_session) 
):
    logger.info(f"OrderManagement: Request to fetch open positions. Symbol filter: {symbol if symbol else 'All'}")
    try:
        exchange_positions = await kucoin_client.fetch_open_positions(symbol=symbol) 
            
        if exchange_positions is None:
            logger.warning(f"OrderManagement: Could not fetch open positions (client returned None). Symbol: {symbol if symbol else 'All'}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="Service temporarily unavailable or error fetching positions from exchange."
            )
        
        combined_positions = []
        for pos in exchange_positions:
            pos_symbol = pos.get('symbol')
            if not pos_symbol:
                logger.warning(f"OrderManagement: Position from exchange has no symbol. Skipping: {pos}")
                continue

            # --- START: Debugging Exchange Position Data ---
            logger.debug(f"OrderManagement: Raw exchange position data for {pos_symbol}: {pos}")
            if pos.get('info'):
                logger.debug(f"OrderManagement: Raw exchange position 'info' for {pos_symbol}: {pos.get('info')}")
            # --- END: Debugging Exchange Position Data ---

            # Try to find the corresponding trade in the database
            db_trade: Optional[TradeModel] = await crud_trade.get_open_trade_by_symbol(db, symbol=pos_symbol)
            
            combined_pos_data = {
                "symbol": pos_symbol,
                "side": pos.get('side'),
                "contracts": pos.get('contracts'),
                "entryPrice": pos.get('entryPrice'),
                "markPrice": pos.get('markPrice'),
                "unrealizedPnl": pos.get('unrealizedPnl'),
                "liquidationPrice": pos.get('liquidationPrice'),
                "marginMode": pos.get('marginMode'),
                "timestamp": pos.get('timestamp'),
                "datetime": pos.get('datetime'),
                "info": pos.get('info'),
                # Fields from DB, default to None/N/A if not found or no matching DB trade
                "initialMargin": None,       
                "leverage": None,            
                "stopLossPrice": None,       
                "takeProfitPrice": None,     
            }

            # --- START: Prioritize initialMargin/leverage from exchange if available and more accurate ---
            # KuCoin specific fields for margin often found in 'info'
            # Look for 'posMargin' or 'initMargin' in the raw 'info' dictionary
            raw_info = pos.get('info', {})
            if raw_info.get('posMargin') is not None:
                try:
                    combined_pos_data["initialMargin"] = float(raw_info['posMargin'])
                    logger.debug(f"OrderManagement: Used posMargin from exchange for {pos_symbol}: {combined_pos_data['initialMargin']}")
                except ValueError:
                    logger.warning(f"OrderManagement: Could not parse posMargin from exchange for {pos_symbol}: {raw_info.get('posMargin')}")
            elif raw_info.get('initMargin') is not None:
                try:
                    combined_pos_data["initialMargin"] = float(raw_info['initMargin'])
                    logger.debug(f"OrderManagement: Used initMargin from exchange for {pos_symbol}: {combined_pos_data['initialMargin']}")
                except ValueError:
                    logger.warning(f"OrderManagement: Could not parse initMargin from exchange for {pos_symbol}: {raw_info.get('initMargin')}")

            # Leverage might also be in 'info'
            if raw_info.get('realLeverage') is not None: # Realized leverage
                try:
                    combined_pos_data["leverage"] = int(float(raw_info['realLeverage']))
                    logger.debug(f"OrderManagement: Used realLeverage from exchange for {pos_symbol}: {combined_pos_data['leverage']}")
                except ValueError:
                    logger.warning(f"OrderManagement: Could not parse realLeverage from exchange for {pos_symbol}: {raw_info.get('realLeverage')}")
            elif raw_info.get('leverag') is not None: # Note the typo 'leverag' sometimes
                try:
                    combined_pos_data["leverage"] = int(float(raw_info['leverag']))
                    logger.debug(f"OrderManagement: Used leverag (typo) from exchange for {pos_symbol}: {combined_pos_data['leverage']}")
                except ValueError:
                    logger.warning(f"OrderManagement: Could not parse leverag (typo) from exchange for {pos_symbol}: {raw_info.get('leverag')}")
            # --- END: Prioritize initialMargin/leverage from exchange ---

            if db_trade:
                logger.debug(f"OrderManagement: Found matching DB trade for {pos_symbol}. ID: {db_trade.id}")
                # If exchange didn't provide margin/leverage, use DB values
                if combined_pos_data["initialMargin"] is None and db_trade.margin_used_initial is not None:
                    combined_pos_data["initialMargin"] = db_trade.margin_used_initial
                    logger.debug(f"OrderManagement: Used DB margin_used_initial for {pos_symbol}: {combined_pos_data['initialMargin']}")

                if combined_pos_data["leverage"] is None and db_trade.leverage_applied is not None:
                    combined_pos_data["leverage"] = db_trade.leverage_applied
                    logger.debug(f"OrderManagement: Used DB leverage_applied for {pos_symbol}: {combined_pos_data['leverage']}")
                
                # SL/TP prices almost always come from DB as exchange might not provide them in position data
                combined_pos_data["stopLossPrice"] = db_trade.current_stop_loss_price if db_trade.current_stop_loss_price is not None else db_trade.stop_loss_initial
                combined_pos_data["takeProfitPrice"] = db_trade.current_take_profit_price if db_trade.current_take_profit_price is not None else db_trade.take_profit_initial
                logger.debug(f"OrderManagement: Used DB SL/TP for {pos_symbol}: SL={combined_pos_data['stopLossPrice']}, TP={combined_pos_data['takeProfitPrice']}")

            else:
                logger.warning(f"OrderManagement: No matching open trade found in DB for exchange position: {pos_symbol}. Displaying partial data.")

            combined_positions.append(combined_pos_data)
            
        logger.info(f"OrderManagement: Successfully fetched and combined {len(combined_positions)} open position(s). Symbol filter: {symbol if symbol else 'All'}")
        return combined_positions
    except KucoinAuthError as e:
        logger.warning(f"OrderManagement: No credentials available for positions check: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"ok": False, "reason": "missing_credentials", "message": "Position data requires API credentials"}
        )
    except KucoinRequestError as e: 
        logger.error(f"OrderManagement: KucoinRequestError fetching positions (symbol: {symbol}): {e}", exc_info=True)
        original_error = e.__cause__ or e.__context__
        if isinstance(original_error, ccxt.BadSymbol) or "Invalid symbol" in str(e): 
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid symbol provided: {symbol}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"OrderManagement: Unexpected error fetching open positions (symbol: {symbol}): {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")

@router.post(
    "/positions/set-sl-tp", 
    response_model=Dict[str, Any], 
    summary="Set/Modify Stop Loss and/or Take Profit for an open position (Future Enhancement)"
)
async def set_position_stop_loss_take_profit_endpoint( 
    symbol: str = Query(..., description="CCXT market symbol (e.g., SUI/USDT:USDT)"), 
    payload: SetSLTPPayload = Body(...),
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    logger.info(f"OrderManagement: Request to set/modify SL/TP for symbol '{symbol}'. Payload: {payload.model_dump_json(exclude_none=True)}")
    
    logger.warning(f"OrderManagement: SL/TP modification for {symbol} is currently set to return 501. SL/TP should be set with initial order.")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="SL/TP are set with the initial order. Modification of SL/TP for existing positions is a future enhancement or requires separate specialized order types."
    )

@router.post(
    "/positions/close", 
    response_model=Dict[str, Any],
    summary="Close an Open Position by Symbol"
)
async def close_position_by_symbol_endpoint(
    payload: ClosePositionPayload = Body(...), 
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client),
    db: AsyncSession = Depends(get_db_session) 
):
    ccxt_market_id = payload.symbol
    logger.info(f"ClosePosition: Request to close position for symbol '{ccxt_market_id}'")

    try:
        await kucoin_client._ensure_markets_loaded() 
        logger.debug(f"ClosePosition: Fetching current open position for {ccxt_market_id}...")
        open_positions = await kucoin_client.fetch_open_positions(symbol=ccxt_market_id)
        
        if not open_positions:
            logger.warning(f"ClosePosition: No open position found for symbol {ccxt_market_id} to close.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No open position found for symbol {ccxt_market_id}.")
        
        current_position = open_positions[0] 
        logger.info(f"ClosePosition: Found open position for {ccxt_market_id}: Contracts={current_position.get('contracts')}, Side={current_position.get('side')}")

        position_amount_to_close_str = current_position.get('contracts') 
        position_side = current_position.get('side') 

        if position_amount_to_close_str is None or position_side is None:
            logger.error(f"ClosePosition: Position data for {ccxt_market_id} missing amount or side. Data: {current_position}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Position data for {ccxt_market_id} is incomplete.")

        position_amount_to_close = abs(float(position_amount_to_close_str))
        if position_amount_to_close == 0:
            logger.warning(f"ClosePosition: Position amount for {ccxt_market_id} is zero. Nothing to close. Data: {current_position}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Position amount for {ccxt_market_id} is zero.")

        closing_order_info = await kucoin_client.close_market_position(
            symbol=ccxt_market_id,
            position_amount=position_amount_to_close,
            current_position_side=position_side 
        )

        if closing_order_info and closing_order_info.get('id'):
            logger.info(f"ClosePosition: Position for {ccxt_market_id} successfully closed with order ID {closing_order_info.get('id')}. Response: {closing_order_info}")
            
            try:
                open_trade_in_db = await crud_trade.get_open_trade_by_symbol(db=db, symbol=ccxt_market_id)
                if open_trade_in_db:
                    exit_price_str = closing_order_info.get('average') or closing_order_info.get('price') 
                    exit_price = float(exit_price_str) if exit_price_str is not None else None
                    
                    closed_ts_ms = closing_order_info.get('timestamp')
                    timestamp_closed = datetime.fromtimestamp(closed_ts_ms / 1000, tz=timezone.utc) if closed_ts_ms else datetime.now(timezone.utc)
                    
                    pnl = None 
                    if open_trade_in_db.entry_price and exit_price and open_trade_in_db.quantity:
                        db_entry_price = float(open_trade_in_db.entry_price)
                        db_quantity = float(open_trade_in_db.quantity)
                        if open_trade_in_db.direction == TradeDirection.LONG:
                            pnl = (exit_price - db_entry_price) * db_quantity
                        elif open_trade_in_db.direction == TradeDirection.SHORT:
                            pnl = (db_entry_price - exit_price) * db_quantity
                    
                    trade_update_payload = {
                        "status": TradeStatus.CLOSED_MANUAL, 
                        "exit_price": exit_price,
                        "timestamp_closed": timestamp_closed,
                        "exit_order_id": str(closing_order_info.get('id')),
                        "pnl": pnl
                    }
                    filtered_update_payload = {k: v for k, v in trade_update_payload.items() if v is not None}
                    trade_update_schema = TradeUpdateSchema(**filtered_update_payload)
                    
                    await crud_trade.update_trade(db=db, db_trade=open_trade_in_db, trade_in=trade_update_schema)
                    logger.info(f"ClosePosition: Trade record {open_trade_in_db.id} updated in DB for closed position {ccxt_market_id}.")
                else:
                    logger.warning(f"ClosePosition: No open trade record found in DB for symbol {ccxt_market_id} to update after closing position.")

            except Exception as db_exc:
                logger.error(f"ClosePosition: Failed to update trade in database for closed position {ccxt_market_id}: {db_exc}", exc_info=True)
                return {
                    "status": "success_position_closed_db_update_failed",
                    "message": f"Position for {ccxt_market_id} closed, but DB update failed.",
                    "closing_order_details": closing_order_info,
                    "db_error": str(db_exc)
                }

            return {
                "status": "success", 
                "message": f"Position for {ccxt_market_id} successfully closed and DB updated.",
                "closing_order_details": closing_order_info
            }
        else:
            logger.error(f"ClosePosition: Failed to close position for {ccxt_market_id} (client returned None or no order ID).")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to close position for {ccxt_market_id} (client error).")

    except KucoinAuthError as e:
        logger.error(f"ClosePosition: Auth error for {ccxt_market_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"KuCoin Auth Error: {str(e)}")
    except KucoinRequestError as e: 
        logger.error(f"ClosePosition: KuCoin request error for {ccxt_market_id}: {e}", exc_info=True)
        original_ccxt_error = e.__cause__ or e.__context__
        if isinstance(original_ccxt_error, ccxt.BadSymbol):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid symbol '{ccxt_market_id}': {str(original_ccxt_error)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"KuCoin Request Error: {str(e)}")
    except Exception as e: 
        logger.error(f"ClosePosition: Unexpected error closing position for {ccxt_market_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected server error: {str(e)}")