# app/schemas/bot_settings.py
from pydantic import BaseModel, Field
from typing import Optional, List # <-- CHANGE: Import List
from datetime import datetime

from app.models.bot_settings import TradeAmountMode 

class BotSettingsBase(BaseModel):
    # --- CHANGE: Added symbols_to_trade field ---
    symbols_to_trade: List[str] = Field(default=[], example=["BTC/USDT:USDT", "ETH/USDT:USDT"])
    
    max_concurrent_trades: int = Field(default=3, ge=0)
    trade_amount_mode: TradeAmountMode = Field(default=TradeAmountMode.FIXED_USD)
    fixed_trade_amount_usd: float = Field(default=10.0, gt=0)
    percentage_trade_amount: float = Field(default=1.0, gt=0, le=100)
    daily_loss_limit_percentage: Optional[float] = Field(default=None, gt=0, le=100)

class BotSettingsCreate(BotSettingsBase):
    pass

class BotSettingsUpdate(BaseModel):
    # --- CHANGE: Added symbols_to_trade field ---
    symbols_to_trade: Optional[List[str]] = None
    
    max_concurrent_trades: Optional[int] = Field(default=None, ge=0)
    trade_amount_mode: Optional[TradeAmountMode] = None
    fixed_trade_amount_usd: Optional[float] = Field(default=None, gt=0)
    percentage_trade_amount: Optional[float] = Field(default=None, gt=0, le=100)
    daily_loss_limit_percentage: Optional[float] = Field(default=None, gt=0, le=100)

class BotSettings(BotSettingsBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True