# backend/app/exchange_clients/__init__.py
"""
Exchange Clients Module Compatibility Layer

Provides backwards compatibility for exchange client access.
"""
import warnings
from backend.app.services.kucoin_futures_client import (
    KucoinFuturesClient as _NewKucoinFuturesClient,
    KucoinClientException as _NewKucoinClientException,
    KucoinAuthError as _NewKucoinAuthError,
    KucoinRequestError as _NewKucoinRequestError
)

class KucoinFuturesClient(_NewKucoinFuturesClient):
    """
    Compatibility wrapper for KucoinFuturesClient.
    
    DEPRECATED: This import path is deprecated.
    Use 'from app.services import KucoinFuturesClient' instead.
    """
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Importing KucoinFuturesClient from app.exchange_clients is deprecated. "
            "Use 'from app.services import KucoinFuturesClient' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)

# Exception compatibility wrappers
class KucoinClientException(_NewKucoinClientException):
    """DEPRECATED: Use app.services.KucoinClientException"""
    pass

class KucoinAuthError(_NewKucoinAuthError):
    """DEPRECATED: Use app.services.KucoinAuthError"""
    pass

class KucoinRequestError(_NewKucoinRequestError):
    """DEPRECATED: Use app.services.KucoinRequestError"""
    pass

__all__ = [
    'KucoinFuturesClient',
    'KucoinClientException',
    'KucoinAuthError', 
    'KucoinRequestError'
]
