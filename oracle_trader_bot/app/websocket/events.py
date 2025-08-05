# app/websocket/events.py
import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, asdict
import time

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events that can be broadcast."""
    # Trading Events
    TRADE_EXECUTED = "trade_executed"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    
    # Market Data Events
    PRICE_UPDATE = "price_update"
    MARKET_DATA = "market_data"
    TICKER_UPDATE = "ticker_update"
    ORDERBOOK_UPDATE = "orderbook_update"
    
    # Bot Status Events
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    BOT_ERROR = "bot_error"
    BOT_STATUS_UPDATE = "bot_status_update"
    
    # System Events
    SYSTEM_ALERT = "system_alert"
    HEALTH_UPDATE = "health_update"
    NOTIFICATION = "notification"
    
    # Analysis Events
    SIGNAL_GENERATED = "signal_generated"
    STRATEGY_UPDATE = "strategy_update"
    ANALYSIS_COMPLETE = "analysis_complete"
    
    # Portfolio Events
    PORTFOLIO_UPDATE = "portfolio_update"
    BALANCE_UPDATE = "balance_update"
    PNL_UPDATE = "pnl_update"


@dataclass
class Event:
    """Base event class."""
    type: EventType
    data: Dict[str, Any]
    timestamp: float
    source: str = "system"
    client_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class EventBroadcaster:
    """Event broadcasting system for WebSocket clients."""
    
    def __init__(self, websocket_manager=None):
        self.websocket_manager = websocket_manager
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.event_history: List[Event] = []
        self.max_history_size = 1000
        
    def set_websocket_manager(self, websocket_manager):
        """Set the WebSocket manager for broadcasting."""
        self.websocket_manager = websocket_manager
    
    def register_handler(self, event_type: EventType, handler: Callable[[Event], None]):
        """
        Register an event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Callable that takes an Event as parameter
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event type: {event_type}")
    
    def unregister_handler(self, event_type: EventType, handler: Callable):
        """
        Unregister an event handler.
        
        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
                logger.debug(f"Unregistered handler for event type: {event_type}")
            except ValueError:
                pass
    
    async def emit(self, event_type: EventType, data: Dict[str, Any], 
                   source: str = "system", client_id: Optional[str] = None) -> Event:
        """
        Emit an event and broadcast it to WebSocket clients.
        
        Args:
            event_type: Type of event
            data: Event data
            source: Source of the event
            client_id: Optional specific client ID
            
        Returns:
            Event: The created event
        """
        event = Event(
            type=event_type,
            data=data,
            timestamp=time.time(),
            source=source,
            client_id=client_id
        )
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
        
        # Call registered handlers
        await self._call_handlers(event)
        
        # Broadcast to WebSocket clients
        await self._broadcast_event(event)
        
        logger.debug(f"Event emitted: {event_type} from {source}")
        return event
    
    async def _call_handlers(self, event: Event):
        """Call all registered handlers for the event type."""
        if event.type in self.event_handlers:
            for handler in self.event_handlers[event.type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event.type}: {e}")
    
    async def _broadcast_event(self, event: Event):
        """Broadcast event to WebSocket clients."""
        if not self.websocket_manager:
            return
        
        event_data = event.to_dict()
        
        # Determine broadcast target based on event type
        topic = self._get_topic_for_event(event.type)
        
        if event.client_id:
            # Send to specific client
            await self.websocket_manager.send_to_client(event.client_id, event_data)
        else:
            # Broadcast to topic subscribers
            sent_count = await self.websocket_manager.broadcast_to_topic(topic, event_data)
            logger.debug(f"Broadcasted {event.type} to {sent_count} clients on topic {topic}")
    
    def _get_topic_for_event(self, event_type: EventType) -> str:
        """Get the appropriate topic for an event type."""
        topic_mapping = {
            # Trading topics
            EventType.TRADE_EXECUTED: "trading",
            EventType.ORDER_PLACED: "trading",
            EventType.ORDER_FILLED: "trading",
            EventType.ORDER_CANCELLED: "trading",
            EventType.POSITION_OPENED: "trading",
            EventType.POSITION_CLOSED: "trading",
            
            # Market data topics
            EventType.PRICE_UPDATE: "market_data",
            EventType.MARKET_DATA: "market_data",
            EventType.TICKER_UPDATE: "market_data",
            EventType.ORDERBOOK_UPDATE: "market_data",
            
            # Bot status topics
            EventType.BOT_STARTED: "bot_status",
            EventType.BOT_STOPPED: "bot_status",
            EventType.BOT_ERROR: "bot_status",
            EventType.BOT_STATUS_UPDATE: "bot_status",
            
            # System topics
            EventType.SYSTEM_ALERT: "system",
            EventType.HEALTH_UPDATE: "system",
            EventType.NOTIFICATION: "notifications",
            
            # Analysis topics
            EventType.SIGNAL_GENERATED: "analysis",
            EventType.STRATEGY_UPDATE: "analysis",
            EventType.ANALYSIS_COMPLETE: "analysis",
            
            # Portfolio topics
            EventType.PORTFOLIO_UPDATE: "portfolio",
            EventType.BALANCE_UPDATE: "portfolio",
            EventType.PNL_UPDATE: "portfolio",
        }
        
        return topic_mapping.get(event_type, "general")
    
    def get_recent_events(self, limit: int = 100, event_type: Optional[EventType] = None) -> List[Dict[str, Any]]:
        """
        Get recent events from history.
        
        Args:
            limit: Maximum number of events to return
            event_type: Optional filter by event type
            
        Returns:
            List of event dictionaries
        """
        events = self.event_history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        return [e.to_dict() for e in events[-limit:]]
    
    def clear_history(self):
        """Clear event history."""
        self.event_history.clear()
        logger.info("Event history cleared")
    
    # Convenience methods for common events
    async def emit_trade_executed(self, trade_data: Dict[str, Any], source: str = "trading_engine"):
        """Emit a trade executed event."""
        await self.emit(EventType.TRADE_EXECUTED, trade_data, source)
    
    async def emit_price_update(self, symbol: str, price: float, timestamp: float = None):
        """Emit a price update event."""
        data = {
            "symbol": symbol,
            "price": price,
            "timestamp": timestamp or time.time()
        }
        await self.emit(EventType.PRICE_UPDATE, data, "market_data")
    
    async def emit_bot_status_update(self, status: str, details: Dict[str, Any] = None):
        """Emit a bot status update event."""
        data = {
            "status": status,
            "details": details or {}
        }
        await self.emit(EventType.BOT_STATUS_UPDATE, data, "bot_engine")
    
    async def emit_notification(self, message: str, level: str = "info", category: str = "general"):
        """Emit a notification event."""
        data = {
            "message": message,
            "level": level,
            "category": category
        }
        await self.emit(EventType.NOTIFICATION, data, "system")
    
    async def emit_portfolio_update(self, portfolio_data: Dict[str, Any]):
        """Emit a portfolio update event."""
        await self.emit(EventType.PORTFOLIO_UPDATE, portfolio_data, "portfolio_manager")
    
    async def emit_signal_generated(self, symbol: str, signal_data: Dict[str, Any]):
        """Emit a signal generated event."""
        data = {
            "symbol": symbol,
            **signal_data
        }
        await self.emit(EventType.SIGNAL_GENERATED, data, "strategy_engine")


# Global event broadcaster instance
event_broadcaster = EventBroadcaster()