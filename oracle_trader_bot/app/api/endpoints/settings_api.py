# app/api/endpoints/settings_api.py
"""
Settings API - Comprehensive system settings management

Provides endpoints for reading and updating all system settings with:
- Safe persistence in both lite (file) and full (DB) modes
- Secret masking on read
- Partial updates with secret preservation
- Automatic service re-initialization
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import logging

from app.schemas.settings import SettingsRead, SettingsUpdate
from app.crud.crud_settings import settings_manager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/",
    response_model=SettingsRead,
    summary="Get System Settings",
    description="Retrieve all system settings with sensitive fields masked",
    tags=["Settings"]
)
async def get_settings():
    """
    Retrieve current system settings.
    Sensitive fields (API keys, passwords) are masked with '***'.
    """
    try:
        return await settings_manager.get_settings()
    except Exception as e:
        logger.error(f"Error retrieving settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve settings"
        )

@router.put(
    "/",
    response_model=SettingsRead,
    summary="Update System Settings",
    description="Update system settings. Only non-null fields are updated. Empty secrets are ignored.",
    tags=["Settings"]
)
async def update_settings(settings_update: SettingsUpdate):
    """
    Update system settings with partial update support.
    
    - Only provided fields are updated
    - Empty secret fields are ignored (existing values preserved)
    - Settings are persisted to file in lite mode
    - Dependent services are re-initialized automatically
    """
    try:
        updated_settings = await settings_manager.update_settings(settings_update)
        logger.info("Settings updated successfully")
        return updated_settings
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )

@router.post(
    "/reset",
    response_model=Dict[str, str],
    summary="Reset Settings to Defaults",
    description="Reset all settings to their default values",
    tags=["Settings"]
)
async def reset_settings():
    """
    Reset all settings to their default values.
    This will remove any custom configuration and restore defaults.
    """
    try:
        # In lite mode, delete the settings file
        import os
        from app.core.config import settings
        
        if settings.APP_STARTUP_MODE == "lite":
            settings_file = settings_manager.settings_file
            if settings_file.exists():
                os.remove(settings_file)
                logger.info("Settings file deleted, defaults will be used")
        
        return {"status": "success", "message": "Settings reset to defaults"}
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset settings"
        )
