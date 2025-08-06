"""Smart alert engine for Oracle Trader Bot."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from app.notifications.push_service import push_notification_service, PushNotification

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of alerts that can be generated."""
    PRICE_MOVEMENT = "price_movement"
    AI_PREDICTION = "ai_prediction"
    NEWS_SENTIMENT = "news_sentiment"
    SOCIAL_SIGNAL = "social_signal"
    TECHNICAL_INDICATOR = "technical_indicator"
    VOLUME_SPIKE = "volume_spike"
    RISK_MANAGEMENT = "risk_management"


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    user_id: str
    alert_type: AlertType
    symbol: str
    title: str
    message: str
    data: Dict[str, Any]
    priority: int = 5  # 1-10, 10 being highest
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    sent: bool = False
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class SmartAlertEngine:
    """Intelligent alert engine that processes market events and generates personalized alerts."""
    
    def __init__(self):
        self.user_preferences: Dict[str, Dict] = {}
        self.alert_history: Dict[str, List[Alert]] = {}
        self.active_alerts: List[Alert] = []
        self.price_thresholds: Dict[str, Dict] = {}  # user_id -> symbol -> thresholds
        self.running = False
    
    async def start(self):
        """Start the alert engine."""
        self.running = True
        logger.info("Smart Alert Engine started")
        
        # Start background tasks
        asyncio.create_task(self._process_market_events())
        asyncio.create_task(self._cleanup_expired_alerts())
    
    async def stop(self):
        """Stop the alert engine."""
        self.running = False
        logger.info("Smart Alert Engine stopped")
    
    async def set_user_preferences(self, user_id: str, preferences: Dict):
        """Set alert preferences for a user."""
        default_preferences = {
            "price_alerts": True,
            "ai_predictions": True,
            "news_alerts": True,
            "social_alerts": True,
            "technical_alerts": False,
            "risk_alerts": True,
            "quiet_hours": {"start": "22:00", "end": "08:00"},
            "max_alerts_per_hour": 5,
            "min_priority": 3
        }
        
        # Merge with defaults
        user_prefs = {**default_preferences, **preferences}
        self.user_preferences[user_id] = user_prefs
        
        logger.info(f"Alert preferences updated for user {user_id}")
    
    async def add_price_alert(self, user_id: str, symbol: str, target_price: float, condition: str = "above"):
        """Add a price alert for a user."""
        if user_id not in self.price_thresholds:
            self.price_thresholds[user_id] = {}
        
        if symbol not in self.price_thresholds[user_id]:
            self.price_thresholds[user_id][symbol] = []
        
        threshold = {
            "target_price": target_price,
            "condition": condition,  # "above" or "below"
            "created_at": datetime.utcnow(),
            "triggered": False
        }
        
        self.price_thresholds[user_id][symbol].append(threshold)
        
        logger.info(f"Price alert added for {user_id}: {symbol} {condition} ${target_price}")
    
    async def process_price_update(self, symbol: str, current_price: float, previous_price: float):
        """Process price updates and trigger relevant alerts."""
        try:
            # Check price threshold alerts
            await self._check_price_thresholds(symbol, current_price)
            
            # Check for significant price movements
            price_change_pct = ((current_price - previous_price) / previous_price) * 100
            
            if abs(price_change_pct) >= 5.0:  # 5% or more movement
                await self._generate_price_movement_alert(symbol, current_price, price_change_pct)
            
        except Exception as e:
            logger.error(f"Error processing price update for {symbol}: {e}")
    
    async def process_ai_prediction(self, symbol: str, prediction: Dict):
        """Process AI predictions and generate alerts."""
        try:
            confidence = prediction.get("confidence", 0)
            action = prediction.get("action", "hold")
            target_price = prediction.get("target_price", 0)
            
            # Only alert on high-confidence predictions
            if confidence >= 0.8 and action in ["buy", "sell"]:
                await self._generate_ai_prediction_alert(symbol, prediction)
                
        except Exception as e:
            logger.error(f"Error processing AI prediction for {symbol}: {e}")
    
    async def process_news_sentiment(self, symbol: str, sentiment_data: Dict):
        """Process news sentiment and generate alerts."""
        try:
            sentiment_score = sentiment_data.get("score", 0)
            sentiment_magnitude = sentiment_data.get("magnitude", 0)
            
            # Alert on extreme sentiment
            if abs(sentiment_score) >= 0.8 and sentiment_magnitude >= 0.7:
                await self._generate_news_sentiment_alert(symbol, sentiment_data)
                
        except Exception as e:
            logger.error(f"Error processing news sentiment for {symbol}: {e}")
    
    async def process_social_signal(self, signal_data: Dict):
        """Process social trading signals."""
        try:
            signal_type = signal_data.get("type")
            
            if signal_type == "leader_trade":
                await self._generate_leader_trade_alert(signal_data)
            elif signal_type == "trending_symbol":
                await self._generate_trending_symbol_alert(signal_data)
            elif signal_type == "community_sentiment":
                await self._generate_community_sentiment_alert(signal_data)
                
        except Exception as e:
            logger.error(f"Error processing social signal: {e}")
    
    async def personalized_alerts(self, user_id: str) -> List[Alert]:
        """Get personalized alerts for a user based on their preferences and behavior."""
        try:
            user_prefs = self.user_preferences.get(user_id, {})
            user_alerts = []
            
            # Get user's trading history and preferences
            # This would typically query the database
            
            # Generate ML-based relevant alerts
            # For now, return recent alerts for the user
            if user_id in self.alert_history:
                recent_alerts = [
                    alert for alert in self.alert_history[user_id]
                    if not alert.sent and alert.created_at > datetime.utcnow() - timedelta(hours=24)
                ]
                user_alerts.extend(recent_alerts)
            
            # Filter by user preferences
            filtered_alerts = []
            for alert in user_alerts:
                if self._should_send_alert(alert, user_prefs):
                    filtered_alerts.append(alert)
            
            # Sort by priority and time
            filtered_alerts.sort(key=lambda x: (x.priority, x.created_at), reverse=True)
            
            return filtered_alerts[:10]  # Limit to 10 alerts
            
        except Exception as e:
            logger.error(f"Error generating personalized alerts for {user_id}: {e}")
            return []
    
    async def _process_market_events(self):
        """Background task to process market events and generate alerts."""
        while self.running:
            try:
                # This would connect to market data feeds
                # For now, we'll simulate processing
                await asyncio.sleep(30)  # Process every 30 seconds
                
                # Process pending alerts
                await self._send_pending_alerts()
                
            except Exception as e:
                logger.error(f"Error in market events processing: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _cleanup_expired_alerts(self):
        """Background task to clean up expired alerts."""
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                # Remove expired alerts
                self.active_alerts = [
                    alert for alert in self.active_alerts
                    if alert.expires_at is None or alert.expires_at > current_time
                ]
                
                # Clean up old alert history (keep last 30 days)
                cutoff_date = current_time - timedelta(days=30)
                for user_id in self.alert_history:
                    self.alert_history[user_id] = [
                        alert for alert in self.alert_history[user_id]
                        if alert.created_at > cutoff_date
                    ]
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                logger.error(f"Error in alert cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def _check_price_thresholds(self, symbol: str, current_price: float):
        """Check if any price thresholds have been crossed."""
        for user_id, user_thresholds in self.price_thresholds.items():
            if symbol in user_thresholds:
                for threshold in user_thresholds[symbol]:
                    if threshold["triggered"]:
                        continue
                    
                    target_price = threshold["target_price"]
                    condition = threshold["condition"]
                    
                    triggered = False
                    if condition == "above" and current_price >= target_price:
                        triggered = True
                    elif condition == "below" and current_price <= target_price:
                        triggered = True
                    
                    if triggered:
                        threshold["triggered"] = True
                        await self._create_alert(
                            user_id=user_id,
                            alert_type=AlertType.PRICE_MOVEMENT,
                            symbol=symbol,
                            title=f"Price Alert: {symbol}",
                            message=f"Price is now {condition} ${target_price:,.2f} at ${current_price:,.2f}",
                            data={
                                "current_price": current_price,
                                "target_price": target_price,
                                "condition": condition
                            },
                            priority=8
                        )
    
    async def _generate_price_movement_alert(self, symbol: str, price: float, change_pct: float):
        """Generate alert for significant price movements."""
        direction = "up" if change_pct > 0 else "down"
        emoji = "📈" if change_pct > 0 else "📉"
        
        # Send to all users interested in this symbol
        interested_users = await self._get_users_interested_in_symbol(symbol)
        
        for user_id in interested_users:
            await self._create_alert(
                user_id=user_id,
                alert_type=AlertType.PRICE_MOVEMENT,
                symbol=symbol,
                title=f"{emoji} {symbol} Price Movement",
                message=f"{symbol} moved {abs(change_pct):.1f}% {direction} to ${price:,.2f}",
                data={
                    "price": price,
                    "change_pct": change_pct,
                    "direction": direction
                },
                priority=7
            )
    
    async def _generate_ai_prediction_alert(self, symbol: str, prediction: Dict):
        """Generate alert for AI predictions."""
        action = prediction.get("action", "hold")
        confidence = prediction.get("confidence", 0)
        target_price = prediction.get("target_price", 0)
        
        interested_users = await self._get_users_interested_in_symbol(symbol)
        
        for user_id in interested_users:
            await self._create_alert(
                user_id=user_id,
                alert_type=AlertType.AI_PREDICTION,
                symbol=symbol,
                title=f"🤖 AI Prediction: {symbol}",
                message=f"AI suggests {action.upper()} with {confidence*100:.0f}% confidence",
                data=prediction,
                priority=9
            )
    
    async def _generate_news_sentiment_alert(self, symbol: str, sentiment_data: Dict):
        """Generate alert for news sentiment."""
        score = sentiment_data.get("score", 0)
        sentiment = "bullish" if score > 0 else "bearish"
        emoji = "🟢" if score > 0 else "🔴"
        
        interested_users = await self._get_users_interested_in_symbol(symbol)
        
        for user_id in interested_users:
            await self._create_alert(
                user_id=user_id,
                alert_type=AlertType.NEWS_SENTIMENT,
                symbol=symbol,
                title=f"{emoji} News Sentiment: {symbol}",
                message=f"Market sentiment is {sentiment} for {symbol}",
                data=sentiment_data,
                priority=6
            )
    
    async def _generate_leader_trade_alert(self, signal_data: Dict):
        """Generate alert for leader trades."""
        leader_id = signal_data.get("leader_id")
        trade_data = signal_data.get("trade_data", {})
        
        # Get followers of this leader
        followers = await self._get_leader_followers(leader_id)
        
        for follower_id in followers:
            await self._create_alert(
                user_id=follower_id,
                alert_type=AlertType.SOCIAL_SIGNAL,
                symbol=trade_data.get("symbol", ""),
                title="🚀 Leader Trade",
                message=f"Leader just traded {trade_data.get('symbol', '')}",
                data=signal_data,
                priority=8
            )
    
    async def _create_alert(self, user_id: str, alert_type: AlertType, symbol: str, 
                          title: str, message: str, data: Dict, priority: int = 5):
        """Create and store a new alert."""
        alert = Alert(
            id=f"{user_id}_{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            alert_type=alert_type,
            symbol=symbol,
            title=title,
            message=message,
            data=data,
            priority=priority,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # Add to active alerts
        self.active_alerts.append(alert)
        
        # Add to user's alert history
        if user_id not in self.alert_history:
            self.alert_history[user_id] = []
        self.alert_history[user_id].append(alert)
        
        logger.info(f"Alert created for {user_id}: {title}")
    
    async def _send_pending_alerts(self):
        """Send pending alerts to users."""
        for alert in self.active_alerts:
            if not alert.sent:
                try:
                    # Check if we should send this alert
                    user_prefs = self.user_preferences.get(alert.user_id, {})
                    if self._should_send_alert(alert, user_prefs):
                        # Send push notification
                        await push_notification_service.send_to_user(
                            alert.user_id,
                            PushNotification(
                                title=alert.title,
                                body=alert.message,
                                data={
                                    "alert_id": alert.id,
                                    "alert_type": alert.alert_type.value,
                                    "symbol": alert.symbol,
                                    **alert.data
                                }
                            )
                        )
                        
                        alert.sent = True
                        logger.info(f"Alert sent to {alert.user_id}: {alert.title}")
                
                except Exception as e:
                    logger.error(f"Error sending alert {alert.id}: {e}")
    
    def _should_send_alert(self, alert: Alert, user_prefs: Dict) -> bool:
        """Check if an alert should be sent based on user preferences."""
        # Check if alert type is enabled
        pref_mapping = {
            AlertType.PRICE_MOVEMENT: "price_alerts",
            AlertType.AI_PREDICTION: "ai_predictions",
            AlertType.NEWS_SENTIMENT: "news_alerts",
            AlertType.SOCIAL_SIGNAL: "social_alerts",
            AlertType.TECHNICAL_INDICATOR: "technical_alerts",
            AlertType.RISK_MANAGEMENT: "risk_alerts"
        }
        
        pref_key = pref_mapping.get(alert.alert_type)
        if pref_key and not user_prefs.get(pref_key, True):
            return False
        
        # Check priority threshold
        min_priority = user_prefs.get("min_priority", 3)
        if alert.priority < min_priority:
            return False
        
        # Check quiet hours
        if self._is_quiet_hours(user_prefs):
            return alert.priority >= 9  # Only send critical alerts during quiet hours
        
        # Check rate limiting
        if self._is_rate_limited(alert.user_id, user_prefs):
            return False
        
        return True
    
    def _is_quiet_hours(self, user_prefs: Dict) -> bool:
        """Check if current time is within user's quiet hours."""
        # Simplified quiet hours check
        return False  # Implement based on user timezone
    
    def _is_rate_limited(self, user_id: str, user_prefs: Dict) -> bool:
        """Check if user has reached their alert rate limit."""
        max_per_hour = user_prefs.get("max_alerts_per_hour", 5)
        
        # Count alerts sent in the last hour
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        recent_alerts = [
            alert for alert in self.alert_history.get(user_id, [])
            if alert.sent and alert.created_at > cutoff_time
        ]
        
        return len(recent_alerts) >= max_per_hour
    
    async def _get_users_interested_in_symbol(self, symbol: str) -> List[str]:
        """Get list of users interested in a specific symbol."""
        # This would query the database for users with positions, watchlists, or alerts for this symbol
        # For now, return empty list
        return []
    
    async def _get_leader_followers(self, leader_id: str) -> List[str]:
        """Get list of followers for a leader."""
        # This would query the follow relationships
        # For now, return empty list
        return []


# Global smart alert engine instance
smart_alert_engine = SmartAlertEngine()