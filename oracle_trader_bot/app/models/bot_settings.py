# app/models/bot_settings.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
import enum
from typing import Optional

from app.db.session import Base 
from app.core.config import settings

class TradeAmountMode(str, enum.Enum):
    FIXED_USD = "FIXED_USD"
    PERCENTAGE_BALANCE = "PERCENTAGE_BALANCE"

class BotSettings(Base):
    __tablename__ = "bot_settings"

    id = Column(Integer, primary_key=True, default=1)
    
    # Trading Configuration
    symbols_to_trade = Column(JSON, nullable=False, default=settings.SYMBOLS_TO_TRADE_BOT)
    max_concurrent_trades = Column(Integer, default=3)
    trade_amount_mode = Column(String, default=TradeAmountMode.FIXED_USD.value) 
    fixed_trade_amount_usd = Column(Float, default=10.0) 
    percentage_trade_amount = Column(Float, default=1.0) 
    daily_loss_limit_percentage: Column[Optional[float]] = Column(Float, nullable=True)
    
    # KuCoin API Configuration (encrypted in production)
    kucoin_api_key = Column(String, nullable=True)
    kucoin_api_secret = Column(String, nullable=True)
    kucoin_api_passphrase = Column(String, nullable=True)
    kucoin_sandbox_mode = Column(Boolean, default=True)
    
    # Risk Management
    leverage = Column(Integer, default=5)
    risk_per_trade = Column(Float, default=1.0)  # Percentage of account balance
    atr_based_tp_enabled = Column(Boolean, default=True)
    atr_based_sl_enabled = Column(Boolean, default=True)
    
    # Timeframes
    timeframes = Column(JSON, nullable=False, default=["1h", "4h"])

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<BotSettings(id={self.id}, max_trades={self.max_concurrent_trades}, mode='{self.trade_amount_mode}')>"