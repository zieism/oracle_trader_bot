# app/dashboard/websocket.py
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from ..websocket.manager import websocket_manager, ClientType
from ..websocket.handlers import message_handler
from ..websocket.events import event_broadcaster

logger = logging.getLogger(__name__)

dashboard_websocket_router = APIRouter()


@dashboard_websocket_router.websocket("/ws/dashboard")
async def dashboard_websocket(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None, description="Optional client ID")
):
    """
    WebSocket endpoint for dashboard real-time communication.
    """
    try:
        # Connect the client
        assigned_client_id = await websocket_manager.connect(
            websocket, 
            ClientType.DASHBOARD, 
            client_id
        )
        
        # Auto-subscribe to relevant topics for dashboard
        dashboard_topics = [
            "trading",
            "bot_status", 
            "portfolio",
            "market_data",
            "notifications",
            "system"
        ]
        
        for topic in dashboard_topics:
            await websocket_manager.subscribe(assigned_client_id, topic)
        
        logger.info(f"Dashboard WebSocket client {assigned_client_id} connected and subscribed to topics")
        
        # Send initial data
        await websocket_manager.send_to_client(assigned_client_id, {
            "type": "dashboard_initialized",
            "subscriptions": dashboard_topics,
            "message": "Dashboard WebSocket connection established"
        })
        
        # Handle incoming messages
        await message_handler.handle_client_messages(websocket, assigned_client_id)
        
    except WebSocketDisconnect:
        logger.info(f"Dashboard WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in dashboard WebSocket: {e}")
        if 'assigned_client_id' in locals():
            await websocket_manager.disconnect(assigned_client_id)


@dashboard_websocket_router.websocket("/ws/trading")
async def trading_websocket(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None, description="Optional client ID")
):
    """
    WebSocket endpoint specifically for trading data.
    """
    try:
        # Connect the client as trader type
        assigned_client_id = await websocket_manager.connect(
            websocket,
            ClientType.TRADER,
            client_id
        )
        
        # Subscribe to trading-specific topics
        trading_topics = ["trading", "market_data", "portfolio"]
        
        for topic in trading_topics:
            await websocket_manager.subscribe(assigned_client_id, topic)
        
        logger.info(f"Trading WebSocket client {assigned_client_id} connected")
        
        # Send initial trading data
        await websocket_manager.send_to_client(assigned_client_id, {
            "type": "trading_connection_established",
            "subscriptions": trading_topics,
            "message": "Trading WebSocket connection established"
        })
        
        # Handle incoming messages
        await message_handler.handle_client_messages(websocket, assigned_client_id)
        
    except WebSocketDisconnect:
        logger.info(f"Trading WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in trading WebSocket: {e}")
        if 'assigned_client_id' in locals():
            await websocket_manager.disconnect(assigned_client_id)


@dashboard_websocket_router.websocket("/ws/monitor")
async def monitor_websocket(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None, description="Optional client ID")
):
    """
    WebSocket endpoint for system monitoring.
    """
    try:
        # Connect the client as monitor type
        assigned_client_id = await websocket_manager.connect(
            websocket,
            ClientType.MONITOR,
            client_id
        )
        
        # Subscribe to monitoring topics
        monitor_topics = ["system", "bot_status", "notifications"]
        
        for topic in monitor_topics:
            await websocket_manager.subscribe(assigned_client_id, topic)
        
        logger.info(f"Monitor WebSocket client {assigned_client_id} connected")
        
        # Send initial monitoring data
        await websocket_manager.send_to_client(assigned_client_id, {
            "type": "monitor_connection_established",
            "subscriptions": monitor_topics,
            "message": "Monitor WebSocket connection established"
        })
        
        # Start sending periodic system updates
        asyncio.create_task(send_periodic_system_updates(assigned_client_id))
        
        # Handle incoming messages
        await message_handler.handle_client_messages(websocket, assigned_client_id)
        
    except WebSocketDisconnect:
        logger.info(f"Monitor WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in monitor WebSocket: {e}")
        if 'assigned_client_id' in locals():
            await websocket_manager.disconnect(assigned_client_id)


async def send_periodic_system_updates(client_id: str):
    """
    Send periodic system updates to a monitor client.
    """
    try:
        while client_id in websocket_manager.connections:
            try:
                import psutil
                import time
                
                # Get system metrics
                system_data = {
                    "type": "system_update",
                    "timestamp": time.time(),
                    "cpu_usage": psutil.cpu_percent(interval=1),
                    "memory_usage": psutil.virtual_memory().percent,
                    "websocket_connections": len(websocket_manager.connections)
                }
                
                await websocket_manager.send_to_client(client_id, system_data)
                await asyncio.sleep(5)  # Send updates every 5 seconds
                
            except Exception as e:
                logger.error(f"Error sending system update to {client_id}: {e}")
                break
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in periodic system updates for {client_id}: {e}")


# Initialize WebSocket manager when module is imported
async def initialize_websocket_system():
    """Initialize the WebSocket system with event broadcaster."""
    event_broadcaster.set_websocket_manager(websocket_manager)
    await websocket_manager.start_background_tasks()
    logger.info("Dashboard WebSocket system initialized")


# This will be called from main.py during startup
async def startup_websocket_system():
    """Startup function for WebSocket system."""
    await initialize_websocket_system()


async def shutdown_websocket_system():
    """Shutdown function for WebSocket system."""
    await websocket_manager.stop_background_tasks()
    logger.info("Dashboard WebSocket system shutdown")