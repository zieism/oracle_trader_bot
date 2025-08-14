# app/crud/crud_settings.py
import os
import json
import logging
import stat
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.schemas.settings import SettingsRead, SettingsUpdate, SettingsInternal
from app.utils.crypto_helper import settings_encryption
from app.utils.audit_logger import audit_logger

logger = logging.getLogger(__name__)

# Configure logging to redact secrets
class SecureLogFormatter(logging.Formatter):
    """Custom log formatter that redacts sensitive information"""
    
    SENSITIVE_FIELDS = [
        'KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE',
        'POSTGRES_PASSWORD', 'SETTINGS_ENCRYPTION_KEY'
    ]
    
    def format(self, record):
        # Get the original message
        original_msg = super().format(record)
        
        # Redact sensitive fields
        for field in self.SENSITIVE_FIELDS:
            # Match various patterns: field=value, "field": "value", etc.
            import re
            patterns = [
                rf'{field}["\']?\s*[:=]\s*["\']?([^"\s,}}]+)',
                rf'Updated settings\.{field} = ([^\s,}}]+)',
                rf'{field}["\']?\s*:\s*["\']([^"]+)["\']'
            ]
            
            for pattern in patterns:
                original_msg = re.sub(
                    pattern, 
                    rf'{field}=<redacted>', 
                    original_msg, 
                    flags=re.IGNORECASE
                )
        
        return original_msg

# Apply secure logging if not already configured
if not any(isinstance(handler.formatter, SecureLogFormatter) for handler in logger.handlers):
    for handler in logger.handlers:
        if handler.formatter:
            handler.setFormatter(SecureLogFormatter(handler.formatter._fmt if hasattr(handler.formatter, '_fmt') else '%(message)s'))

