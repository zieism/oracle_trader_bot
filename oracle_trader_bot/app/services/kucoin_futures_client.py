"""
Compatibility shim for kucoin_futures_client.

The KuCoin Futures client has been moved from app.exchange_clients to app.services
for better service organization.
"""

import warnings
from app.exchange_clients.kucoin_futures_client import *

warnings.warn(
    "Importing KucoinFuturesClient from app.services is deprecated. "
    "The client is still available from app.exchange_clients.kucoin_futures_client. "
    "This shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)
