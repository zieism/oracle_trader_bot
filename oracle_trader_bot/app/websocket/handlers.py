# app/websocket/handlers.py
import json
import logging
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from .manager import websocket_manager, ClientType
from .events import event_broadcaster

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles incoming WebSocket messages from clients."""
    
    def __init__(self):
        self.message_handlers = {
            "subscribe": self._handle_subscribe,
            "unsubscribe": self._handle_unsubscribe,
            "ping": self._handle_ping,
            "pong": self._handle_pong,
            "get_status": self._handle_get_status,
            "get_events": self._handle_get_events,
            "trading_command": self._handle_trading_command,
        }
    
    async def handle_client_messages(self, websocket: WebSocket, client_id: str):
        """
        Handle incoming messages from a WebSocket client.
        
        Args:
            websocket: The WebSocket connection
            client_id: The client ID
        """
        try:
            while True:
                # Wait for message from client
                message = await websocket.receive_text()
                
                try:
                    data = json.loads(message)
                    await self._process_message(client_id, data)
                except json.JSONDecodeError:
                    await self._send_error(client_id, "Invalid JSON format")
                except Exception as e:
                    logger.error(f"Error processing message from {client_id}: {e}")
                    await self._send_error(client_id, f"Error processing message: {str(e)}")
                    
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected")
            await websocket_manager.disconnect(client_id)
        except Exception as e:
            logger.error(f"Error in message handler for {client_id}: {e}")
            await websocket_manager.disconnect(client_id)
    
    async def _process_message(self, client_id: str, data: Dict[str, Any]):
        """
        Process a message from a client.
        
        Args:
            client_id: The client ID
            data: The message data
        """
        message_type = data.get("type")
        
        if not message_type:
            await self._send_error(client_id, "Message type is required")
            return
        
        if message_type not in self.message_handlers:
            await self._send_error(client_id, f"Unknown message type: {message_type}")
            return
        
        handler = self.message_handlers[message_type]
        await handler(client_id, data)
    
    async def _handle_subscribe(self, client_id: str, data: Dict[str, Any]):
        """Handle subscription request."""
        topic = data.get("topic")
        
        if not topic:
            await self._send_error(client_id, "Topic is required for subscription")
            return
        
        success = await websocket_manager.subscribe(client_id, topic)
        
        if success:
            await websocket_manager.send_to_client(client_id, {
                "type": "subscription_confirmed",
                "topic": topic,
                "status": "subscribed"
            })
            logger.debug(f"Client {client_id} subscribed to {topic}")
        else:
            await self._send_error(client_id, f"Failed to subscribe to topic: {topic}")
    
    async def _handle_unsubscribe(self, client_id: str, data: Dict[str, Any]):
        """Handle unsubscription request."""
        topic = data.get("topic")
        
        if not topic:
            await self._send_error(client_id, "Topic is required for unsubscription")
            return
        
        success = await websocket_manager.unsubscribe(client_id, topic)
        
        if success:
            await websocket_manager.send_to_client(client_id, {
                "type": "unsubscription_confirmed",
                "topic": topic,
                "status": "unsubscribed"
            })
            logger.debug(f"Client {client_id} unsubscribed from {topic}")
        else:
            await self._send_error(client_id, f"Failed to unsubscribe from topic: {topic}")
    
    async def _handle_ping(self, client_id: str, data: Dict[str, Any]):
        """Handle ping request."""
        await websocket_manager.send_to_client(client_id, {
            "type": "pong",
            "timestamp": data.get("timestamp")
        })
    
    async def _handle_pong(self, client_id: str, data: Dict[str, Any]):
        """Handle pong response."""
        # Update last ping time
        if client_id in websocket_manager.connections:
            import time
            websocket_manager.connections[client_id].last_ping = time.time()
    
    async def _handle_get_status(self, client_id: str, data: Dict[str, Any]):
        """Handle status request."""
        stats = websocket_manager.get_connection_stats()
        client_info = websocket_manager.get_client_info(client_id)
        
        await websocket_manager.send_to_client(client_id, {
            "type": "status_response",
            "websocket_stats": stats,
            "client_info": client_info
        })
    
    async def _handle_get_events(self, client_id: str, data: Dict[str, Any]):
        """Handle request for recent events."""
        limit = min(data.get("limit", 50), 200)  # Cap at 200 events
        event_type = data.get("event_type")
        
        events = event_broadcaster.get_recent_events(limit=limit, event_type=event_type)
        
        await websocket_manager.send_to_client(client_id, {
            "type": "events_response",
            "events": events,
            "count": len(events)
        })
    
    async def _handle_trading_command(self, client_id: str, data: Dict[str, Any]):
        """Handle trading command from client."""
        command = data.get("command")
        
        if not command:
            await self._send_error(client_id, "Trading command is required")
            return
        
        # For now, just acknowledge the command
        # In a real implementation, this would interface with the trading engine
        await websocket_manager.send_to_client(client_id, {
            "type": "trading_command_received",
            "command": command,
            "status": "acknowledged",
            "message": "Trading command received (demo mode)"
        })
        
        # Emit event about the command
        await event_broadcaster.emit_notification(
            f"Trading command received: {command}",
            level="info",
            category="trading"
        )
    
    async def _send_error(self, client_id: str, error_message: str):
        """Send error message to client."""
        await websocket_manager.send_to_client(client_id, {
            "type": "error",
            "message": error_message
        })
        logger.warning(f"Sent error to {client_id}: {error_message}")


# Global message handler instance
message_handler = MessageHandler()