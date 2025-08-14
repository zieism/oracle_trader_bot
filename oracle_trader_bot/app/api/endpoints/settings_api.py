# app/api/endpoints/settings_api.py
"""
Settings API - Comprehensive system settings management

Provides endpoints for reading and updating all system settings with:
- Safe persistence in both lite (file) and full (DB) modes
- Secret masking on read
- Partial updates with secret preservation
- Automatic service re-initialization
"""

from fastapi import APIRouter, HTTPException, status, Request, Query, Response, Depends
from typing import Dict, Any
import logging

from app.schemas.settings import SettingsRead, SettingsUpdate
from app.crud.crud_settings import settings_manager
from app.utils.audit_logger import audit_logger
from app.security.admin_auth import admin_auth
from app.utils.rate_limiter import rate_limit
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/",
    response_model=SettingsRead,
    summary="Get System Settings",
    description="Retrieve all system settings with sensitive fields masked",
    tags=["Settings"]
)
async def get_settings(
    request: Request,
    response: Response,
    _: None = Depends(rate_limit(settings.SETTINGS_RATE_LIMIT, "settings"))
):
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
async def update_settings(
    settings_update: SettingsUpdate,
    request: Request,
    response: Response,
    _: None = Depends(rate_limit(settings.SETTINGS_RATE_LIMIT, "settings"))
):
    """
    Update system settings with partial update support.
    
    - Only provided fields are updated
    - Empty secret fields are ignored (existing values preserved)
    - Settings are persisted to file in lite mode
    - Dependent services are re-initialized automatically
    - All changes are logged to audit trail
    
    Requires admin token if ADMIN_API_TOKEN environment variable is set.
    """
    try:
        # Check admin authentication if enabled
        admin_auth.verify_admin_token(request)
        
        updated_settings = await settings_manager.update_settings(settings_update, request)
        logger.info("Settings updated successfully")
        return updated_settings
    except HTTPException:
        # Re-raise HTTP exceptions (like 401) as-is
        raise
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )

@router.get(
    "/audit",
    response_model=Dict[str, Any],
    summary="Get Settings Audit Log",
    description="Retrieve paginated audit log of settings changes with redacted sensitive values",
    tags=["Settings"]
)
async def get_settings_audit(
    request: Request,
    response: Response,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of entries per page"),
    _: None = Depends(rate_limit(settings.SETTINGS_RATE_LIMIT, "settings"))
):
    """
    Retrieve paginated audit log of settings changes.
    
    Returns audit entries with:
    - Timestamp of change
    - Actor information (IP, User-Agent if available)
    - Field changes with redacted sensitive values
    - Pagination metadata
    
    Requires admin token if ADMIN_API_TOKEN environment variable is set.
    TODO: Add authentication/authorization when user system is implemented
    """
    try:
        # Check admin authentication if enabled
        admin_auth.verify_admin_token(request)
        
        audit_data = audit_logger.get_audit_entries(page=page, page_size=page_size)
        return audit_data
    except HTTPException:
        # Re-raise HTTP exceptions (like 401) as-is
        raise
    except Exception as e:
        logger.error(f"Error retrieving audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log"
        )

@router.post(
    "/reset",
    response_model=Dict[str, str],
    summary="Reset Settings to Defaults",
    description="Reset all settings to their default values",
    tags=["Settings"]
)
async def reset_settings(
    request: Request,
    response: Response,
    _: None = Depends(rate_limit(settings.SETTINGS_RATE_LIMIT, "settings"))
):
    """
    Reset all settings to their default values.
    This will remove any custom configuration and restore defaults.
    
    Requires admin token if ADMIN_API_TOKEN environment variable is set.
    """
    try:
        # Check admin authentication if enabled
        admin_auth.verify_admin_token(request)
        
        # In lite mode, delete the settings file
        import os
        from app.core.config import settings
        
        if settings.APP_STARTUP_MODE == "lite":
            settings_file = settings_manager.settings_file
            if settings_file.exists():
                os.remove(settings_file)
                logger.info("Settings file deleted, defaults will be used")
        
        return {"status": "success", "message": "Settings reset to defaults"}
    except HTTPException:
        # Re-raise HTTP exceptions (like 401) as-is
        raise
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset settings"
        )
