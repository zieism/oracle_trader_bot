"""
Health check endpoints for monitoring app, database, and exchange status.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app.core.config import settings
from app.db.lazy_session import test_db_connection, get_db_status
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Base health response model."""
    ok: bool
    timestamp: str
    details: Dict[str, Any] = {}


class AppHealthResponse(HealthResponse):
    """Application health response."""
    mode: str
    version: str


class DatabaseHealthResponse(HealthResponse):
    """Database health response."""
    error: Optional[str] = None


class ExchangeHealthResponse(HealthResponse):
    """Exchange health response."""
    exchange: str
    markets_loaded: bool
    credentials_configured: bool
    error: Optional[str] = None


@router.get("/app", response_model=AppHealthResponse)
async def health_app():
    """
    Application health check.
    Always returns 200 OK with app status.
    """
    from datetime import datetime
    
    return AppHealthResponse(
        ok=True,
        timestamp=datetime.utcnow().isoformat() + "Z",
        mode=settings.APP_STARTUP_MODE,
        version=settings.VERSION,
        details={
            "project_name": settings.PROJECT_NAME,
            "debug": settings.DEBUG,
            "skip_db_init": settings.SKIP_DB_INIT
        }
    )


@router.get("/db", response_model=DatabaseHealthResponse)
async def health_db():
    """
    Database health check.
    Tests actual database connectivity with a lightweight query.
    """
    from datetime import datetime
    
    db_status = get_db_status()
    
    # If in lite mode and DB not checked, return appropriate status
    if db_status["lite_mode"] and not db_status["available"]:
        return DatabaseHealthResponse(
            ok=False,
            timestamp=datetime.utcnow().isoformat() + "Z",
            error="Database unavailable - running in lite mode",
            details=db_status
        )
    
    # Test actual connection
    success, error = await test_db_connection()
    
    return DatabaseHealthResponse(
        ok=success,
        timestamp=datetime.utcnow().isoformat() + "Z",
        error=error,
        details=db_status
    )


@router.get("/exchange", response_model=ExchangeHealthResponse)
async def health_exchange():
    """
    Exchange health check.
    Always returns 200 with status information: ok, sandbox, mode, reason.
    """
    from datetime import datetime
    
    try:
        # Create a test client to check status
        client = KucoinFuturesClient()
        
        # Get client status information
        status = client.get_client_status()
        
        # Try to test basic market functionality (works in both auth/no-auth modes)
        try:
            # Test basic market loading - this works without credentials
            await client._ensure_markets_loaded()
            markets_available = True
            error = None
        except Exception as e:
            markets_available = False
            error = f"Market data unavailable: {str(e)}"
            
        return ExchangeHealthResponse(
            ok=status['ok'],
            timestamp=datetime.utcnow().isoformat() + "Z",
            exchange="kucoinfutures",
            markets_loaded=markets_available,
            credentials_configured=status['ok'],
            error=error,
            details={
                "mode": status['mode'],
                "sandbox": status['sandbox'],
                "reason": status.get('reason'),
                "api_base_url": settings.KUCOIN_API_BASE_URL
            }
        )
        
    except Exception as e:
        logger.error(f"Exchange health check failed: {e}")
        return ExchangeHealthResponse(
            ok=False,
            timestamp=datetime.utcnow().isoformat() + "Z", 
            exchange="kucoinfutures",
            markets_loaded=False,
            credentials_configured=False,
            error=f"Health check failed: {str(e)}",
            details={
                "mode": "error",
                "sandbox": settings.is_sandbox(),
                "reason": "health_check_exception"
            }
        )


# Legacy health endpoint for backward compatibility
@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse)  
async def health_legacy():
    """
    Legacy health endpoint.
    Returns basic OK status for backward compatibility.
    """
    from datetime import datetime
    
    return HealthResponse(
        ok=True,
        timestamp=datetime.utcnow().isoformat() + "Z",
        details={
            "status": "healthy",
            "mode": settings.APP_STARTUP_MODE
        }
    )
