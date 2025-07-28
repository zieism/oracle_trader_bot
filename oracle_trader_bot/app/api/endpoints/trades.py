# app/api/endpoints/trades.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.session import get_db_session
from app.schemas.trade import Trade as TradeSchema, TradeCreate, TradeUpdate # Assuming Trade is your response schema
from app.crud import crud_trade
from app.models.trade import Trade as TradeModel # For type hinting if needed

router = APIRouter()

@router.post("/", response_model=TradeSchema, status_code=status.HTTP_201_CREATED)
async def create_new_trade(
    trade: TradeCreate, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new trade record. 
    This endpoint might be used internally by the bot engine more than directly by a user.
    """
    # Basic validation or business logic can be added here if needed
    db_trade = await crud_trade.create_trade(db=db, trade_in=trade)
    return db_trade

@router.get("/", response_model=List[TradeSchema])
async def read_trades_history(
    skip: int = Query(0, ge=0), 
    limit: int = Query(10, ge=1, le=100), # Default limit 10, max 100
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve a list of trades with pagination.
    """
    trades = await crud_trade.get_trades(db=db, skip=skip, limit=limit)
    return trades

# --- NEW ENDPOINT ---
@router.get("/total-count", response_model=int)
async def read_total_trades_count(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the total number of all trades in the database.
    """
    total_count = await crud_trade.count_all_trades(db=db)
    return total_count
# --------------------

@router.get("/{trade_id}", response_model=TradeSchema)
async def read_trade_by_id(
    trade_id: int, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve a specific trade by its ID.
    """
    db_trade = await crud_trade.get_trade_by_id(db=db, trade_id=trade_id)
    if db_trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    return db_trade

@router.put("/{trade_id}", response_model=TradeSchema)
async def update_existing_trade(
    trade_id: int, 
    trade_in: TradeUpdate, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update an existing trade record.
    """
    db_trade = await crud_trade.get_trade_by_id(db=db, trade_id=trade_id)
    if db_trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    
    updated_trade = await crud_trade.update_trade(db=db, db_trade=db_trade, trade_in=trade_in)
    return updated_trade

@router.delete("/{trade_id}", response_model=TradeSchema)
async def delete_existing_trade( # Renamed for clarity
    trade_id: int, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete a trade by its ID. (Use with caution)
    """
    deleted_trade = await crud_trade.delete_trade(db=db, trade_id=trade_id)
    if deleted_trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    return deleted_trade
