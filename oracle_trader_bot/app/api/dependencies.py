from fastapi import Request, HTTPException, status
# Ensure KucoinFuturesClient is imported from its correct location
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient

async def get_kucoin_client(request: Request) -> KucoinFuturesClient:
    """
    FastAPI dependency to get the KucoinFuturesClient instance from app.state.
    """
    if not hasattr(request.app.state, 'kucoin_client') or \
       request.app.state.kucoin_client is None:
        # This should ideally not happen if the lifespan event initializes it correctly.
        # Log this critical failure.
        # logger.error("Critical: Kucoin client not found in application state!") # You'd need to set up logging here or pass logger
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, # Or 500
            detail="Kucoin client not initialized in application state. Please check server logs."
        )
    return request.app.state.kucoin_client
