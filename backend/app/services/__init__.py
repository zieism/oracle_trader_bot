# backend/app/services/__init__.py
"""
Services Module

Professional trading services including exchange clients, position monitoring,
and market regime analysis.
"""

from .kucoin_futures_client import KucoinFuturesClient, KucoinClientException, KucoinAuthError, KucoinRequestError
from .position_monitor import (
    check_tp_sl_conditions,
    close_position_at_market, 
    monitor_open_positions
)
from .market_regime_service import determine_market_regime

__all__ = [
    # Exchange Client
    'KucoinFuturesClient',
    'KucoinClientException', 
    'KucoinAuthError',
    'KucoinRequestError',
    
    # Position Monitoring
    'check_tp_sl_conditions',
    'close_position_at_market',
    'monitor_open_positions',
    
    # Market Regime Analysis
    'determine_market_regime',
]
