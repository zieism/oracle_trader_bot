# backend/app/strategies/__init__.py
"""
Trading Strategies Module

Professional trading strategy implementations for different market conditions.
"""

from .trend_following_strategy import generate_trend_signal
from .range_trading_strategy import generate_range_signal

__all__ = [
    'generate_trend_signal',
    'generate_range_signal',
]
