# app/schemas/settings.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SettingsRead(BaseModel):
    """Schema for reading settings - secrets are masked"""
    
    # Project & App Configuration
    PROJECT_NAME: str
    VERSION: str
    DEBUG: bool
    APP_STARTUP_MODE: str
    SKIP_DB_INIT: bool
    
    # Exchange Configuration
    KUCOIN_API_KEY: Optional[str] = None  # Will be masked with ***
    KUCOIN_API_SECRET: Optional[str] = None  # Will be masked with ***
    KUCOIN_API_PASSPHRASE: Optional[str] = None  # Will be masked with ***
    KUCOIN_API_BASE_URL: str
    KUCOIN_SANDBOX: bool
    
    # Server Configuration
    SERVER_PUBLIC_IP: str
    API_INTERNAL_BASE_URL: str
    CORS_ALLOWED_ORIGINS: List[str]
    
    # Database Configuration (masked)
    POSTGRES_SERVER: str
    POSTGRES_PORT: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = "***"  # Always masked
    POSTGRES_DB: str
    
    # Bot Core Loop Settings
    SYMBOLS_TO_TRADE_BOT: List[str]
    PRIMARY_TIMEFRAME_BOT: str
    CANDLE_LIMIT_BOT: int
    LOOP_SLEEP_DURATION_SECONDS_BOT: int
    DELAY_BETWEEN_SYMBOL_PROCESSING_SECONDS_BOT: int
    
    # General Trading Parameters
    FIXED_USD_AMOUNT_PER_TRADE: float
    BOT_DEFAULT_LEVERAGE: int
    
    # Default Bot Settings
    MAX_CONCURRENT_TRADES_BOT_CONFIG: int
    TRADE_AMOUNT_MODE_BOT_CONFIG: str
    PERCENTAGE_TRADE_AMOUNT_BOT_CONFIG: float
    DAILY_LOSS_LIMIT_PERCENTAGE_BOT_CONFIG: Optional[float]
    
    # Market Regime Analysis Parameters
    REGIME_ADX_PERIOD: int
    REGIME_ADX_WEAK_TREND_THRESHOLD: float
    REGIME_ADX_STRONG_TREND_THRESHOLD: float
    REGIME_BBW_PERIOD: int
    REGIME_BBW_STD_DEV: float
    REGIME_BBW_LOW_THRESHOLD: float
    REGIME_BBW_HIGH_THRESHOLD: float
    
    # Trend Following Strategy Parameters
    TREND_EMA_FAST_PERIOD: int
    TREND_EMA_MEDIUM_PERIOD: int
    TREND_EMA_SLOW_PERIOD: int
    TREND_RSI_PERIOD: int
    TREND_RSI_OVERBOUGHT: int
    TREND_RSI_OVERSOLD: int
    TREND_RSI_BULL_ZONE_MIN: int
    TREND_RSI_BEAR_ZONE_MAX: int
    TREND_MACD_FAST: int
    TREND_MACD_SLOW: int
    TREND_MACD_SIGNAL: int
    TREND_ATR_PERIOD_SL_TP: int
    TREND_ATR_MULTIPLIER_SL: float
    TREND_TP_RR_RATIO: float
    TREND_MIN_SIGNAL_STRENGTH: float
    TREND_LEVERAGE_TIERS_JSON: str
    
    # Range Trading Strategy Parameters
    RANGE_RSI_PERIOD: int
    RANGE_RSI_OVERBOUGHT: int
    RANGE_RSI_OVERSOLD: int
    RANGE_BBANDS_PERIOD: int
    RANGE_BBANDS_STD_DEV: float
    RANGE_ATR_PERIOD_SL_TP: int
    RANGE_ATR_MULTIPLIER_SL: float
    RANGE_TP_RR_RATIO: float
    RANGE_MIN_SIGNAL_STRENGTH: float
    RANGE_LEVERAGE_TIERS_JSON: str
    
    # Logging Settings
    LOG_DIR: str
    BOT_ENGINE_LOG_FILE: str
    API_SERVER_LOG_FILE: str
    MAX_LOG_FILE_SIZE_MB: int
    LOG_FILE_BACKUP_COUNT: int

