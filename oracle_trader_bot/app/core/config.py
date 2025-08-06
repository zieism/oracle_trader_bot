# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional, Tuple, Any
from pydantic import Field, model_validator 
import json
import os # Import os module

class Settings(BaseSettings):
    PROJECT_NAME: str = "Oracle Trader Bot"
    DEBUG: bool = False

    # KuCoin API Credentials
    KUCOIN_API_KEY: Optional[str] = None
    KUCOIN_API_SECRET: Optional[str] = None
    KUCOIN_API_PASSPHRASE: Optional[str] = None
    KUCOIN_API_BASE_URL: str = "https://api-futures.kucoin.com" 

    # Multi-Exchange API Credentials
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None
    COINBASE_API_KEY: Optional[str] = None
    COINBASE_SECRET_KEY: Optional[str] = None
    COINBASE_PASSPHRASE: Optional[str] = None
    KRAKEN_API_KEY: Optional[str] = None
    KRAKEN_SECRET_KEY: Optional[str] = None

    # Cloud Configuration
    ENVIRONMENT: str = "development"
    KUBERNETES_NAMESPACE: str = "oracle-trader"
    REDIS_URL: str = "redis://localhost:6379"

    # Monitoring
    PROMETHEUS_PORT: int = 8000
    GRAFANA_URL: str = "http://localhost:3000" 

    # Database Credentials
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_USER: str = "youruser" # Replace with your actual user
    POSTGRES_PASSWORD: str = "yourpassword" # Replace with your actual password
    POSTGRES_DB: str = "yourdb" # Replace with your actual db name
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Bot Core Loop Settings
    SYMBOLS_TO_TRADE_BOT: List[str] = Field(default_factory=lambda: ["BTC/USDT:USDT", "ETH/USDT:USDT"], json_loads=True)
    PRIMARY_TIMEFRAME_BOT: str = "1h"
    CANDLE_LIMIT_BOT: int = 200
    LOOP_SLEEP_DURATION_SECONDS_BOT: int = 300 
    DELAY_BETWEEN_SYMBOL_PROCESSING_SECONDS_BOT: int = 5 
    
    # General Trading Parameters (can be overridden by DB settings if BotSettings model is used)
    FIXED_USD_AMOUNT_PER_TRADE: float = 10.0 
    BOT_DEFAULT_LEVERAGE: int = 5 

    # --- Default Bot Settings (for initial creation in DB if not present by crud_bot_settings) ---
    # These are fallback values if DB settings are not found or if specific fields are missing
    MAX_CONCURRENT_TRADES_BOT_CONFIG: int = 3
    TRADE_AMOUNT_MODE_BOT_CONFIG: str = "FIXED_USD" 
    PERCENTAGE_TRADE_AMOUNT_BOT_CONFIG: float = 1.0 
    DAILY_LOSS_LIMIT_PERCENTAGE_BOT_CONFIG: Optional[float] = None

    # --- Market Regime Analysis Parameters ---
    REGIME_ADX_PERIOD: int = 14
    REGIME_ADX_WEAK_TREND_THRESHOLD: float = 20.0
    REGIME_ADX_STRONG_TREND_THRESHOLD: float = 25.0
    REGIME_BBW_PERIOD: int = 20 
    REGIME_BBW_STD_DEV: float = 2.0  
    REGIME_BBW_LOW_THRESHOLD: float = 0.03 
    REGIME_BBW_HIGH_THRESHOLD: float = 0.10 

    # --- Trend Following Strategy Parameters ---
    TREND_EMA_FAST_PERIOD: int = 10
    TREND_EMA_MEDIUM_PERIOD: int = 20
    TREND_EMA_SLOW_PERIOD: int = 50
    TREND_RSI_PERIOD: int = 14
    TREND_RSI_OVERBOUGHT: int = 70 
    TREND_RSI_OVERSOLD: int = 30   
    TREND_RSI_BULL_ZONE_MIN: int = 50 
    TREND_RSI_BEAR_ZONE_MAX: int = 50 
    TREND_MACD_FAST: int = 12 
    TREND_MACD_SLOW: int = 26 
    TREND_MACD_SIGNAL: int = 9 
    TREND_ATR_PERIOD_SL_TP: int = 14
    TREND_ATR_MULTIPLIER_SL: float = 1.5
    TREND_TP_RR_RATIO: float = 2.0 
    TREND_MIN_SIGNAL_STRENGTH: float = 0.5 
    TREND_LEVERAGE_TIERS_JSON: str = '[{"threshold": 0.5, "leverage": 5}, {"threshold": 0.7, "leverage": 10}, {"threshold": 0.9, "leverage": 15}]'
    
    # --- Range Trading Strategy Parameters ---
    RANGE_RSI_PERIOD: int = 14
    RANGE_RSI_OVERBOUGHT: int = 70 
    RANGE_RSI_OVERSOLD: int = 30   
    RANGE_BBANDS_PERIOD: int = 20
    RANGE_BBANDS_STD_DEV: float = 2.0 
    RANGE_ATR_PERIOD_SL_TP: int = 14
    RANGE_ATR_MULTIPLIER_SL: float = 1.0
    RANGE_TP_RR_RATIO: float = 1.5
    RANGE_MIN_SIGNAL_STRENGTH: float = 0.8
    RANGE_LEVERAGE_TIERS_JSON: str = '[{"threshold": 0.8, "leverage": 3}, {"threshold": 0.95, "leverage": 5}]'

    # --- Logging Settings ---
    LOG_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    BOT_ENGINE_LOG_FILE: str = "bot_engine.log"
    API_SERVER_LOG_FILE: str = "api_server.log"
    MAX_LOG_FILE_SIZE_MB: int = 5 # 5 MB
    LOG_FILE_BACKUP_COUNT: int = 5 # Keep 5 backup log files

    # These fields will hold the parsed list of tuples
    TREND_LEVERAGE_TIERS: List[Tuple[float, int]] = Field(default_factory=list, validate_default=False)
    RANGE_LEVERAGE_TIERS: List[Tuple[float, int]] = Field(default_factory=list, validate_default=False)

    @model_validator(mode='after')
    def _parse_leverage_tiers_from_json(cls, instance: 'Settings') -> 'Settings':
        """Parses JSON string for leverage tiers into a list of tuples."""
        # For Pydantic v2, the validator receives the model instance
        
        trend_json_str = instance.TREND_LEVERAGE_TIERS_JSON
        if trend_json_str:
            try:
                parsed = json.loads(trend_json_str)
                instance.TREND_LEVERAGE_TIERS = [(float(tier['threshold']), int(tier['leverage'])) for tier in parsed]
            except json.JSONDecodeError:
                print(f"Warning: Error decoding TREND_LEVERAGE_TIERS_JSON: '{trend_json_str}'. Using empty list.")
                instance.TREND_LEVERAGE_TIERS = [] # Ensure it's an empty list on error
        else:
             instance.TREND_LEVERAGE_TIERS = []


        range_json_str = instance.RANGE_LEVERAGE_TIERS_JSON
        if range_json_str:
            try:
                parsed = json.loads(range_json_str)
                instance.RANGE_LEVERAGE_TIERS = [(float(tier['threshold']), int(tier['leverage'])) for tier in parsed]
            except json.JSONDecodeError:
                print(f"Warning: Error decoding RANGE_LEVERAGE_TIERS_JSON: '{range_json_str}'. Using empty list.")
                instance.RANGE_LEVERAGE_TIERS = []
        else:
            instance.RANGE_LEVERAGE_TIERS = []
            
        return instance

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore'

settings = Settings()