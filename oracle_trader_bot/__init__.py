"""
DEPRECATED: This module structure is being refactored.

This shim maintains backward compatibility for existing imports while the codebase
is being reorganized. All functionality is being moved to the 'backend' package.

Import warnings will guide developers to use the new import paths.

Deprecated: oracle_trader_bot.app.*
New: backend.app.*
"""

import warnings
import sys
from pathlib import Path

def _show_deprecation_warning(old_path: str, new_path: str):
    """Show a deprecation warning for moved modules."""
    warnings.warn(
        f"Importing from '{old_path}' is deprecated and will be removed in a future version. "
        f"Please update your imports to use '{new_path}' instead.",
        DeprecationWarning,
        stacklevel=3
    )

# This will be populated as modules are moved
_IMPORT_MAPPING = {
    # Will be filled as we move modules
    # 'oracle_trader_bot.app.core.config': 'backend.app.core.config',
    # 'oracle_trader_bot.app.api.endpoints': 'backend.app.api.routers',
    # etc.
}

class CompatibilityShim:
    """
    Import compatibility shim that redirects old imports to new locations.
    """
    
    def __init__(self, old_prefix: str, new_prefix: str):
        self.old_prefix = old_prefix
        self.new_prefix = new_prefix
        
    def __getattr__(self, name: str):
        old_path = f"{self.old_prefix}.{name}"
        new_path = f"{self.new_prefix}.{name}"
        
        _show_deprecation_warning(old_path, new_path)
        
        try:
            # Try to import from new location
            parts = new_path.split('.')
            module = __import__(new_path, fromlist=[parts[-1]])
            return getattr(module, parts[-1]) if hasattr(module, parts[-1]) else module
        except ImportError:
            # Fall back to original location if new location doesn't exist yet
            try:
                original_path = old_path.replace('oracle_trader_bot.', '')
                module = __import__(original_path, fromlist=[name])
                return getattr(module, name) if hasattr(module, name) else module
            except ImportError:
                raise ImportError(f"Cannot import '{name}' from either '{old_path}' or '{new_path}'")

# Create app shim
app = CompatibilityShim('oracle_trader_bot.app', 'backend.app')