class SettingsUpdate(BaseModel):
    """Schema for updating settings - secrets are optional and only updated if provided"""
    
    # Project & App Configuration
    PROJECT_NAME: Optional[str] = None
    VERSION: Optional[str] = None
    DEBUG: Optional[bool] = None
    APP_STARTUP_MODE: Optional[str] = Field(None, pattern="^(lite|full)$")
    SKIP_DB_INIT: Optional[bool] = None
    
    # Exchange Configuration - secrets only updated if not empty
    KUCOIN_API_KEY: Optional[str] = None
    KUCOIN_API_SECRET: Optional[str] = None
    KUCOIN_API_PASSPHRASE: Optional[str] = None
    KUCOIN_API_BASE_URL: Optional[str] = None
    KUCOIN_SANDBOX: Optional[bool] = None
    
    # Server Configuration
    SERVER_PUBLIC_IP: Optional[str] = None
    API_INTERNAL_BASE_URL: Optional[str] = None
    CORS_ALLOWED_ORIGINS: Optional[List[str]] = None
    
    # Database Configuration
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_PORT: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None  # Only updated if not empty
    POSTGRES_DB: Optional[str] = None
    
    # Bot Core Loop Settings
    SYMBOLS_TO_TRADE_BOT: Optional[List[str]] = None
    PRIMARY_TIMEFRAME_BOT: Optional[str] = None
    CANDLE_LIMIT_BOT: Optional[int] = Field(None, ge=1)
    LOOP_SLEEP_DURATION_SECONDS_BOT: Optional[int] = Field(None, ge=1)
    DELAY_BETWEEN_SYMBOL_PROCESSING_SECONDS_BOT: Optional[int] = Field(None, ge=0)
    
    # General Trading Parameters
    FIXED_USD_AMOUNT_PER_TRADE: Optional[float] = Field(None, gt=0)
    BOT_DEFAULT_LEVERAGE: Optional[int] = Field(None, ge=1, le=100)
    
    # Default Bot Settings
    MAX_CONCURRENT_TRADES_BOT_CONFIG: Optional[int] = Field(None, ge=0)
    TRADE_AMOUNT_MODE_BOT_CONFIG: Optional[str] = None
    PERCENTAGE_TRADE_AMOUNT_BOT_CONFIG: Optional[float] = Field(None, gt=0, le=100)
    DAILY_LOSS_LIMIT_PERCENTAGE_BOT_CONFIG: Optional[float] = Field(None, gt=0, le=100)
    
    # Market Regime Analysis Parameters
    REGIME_ADX_PERIOD: Optional[int] = Field(None, ge=1)
    REGIME_ADX_WEAK_TREND_THRESHOLD: Optional[float] = Field(None, ge=0)
    REGIME_ADX_STRONG_TREND_THRESHOLD: Optional[float] = Field(None, ge=0)
    REGIME_BBW_PERIOD: Optional[int] = Field(None, ge=1)
    REGIME_BBW_STD_DEV: Optional[float] = Field(None, gt=0)
    REGIME_BBW_LOW_THRESHOLD: Optional[float] = Field(None, ge=0)
    REGIME_BBW_HIGH_THRESHOLD: Optional[float] = Field(None, ge=0)
    
    # Trend Following Strategy Parameters
    TREND_EMA_FAST_PERIOD: Optional[int] = Field(None, ge=1)
    TREND_EMA_MEDIUM_PERIOD: Optional[int] = Field(None, ge=1)
    TREND_EMA_SLOW_PERIOD: Optional[int] = Field(None, ge=1)
    TREND_RSI_PERIOD: Optional[int] = Field(None, ge=1)
    TREND_RSI_OVERBOUGHT: Optional[int] = Field(None, ge=0, le=100)
    TREND_RSI_OVERSOLD: Optional[int] = Field(None, ge=0, le=100)
    TREND_RSI_BULL_ZONE_MIN: Optional[int] = Field(None, ge=0, le=100)
    TREND_RSI_BEAR_ZONE_MAX: Optional[int] = Field(None, ge=0, le=100)
    TREND_MACD_FAST: Optional[int] = Field(None, ge=1)
    TREND_MACD_SLOW: Optional[int] = Field(None, ge=1)
    TREND_MACD_SIGNAL: Optional[int] = Field(None, ge=1)
    TREND_ATR_PERIOD_SL_TP: Optional[int] = Field(None, ge=1)
    TREND_ATR_MULTIPLIER_SL: Optional[float] = Field(None, gt=0)
    TREND_TP_RR_RATIO: Optional[float] = Field(None, gt=0)
    TREND_MIN_SIGNAL_STRENGTH: Optional[float] = Field(None, ge=0, le=1)
    TREND_LEVERAGE_TIERS_JSON: Optional[str] = None
    
    # Range Trading Strategy Parameters
    RANGE_RSI_PERIOD: Optional[int] = Field(None, ge=1)
    RANGE_RSI_OVERBOUGHT: Optional[int] = Field(None, ge=0, le=100)
    RANGE_RSI_OVERSOLD: Optional[int] = Field(None, ge=0, le=100)
    RANGE_BBANDS_PERIOD: Optional[int] = Field(None, ge=1)
    RANGE_BBANDS_STD_DEV: Optional[float] = Field(None, gt=0)
    RANGE_ATR_PERIOD_SL_TP: Optional[int] = Field(None, ge=1)
    RANGE_ATR_MULTIPLIER_SL: Optional[float] = Field(None, gt=0)
    RANGE_TP_RR_RATIO: Optional[float] = Field(None, gt=0)
    RANGE_MIN_SIGNAL_STRENGTH: Optional[float] = Field(None, ge=0, le=1)
    RANGE_LEVERAGE_TIERS_JSON: Optional[str] = None
    
    # Logging Settings
    LOG_DIR: Optional[str] = None
    BOT_ENGINE_LOG_FILE: Optional[str] = None
    API_SERVER_LOG_FILE: Optional[str] = None
    MAX_LOG_FILE_SIZE_MB: Optional[int] = Field(None, ge=1)
    LOG_FILE_BACKUP_COUNT: Optional[int] = Field(None, ge=0)

