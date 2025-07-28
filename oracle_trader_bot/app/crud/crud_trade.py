# app/crud/crud_trade.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func 
from typing import List, Optional, Dict, Any
from datetime import datetime 

from app.models.trade import Trade as TradeModel, TradeStatus
from app.schemas.trade import TradeCreate as TradeCreateSchema, TradeUpdate as TradeUpdateSchema

async def create_trade(db: AsyncSession, trade_in: TradeCreateSchema) -> TradeModel:
    trade_data = trade_in.model_dump(exclude_unset=True)
    
    if 'direction' in trade_data and hasattr(trade_data['direction'], 'value'):
        trade_data['direction'] = trade_data['direction'].value
    if 'status' in trade_data and hasattr(trade_data['status'], 'value'):
        trade_data['status'] = trade_data['status'].value

    db_trade = TradeModel(**trade_data)
    db.add(db_trade)
    await db.flush()
    await db.refresh(db_trade)
    return db_trade

async def get_trade_by_id(db: AsyncSession, trade_id: int) -> Optional[TradeModel]:
    result = await db.execute(select(TradeModel).filter(TradeModel.id == trade_id))
    return result.scalar_one_or_none()

async def get_trades(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[TradeModel]:
    result = await db.execute(
        select(TradeModel)
        .order_by(TradeModel.timestamp_created.desc()) 
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_open_trade_by_symbol(db: AsyncSession, symbol: str) -> Optional[TradeModel]:
    result = await db.execute(
        select(TradeModel)
        .filter(TradeModel.symbol == symbol)
        .filter(TradeModel.status == TradeStatus.OPEN) 
        .order_by(TradeModel.timestamp_opened.desc()) 
    )
    return result.scalars().first()

async def count_open_trades(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(TradeModel.id)) 
        .filter(TradeModel.status == TradeStatus.OPEN)
    )
    count = result.scalar_one_or_none()
    return count if count is not None else 0

# --- NEW FUNCTION ---
async def count_all_trades(db: AsyncSession) -> int:
    """Counts the total number of all trades in the database."""
    result = await db.execute(
        select(func.count(TradeModel.id))
    )
    count = result.scalar_one_or_none()
    return count if count is not None else 0
# --------------------

async def update_trade(
    db: AsyncSession, db_trade: TradeModel, trade_in: TradeUpdateSchema
) -> TradeModel:
    update_data = trade_in.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        if key == 'status' and hasattr(value, 'value'):
            setattr(db_trade, key, value.value)
        elif hasattr(db_trade, key):
            setattr(db_trade, key, value)
            
    db.add(db_trade) 
    await db.flush() 
    await db.refresh(db_trade) 
    return db_trade

async def delete_trade(db: AsyncSession, trade_id: int) -> Optional[TradeModel]:
    db_trade = await get_trade_by_id(db, trade_id=trade_id)
    if db_trade:
        await db.delete(db_trade)
        await db.flush() 
    return db_trade
