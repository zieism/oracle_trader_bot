"""
Compatibility shim for market_regime_service.

The market regime analysis has been moved from app.analysis.market_regime
to app.services.market_regime_service for better service organization.
"""

import warnings
from app.analysis.market_regime import *

warnings.warn(
    "Importing market regime functions from app.services.market_regime_service is deprecated. "
    "The functions are still available from app.analysis.market_regime. "
    "This shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)
