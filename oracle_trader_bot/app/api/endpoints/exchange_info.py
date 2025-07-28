from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, Dict, List, Any 
import time

from app.api.dependencies import get_kucoin_client
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient
from app.core.config import settings # <--- ??? ?? ????? ??? ???

router = APIRouter()

@router.get("/kucoin/time", response_model=Dict[str, Any])
async def get_kucoin_server_time_endpoint(
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Fetches the current server time from KuCoin Futures API.
    Also returns local server time and the difference.
    """
    try:
        time_data = await kucoin_client.get_server_time()
        if time_data is None or "server_time_ms" not in time_data:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not fetch server time from KuCoin or response was malformed."
            )
        
        local_time_ms = int(time.time() * 1000)
        return {
            "kucoin_server_time_ms": time_data["server_time_ms"],
            "local_server_time_ms": local_time_ms,
            "time_difference_ms": local_time_ms - time_data["server_time_ms"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching KuCoin server time: {str(e)}"
        )

@router.get("/kucoin/contracts", response_model=List[Dict[str, Any]])
async def get_kucoin_active_contracts(
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Fetches the list of active tradable futures contracts from KuCoin.
    """
    try:
        contracts = await kucoin_client.get_active_contracts()
        if contracts is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not fetch active contracts from KuCoin."
            )
        return contracts
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching active contracts: {str(e)}"
        )

@router.get("/kucoin/account-overview", response_model=Dict[str, Any])
async def get_kucoin_account_summary(
    currency: Optional[str] = "USDT",
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Fetches the futures account overview from KuCoin for the specified currency.
    Requires API key with appropriate permissions.
    """
    try:
        # Ensure API keys are actually set before calling an authenticated endpoint
        if not all([settings.KUCOIN_API_KEY, settings.KUCOIN_API_SECRET, settings.KUCOIN_API_PASSPHRASE]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, # Unauthorized
                detail="KuCoin API credentials are not configured in the bot settings."
            )
            
        overview = await kucoin_client.get_account_overview(currency=currency)
        if overview is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not fetch account overview from KuCoin for currency {currency}."
            )
        return overview
    except Exception as e:
        if "KuCoin API Error" in str(e):
             # Specific error from KuCoin client (e.g., bad signature, insufficient perms)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) 
        elif isinstance(e, HTTPException): # Re-raise HTTPExceptions we've thrown
            raise e
        else: # Other unexpected server errors
            # You might want to log the original error 'e' here for debugging
            # logger.error(f"Unexpected error in /kucoin/account-overview: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected server error occurred: {str(e)}"
            )