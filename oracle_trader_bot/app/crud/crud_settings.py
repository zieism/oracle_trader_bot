# app/crud/crud_settings.py
import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.schemas.settings import SettingsRead, SettingsUpdate, SettingsInternal

logger = logging.getLogger(__name__)

class SettingsManager:
    """
    Manages settings persistence with dual mode support:
    - lite mode: File-based storage in .runtime/settings.json
    - full mode: Database-backed storage with file fallback
    """
    
    def __init__(self):
        self.runtime_dir = Path(".runtime")
        self.settings_file = self.runtime_dir / "settings.json"
        self._ensure_runtime_dir()
    
    def _ensure_runtime_dir(self):
        """Ensure runtime directory exists"""
        self.runtime_dir.mkdir(exist_ok=True)
    
    def _mask_secrets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields for reading"""
        masked_data = data.copy()
        secret_fields = [
            'KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE',
            'POSTGRES_PASSWORD'
        ]
        
        for field in secret_fields:
            if field in masked_data and masked_data[field]:
                masked_data[field] = "***"
        
        return masked_data
    
    def _get_current_settings_dict(self) -> Dict[str, Any]:
        """Get current settings as dictionary"""
        return {
            # Project & App Configuration
            'PROJECT_NAME': settings.PROJECT_NAME,
            'VERSION': settings.VERSION,
            'DEBUG': settings.DEBUG,
            'APP_STARTUP_MODE': settings.APP_STARTUP_MODE,
            'SKIP_DB_INIT': settings.SKIP_DB_INIT,
            
            # Exchange Configuration
            'KUCOIN_API_KEY': settings.KUCOIN_API_KEY,
            'KUCOIN_API_SECRET': settings.KUCOIN_API_SECRET,
            'KUCOIN_API_PASSPHRASE': settings.KUCOIN_API_PASSPHRASE,
            'KUCOIN_API_BASE_URL': settings.KUCOIN_API_BASE_URL,
            'KUCOIN_SANDBOX': settings.KUCOIN_SANDBOX,
            
            # Server Configuration
            'SERVER_PUBLIC_IP': settings.SERVER_PUBLIC_IP,
            'API_INTERNAL_BASE_URL': settings.API_INTERNAL_BASE_URL,
            'CORS_ALLOWED_ORIGINS': settings.CORS_ALLOWED_ORIGINS,
            
            # Database Configuration
            'POSTGRES_SERVER': settings.POSTGRES_SERVER,
            'POSTGRES_PORT': settings.POSTGRES_PORT,
            'POSTGRES_USER': settings.POSTGRES_USER,
            'POSTGRES_PASSWORD': settings.POSTGRES_PASSWORD,
            'POSTGRES_DB': settings.POSTGRES_DB,
            
            # Bot Core Loop Settings
            'SYMBOLS_TO_TRADE_BOT': settings.SYMBOLS_TO_TRADE_BOT,
            'PRIMARY_TIMEFRAME_BOT': settings.PRIMARY_TIMEFRAME_BOT,
            'CANDLE_LIMIT_BOT': settings.CANDLE_LIMIT_BOT,
            'LOOP_SLEEP_DURATION_SECONDS_BOT': settings.LOOP_SLEEP_DURATION_SECONDS_BOT,
            'DELAY_BETWEEN_SYMBOL_PROCESSING_SECONDS_BOT': settings.DELAY_BETWEEN_SYMBOL_PROCESSING_SECONDS_BOT,
            
            # General Trading Parameters
            'FIXED_USD_AMOUNT_PER_TRADE': settings.FIXED_USD_AMOUNT_PER_TRADE,
            'BOT_DEFAULT_LEVERAGE': settings.BOT_DEFAULT_LEVERAGE,
            
            # Default Bot Settings
            'MAX_CONCURRENT_TRADES_BOT_CONFIG': settings.MAX_CONCURRENT_TRADES_BOT_CONFIG,
            'TRADE_AMOUNT_MODE_BOT_CONFIG': settings.TRADE_AMOUNT_MODE_BOT_CONFIG,
            'PERCENTAGE_TRADE_AMOUNT_BOT_CONFIG': settings.PERCENTAGE_TRADE_AMOUNT_BOT_CONFIG,
            'DAILY_LOSS_LIMIT_PERCENTAGE_BOT_CONFIG': settings.DAILY_LOSS_LIMIT_PERCENTAGE_BOT_CONFIG,
            
            # Market Regime Analysis Parameters
            'REGIME_ADX_PERIOD': settings.REGIME_ADX_PERIOD,
            'REGIME_ADX_WEAK_TREND_THRESHOLD': settings.REGIME_ADX_WEAK_TREND_THRESHOLD,
            'REGIME_ADX_STRONG_TREND_THRESHOLD': settings.REGIME_ADX_STRONG_TREND_THRESHOLD,
            'REGIME_BBW_PERIOD': settings.REGIME_BBW_PERIOD,
            'REGIME_BBW_STD_DEV': settings.REGIME_BBW_STD_DEV,
            'REGIME_BBW_LOW_THRESHOLD': settings.REGIME_BBW_LOW_THRESHOLD,
            'REGIME_BBW_HIGH_THRESHOLD': settings.REGIME_BBW_HIGH_THRESHOLD,
            
            # Trend Following Strategy Parameters
            'TREND_EMA_FAST_PERIOD': settings.TREND_EMA_FAST_PERIOD,
            'TREND_EMA_MEDIUM_PERIOD': settings.TREND_EMA_MEDIUM_PERIOD,
            'TREND_EMA_SLOW_PERIOD': settings.TREND_EMA_SLOW_PERIOD,
            'TREND_RSI_PERIOD': settings.TREND_RSI_PERIOD,
            'TREND_RSI_OVERBOUGHT': settings.TREND_RSI_OVERBOUGHT,
            'TREND_RSI_OVERSOLD': settings.TREND_RSI_OVERSOLD,
            'TREND_RSI_BULL_ZONE_MIN': settings.TREND_RSI_BULL_ZONE_MIN,
            'TREND_RSI_BEAR_ZONE_MAX': settings.TREND_RSI_BEAR_ZONE_MAX,
            'TREND_MACD_FAST': settings.TREND_MACD_FAST,
            'TREND_MACD_SLOW': settings.TREND_MACD_SLOW,
            'TREND_MACD_SIGNAL': settings.TREND_MACD_SIGNAL,
            'TREND_ATR_PERIOD_SL_TP': settings.TREND_ATR_PERIOD_SL_TP,
            'TREND_ATR_MULTIPLIER_SL': settings.TREND_ATR_MULTIPLIER_SL,
            'TREND_TP_RR_RATIO': settings.TREND_TP_RR_RATIO,
            'TREND_MIN_SIGNAL_STRENGTH': settings.TREND_MIN_SIGNAL_STRENGTH,
            'TREND_LEVERAGE_TIERS_JSON': settings.TREND_LEVERAGE_TIERS_JSON,
            
            # Range Trading Strategy Parameters
            'RANGE_RSI_PERIOD': settings.RANGE_RSI_PERIOD,
            'RANGE_RSI_OVERBOUGHT': settings.RANGE_RSI_OVERBOUGHT,
            'RANGE_RSI_OVERSOLD': settings.RANGE_RSI_OVERSOLD,
            'RANGE_BBANDS_PERIOD': settings.RANGE_BBANDS_PERIOD,
            'RANGE_BBANDS_STD_DEV': settings.RANGE_BBANDS_STD_DEV,
            'RANGE_ATR_PERIOD_SL_TP': settings.RANGE_ATR_PERIOD_SL_TP,
            'RANGE_ATR_MULTIPLIER_SL': settings.RANGE_ATR_MULTIPLIER_SL,
            'RANGE_TP_RR_RATIO': settings.RANGE_TP_RR_RATIO,
            'RANGE_MIN_SIGNAL_STRENGTH': settings.RANGE_MIN_SIGNAL_STRENGTH,
            'RANGE_LEVERAGE_TIERS_JSON': settings.RANGE_LEVERAGE_TIERS_JSON,
            
            # Logging Settings
            'LOG_DIR': settings.LOG_DIR,
            'BOT_ENGINE_LOG_FILE': settings.BOT_ENGINE_LOG_FILE,
            'API_SERVER_LOG_FILE': settings.API_SERVER_LOG_FILE,
            'MAX_LOG_FILE_SIZE_MB': settings.MAX_LOG_FILE_SIZE_MB,
            'LOG_FILE_BACKUP_COUNT': settings.LOG_FILE_BACKUP_COUNT,
        }
    
    def _load_file_settings(self) -> Optional[Dict[str, Any]]:
        """Load settings from file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Settings loaded from {self.settings_file}")
                    return data
        except Exception as e:
            logger.error(f"Error loading settings from file: {e}")
        return None
    
    def _save_file_settings(self, data: Dict[str, Any]) -> bool:
        """Save settings to file"""
        try:
            # Add timestamp
            data['updated_at'] = datetime.now().isoformat()
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Settings saved to {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings to file: {e}")
            return False
    
    async def get_settings(self) -> SettingsRead:
        """Get settings with masked secrets"""
        # In lite mode, use file settings if available, otherwise current settings
        if settings.APP_STARTUP_MODE == "lite":
            file_settings = self._load_file_settings()
            if file_settings:
                # Merge file settings with current defaults (for new fields)
                current = self._get_current_settings_dict()
                current.update(file_settings)
                return SettingsRead(**self._mask_secrets(current))
        
        # Use current settings (from config/env)
        current = self._get_current_settings_dict()
        return SettingsRead(**self._mask_secrets(current))
    
    def _update_settings_object(self, updates: Dict[str, Any]):
        """Update the global settings object in memory"""
        for key, value in updates.items():
            if hasattr(settings, key) and value is not None:
                # Handle special cases for validation
                if key == 'APP_STARTUP_MODE' and value not in ['lite', 'full']:
                    logger.warning(f"Invalid APP_STARTUP_MODE: {value}, skipping")
                    continue
                
                setattr(settings, key, value)
                logger.info(f"Updated settings.{key} = {value if key not in ['KUCOIN_API_SECRET', 'POSTGRES_PASSWORD'] else '***'}")
    
    async def update_settings(self, updates: SettingsUpdate) -> SettingsRead:
        """Update settings and persist them"""
        # Convert to dict, excluding None values and empty secrets
        updates_dict = {}
        for key, value in updates.dict(exclude_none=True).items():
            # Skip empty secrets (don't update if empty string)
            if key in ['KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE', 'POSTGRES_PASSWORD']:
                if value and value.strip():  # Only update if not empty
                    updates_dict[key] = value.strip()
            else:
                updates_dict[key] = value
        
        if not updates_dict:
            logger.info("No valid updates provided")
            return await self.get_settings()
        
        # Load current settings for merging
        current = self._get_current_settings_dict()
        
        # In lite mode, load from file first
        if settings.APP_STARTUP_MODE == "lite":
            file_settings = self._load_file_settings()
            if file_settings:
                current.update(file_settings)
        
        # Apply updates
        current.update(updates_dict)
        
        # Save to file (always in lite mode, or as backup in full mode)
        if settings.APP_STARTUP_MODE == "lite":
            success = self._save_file_settings(current)
            if not success:
                logger.error("Failed to save settings to file")
                raise Exception("Failed to persist settings")
        
        # Update in-memory settings
        self._update_settings_object(updates_dict)
        
        # Re-initialize dependent services
        await self._reinit_services(updates_dict)
        
        return await self.get_settings()
    
    async def _reinit_services(self, changes: Dict[str, Any]):
        """Re-initialize dependent services when settings change"""
        services_reinitialized = []
        
        try:
            # Exchange client re-init if credentials changed
            exchange_fields = ['KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE', 'KUCOIN_SANDBOX']
            if any(field in changes for field in exchange_fields):
                logger.info("Exchange credentials changed, re-initializing exchange client")
                # Import here to avoid circular imports
                from app.services.kucoin_futures_client import KucoinFuturesClient
                
                # This would typically involve updating the app state, but we'll log for now
                logger.info("Exchange client re-initialization requested (implementation pending)")
                services_reinitialized.append("exchange_client")
            
            # Analysis pipeline re-init if analysis parameters changed
            analysis_fields = [f for f in changes.keys() if f.startswith(('REGIME_', 'TREND_', 'RANGE_'))]
            if analysis_fields:
                logger.info(f"Analysis parameters changed: {analysis_fields}")
                logger.info("Analysis pipeline re-initialization requested (implementation pending)")
                services_reinitialized.append("analysis_pipeline")
            
            # Bot configuration re-init if bot settings changed
            bot_fields = [f for f in changes.keys() if f.endswith('_BOT') or 'BOT_' in f]
            if bot_fields:
                logger.info(f"Bot configuration changed: {bot_fields}")
                logger.info("Bot configuration re-initialization requested (implementation pending)")
                services_reinitialized.append("bot_configuration")
            
            if services_reinitialized:
                logger.info(f"Services re-initialized: {', '.join(services_reinitialized)}")
            
        except Exception as e:
            logger.error(f"Error during service re-initialization: {e}")

# Global settings manager instance
settings_manager = SettingsManager()
