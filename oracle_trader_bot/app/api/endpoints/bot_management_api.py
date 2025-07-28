# app/api/endpoints/bot_management_api.py
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Optional # <-- FIX: Imported Optional

from app.core import bot_process_manager # Import the manager

router = APIRouter()

@router.post("/start", summary="Start the Bot Engine")
async def start_bot() -> Dict[str, str]:
    success, message = bot_process_manager.start_bot_engine()
    if not success:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    return {"status": "success", "message": message}

@router.post("/stop", summary="Stop the Bot Engine")
async def stop_bot() -> Dict[str, str]:
    success, message = bot_process_manager.stop_bot_engine()
    if not success and "already stopped" not in message.lower() and "stale" not in message.lower(): # Don't error if already stopped
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
    return {"status": "success", "message": message}

@router.get("/status", summary="Get Bot Engine Status")
async def get_bot_status() -> Dict[str, Optional[str]]: # <-- FIX: Changed Dict[str, str] to allow None for values
    status_str, pid = bot_process_manager.get_bot_process_status()
    return {"status": status_str, "pid": str(pid) if pid else None}