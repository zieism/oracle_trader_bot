# backend/app/api/routers/settings.py
"""
Settings Router - Bot Settings & Management

Combines bot configuration settings and lifecycle management into a single domain.
Handles bot settings CRUD operations and bot engine start/stop/status management.

Routes:
- GET /api/v1/bot-settings/ - Get current bot settings
- PUT /api/v1/bot-settings/ - Update bot settings  
- POST /api/v1/bot-management/start - Start bot engine
- POST /api/v1/bot-management/stop - Stop bot engine
- GET /api/v1/bot-management/status - Get bot engine status
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict

from app.db.session import get_db_session
from app.schemas.bot_settings import BotSettings as BotSettingsSchema, BotSettingsUpdate
from app.crud import crud_bot_settings
from app.models.bot_settings import BotSettings as BotSettingsModel # For type hinting if needed
from app.core import bot_process_manager # Import the manager

router = APIRouter()

# ============================================================================
# BOT SETTINGS ENDPOINTS
# ============================================================================

@router.get(
    "/bot-settings/", # Full path: /api/v1/bot-settings/
    response_model=BotSettingsSchema,
    summary="Get Current Bot Settings",
    tags=["Bot Settings"]
)
async def read_bot_settings(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the current bot operational settings.
    If no settings exist, default settings will be created and returned.
    """
    db_settings = await crud_bot_settings.get_bot_settings(db=db)
    if db_settings is None:
        # This case should ideally be handled by get_bot_settings creating defaults
        # But if it can still return None (e.g., DB error during creation of defaults)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot settings not found and could not be created with defaults."
        )
    return db_settings

@router.put(
    "/bot-settings/", # Full path: /api/v1/bot-settings/
    response_model=BotSettingsSchema,
    summary="Update Bot Settings",
    tags=["Bot Settings"]
)
async def update_bot_settings_endpoint( # Renamed for clarity
    settings_in: BotSettingsUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update the bot operational settings.
    Only provided fields will be updated.
    """
    updated_settings = await crud_bot_settings.update_bot_settings(
        db=db, settings_update=settings_in
    )
    if updated_settings is None:
        # This could happen if get_bot_settings within update_bot_settings failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bot settings."
        )
    return updated_settings

# ============================================================================
# BOT MANAGEMENT ENDPOINTS
# ============================================================================

@router.post(
    "/bot-management/start", # Full path: /api/v1/bot-management/start
    summary="Start the Bot Engine",
    tags=["Bot Management"]
)
async def start_bot() -> Dict[str, str]:
    """Start the automated trading bot engine."""
    success, message = bot_process_manager.start_bot_engine()
    if not success:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    return {"status": "success", "message": message}

@router.post(
    "/bot-management/stop", # Full path: /api/v1/bot-management/stop
    summary="Stop the Bot Engine",
    tags=["Bot Management"]
)
async def stop_bot() -> Dict[str, str]:
    """Stop the automated trading bot engine."""
    success, message = bot_process_manager.stop_bot_engine()
    if not success and "already stopped" not in message.lower() and "stale" not in message.lower(): # Don't error if already stopped
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
    return {"status": "success", "message": message}

@router.get(
    "/bot-management/status", # Full path: /api/v1/bot-management/status
    summary="Get Bot Engine Status",
    tags=["Bot Management"]
)
async def get_bot_status() -> Dict[str, Optional[str]]:
    """Get the current status of the bot engine (running, stopped, etc.)."""
    status_str, pid = bot_process_manager.get_bot_process_status()
    return {"status": status_str, "pid": str(pid) if pid else None}
