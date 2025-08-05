# app/models/trade.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLAlchemyEnum, Boolean, Index
from sqlalchemy.sql import func 
import enum 

from app.db.session import Base 

# Python Enums for database choices
class TradeDirection(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class TradeStatus(str, enum.Enum):
    PENDING_OPEN = "PENDING_OPEN"     
    OPEN = "OPEN"                     
    CLOSED_TP = "CLOSED_TP"           # Closed by Take Profit
    CLOSED_SL = "CLOSED_SL"           # Closed by Stop Loss
    CLOSED_MANUAL = "CLOSED_MANUAL"   # Closed manually by user/API call
    CLOSED_BOT_EXIT = "CLOSED_BOT_EXIT" 
    CLOSED_LIQUIDATION = "CLOSED_LIQUIDATION" 
    CLOSED_EXCHANGE = "CLOSED_EXCHANGE" # Closed by exchange for other reasons (e.g. delisting, maintenance) or inferred
    ERROR = "ERROR"                   
    CANCELLED = "CANCELLED"           
    CLOSED_SL_TP_EXCHANGE = "CLOSED_SL_TP_EXCHANGE" # Generic for SL/TP hit on exchange side

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    timestamp_opened = Column(DateTime(timezone=True), nullable=True, index=True)
    timestamp_closed = Column(DateTime(timezone=True), nullable=True, index=True)
    timestamp_created = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    symbol = Column(String, nullable=False, index=True) 
    exchange_trade_id = Column(String, nullable=True, index=True) 
    
    entry_order_id = Column(String, nullable=False, index=True) 
    exit_order_id = Column(String, nullable=True, index=True)  
    client_order_id_entry = Column(String, nullable=True, index=True) 
    client_order_id_exit = Column(String, nullable=True, index=True)

    direction = Column(SQLAlchemyEnum(TradeDirection, name="tradedirection"), nullable=False) # Added name for enum type
    entry_price = Column(Float, nullable=True) 
    exit_price = Column(Float, nullable=True)  
    quantity = Column(Float, nullable=True)    

    margin_used_initial = Column(Float, nullable=True) 
    margin_added_total = Column(Float, default=0.0, nullable=True) 
    leverage_applied = Column(Integer, nullable=True)

    pnl = Column(Float, nullable=True) 
    pnl_percentage = Column(Float, nullable=True) 
    status = Column(SQLAlchemyEnum(TradeStatus, name="tradestatus"), default=TradeStatus.PENDING_OPEN, nullable=False, index=True) # Added name for enum type
    
    exit_reason = Column(String, nullable=True) 
    strategy_name = Column(String, nullable=True) 
    market_regime_at_entry = Column(String, nullable=True) 

    stop_loss_initial = Column(Float, nullable=True)
    take_profit_initial = Column(Float, nullable=True)
    
    stop_loss_order_id = Column(String, nullable=True, index=True)
    take_profit_order_id = Column(String, nullable=True, index=True)
    
    current_stop_loss_price = Column(Float, nullable=True) 
    current_take_profit_price = Column(Float, nullable=True)

    entry_fee = Column(Float, nullable=True, default=0.0)
    exit_fee = Column(Float, nullable=True, default=0.0)
    total_fees = Column(Float, nullable=True, default=0.0)

    def __repr__(self):
        return f"<Trade(id={self.id}, symbol='{self.symbol}', direction='{self.direction.value if self.direction else 'N/A'}', status='{self.status.value if self.status else 'N/A'}')>"


# Composite indexes for performance optimization
Index('idx_trades_symbol_status', Trade.symbol, Trade.status)
Index('idx_trades_symbol_timestamp_created', Trade.symbol, Trade.timestamp_created.desc())
Index('idx_trades_status_timestamp_opened', Trade.status, Trade.timestamp_opened.desc())
Index('idx_trades_symbol_status_timestamp', Trade.symbol, Trade.status, Trade.timestamp_created.desc())
Index('idx_trades_strategy_status', Trade.strategy_name, Trade.status)
Index('idx_trades_open_positions', Trade.symbol, Trade.status, Trade.timestamp_opened, 
      postgresql_where=(Trade.status == TradeStatus.OPEN))

