from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, Optional
# Ensure KucoinFuturesClient is imported from its correct location
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient
from app.db.lazy_session import get_db_session, get_db_status
import logging

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions with lite mode support.
    Raises 503 error only when DB is actually needed but unavailable.
    """
    async for session in get_db_session():
        if session is None:
            # DB is unavailable - check if this endpoint actually needs it
            db_status = get_db_status()
            if db_status["lite_mode"]:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database temporarily unavailable. Server running in lite mode."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database connection failed."
                )
        yield session


async def get_db_optional() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    Optional DB dependency that yields None if DB is unavailable.
    Use this for endpoints that can work without DB.
    """
    async for session in get_db_session():
        yield session

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
