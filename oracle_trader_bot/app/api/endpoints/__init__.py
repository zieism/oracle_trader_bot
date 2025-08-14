"""
DEPRECATED: API endpoints are being reorganized into domain-based routers.

This shim maintains backward compatibility while endpoints are consolidated:

OLD STRUCTURE:
- app.api.endpoints.bot_settings_api
- app.api.endpoints.bot_management_api
- app.api.endpoints.trading
- app.api.endpoints.order_management
- etc.

NEW STRUCTURE (domain-based):
- backend.app.api.routers.settings (bot settings + management)
- backend.app.api.routers.trading (trading + orders + trades)
- backend.app.api.routers.analysis (signals + analysis logs)
- backend.app.api.routers.exchange (exchange info + market data)
- backend.app.api.routers.logs (server logs)
- backend.app.api.routers.ui (FastUI components)
"""

import warnings
import sys

def _show_endpoints_deprecation_warning(old_endpoint: str, new_router: str):
    """Show deprecation warning for moved endpoints."""
    warnings.warn(
        f"Importing from 'app.api.endpoints.{old_endpoint}' is deprecated. "
        f"This functionality has moved to 'backend.app.api.routers.{new_router}'. "
        f"Please update your imports accordingly.",
        DeprecationWarning,
        stacklevel=3
    )

# Mapping of old endpoints to new routers
_ENDPOINT_TO_ROUTER_MAPPING = {
    'bot_settings_api': 'settings',
    'bot_management_api': 'settings', 
    'analysis_logs_websocket': 'analysis',
    'strategy_signals': 'analysis',
    'trading': 'trading',
    'order_management': 'trading',
    'trades': 'trading',
    'exchange_info': 'exchange',
    'market_data': 'exchange',
    'server_logs_api': 'logs',
    'frontend_fastui': 'ui',
}

class EndpointsCompatibilityShim:
    """
    Compatibility shim for api.endpoints module.
    """
    
    def __getattr__(self, name: str):
        new_router = _ENDPOINT_TO_ROUTER_MAPPING.get(name)
        
        if new_router:
            _show_endpoints_deprecation_warning(name, new_router)
            
            try:
                # Try to import from new router location
                full_new_path = f'backend.app.api.routers.{new_router}'
                module = __import__(full_new_path, fromlist=[new_router])
                return module
            except ImportError:
                # Fall back to original location
                pass
        
        # Fall back to current location (will work until files are actually moved)
        try:
            current_path = f'oracle_trader_bot.app.api.endpoints.{name}'
            module = __import__(current_path, fromlist=[name])
            return module
        except ImportError:
            raise ImportError(f"Cannot import endpoint '{name}' from api.endpoints")

# Replace this module with the shim
sys.modules[__name__] = EndpointsCompatibilityShim()
