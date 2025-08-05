# app/config/config_manager.py
import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from app.core.config import settings


logger = logging.getLogger(__name__)


class ConfigEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ConfigChange:
    timestamp: datetime
    environment: str
    section: str
    key: str
    old_value: Any
    new_value: Any
    user: str = "system"


@dataclass
class ConfigValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ConfigManager:
    """
    Advanced configuration management system with environment-specific configs,
    hot-reload capabilities, validation, and change tracking.
    """
    
    def __init__(self):
        self.logger = logger
        self.current_environment = self._detect_environment()
        self.config_dir = Path(settings.LOG_DIR).parent / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.config_history: List[ConfigChange] = []
        self.validation_rules: Dict[str, Dict] = {}
        self.hot_reload_enabled = True
        self.file_watchers: Dict[str, float] = {}  # filename -> last_modified
        self._initialized = False
    
    async def initialize(self):
        """Initialize the configuration manager (call this once in async context)."""
        if not self._initialized:
            await self._initialize_configs()
            self._initialized = True
    
    def _detect_environment(self) -> ConfigEnvironment:
        """Detect current environment from environment variables."""
        env = os.getenv('APP_ENV', os.getenv('ENVIRONMENT', 'development')).lower()
        
        if env in ['prod', 'production']:
            return ConfigEnvironment.PRODUCTION
        elif env in ['stage', 'staging']:
            return ConfigEnvironment.STAGING
        else:
            return ConfigEnvironment.DEVELOPMENT
    
    async def _initialize_configs(self):
        """Initialize configuration files for all environments."""
        try:
            # Create environment-specific config files
            for env in ConfigEnvironment:
                config_file = self.config_dir / f"config_{env.value}.json"
                
                if not config_file.exists():
                    default_config = await self._get_default_config(env)
                    await self._save_config_file(config_file, default_config)
                    self.logger.info(f"Created default config for {env.value}")
                
                # Load the config
                self.configs[env.value] = await self._load_config_file(config_file)
                self.file_watchers[str(config_file)] = config_file.stat().st_mtime
            
            # Load validation rules
            await self._load_validation_rules()
            
            self.logger.info(f"Configuration manager initialized for {self.current_environment.value}")
            
        except Exception as e:
            self.logger.error(f"Error initializing config manager: {e}")
    
    async def _get_default_config(self, environment: ConfigEnvironment) -> Dict[str, Any]:
        """Get default configuration for specified environment."""
        base_config = {
            "trading": {
                "max_concurrent_trades": 3 if environment == ConfigEnvironment.PRODUCTION else 2,
                "fixed_trade_amount_usd": 10.0 if environment == ConfigEnvironment.PRODUCTION else 5.0,
                "daily_loss_limit_percentage": 5.0,
                "enable_trading": environment != ConfigEnvironment.DEVELOPMENT,
                "symbols_to_trade": ["BTC/USDT:USDT", "ETH/USDT:USDT"]
            },
            "risk_management": {
                "daily_loss_limit_pct": 5.0,
                "max_position_correlation": 0.7,
                "max_portfolio_leverage": 10.0,
                "max_drawdown_pct": 15.0,
                "volatility_threshold": 0.08,
                "margin_usage_limit": 0.8,
                "emergency_stop_enabled": True
            },
            "strategy_parameters": {
                "trend_following": {
                    "ema_fast_period": 10,
                    "ema_medium_period": 20,
                    "ema_slow_period": 50,
                    "rsi_period": 14,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30,
                    "min_signal_strength": 0.5
                },
                "range_trading": {
                    "rsi_period": 14,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30,
                    "bbands_period": 20,
                    "bbands_std_dev": 2.0,
                    "min_signal_strength": 0.8
                }
            },
            "monitoring": {
                "enable_alerts": True,
                "alert_channels": ["log", "email"] if environment == ConfigEnvironment.PRODUCTION else ["log"],
                "performance_tracking_enabled": True,
                "metrics_retention_days": 90 if environment == ConfigEnvironment.PRODUCTION else 30
            },
            "api": {
                "rate_limit_per_minute": 60 if environment == ConfigEnvironment.PRODUCTION else 30,
                "enable_cors": environment != ConfigEnvironment.PRODUCTION,
                "debug_mode": environment == ConfigEnvironment.DEVELOPMENT,
                "request_timeout_seconds": 30
            },
            "database": {
                "connection_pool_size": 20 if environment == ConfigEnvironment.PRODUCTION else 5,
                "connection_timeout": 30,
                "query_timeout": 60,
                "enable_query_logging": environment == ConfigEnvironment.DEVELOPMENT
            },
            "security": {
                "encrypt_api_keys": True,
                "enable_audit_logging": environment == ConfigEnvironment.PRODUCTION,
                "session_timeout_minutes": 60,
                "max_login_attempts": 5
            }
        }
        
        return base_config
    
    async def _load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading config file {config_file}: {e}")
            return {}
    
    async def _save_config_file(self, config_file: Path, config_data: Dict[str, Any]):
        """Save configuration to file."""
        try:
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error saving config file {config_file}: {e}")
    
    async def _load_validation_rules(self):
        """Load configuration validation rules."""
        self.validation_rules = {
            "trading.max_concurrent_trades": {
                "type": int,
                "min": 1,
                "max": 10,
                "required": True
            },
            "trading.fixed_trade_amount_usd": {
                "type": float,
                "min": 1.0,
                "max": 1000.0,
                "required": True
            },
            "trading.daily_loss_limit_percentage": {
                "type": float,
                "min": 1.0,
                "max": 50.0,
                "required": True
            },
            "risk_management.daily_loss_limit_pct": {
                "type": float,
                "min": 1.0,
                "max": 50.0,
                "required": True
            },
            "risk_management.volatility_threshold": {
                "type": float,
                "min": 0.01,
                "max": 0.5,
                "required": True
            },
            "risk_management.margin_usage_limit": {
                "type": float,
                "min": 0.1,
                "max": 0.95,
                "required": True
            },
            "strategy_parameters.trend_following.ema_fast_period": {
                "type": int,
                "min": 5,
                "max": 50,
                "required": True
            },
            "strategy_parameters.trend_following.ema_medium_period": {
                "type": int,
                "min": 10,
                "max": 100,
                "required": True
            },
            "strategy_parameters.trend_following.ema_slow_period": {
                "type": int,
                "min": 20,
                "max": 200,
                "required": True
            },
            "api.rate_limit_per_minute": {
                "type": int,
                "min": 10,
                "max": 1000,
                "required": True
            },
            "database.connection_pool_size": {
                "type": int,
                "min": 1,
                "max": 50,
                "required": True
            }
        }
    
    async def get_config(
        self, 
        key: str, 
        environment: Optional[ConfigEnvironment] = None,
        default: Any = None
    ) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (e.g., 'trading.max_concurrent_trades')
            environment: Specific environment (defaults to current)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            env = environment or self.current_environment
            config = self.configs.get(env.value, {})
            
            # Navigate nested keys
            keys = key.split('.')
            value = config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception as e:
            self.logger.error(f"Error getting config key {key}: {e}")
            return default
    
    async def set_config(
        self,
        key: str,
        value: Any,
        environment: Optional[ConfigEnvironment] = None,
        user: str = "system",
        validate: bool = True
    ) -> bool:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: New value
            environment: Target environment
            user: User making the change
            validate: Whether to validate the change
            
        Returns:
            True if successful
        """
        try:
            env = environment or self.current_environment
            
            # Validate if requested
            if validate:
                validation_result = await self._validate_config_change(key, value)
                if not validation_result.is_valid:
                    self.logger.error(f"Config validation failed for {key}: {validation_result.errors}")
                    return False
                
                if validation_result.warnings:
                    self.logger.warning(f"Config warnings for {key}: {validation_result.warnings}")
            
            # Get current value for history
            old_value = await self.get_config(key, env)
            
            # Update configuration
            config = self.configs.get(env.value, {})
            keys = key.split('.')
            
            # Navigate to parent dict
            current = config
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # Set the value
            current[keys[-1]] = value
            
            # Save to file
            config_file = self.config_dir / f"config_{env.value}.json"
            await self._save_config_file(config_file, config)
            
            # Update file watcher
            self.file_watchers[str(config_file)] = config_file.stat().st_mtime
            
            # Record change
            change = ConfigChange(
                timestamp=datetime.utcnow(),
                environment=env.value,
                section=keys[0] if keys else "root",
                key=key,
                old_value=old_value,
                new_value=value,
                user=user
            )
            
            self.config_history.append(change)
            
            # Limit history size
            if len(self.config_history) > 1000:
                self.config_history = self.config_history[-500:]
            
            self.logger.info(f"Configuration updated: {key} = {value} (env: {env.value}, user: {user})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting config {key}: {e}")
            return False
    
    async def _validate_config_change(self, key: str, value: Any) -> ConfigValidationResult:
        """Validate a configuration change."""
        errors = []
        warnings = []
        
        try:
            # Check if validation rule exists
            if key in self.validation_rules:
                rule = self.validation_rules[key]
                
                # Type validation
                expected_type = rule.get("type")
                if expected_type and not isinstance(value, expected_type):
                    errors.append(f"Expected {expected_type.__name__}, got {type(value).__name__}")
                
                # Range validation for numbers
                if isinstance(value, (int, float)):
                    min_val = rule.get("min")
                    max_val = rule.get("max")
                    
                    if min_val is not None and value < min_val:
                        errors.append(f"Value {value} is below minimum {min_val}")
                    
                    if max_val is not None and value > max_val:
                        errors.append(f"Value {value} is above maximum {max_val}")
                
                # String validation
                if isinstance(value, str):
                    min_length = rule.get("min_length", 0)
                    max_length = rule.get("max_length")
                    
                    if len(value) < min_length:
                        errors.append(f"String too short (min: {min_length})")
                    
                    if max_length and len(value) > max_length:
                        errors.append(f"String too long (max: {max_length})")
                
                # List validation
                if isinstance(value, list):
                    min_items = rule.get("min_items", 0)
                    max_items = rule.get("max_items")
                    
                    if len(value) < min_items:
                        errors.append(f"List too short (min items: {min_items})")
                    
                    if max_items and len(value) > max_items:
                        errors.append(f"List too long (max items: {max_items})")
            
            # Custom validation for specific keys
            if key == "trading.symbols_to_trade":
                if isinstance(value, list):
                    for symbol in value:
                        if not isinstance(symbol, str) or '/' not in symbol:
                            errors.append(f"Invalid symbol format: {symbol}")
                
            elif key.endswith("_period") and isinstance(value, int):
                if "fast" in key and "medium" in key.replace("fast", ""):
                    # Check that fast period < medium period
                    medium_key = key.replace("fast", "medium")
                    medium_value = await self.get_config(medium_key)
                    if medium_value and value >= medium_value:
                        warnings.append("Fast period should be less than medium period")
            
            return ConfigValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error(f"Error validating config {key}: {e}")
            return ConfigValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[]
            )
    
    async def check_for_config_changes(self):
        """Check for external configuration file changes (hot-reload)."""
        if not self.hot_reload_enabled:
            return
        
        try:
            changes_detected = False
            
            for config_file_path, last_modified in self.file_watchers.items():
                config_file = Path(config_file_path)
                
                if config_file.exists():
                    current_modified = config_file.stat().st_mtime
                    
                    if current_modified > last_modified:
                        self.logger.info(f"Configuration file changed: {config_file}")
                        
                        # Reload the configuration
                        env_name = config_file.stem.split('_')[1]  # Extract env from filename
                        self.configs[env_name] = await self._load_config_file(config_file)
                        self.file_watchers[config_file_path] = current_modified
                        
                        changes_detected = True
            
            if changes_detected:
                self.logger.info("Hot-reload: Configuration changes applied")
            
        except Exception as e:
            self.logger.error(f"Error checking for config changes: {e}")
    
    async def export_config(self, environment: Optional[ConfigEnvironment] = None) -> str:
        """Export configuration as JSON string."""
        try:
            env = environment or self.current_environment
            config = self.configs.get(env.value, {})
            
            export_data = {
                "environment": env.value,
                "exported_at": datetime.utcnow().isoformat(),
                "configuration": config
            }
            
            return json.dumps(export_data, indent=2, default=str)
            
        except Exception as e:
            self.logger.error(f"Error exporting config: {e}")
            return "{}"
    
    async def import_config(self, config_json: str, environment: Optional[ConfigEnvironment] = None) -> bool:
        """Import configuration from JSON string."""
        try:
            import_data = json.loads(config_json)
            config = import_data.get("configuration", {})
            
            env = environment or self.current_environment
            
            # Validate entire configuration
            validation_errors = []
            for key, value in self._flatten_dict(config).items():
                validation_result = await self._validate_config_change(key, value)
                if not validation_result.is_valid:
                    validation_errors.extend([f"{key}: {error}" for error in validation_result.errors])
            
            if validation_errors:
                self.logger.error(f"Config import validation failed: {validation_errors}")
                return False
            
            # Update configuration
            self.configs[env.value] = config
            
            # Save to file
            config_file = self.config_dir / f"config_{env.value}.json"
            await self._save_config_file(config_file, config)
            
            self.logger.info(f"Configuration imported successfully for {env.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing config: {e}")
            return False
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def get_config_history(self, limit: int = 50) -> List[Dict]:
        """Get recent configuration changes."""
        try:
            recent_changes = self.config_history[-limit:] if limit > 0 else self.config_history
            
            return [
                {
                    "timestamp": change.timestamp.isoformat(),
                    "environment": change.environment,
                    "section": change.section,
                    "key": change.key,
                    "old_value": change.old_value,
                    "new_value": change.new_value,
                    "user": change.user
                }
                for change in reversed(recent_changes)
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting config history: {e}")
            return []
    
    def get_config_summary(self) -> Dict:
        """Get configuration manager status summary."""
        try:
            return {
                "current_environment": self.current_environment.value,
                "hot_reload_enabled": self.hot_reload_enabled,
                "loaded_environments": list(self.configs.keys()),
                "config_files_monitored": len(self.file_watchers),
                "total_config_changes": len(self.config_history),
                "validation_rules_count": len(self.validation_rules),
                "config_directory": str(self.config_dir)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting config summary: {e}")
            return {"status": "error"}


# Global instance
config_manager = ConfigManager()