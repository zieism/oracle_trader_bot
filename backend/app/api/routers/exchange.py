# backend/app/api/routers/exchange.py
"""
Exchange Router - Exchange Info & Account Management

Provides exchange connectivity health checks, symbol information, account data, and market info.
Handles KuCoin Futures exchange integration and validation.

Routes:
- GET /api/v1/exchange/health - Check exchange connection and API health
- GET /api/v1/exchange/symbols - Get all available trading symbols  
- GET /api/v1/exchange/kucoin/time - Get KuCoin server time with sync info
- GET /api/v1/exchange/kucoin/contracts - Get active futures contracts
- GET /api/v1/exchange/kucoin/account-overview - Get account balance and overview
"""

import time
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, List, Any

from app.api.dependencies import get_kucoin_client
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get(
    "/health", # Full path: /api/v1/exchange/health
    response_model=Dict[str, Any],
    summary="Exchange Health Check",
    tags=["Exchange"]
)
async def get_exchange_health(
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Check the health of the exchange connection and API credentials.
    
    Tests basic connectivity to KuCoin Futures and validates API credentials if configured.
    Returns server time synchronization info and API credential status.
    """
    try:
        # Test basic connectivity
        time_data = await kucoin_client.get_server_time()
        if time_data is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cannot connect to KuCoin exchange"
            )
        
        # Test API credentials if configured
        api_status = "not_configured"
        if all([settings.KUCOIN_API_KEY, settings.KUCOIN_API_SECRET, settings.KUCOIN_API_PASSPHRASE]):
            try:
                account_data = await kucoin_client.get_account_overview()
                api_status = "configured_and_working" if account_data else "configured_but_failing"
            except Exception:
                api_status = "configured_but_failing"
        
        return {
            "status": "healthy",
            "message": "Exchange connection is operational",
            "server_time_ms": time_data.get("kucoin_server_time_ms"),
            "local_time_ms": time_data.get("local_server_time_ms"),
            "time_difference_ms": time_data.get("time_difference_ms"),
            "api_credentials_status": api_status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Exchange health check failed: {str(e)}"
        )

@router.get(
    "/symbols", # Full path: /api/v1/exchange/symbols
    response_model=Dict[str, Any],
    summary="Get Available Trading Symbols",
    tags=["Exchange"]
)
async def get_exchange_symbols(
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Get all available trading symbols from the exchange.
    
    Returns a list of all active futures contracts available for trading on KuCoin.
    Useful for symbol validation and trading pair discovery.
    """
    try:
        contracts = await kucoin_client.get_active_contracts()
        if contracts is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not fetch symbols from KuCoin."
            )
        
        symbols = [contract.get('symbol', '') for contract in contracts if contract.get('symbol')]
        
        return {
            "symbols": symbols,
            "count": len(symbols)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch exchange symbols: {str(e)}"
        )

@router.get(
    "/kucoin/time", # Full path: /api/v1/exchange/kucoin/time
    response_model=Dict[str, Any],
    summary="Get KuCoin Server Time",
    tags=["Exchange", "KuCoin"]
)
async def get_kucoin_server_time_endpoint(
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Fetches the current server time from KuCoin Futures API.
    Also returns local server time and the time difference for synchronization monitoring.
    
    Important for ensuring API requests are properly timestamped and within acceptable time windows.
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

@router.get(
    "/kucoin/contracts", # Full path: /api/v1/exchange/kucoin/contracts
    response_model=List[Dict[str, Any]],
    summary="Get Active Futures Contracts",
    tags=["Exchange", "KuCoin"]
)
async def get_kucoin_active_contracts(
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Fetches the list of active tradable futures contracts from KuCoin.
    
    Returns detailed information about each contract including:
    - Symbol, base/quote currencies
    - Contract specifications (size, tick size, etc.)
    - Trading status and availability
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

@router.get(
    "/kucoin/account-overview", # Full path: /api/v1/exchange/kucoin/account-overview
    response_model=Dict[str, Any],
    summary="Get Account Balance Overview",
    tags=["Exchange", "KuCoin", "Account"]
)
async def get_kucoin_account_summary(
    currency: Optional[str] = Query("USDT", description="Currency for account overview (default: USDT)"),
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Fetches the futures account overview from KuCoin for the specified currency.
    
    **Requires valid API credentials with appropriate permissions.**
    
    Returns account balance information including:
    - Available balance for trading
    - Total equity and margin details
    - Position-related balance information
    
    - **currency**: Base currency for balance display (default: USDT)
    """
    try:
        # Ensure API keys are actually set before calling an authenticated endpoint
        if not all([settings.KUCOIN_API_KEY, settings.KUCOIN_API_SECRET, settings.KUCOIN_API_PASSPHRASE]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
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
        elif isinstance(e, HTTPException):  # Re-raise HTTPExceptions we've thrown
            raise e
        else:  # Other unexpected server errors
            logger.error(f"Unexpected error in /kucoin/account-overview: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected server error occurred: {str(e)}"
            )
