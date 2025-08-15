# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional, Tuple, Any
from pydantic import Field, model_validator 
import json
import os # Import os module

class Settings(BaseSettings):
    PROJECT_NAME: str = "Oracle Trader Bot"
    VERSION: str = "1.0.1"
    DEBUG: bool = False

    # App Startup Mode Settings
    APP_STARTUP_MODE: str = Field(default="lite", description="Startup mode: 'lite' (DB optional) or 'full' (DB required)")
    SKIP_DB_INIT: bool = Field(default=True, description="Skip DB initialization on startup")

    @model_validator(mode='after')
    def _validate_startup_mode(cls, instance: 'Settings') -> 'Settings':
        """Validate startup mode and sync with SKIP_DB_INIT."""
        if instance.APP_STARTUP_MODE not in ["lite", "full"]:
            raise ValueError("APP_STARTUP_MODE must be 'lite' or 'full'")
        
        # Sync SKIP_DB_INIT with APP_STARTUP_MODE
        if instance.APP_STARTUP_MODE == "lite":
            instance.SKIP_DB_INIT = True
        elif instance.APP_STARTUP_MODE == "full":
            instance.SKIP_DB_INIT = False
            
        return instance

    # KuCoin API Credentials
    KUCOIN_API_KEY: Optional[str] = None
    KUCOIN_API_SECRET: Optional[str] = None
    KUCOIN_API_PASSPHRASE: Optional[str] = None
    KUCOIN_API_BASE_URL: str = "https://api-futures.kucoin.com"
    KUCOIN_SANDBOX: bool = Field(default=False, description="Use KuCoin sandbox environment")

    # Server Configuration - Dynamic resolution, no hardcoded IPs
    @property
    def external_base_url(self) -> str:
        """Get external base URL dynamically without hardcoded IPs."""
        from .network import resolve_external_base_url
        return resolve_external_base_url()
    
    # DEPRECATED: For backward compatibility - will be removed in v1.2
    SERVER_PUBLIC_IP: str = Field(default="localhost", description="DEPRECATED: Use external_base_url property instead")
    API_INTERNAL_BASE_URL: str = Field(default="http://localhost:8000", description="Internal API URL for bot communication")
    
    # CORS Configuration - Environment-driven exact origin allowlist
    FRONTEND_ORIGINS: str = Field(
        default="http://localhost:5173,https://oracletrader.app,https://www.oracletrader.app",
        description="Comma-separated list of allowed CORS origins for frontend"
    )
    WS_ORIGINS: str = Field(
        default="ws://localhost:5173,wss://oracletrader.app,wss://www.oracletrader.app", 
        description="Comma-separated list of allowed WebSocket origins"
    )

    def parse_csv_env(self, var_name: str) -> List[str]:
        """Parse comma-separated environment variable into list of strings."""
        value = getattr(self, var_name, "")
        if not value:
            return []
        # Split by comma, strip whitespace, filter empty strings, ensure unique
        origins = list(set(origin.strip() for origin in value.split(',') if origin.strip()))
        return origins

    def get_all_cors_origins(self) -> List[str]:
        """Get all CORS origins from environment configuration + dynamic resolution."""
        # Get explicit origins from environment
        explicit_origins = self.parse_csv_env("FRONTEND_ORIGINS")
        
        # Add dynamic origins based on external base URL
        from .network import get_cors_origins
        dynamic_origins = get_cors_origins()
        
        # Combine and deduplicate
        all_origins = list(set(explicit_origins + dynamic_origins))
        return all_origins
    
    def get_all_ws_origins(self) -> List[str]:
        """Get all WebSocket origins from environment configuration."""
        return self.parse_csv_env("WS_ORIGINS")

    # Legacy CORS configuration (deprecated - use FRONTEND_ORIGINS instead)
    CORS_ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: [],
        description="Legacy CORS origins list - use FRONTEND_ORIGINS instead"
    )

    def has_exchange_credentials(self) -> bool:
        """Check if all required KuCoin API credentials are available."""
        return all([
            self.KUCOIN_API_KEY,
            self.KUCOIN_API_SECRET, 
            self.KUCOIN_API_PASSPHRASE
        ])

    def is_sandbox(self) -> bool:
        """Check if running in sandbox mode."""
        return self.KUCOIN_SANDBOX 

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

    # --- Rate Limiting Settings ---
    SETTINGS_RATE_LIMIT: str = Field(default="10/min", description="Rate limit for /api/v1/settings* endpoints per IP")
    HEALTH_RATE_LIMIT: str = Field(default="30/min", description="Rate limit for /api/v1/health/* endpoints per IP")
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL for distributed rate limiting (optional)")

    # --- Security Headers Settings ---
    SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS: bool = Field(default=True, description="Enable X-Content-Type-Options: nosniff header")
    SECURITY_HEADERS_X_FRAME_OPTIONS: bool = Field(default=True, description="Enable X-Frame-Options: DENY header")
    SECURITY_HEADERS_REFERRER_POLICY: bool = Field(default=True, description="Enable Referrer-Policy: no-referrer header")
    SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY: bool = Field(default=True, description="Enable Strict-Transport-Security header (HTTPS only)")
    SECURITY_HEADERS_CONTENT_SECURITY_POLICY: bool = Field(default=False, description="Enable Content-Security-Policy: default-src 'self' header")

    # These fields will hold the parsed list of tuples
    TREND_LEVERAGE_TIERS: List[Tuple[float, int]] = Field(default_factory=list, validate_default=False)
    RANGE_LEVERAGE_TIERS: List[Tuple[float, int]] = Field(default_factory=list, validate_default=False)

    @model_validator(mode='after')
    def _validate_startup_mode(cls, instance: 'Settings') -> 'Settings':
        """Validate startup mode and sync with SKIP_DB_INIT."""
        if instance.APP_STARTUP_MODE not in ["lite", "full"]:
            raise ValueError("APP_STARTUP_MODE must be 'lite' or 'full'")
        
        # Sync SKIP_DB_INIT with APP_STARTUP_MODE
        if instance.APP_STARTUP_MODE == "lite":
            instance.SKIP_DB_INIT = True
        elif instance.APP_STARTUP_MODE == "full":
            instance.SKIP_DB_INIT = False
            
        return instance

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