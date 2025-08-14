# backend/app/analysis/__init__.py
"""
Analysis Module Compatibility Layer

Provides backwards compatibility for market regime analysis.
"""
import warnings
from backend.app.services.market_regime_service import determine_market_regime as _new_determine_market_regime

def determine_market_regime(*args, **kwargs):
    """
    Compatibility wrapper for determine_market_regime function.
    
    DEPRECATED: This import path is deprecated. 
    Use 'from app.services.market_regime_service import determine_market_regime' instead.
    """
    warnings.warn(
        "Importing determine_market_regime from app.analysis.market_regime is deprecated. "
        "Use 'from app.services.market_regime_service import determine_market_regime' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _new_determine_market_regime(*args, **kwargs)

__all__ = ['determine_market_regime']
