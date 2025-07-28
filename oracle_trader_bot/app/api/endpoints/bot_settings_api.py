# app/api/endpoints/bot_settings_api.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional # Optional might not be needed here if response is always BotSettings

from app.db.session import get_db_session
from app.schemas.bot_settings import BotSettings as BotSettingsSchema, BotSettingsUpdate
from app.crud import crud_bot_settings
from app.models.bot_settings import BotSettings as BotSettingsModel # For type hinting if needed

router = APIRouter()

@router.get(
    "/", # Endpoint will be /api/v1/bot-settings/
    response_model=BotSettingsSchema,
    summary="Get Current Bot Settings"
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
    "/", # Endpoint will be /api/v1/bot-settings/
    response_model=BotSettingsSchema,
    summary="Update Bot Settings"
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