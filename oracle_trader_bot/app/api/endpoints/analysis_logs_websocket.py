# app/api/endpoints/analysis_logs_websocket.py
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional # ADDED: Import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, Request
from pydantic import BaseModel 

router = APIRouter()

logger = logging.getLogger(__name__)

# This is a global list to keep track of active WebSocket connections
# In a real-world production app, consider using a more robust pub-sub system (e.g., Redis Pub/Sub)
# for scalability across multiple worker processes.
active_connections: List[WebSocket] = []

# Pydantic model for incoming analysis log entries from bot_engine
class AnalysisLogEntry(BaseModel):
    timestamp: str
    level: str
    symbol: str
    strategy: str
    message: str
    decision: str
    details: Optional[Dict[str, Any]] = None # Optional field for additional details

async def broadcast_analysis_log(log_entry: Dict[str, Any]):
    """
    Broadcasts a new analysis log entry to all active WebSocket clients.
    """
    disconnected_connections = []
    for connection in active_connections:
        try:
            await connection.send_text(json.dumps(log_entry))
        except WebSocketDisconnect:
            logger.warning(f"WebSocket client disconnected during broadcast.")
            disconnected_connections.append(connection)
        except Exception as e:
            logger.error(f"Error broadcasting analysis log to WebSocket client: {e}", exc_info=True)
            disconnected_connections.append(connection)
    
    # Remove disconnected clients
    for connection in disconnected_connections:
        if connection in active_connections:
            active_connections.remove(connection)
    
    if disconnected_connections:
        logger.info(f"Removed {len(disconnected_connections)} disconnected WebSocket clients. Remaining: {len(active_connections)}")


@router.websocket("/ws/analysis-logs")
async def websocket_analysis_logs(websocket: WebSocket):
    """
    WebSocket endpoint for real-time analysis logs.
    Clients connect here to receive live updates from the bot engine.
    """
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"New WebSocket connection established for analysis logs. Total active: {len(active_connections)}")
    
    try:
        while True:
            await asyncio.sleep(60) 
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from analysis logs.")
    except Exception as e:
        logger.error(f"WebSocket error for analysis logs: {e}", exc_info=True)
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
            logger.info(f"WebSocket connection closed for analysis logs. Total active: {len(active_connections)}")

@router.post("/analysis-logs/internal-publish", status_code=status.HTTP_202_ACCEPTED)
async def internal_publish_analysis_log(
    log_entry: AnalysisLogEntry, 
    request: Request 
):
    """
    Internal API endpoint for bot_engine to publish analysis logs.
    These logs are then broadcasted to active WebSocket clients.
    Only accepts POST requests from trusted internal sources (e.g., localhost).
    """
    client_host = request.client.host
    if client_host != "127.0.0.1" and client_host != "localhost":
        logger.warning(f"Rejected internal-publish request from untrusted host: {client_host}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Internal endpoint.")

    logger.info(f"Received analysis log from bot_engine: {log_entry.message}")
    await broadcast_analysis_log(log_entry.model_dump())

    return {"status": "success", "message": "Log received and broadcasted."}