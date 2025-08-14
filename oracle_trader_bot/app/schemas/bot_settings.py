# app/schemas/bot_settings.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.models.bot_settings import TradeAmountMode 

class BotSettingsBase(BaseModel):
    # Trading Configuration
    symbols_to_trade: List[str] = Field(default=[], example=["BTC/USDT:USDT", "ETH/USDT:USDT"])
    max_concurrent_trades: int = Field(default=3, ge=0)
    trade_amount_mode: TradeAmountMode = Field(default=TradeAmountMode.FIXED_USD)
    fixed_trade_amount_usd: float = Field(default=10.0, gt=0)
    percentage_trade_amount: float = Field(default=1.0, gt=0, le=100)
    daily_loss_limit_percentage: Optional[float] = Field(default=None, gt=0, le=100)
    
    # KuCoin API Configuration
    kucoin_api_key: Optional[str] = None
    kucoin_api_secret: Optional[str] = None
    kucoin_api_passphrase: Optional[str] = None
    kucoin_sandbox_mode: bool = Field(default=True)
    
    # Risk Management
    leverage: int = Field(default=5, ge=1, le=100)
    risk_per_trade: float = Field(default=1.0, gt=0, le=10)
    atr_based_tp_enabled: bool = Field(default=True)
    atr_based_sl_enabled: bool = Field(default=True)
    
    # Timeframes
    timeframes: List[str] = Field(default=["1h", "4h"], example=["1m", "5m", "1h", "4h", "1d"])

class BotSettingsCreate(BotSettingsBase):
    pass

class BotSettingsUpdate(BaseModel):
    # Trading Configuration
    symbols_to_trade: Optional[List[str]] = None
    max_concurrent_trades: Optional[int] = Field(default=None, ge=0)
    trade_amount_mode: Optional[TradeAmountMode] = None
    fixed_trade_amount_usd: Optional[float] = Field(default=None, gt=0)
    percentage_trade_amount: Optional[float] = Field(default=None, gt=0, le=100)
    daily_loss_limit_percentage: Optional[float] = Field(default=None, gt=0, le=100)
    
    # KuCoin API Configuration
    kucoin_api_key: Optional[str] = None
    kucoin_api_secret: Optional[str] = None
    kucoin_api_passphrase: Optional[str] = None
    kucoin_sandbox_mode: Optional[bool] = None
    
    # Risk Management
    leverage: Optional[int] = Field(default=None, ge=1, le=100)
    risk_per_trade: Optional[float] = Field(default=None, gt=0, le=10)
    atr_based_tp_enabled: Optional[bool] = None
    atr_based_sl_enabled: Optional[bool] = None
    
    # Timeframes
    timeframes: Optional[List[str]] = None

class BotSettings(BotSettingsBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True