# backend/app/api/routers/trades.py
"""
Trades Router - Trade History & Management

Provides CRUD operations for trade records and trading history management.
Handles trade creation, retrieval, updates, and deletion with pagination support.

Routes:
- POST /api/v1/trades/ - Create new trade record
- GET /api/v1/trades/ - Get trade history with pagination
- GET /api/v1/trades/total-count - Get total number of trades
- GET /api/v1/trades/{trade_id} - Get specific trade by ID
- PUT /api/v1/trades/{trade_id} - Update existing trade
- DELETE /api/v1/trades/{trade_id} - Delete trade record
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.session import get_db_session
from app.schemas.trade import Trade as TradeSchema, TradeCreate, TradeUpdate
from app.crud import crud_trade
from app.models.trade import Trade as TradeModel

router = APIRouter()

@router.post(
    "/", # Full path: /api/v1/trades/
    response_model=TradeSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Trade Record",
    tags=["Trades"]
)
async def create_new_trade(
    trade: TradeCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new trade record in the database.
    
    This endpoint is primarily used internally by the bot engine when executing trades,
    but can also be used manually to log trades from external sources.
    
    - **trade**: Complete trade information including symbol, direction, prices, quantities
    """
    # Basic validation or business logic can be added here if needed
    db_trade = await crud_trade.create_trade(db=db, trade_in=trade)
    return db_trade

@router.get(
    "/", # Full path: /api/v1/trades/
    response_model=List[TradeSchema],
    summary="Get Trade History",
    tags=["Trades"]
)
async def read_trades_history(
    skip: int = Query(0, ge=0, description="Number of trades to skip (for pagination)"),
    limit: int = Query(10, ge=1, le=100, description="Number of trades to return (max 100)"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve a paginated list of trade records.
    
    Returns trades in reverse chronological order (newest first) by default.
    Use skip and limit parameters for pagination through large trade histories.
    
    - **skip**: Number of records to skip (offset)
    - **limit**: Maximum number of records to return (1-100)
    """
    trades = await crud_trade.get_trades(db=db, skip=skip, limit=limit)
    return trades

@router.get(
    "/total-count", # Full path: /api/v1/trades/total-count
    response_model=int,
    summary="Get Total Trade Count",
    tags=["Trades"]
)
async def read_total_trades_count(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the total number of all trades in the database.
    
    Useful for calculating pagination parameters and displaying total trade statistics.
    """
    total_count = await crud_trade.count_all_trades(db=db)
    return total_count

@router.get(
    "/{trade_id}", # Full path: /api/v1/trades/{trade_id}
    response_model=TradeSchema,
    summary="Get Trade by ID",
    tags=["Trades"]
)
async def read_trade_by_id(
    trade_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve a specific trade record by its unique ID.
    
    - **trade_id**: Unique identifier of the trade to retrieve
    """
    db_trade = await crud_trade.get_trade_by_id(db=db, trade_id=trade_id)
    if db_trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    return db_trade

@router.put(
    "/{trade_id}", # Full path: /api/v1/trades/{trade_id}
    response_model=TradeSchema,
    summary="Update Trade Record",
    tags=["Trades"]
)
async def update_existing_trade(
    trade_id: int,
    trade_in: TradeUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update an existing trade record.
    
    Allows modification of trade details such as exit prices, status updates,
    profit/loss calculations, and other trade metadata.
    
    - **trade_id**: Unique identifier of the trade to update
    - **trade_in**: Updated trade information (only provided fields will be modified)
    """
    db_trade = await crud_trade.get_trade_by_id(db=db, trade_id=trade_id)
    if db_trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    
    updated_trade = await crud_trade.update_trade(db=db, db_trade=db_trade, trade_in=trade_in)
    return updated_trade

@router.delete(
    "/{trade_id}", # Full path: /api/v1/trades/{trade_id}
    response_model=TradeSchema,
    summary="Delete Trade Record",
    tags=["Trades"]
)
async def delete_existing_trade(
    trade_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete a trade record by its unique ID.
    
    **Use with caution** - this permanently removes the trade from the database.
    Consider updating the trade status instead of deletion for audit trail purposes.
    
    - **trade_id**: Unique identifier of the trade to delete
    """
    deleted_trade = await crud_trade.delete_trade(db=db, trade_id=trade_id)
    if deleted_trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    return deleted_trade
