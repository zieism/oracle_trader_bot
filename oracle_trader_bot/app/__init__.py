"""
DEPRECATED: App module structure is being refactored.

This shim maintains backward compatibility for app-level imports.
All modules under 'app' are being reorganized and moved to 'backend.app'.

Examples of deprecated imports that will be redirected:
- from app.core.config import settings → from backend.app.core.config import settings
- from app.api.endpoints import trades → from backend.app.api.routers import trading
- from app.models.trade import Trade → from backend.app.models.trade import Trade
"""

import warnings
import sys
from pathlib import Path

def _show_app_deprecation_warning(old_path: str, new_path: str):
    """Show a deprecation warning for moved app modules."""
    warnings.warn(
        f"Importing from 'app.{old_path}' is deprecated. "
        f"Please update to 'backend.app.{new_path}' instead.",
        DeprecationWarning,
        stacklevel=3
    )

# Mapping of old app paths to new backend paths
_APP_IMPORT_MAPPING = {
    # Core modules
    'core.config': 'core.config',
    'core.bot_process_manager': 'services.bot_manager',
    
    # API endpoints → routers (will be updated as we merge)
    'api.endpoints.bot_settings_api': 'api.routers.settings',
    'api.endpoints.bot_management_api': 'api.routers.settings',
    'api.endpoints.analysis_logs_websocket': 'api.routers.analysis',
    'api.endpoints.strategy_signals': 'api.routers.analysis',
    'api.endpoints.trading': 'api.routers.trading',
    'api.endpoints.order_management': 'api.routers.trading',
    'api.endpoints.trades': 'api.routers.trading',
    'api.endpoints.exchange_info': 'api.routers.exchange',
    'api.endpoints.market_data': 'api.routers.exchange',
    'api.endpoints.server_logs_api': 'api.routers.logs',
    'api.endpoints.frontend_fastui': 'api.routers.ui',
    'api.dependencies': 'api.dependencies',
    
    # Services
    'services.position_monitor': 'services.position_service',
    'exchange_clients.kucoin_futures_client': 'exchange.kucoin',
    
    # Strategies
    'strategies.trend_following_strategy': 'strategies.trend_following',
    'strategies.range_trading_strategy': 'strategies.range_trading',
    
    # Indicators
    'indicators.technical_indicators': 'indicators.technical',
    
    # Analysis
    'analysis.market_regime': 'analysis.market_regime',
    
    # Data layer (unchanged)
    'db': 'db',
    'models': 'models', 
    'schemas': 'schemas',
    'crud': 'crud',
}

class AppCompatibilityShim:
    """
    App-level compatibility shim for redirecting imports.
    """
    
    def __getattr__(self, name: str):
        # Check if this is a direct module import
        if name in ['core', 'api', 'services', 'exchange_clients', 'strategies', 
                   'indicators', 'analysis', 'db', 'models', 'schemas', 'crud']:
            return AppModuleShim(name)
        
        # Handle direct imports
        old_path = name
        new_path = _APP_IMPORT_MAPPING.get(name, name)
        
        _show_app_deprecation_warning(old_path, new_path)
        
        try:
            # Try to import from new backend location
            full_new_path = f'backend.app.{new_path}'
            module = __import__(full_new_path, fromlist=[new_path.split('.')[-1]])
            return module
        except ImportError:
            # Fall back to current location
            try:
                current_location = f'oracle_trader_bot.app.{name}'
                module = __import__(current_location, fromlist=[name.split('.')[-1]])
                return module
            except ImportError:
                raise ImportError(f"Cannot import '{name}' from app module")

class AppModuleShim:
    """
    Shim for app submodules (e.g., app.core, app.api, etc.)
    """
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        
    def __getattr__(self, name: str):
        full_old_path = f'{self.module_name}.{name}'
        new_path = _APP_IMPORT_MAPPING.get(full_old_path, full_old_path)
        
        _show_app_deprecation_warning(full_old_path, new_path)
        
        try:
            # Try new location
            full_new_path = f'backend.app.{new_path}'
            module = __import__(full_new_path, fromlist=[new_path.split('.')[-1]])
            return module
        except ImportError:
            # Fall back to current location
            try:
                current_path = f'oracle_trader_bot.app.{full_old_path}'
                module = __import__(current_path, fromlist=[name])
                return module
            except ImportError:
                raise ImportError(f"Cannot import '{name}' from app.{self.module_name}")

# Create the main app compatibility interface
sys.modules[__name__] = AppCompatibilityShim()
