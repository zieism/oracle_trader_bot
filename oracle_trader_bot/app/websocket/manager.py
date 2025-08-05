# app/websocket/manager.py
import asyncio
import json
import logging
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum
import time

logger = logging.getLogger(__name__)


class ClientType(str, Enum):
    """Types of WebSocket clients."""
    DASHBOARD = "dashboard"
    TRADER = "trader"
    MONITOR = "monitor"
    ANALYTICS = "analytics"


class ConnectionInfo:
    """Information about a WebSocket connection."""
    
    def __init__(self, websocket: WebSocket, client_type: ClientType, client_id: str):
        self.websocket = websocket
        self.client_type = client_type
        self.client_id = client_id
        self.connected_at = time.time()
        self.last_ping = time.time()
        self.subscriptions: Set[str] = set()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "client_type": self.client_type.value,
            "connected_at": self.connected_at,
            "last_ping": self.last_ping,
            "subscriptions": list(self.subscriptions),
            "is_alive": time.time() - self.last_ping < 60
        }


class WebSocketManager:
    """Enhanced WebSocket connection manager with client handling and broadcasting."""
    
    def __init__(self):
        self.connections: Dict[str, ConnectionInfo] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # topic -> set of client_ids
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start_background_tasks(self):
        """Start background tasks for heartbeat and cleanup."""
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_background_tasks(self):
        """Stop background tasks."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def connect(self, websocket: WebSocket, client_type: ClientType, client_id: str = None) -> str:
        """
        Accept a WebSocket connection and register the client.
        
        Args:
            websocket: The WebSocket connection
            client_type: Type of client connecting
            client_id: Optional client ID, generated if not provided
            
        Returns:
            str: The client ID assigned to this connection
        """
        await websocket.accept()
        
        if not client_id:
            client_id = f"{client_type.value}_{int(time.time() * 1000)}"
        
        # Ensure unique client ID
        counter = 1
        original_id = client_id
        while client_id in self.connections:
            client_id = f"{original_id}_{counter}"
            counter += 1
        
        connection_info = ConnectionInfo(websocket, client_type, client_id)
        self.connections[client_id] = connection_info
        
        logger.info(f"WebSocket client connected: {client_id} ({client_type.value})")
        
        # Send welcome message
        await self.send_to_client(client_id, {
            "type": "connection_established",
            "client_id": client_id,
            "client_type": client_type.value,
            "timestamp": time.time()
        })
        
        return client_id

    async def disconnect(self, client_id: str):
        """
        Disconnect a WebSocket client and clean up.
        
        Args:
            client_id: The client ID to disconnect
        """
        if client_id not in self.connections:
            return
        
        connection_info = self.connections[client_id]
        
        # Remove from all subscriptions
        for topic in list(connection_info.subscriptions):
            await self.unsubscribe(client_id, topic)
        
        # Close the WebSocket connection
        try:
            await connection_info.websocket.close()
        except Exception as e:
            logger.warning(f"Error closing WebSocket for {client_id}: {e}")
        
        # Remove from connections
        del self.connections[client_id]
        
        logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_to_client(self, client_id: str, data: Dict[str, Any]) -> bool:
        """
        Send data to a specific client.
        
        Args:
            client_id: Target client ID
            data: Data to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if client_id not in self.connections:
            return False
        
        connection_info = self.connections[client_id]
        
        try:
            message = json.dumps(data, default=str)
            await connection_info.websocket.send_text(message)
            return True
        except WebSocketDisconnect:
            logger.warning(f"Client {client_id} disconnected during send")
            await self.disconnect(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            return False

    async def broadcast_to_type(self, client_type: ClientType, data: Dict[str, Any]) -> int:
        """
        Broadcast data to all clients of a specific type.
        
        Args:
            client_type: Type of clients to broadcast to
            data: Data to broadcast
            
        Returns:
            int: Number of clients successfully sent to
        """
        sent_count = 0
        clients_to_disconnect = []
        
        for client_id, connection_info in self.connections.items():
            if connection_info.client_type == client_type:
                success = await self.send_to_client(client_id, data)
                if success:
                    sent_count += 1
                else:
                    clients_to_disconnect.append(client_id)
        
        # Clean up failed connections
        for client_id in clients_to_disconnect:
            await self.disconnect(client_id)
        
        return sent_count

    async def subscribe(self, client_id: str, topic: str) -> bool:
        """
        Subscribe a client to a topic.
        
        Args:
            client_id: Client ID to subscribe
            topic: Topic to subscribe to
            
        Returns:
            bool: True if subscribed successfully
        """
        if client_id not in self.connections:
            return False
        
        connection_info = self.connections[client_id]
        connection_info.subscriptions.add(topic)
        
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(client_id)
        
        logger.debug(f"Client {client_id} subscribed to topic: {topic}")
        return True

    async def unsubscribe(self, client_id: str, topic: str) -> bool:
        """
        Unsubscribe a client from a topic.
        
        Args:
            client_id: Client ID to unsubscribe
            topic: Topic to unsubscribe from
            
        Returns:
            bool: True if unsubscribed successfully
        """
        if client_id not in self.connections:
            return False
        
        connection_info = self.connections[client_id]
        connection_info.subscriptions.discard(topic)
        
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
        
        logger.debug(f"Client {client_id} unsubscribed from topic: {topic}")
        return True

    async def broadcast_to_topic(self, topic: str, data: Dict[str, Any]) -> int:
        """
        Broadcast data to all clients subscribed to a topic.
        
        Args:
            topic: Topic to broadcast to
            data: Data to broadcast
            
        Returns:
            int: Number of clients successfully sent to
        """
        if topic not in self.subscriptions:
            return 0
        
        sent_count = 0
        clients_to_disconnect = []
        
        for client_id in list(self.subscriptions[topic]):
            success = await self.send_to_client(client_id, data)
            if success:
                sent_count += 1
            else:
                clients_to_disconnect.append(client_id)
        
        # Clean up failed connections
        for client_id in clients_to_disconnect:
            await self.disconnect(client_id)
        
        return sent_count

    async def ping_client(self, client_id: str) -> bool:
        """
        Send ping to a client and update last_ping time.
        
        Args:
            client_id: Client to ping
            
        Returns:
            bool: True if ping sent successfully
        """
        if client_id not in self.connections:
            return False
        
        success = await self.send_to_client(client_id, {
            "type": "ping",
            "timestamp": time.time()
        })
        
        if success:
            self.connections[client_id].last_ping = time.time()
        
        return success

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current connections.
        
        Returns:
            Dict with connection statistics
        """
        stats = {
            "total_connections": len(self.connections),
            "connections_by_type": {},
            "topics": list(self.subscriptions.keys()),
            "total_subscriptions": sum(len(subs) for subs in self.subscriptions.values())
        }
        
        for connection in self.connections.values():
            client_type = connection.client_type.value
            if client_type not in stats["connections_by_type"]:
                stats["connections_by_type"][client_type] = 0
            stats["connections_by_type"][client_type] += 1
        
        return stats

    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific client.
        
        Args:
            client_id: Client ID to get info for
            
        Returns:
            Dict with client information or None if not found
        """
        if client_id not in self.connections:
            return None
        
        return self.connections[client_id].to_dict()

    async def _heartbeat_loop(self):
        """Background task to send periodic heartbeats."""
        while True:
            try:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
                for client_id in list(self.connections.keys()):
                    await self.ping_client(client_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def _cleanup_loop(self):
        """Background task to clean up dead connections."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = time.time()
                dead_clients = []
                
                for client_id, connection in self.connections.items():
                    if current_time - connection.last_ping > 120:  # 2 minutes timeout
                        dead_clients.append(client_id)
                
                for client_id in dead_clients:
                    logger.warning(f"Cleaning up dead connection: {client_id}")
                    await self.disconnect(client_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()