# backend/app/services/position_monitor.py
"""
Position Monitoring Service

Handles take profit and stop loss logic for open trades.
Monitors position conditions and executes automated trade closures.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Trade as TradeModel, TradeStatus, TradeDirection
from app.schemas.trade import TradeUpdate as TradeUpdateSchema
from app.crud import crud_trade
from app.services.kucoin_futures_client import KucoinFuturesClient

logger = logging.getLogger(__name__)

async def check_tp_sl_conditions(
    db: AsyncSession,
    kucoin_client: KucoinFuturesClient,
    open_trades: List[TradeModel]
) -> List[Dict[str, Any]]:
    """
    Check take profit and stop loss conditions for open trades.
    Returns list of trades that need to be closed.
    
    Corrected logic for short positions:
    - Short TP: mark_price <= take_profit_price (price went down, profit)
    - Short SL: mark_price >= stop_loss_price (price went up, loss)
    """
    trades_to_close = []
    
    for trade in open_trades:
        if not trade.take_profit and not trade.stop_loss:
            continue
            
        try:
            # Get current market price
            ticker = await kucoin_client.fetch_ticker(trade.symbol)
            if not ticker or 'last' not in ticker:
                logger.warning(f"Could not get ticker for {trade.symbol}")
                continue
                
            mark_price = float(ticker['last'])
            should_close = False
            exit_reason = ""
            
            if trade.direction == TradeDirection.LONG:
                # Long position logic
                if trade.take_profit and mark_price >= trade.take_profit:
                    should_close = True
                    exit_reason = f"Take Profit hit: {mark_price} >= {trade.take_profit}"
                elif trade.stop_loss and mark_price <= trade.stop_loss:
                    should_close = True
                    exit_reason = f"Stop Loss hit: {mark_price} <= {trade.stop_loss}"
                    
            elif trade.direction == TradeDirection.SHORT:
                # Short position logic (CORRECTED)
                if trade.take_profit and mark_price <= trade.take_profit:
                    should_close = True
                    exit_reason = f"Take Profit hit: {mark_price} <= {trade.take_profit}"
                elif trade.stop_loss and mark_price >= trade.stop_loss:
                    should_close = True
                    exit_reason = f"Stop Loss hit: {mark_price} >= {trade.stop_loss}"
            
            if should_close:
                logger.info(f"TP/SL condition met for trade {trade.id}: {exit_reason}")
                trades_to_close.append({
                    'trade': trade,
                    'mark_price': mark_price,
                    'exit_reason': exit_reason
                })
                
        except Exception as e:
            logger.error(f"Error checking TP/SL for trade {trade.id}: {e}")
            continue
    
    return trades_to_close

async def close_position_at_market(
    db: AsyncSession,
    kucoin_client: KucoinFuturesClient,
    trade: TradeModel,
    mark_price: float,
    exit_reason: str
) -> bool:
    """
    Close a position at market price and update the trade in database.
    """
    try:
        # Determine the side for closing order
        close_side = "sell" if trade.direction == TradeDirection.LONG else "buy"
        
        # Place market order to close position
        order = await kucoin_client.create_futures_order(
            symbol=trade.symbol,
            order_type="market",
            side=close_side,
            amount=abs(float(trade.quantity)) if trade.quantity else 0,
            leverage=trade.leverage
        )
        
        if order:
            # Calculate PnL
            entry_price = float(trade.entry_price) if trade.entry_price else mark_price
            quantity = float(trade.quantity) if trade.quantity else 0
            
            if trade.direction == TradeDirection.LONG:
                pnl = (mark_price - entry_price) * quantity
            else:  # SHORT
                pnl = (entry_price - mark_price) * quantity
                
            pnl_percentage = (pnl / (entry_price * quantity)) * 100 if entry_price and quantity else 0
            
            # Update trade in database
            trade_update = TradeUpdateSchema(
                status=TradeStatus.CLOSED_TP_SL,
                exit_price=mark_price,
                exit_order_id=order.get('id'),
                pnl=pnl,
                pnl_percentage=pnl_percentage,
                timestamp_closed=datetime.now(timezone.utc),
                exit_reason=exit_reason
            )
            
            updated_trade = await crud_trade.update_trade(
                db=db, 
                db_trade=trade, 
                trade_in=trade_update
            )
            
            if updated_trade:
                await db.commit()
                logger.info(f"Successfully closed trade {trade.id} at {mark_price} via TP/SL")
                return True
            else:
                await db.rollback()
                logger.error(f"Failed to update trade {trade.id} in database")
                return False
                
    except Exception as e:
        logger.error(f"Error closing position for trade {trade.id}: {e}")
        await db.rollback()
        return False
    
    return False

async def monitor_open_positions(
    db: AsyncSession,
    kucoin_client: KucoinFuturesClient
) -> Dict[str, Any]:
    """
    Main position monitoring function to be called periodically.
    """
    try:
        # Get all open trades from database
        open_trades = await crud_trade.get_trades_by_status(
            db=db, 
            status=TradeStatus.OPEN
        )
        
        if not open_trades:
            return {"message": "No open trades to monitor", "actions_taken": 0}
        
        logger.info(f"Monitoring {len(open_trades)} open positions for TP/SL conditions")
        
        # Check TP/SL conditions
        trades_to_close = await check_tp_sl_conditions(db, kucoin_client, open_trades)
        
        actions_taken = 0
        for trade_info in trades_to_close:
            success = await close_position_at_market(
                db=db,
                kucoin_client=kucoin_client,
                trade=trade_info['trade'],
                mark_price=trade_info['mark_price'],
                exit_reason=trade_info['exit_reason']
            )
            if success:
                actions_taken += 1
        
        return {
            "message": f"Position monitoring completed",
            "open_trades": len(open_trades),
            "tp_sl_triggers": len(trades_to_close),
            "actions_taken": actions_taken
        }
        
    except Exception as e:
        logger.error(f"Error in position monitoring: {e}")
        return {"error": str(e)}
