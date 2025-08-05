# app/services/trade_manager.py
"""Trade lifecycle management service."""
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Trade as TradeModel, TradeStatus
from app.schemas.trade import TradeCreate as TradeCreateSchema, TradeUpdate as TradeUpdateSchema
from app.schemas.trading_signal import TradeDirection
from app.crud import crud_trade
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient

logger = logging.getLogger(__name__)


class TradeManager:
    """Manages the complete lifecycle of trades."""
    
    def __init__(self, kucoin_client: KucoinFuturesClient):
        self.kucoin_client = kucoin_client
    
    async def manage_existing_trade(
        self, 
        db: AsyncSession, 
        trade_in_db: TradeModel, 
        symbol: str
    ) -> Dict[str, Any]:
        """
        Manages an existing open trade by checking exchange status and updating database.
        
        Returns:
            Dict with 'action' and 'details' keys indicating what was done
        """
        logger.info(f"TradeManager: Managing existing trade ID: {trade_in_db.id} for {symbol}")
        
        # Check if position is still open on exchange
        open_positions = await self.kucoin_client.fetch_open_positions(symbol=symbol)
        position_is_live = False
        
        if open_positions:
            for pos in open_positions:
                current_qty = float(pos.get('info', {}).get('currentQty', '0'))
                contracts_unified = pos.get('contracts', 0.0)
                
                if abs(current_qty) > 1e-9 or abs(contracts_unified) > 1e-9:
                    position_is_live = True
                    break
        
        if position_is_live:
            logger.info(f"TradeManager: Trade {trade_in_db.id} still open on exchange")
            return {"action": "HOLD", "details": "Position still open on exchange"}
        
        # Position is closed, update trade status
        result = await self._update_closed_trade(db, trade_in_db)
        return {"action": "CLOSED", "details": result}
    
    async def _update_closed_trade(
        self, 
        db: AsyncSession, 
        trade_in_db: TradeModel
    ) -> Dict[str, Any]:
        """Updates a closed trade with exit details."""
        since_timestamp_ms = int(trade_in_db.timestamp_opened.timestamp() * 1000) if trade_in_db.timestamp_opened else None
        
        # Fetch recent trades to find closing fills
        my_trades = await self.kucoin_client.fetch_my_recent_trades(
            symbol=trade_in_db.symbol, 
            since=since_timestamp_ms, 
            limit=20
        )
        
        if not my_trades:
            # No fills found, update with estimated status
            trade_update = TradeUpdateSchema(
                status=TradeStatus.CLOSED_EXCHANGE,
                exit_reason="Position closed on exchange; fill details not found",
                timestamp_closed=datetime.now(timezone.utc)
            )
            await crud_trade.update_trade(db=db, db_trade=trade_in_db, trade_in=trade_update)
            await db.commit()
            return {"status": "updated_no_fills", "trade_id": trade_in_db.id}
        
        # Process closing fills
        closing_details = self._process_closing_fills(trade_in_db, my_trades, since_timestamp_ms)
        
        if closing_details["closing_fills"]:
            # Update trade with closing details
            trade_update = TradeUpdateSchema(
                status=closing_details["final_status"],
                exit_price=closing_details["avg_exit_price"],
                timestamp_closed=closing_details["timestamp_closed"],
                exit_order_id=closing_details["exit_order_id"],
                pnl=closing_details["pnl"],
                pnl_percentage=closing_details["pnl_percentage"],
                exit_fee=closing_details["total_exit_fees"],
                exit_reason=closing_details["exit_reason"]
            )
            await crud_trade.update_trade(db=db, db_trade=trade_in_db, trade_in=trade_update)
            await db.commit()
            return {"status": "updated_with_fills", "trade_id": trade_in_db.id, "pnl": closing_details["pnl"]}
        
        return {"status": "no_closing_fills", "trade_id": trade_in_db.id}
    
    def _process_closing_fills(
        self, 
        trade_in_db: TradeModel, 
        my_trades: List[Dict], 
        since_timestamp_ms: Optional[int]
    ) -> Dict[str, Any]:
        """Processes trade fills to determine closing details."""
        closing_fills = []
        remaining_qty = float(trade_in_db.quantity) if trade_in_db.quantity else 0.0
        db_direction = trade_in_db.direction.value.lower()
        
        # Filter and process fills
        for trade in sorted(my_trades, key=lambda x: x.get('timestamp', 0)):
            if since_timestamp_ms and trade.get('timestamp', 0) < since_timestamp_ms:
                continue
                
            fill_side = trade.get('side', '').lower()
            fill_amount = float(trade.get('amount', 0.0))
            
            # Check if this fill closes the position
            is_closing = (
                (db_direction == 'long' and fill_side == 'sell') or 
                (db_direction == 'short' and fill_side == 'buy')
            )
            
            if is_closing and remaining_qty > 1e-9:
                amount_from_fill = min(remaining_qty, fill_amount)
                closing_fills.append({
                    'price': float(trade.get('price', 0.0)),
                    'amount': amount_from_fill,
                    'cost': float(trade.get('cost', 0.0)),
                    'fee_cost': float(trade.get('fee', {}).get('cost', 0.0)),
                    'timestamp': trade.get('timestamp'),
                    'order_id': trade.get('order')
                })
                remaining_qty -= amount_from_fill
                
                if remaining_qty <= 1e-9:
                    break
        
        # Calculate aggregated closing details
        if not closing_fills:
            return {"closing_fills": []}
        
        total_exit_value = sum(cf['price'] * cf['amount'] for cf in closing_fills)
        total_closed_quantity = sum(cf['amount'] for cf in closing_fills)
        avg_exit_price = total_exit_value / total_closed_quantity if total_closed_quantity > 0 else None
        total_exit_fees = sum(cf['fee_cost'] for cf in closing_fills)
        
        last_fill = closing_fills[-1]
        timestamp_closed = datetime.fromtimestamp(
            last_fill['timestamp'] / 1000, tz=timezone.utc
        ) if last_fill['timestamp'] else datetime.now(timezone.utc)
        
        # Calculate PnL
        pnl = None
        pnl_percentage = None
        entry_price = float(trade_in_db.entry_price) if trade_in_db.entry_price else None
        quantity = float(trade_in_db.quantity) if trade_in_db.quantity else None
        
        if entry_price and avg_exit_price and quantity:
            if trade_in_db.direction == TradeDirection.LONG:
                pnl = (avg_exit_price - entry_price) * quantity
            elif trade_in_db.direction == TradeDirection.SHORT:
                pnl = (entry_price - avg_exit_price) * quantity
                
            if pnl is not None:
                pnl -= total_exit_fees
                if trade_in_db.entry_fee:
                    pnl -= float(trade_in_db.entry_fee)
                    
                if trade_in_db.margin_used_initial and float(trade_in_db.margin_used_initial) != 0:
                    pnl_percentage = (pnl / float(trade_in_db.margin_used_initial)) * 100
        
        # Determine exit reason and status
        exit_reason = "Closed_by_Exchange_Fills"
        final_status = TradeStatus.CLOSED_EXCHANGE
        
        # Infer if SL or TP was hit
        if trade_in_db.stop_loss_initial and avg_exit_price:
            sl_hit = (
                (trade_in_db.direction == TradeDirection.LONG and avg_exit_price <= trade_in_db.stop_loss_initial) or
                (trade_in_db.direction == TradeDirection.SHORT and avg_exit_price >= trade_in_db.stop_loss_initial)
            )
            if sl_hit:
                exit_reason = "StopLoss_Hit_Inferred"
                final_status = TradeStatus.CLOSED_SL
        
        if trade_in_db.take_profit_initial and avg_exit_price:
            tp_hit = (
                (trade_in_db.direction == TradeDirection.LONG and avg_exit_price >= trade_in_db.take_profit_initial) or
                (trade_in_db.direction == TradeDirection.SHORT and avg_exit_price <= trade_in_db.take_profit_initial)
            )
            if tp_hit:
                exit_reason = "TakeProfit_Hit_Inferred"
                final_status = TradeStatus.CLOSED_TP
        
        return {
            "closing_fills": closing_fills,
            "avg_exit_price": avg_exit_price,
            "total_exit_fees": total_exit_fees,
            "timestamp_closed": timestamp_closed,
            "exit_order_id": str(last_fill['order_id']) if last_fill['order_id'] else None,
            "pnl": pnl,
            "pnl_percentage": pnl_percentage,
            "exit_reason": exit_reason,
            "final_status": final_status
        }
    
    async def create_trade_record(
        self, 
        db: AsyncSession, 
        order_info: Dict[str, Any], 
        trading_signal, 
        margin_used: float,
        market_regime_label: str
    ) -> Optional[TradeModel]:
        """Creates a new trade record in the database."""
        try:
            entry_price = order_info.get('average') or trading_signal.entry_price
            quantity = order_info.get('filled') if order_info.get('filled') is not None else 0.0
            
            trade_entry = TradeCreateSchema(
                symbol=order_info.get('symbol', trading_signal.symbol),
                entry_order_id=str(order_info.get('id')),
                client_order_id_entry=order_info.get('clientOrderId'),
                direction=trading_signal.direction,
                entry_price=float(entry_price) if entry_price else None,
                quantity=float(quantity),
                margin_used_initial=float(margin_used),
                leverage_applied=int(trading_signal.suggested_leverage),
                status=TradeStatus.OPEN,
                timestamp_opened=datetime.fromtimestamp(
                    order_info.get('timestamp') / 1000, tz=timezone.utc
                ) if order_info.get('timestamp') else datetime.now(timezone.utc),
                strategy_name=trading_signal.strategy_name,
                market_regime_at_entry=market_regime_label,
                stop_loss_initial=trading_signal.stop_loss,
                take_profit_initial=trading_signal.take_profit,
                entry_fee=float(order_info.get('fee', {}).get('cost', 0.0)) if order_info.get('fee') else 0.0
            )
            
            db_trade = await crud_trade.create_trade(db=db, trade_in=trade_entry)
            await db.commit()
            logger.info(f"TradeManager: Created trade record ID: {db_trade.id}")
            return db_trade
            
        except Exception as e:
            logger.error(f"TradeManager: Failed to create trade record: {e}", exc_info=True)
            await db.rollback()
            return None