class SettingsInternal(BaseModel):
    """Internal schema with all unmasked values"""
    
    # Project & App Configuration
    PROJECT_NAME: str
    VERSION: str
    DEBUG: bool
    APP_STARTUP_MODE: str
    SKIP_DB_INIT: bool
    
    # Exchange Configuration (unmasked)
    KUCOIN_API_KEY: Optional[str] = None
    KUCOIN_API_SECRET: Optional[str] = None
    KUCOIN_API_PASSPHRASE: Optional[str] = None
    KUCOIN_API_BASE_URL: str
    KUCOIN_SANDBOX: bool
    
    # Server Configuration
    SERVER_PUBLIC_IP: str
    API_INTERNAL_BASE_URL: str
    CORS_ALLOWED_ORIGINS: List[str]
    
    # Database Configuration (unmasked)
    POSTGRES_SERVER: str
    POSTGRES_PORT: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    
    # Bot Core Loop Settings
    SYMBOLS_TO_TRADE_BOT: List[str]
    PRIMARY_TIMEFRAME_BOT: str
    CANDLE_LIMIT_BOT: int
    LOOP_SLEEP_DURATION_SECONDS_BOT: int
    DELAY_BETWEEN_SYMBOL_PROCESSING_SECONDS_BOT: int
    
    # General Trading Parameters
    FIXED_USD_AMOUNT_PER_TRADE: float
    BOT_DEFAULT_LEVERAGE: int
    
    # Default Bot Settings
    MAX_CONCURRENT_TRADES_BOT_CONFIG: int
    TRADE_AMOUNT_MODE_BOT_CONFIG: str
    PERCENTAGE_TRADE_AMOUNT_BOT_CONFIG: float
    DAILY_LOSS_LIMIT_PERCENTAGE_BOT_CONFIG: Optional[float]
    
    # Market Regime Analysis Parameters
    REGIME_ADX_PERIOD: int
    REGIME_ADX_WEAK_TREND_THRESHOLD: float
    REGIME_ADX_STRONG_TREND_THRESHOLD: float
    REGIME_BBW_PERIOD: int
    REGIME_BBW_STD_DEV: float
    REGIME_BBW_LOW_THRESHOLD: float
    REGIME_BBW_HIGH_THRESHOLD: float
    
    # Trend Following Strategy Parameters
    TREND_EMA_FAST_PERIOD: int
    TREND_EMA_MEDIUM_PERIOD: int
    TREND_EMA_SLOW_PERIOD: int
    TREND_RSI_PERIOD: int
    TREND_RSI_OVERBOUGHT: int
    TREND_RSI_OVERSOLD: int
    TREND_RSI_BULL_ZONE_MIN: int
    TREND_RSI_BEAR_ZONE_MAX: int
    TREND_MACD_FAST: int
    TREND_MACD_SLOW: int
    TREND_MACD_SIGNAL: int
    TREND_ATR_PERIOD_SL_TP: int
    TREND_ATR_MULTIPLIER_SL: float
    TREND_TP_RR_RATIO: float
    TREND_MIN_SIGNAL_STRENGTH: float
    TREND_LEVERAGE_TIERS_JSON: str
    
    # Range Trading Strategy Parameters
    RANGE_RSI_PERIOD: int
    RANGE_RSI_OVERBOUGHT: int
    RANGE_RSI_OVERSOLD: int
    RANGE_BBANDS_PERIOD: int
    RANGE_BBANDS_STD_DEV: float
    RANGE_ATR_PERIOD_SL_TP: int
    RANGE_ATR_MULTIPLIER_SL: float
    RANGE_TP_RR_RATIO: float
    RANGE_MIN_SIGNAL_STRENGTH: float
    RANGE_LEVERAGE_TIERS_JSON: str
    
    # Logging Settings
    LOG_DIR: str
    BOT_ENGINE_LOG_FILE: str
    API_SERVER_LOG_FILE: str
    MAX_LOG_FILE_SIZE_MB: int
    LOG_FILE_BACKUP_COUNT: int
    
    # Computed properties
    updated_at: Optional[datetime] = None

    class Config:
        extra = 'ignore'
