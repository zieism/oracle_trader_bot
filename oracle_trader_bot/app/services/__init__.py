"""
DEPRECATED: Services are being reorganized and renamed.

This shim maintains backward compatibility for service imports.

OLD STRUCTURE:
- app.services.position_monitor
- app.core.bot_process_manager (moved to services)

NEW STRUCTURE:
- backend.app.services.position_service
- backend.app.services.bot_manager
"""

import warnings
import sys

def _show_services_deprecation_warning(old_service: str, new_service: str):
    """Show deprecation warning for moved services."""
    warnings.warn(
        f"Importing from 'app.services.{old_service}' is deprecated. "
        f"This functionality has moved to 'backend.app.services.{new_service}'. "
        f"Please update your imports accordingly.",
        DeprecationWarning,
        stacklevel=3
    )

# Mapping of old services to new services
_SERVICE_MAPPING = {
    'position_monitor': 'position_service',
}

class ServicesCompatibilityShim:
    """
    Compatibility shim for services module.
    """
    
    def __getattr__(self, name: str):
        new_service = _SERVICE_MAPPING.get(name, name)
        
        _show_services_deprecation_warning(name, new_service)
        
        try:
            # Try to import from new services location
            full_new_path = f'backend.app.services.{new_service}'
            module = __import__(full_new_path, fromlist=[new_service])
            return module
        except ImportError:
            # Fall back to original location
            try:
                current_path = f'oracle_trader_bot.app.services.{name}'
                module = __import__(current_path, fromlist=[name])
                return module
            except ImportError:
                raise ImportError(f"Cannot import service '{name}' from app.services")

# Replace this module with the shim
sys.modules[__name__] = ServicesCompatibilityShim()