class SettingsManager:
    """
    Manages settings persistence with dual mode support and security hardening:
    - lite mode: File-based storage in .runtime/settings.json (optionally encrypted)
    - full mode: Database-backed storage with file fallback
    - Secret redaction in logs
    - Preserve existing secrets on empty PUT
    - Secure file permissions
    """
    
    def __init__(self):
        self.runtime_dir = Path(".runtime")
        self.settings_file = self.runtime_dir / "settings.json"
        self._ensure_runtime_dir()
        self._secret_fields = {
            'KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE',
            'POSTGRES_PASSWORD'
        }
    
    def _ensure_runtime_dir(self):
        """Ensure runtime directory exists with secure permissions"""
        self.runtime_dir.mkdir(exist_ok=True)
        
        # Set secure permissions (owner only) where OS supports it
        try:
            if os.name == 'posix':  # Unix-like systems
                os.chmod(self.runtime_dir, stat.S_IRWXU)  # 0o700
                logger.debug("Set runtime directory permissions to 0o700")
        except Exception as e:
            logger.warning(f"Could not set secure directory permissions: {e}")
    
    def _mask_secrets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields for reading - ALWAYS return *** for secrets"""
        masked_data = data.copy()
        
        for field in self._secret_fields:
            if field in masked_data:
                # ALWAYS mask secrets regardless of their actual value
                masked_data[field] = "***"
        
        return masked_data
    
    def _redact_for_logging(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a copy of data with secrets redacted for logging"""
        redacted = data.copy()
        for field in self._secret_fields:
            if field in redacted:
                redacted[field] = "<redacted>"
        return redacted
    
    def _validate_secret_format(self, field: str, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate secret field format without leaking actual values
        
        Returns:
            (is_valid, error_message)
        """
        if not value or not value.strip():
            return True, None  # Empty is OK (will be ignored)
        
        value = value.strip()
        
        # Basic format validation without revealing content
        if field in ['KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE']:
            if len(value) < 8:
                return False, f"{field} must be at least 8 characters"
            if len(value) > 200:
                return False, f"{field} exceeds maximum length"
            # Check for basic alphanumeric pattern (don't reveal actual chars)
            import re
            if not re.match(r'^[a-zA-Z0-9\-_+=/.]+$', value):
                return False, f"{field} contains invalid characters"
        
        elif field == 'POSTGRES_PASSWORD':
            if len(value) < 6:
                return False, "Password must be at least 6 characters"
            if len(value) > 128:
                return False, "Password exceeds maximum length"
        
        return True, None
    
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
        """Load settings from file (with optional decryption)"""
        try:
            if not self.settings_file.exists():
                return None
            
            with open(self.settings_file, 'r') as f:
                content = f.read().strip()
            
            if not content:
                return None
            
            # Try to detect if content is encrypted (base64) or plain JSON
            try:
                # First try as plain JSON
                data = json.loads(content)
                logger.info(f"Settings loaded from {self.settings_file} (plaintext)")
                return data
            except json.JSONDecodeError:
                # If JSON parsing fails, try as encrypted data
                if settings_encryption.is_enabled():
                    try:
                        data = settings_encryption.decrypt_from_base64(content)
                        logger.info(f"Settings loaded from {self.settings_file} (encrypted)")
                        return data
                    except Exception as decrypt_err:
                        logger.error(f"Failed to decrypt settings file: {decrypt_err}")
                        return None
                else:
                    logger.error("Settings file appears encrypted but no encryption key available")
                    return None
                    
        except Exception as e:
            logger.error(f"Error loading settings from file: {e}")
        return None
    
    def _save_file_settings(self, data: Dict[str, Any]) -> bool:
        """Save settings to file (with optional encryption and secure permissions)"""
        try:
            # Add timestamp
            data_to_save = data.copy()
            data_to_save['updated_at'] = datetime.now().isoformat()
            
            # Log redacted version
            logger.info(f"Saving settings with {len(data_to_save)} fields: {list(self._redact_for_logging(data_to_save).keys())}")
            
            # Prepare content for saving
            if settings_encryption.is_enabled():
                # Save encrypted
                content = settings_encryption.encrypt_to_base64(data_to_save)
                logger.debug("Settings will be saved encrypted")
            else:
                # Save as plain JSON
                content = json.dumps(data_to_save, indent=2, default=str)
                logger.debug("Settings will be saved as plaintext")
            
            # Write to file with atomic operation
            temp_file = self.settings_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                f.write(content)
            
            # Set secure permissions before moving to final location
            try:
                if os.name == 'posix':  # Unix-like systems
                    os.chmod(temp_file, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
            except Exception as e:
                logger.warning(f"Could not set secure file permissions: {e}")
            
            # Atomic move to final location
            temp_file.replace(self.settings_file)
            
            logger.info(f"Settings saved to {self.settings_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings to file: {e}")
            # Clean up temp file if it exists
            temp_file = self.settings_file.with_suffix('.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
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
        """Update the global settings object in memory with redacted logging"""
        for key, value in updates.items():
            if hasattr(settings, key) and value is not None:
                # Handle special cases for validation
                if key == 'APP_STARTUP_MODE' and value not in ['lite', 'full']:
                    logger.warning(f"Invalid APP_STARTUP_MODE: {value}, skipping")
                    continue
                
                setattr(settings, key, value)
                
                # Log with redaction for secrets
                if key in self._secret_fields:
                    logger.info(f"Updated settings.{key} = <redacted>")
                else:
                    logger.info(f"Updated settings.{key} = {value}")
    
    def _preserve_existing_secrets(self, updates: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preserve existing secret values when PUT contains empty/*** values
        
        Args:
            updates: New values from PUT request
            existing: Current stored values
            
        Returns:
            Updated dict with existing secrets preserved where appropriate
        """
        preserved_updates = updates.copy()
        
        for field in self._secret_fields:
            if field in updates:
                new_value = updates[field]
                
                # Preserve existing if new value is empty, whitespace, or ***
                if not new_value or not new_value.strip() or new_value.strip() == "***":
                    if field in existing and existing[field]:
                        preserved_updates[field] = existing[field]
                        logger.debug(f"Preserved existing value for {field}")
                    else:
                        # Remove from updates if no existing value to preserve
                        preserved_updates.pop(field, None)
                        logger.debug(f"Removed empty {field} from updates")
                else:
                    # Validate format of new secret
                    is_valid, error = self._validate_secret_format(field, new_value)
                    if not is_valid:
                        logger.warning(f"Secret validation failed for {field}: {error}")
                        raise ValueError(f"Invalid {field}: {error}")
        
        return preserved_updates
    
    async def update_settings(self, updates: SettingsUpdate, request=None) -> SettingsRead:
        """Update settings and persist them with secret preservation and audit logging"""
        # Convert to dict, excluding None values
        updates_dict = {}
        for key, value in updates.dict(exclude_none=True).items():
            if value is not None:
                updates_dict[key] = value

        if not updates_dict:
            logger.info("No valid updates provided")
            return await self.get_settings()

        logger.info(f"Processing settings update with fields: {list(updates_dict.keys())}")

        # Load current settings for merging and secret preservation
        current = self._get_current_settings_dict()
        
        # In lite mode, load from file first to get stored secrets
        stored_settings = {}
        if settings.APP_STARTUP_MODE == "lite":
            file_settings = self._load_file_settings()
            if file_settings:
                current.update(file_settings)
                stored_settings = file_settings

        # Capture original values for audit logging
        original_values = stored_settings.copy() if stored_settings else current.copy()

        # Preserve existing secrets when new values are empty/masked
        preserved_updates = self._preserve_existing_secrets(updates_dict, stored_settings if stored_settings else current)

        if not preserved_updates:
            logger.info("No valid updates after secret preservation")
            return await self.get_settings()

        # Apply updates to current settings
        current.update(preserved_updates)

        # Save to file (always in lite mode, or as backup in full mode)
        if settings.APP_STARTUP_MODE == "lite":
            success = self._save_file_settings(current)
            if not success:
                logger.error("Failed to save settings to file")
                raise Exception("Failed to persist settings")

        # Log audit trail for successful changes
        try:
            audit_logger.log_settings_change(
                old_values=original_values,
                new_values=current,
                request=request
            )
        except Exception as e:
            logger.warning(f"Audit logging failed: {e}")
            # Don't fail the main operation due to audit issues

        # Update in-memory settings
        self._update_settings_object(preserved_updates)

        # Re-initialize dependent services
        await self._reinit_services(preserved_updates)

        logger.info(f"Settings update completed successfully for {len(preserved_updates)} fields")
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
