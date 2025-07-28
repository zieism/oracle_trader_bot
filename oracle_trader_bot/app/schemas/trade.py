# app/schemas/trade.py
from pydantic import BaseModel, Field
from typing import Optional, List # List might be used for response_model in future
from datetime import datetime, timezone

# Import Enums from your models.trade file
from app.models.trade import TradeDirection, TradeStatus 

# Base schema with common fields, used for inheritance
class TradeBase(BaseModel):
    symbol: str                     
    direction: TradeDirection
    strategy_name: Optional[str] = None
    market_regime_at_entry: Optional[str] = None


# Schema for creating a new trade record in DB (when an order is placed)
# This should contain all information available at the point of opening a trade.
class TradeCreate(TradeBase):
    entry_order_id: str 
    
    entry_price: Optional[float] = None # Actual or intended entry price
    quantity: Optional[float] = None    # Actual or intended quantity

    margin_used_initial: Optional[float] = None
    leverage_applied: Optional[int] = None
    
    stop_loss_initial: Optional[float] = None
    take_profit_initial: Optional[float] = None
    
    status: TradeStatus = TradeStatus.PENDING_OPEN # Default status when creating order
    timestamp_opened: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_order_id_entry: Optional[str] = None


# Schema for updating an existing trade (e.g., when filled, closed, or SL/TP updated)
class TradeUpdate(BaseModel):
    # Fields that can be updated after trade is opened or closed
    status: Optional[TradeStatus] = None
    entry_price: Optional[float] = None # Actual filled entry price
    quantity: Optional[float] = None    # Actual filled quantity
    timestamp_opened: Optional[datetime] = None # Actual open time if different from creation

    exit_price: Optional[float] = None
    timestamp_closed: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None
    exit_order_id: Optional[str] = None
    client_order_id_exit: Optional[str] = None
    exit_reason: Optional[str] = None
    
    entry_fee: Optional[float] = None
    exit_fee: Optional[float] = None
    total_fees: Optional[float] = None
    
    margin_added_total: Optional[float] = None
    
    stop_loss_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None
    current_stop_loss_price: Optional[float] = None 
    current_take_profit_price: Optional[float] = None
    exchange_trade_id: Optional[str] = None # Fill ID(s)


# Schema for reading/returning a trade from the API (output)
class Trade(TradeBase): # Inherits from TradeBase
    id: int
    entry_order_id: str # Should always exist if trade was attempted
    exit_order_id: Optional[str] = None
    client_order_id_entry: Optional[str] = None
    client_order_id_exit: Optional[str] = None
    
    timestamp_opened: Optional[datetime] = None # Nullable until actually opened
    timestamp_closed: Optional[datetime] = None
    
    entry_price: Optional[float] = None 
    exit_price: Optional[float] = None
    quantity: Optional[float] = None    

    margin_used_initial: Optional[float] = None
    margin_added_total: Optional[float] = None
    leverage_applied: Optional[int] = None
    
    status: TradeStatus 
    
    pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None
    
    entry_fee: Optional[float] = None
    exit_fee: Optional[float] = None
    total_fees: Optional[float] = None
    
    stop_loss_initial: Optional[float] = None
    take_profit_initial: Optional[float] = None
    current_stop_loss_price: Optional[float] = None 
    current_take_profit_price: Optional[float] = None
    stop_loss_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None

    exchange_trade_id: Optional[str] = None 

    class Config:
        from_attributes = True 
