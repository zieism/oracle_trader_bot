"""Push notification service for Oracle Trader Bot."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class PushNotification:
    """Push notification data structure."""
    title: str
    body: str
    data: Dict[str, Any] = None
    image_url: Optional[str] = None
    sound: str = "default"
    badge: Optional[int] = None
    click_action: Optional[str] = None


class FirebaseCloudMessaging:
    """Firebase Cloud Messaging service for push notifications."""
    
    def __init__(self, server_key: str):
        self.server_key = server_key
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
        self.headers = {
            "Authorization": f"key={server_key}",
            "Content-Type": "application/json"
        }
    
    async def send_notification(self, device_token: str, notification: PushNotification) -> bool:
        """Send push notification to a single device."""
        try:
            payload = {
                "to": device_token,
                "notification": {
                    "title": notification.title,
                    "body": notification.body,
                    "sound": notification.sound,
                    "click_action": notification.click_action
                },
                "data": notification.data or {}
            }
            
            if notification.image_url:
                payload["notification"]["image"] = notification.image_url
            
            if notification.badge is not None:
                payload["notification"]["badge"] = notification.badge
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.fcm_url,
                    headers=self.headers,
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success", 0) > 0:
                        logger.info(f"Push notification sent successfully to {device_token[:10]}...")
                        return True
                    else:
                        logger.error(f"FCM error: {result}")
                        return False
                else:
                    logger.error(f"FCM HTTP error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            return False
    
    async def send_multicast(self, device_tokens: List[str], notification: PushNotification) -> Dict[str, bool]:
        """Send push notification to multiple devices."""
        results = {}
        
        # FCM allows up to 1000 tokens per request
        batch_size = 1000
        for i in range(0, len(device_tokens), batch_size):
            batch_tokens = device_tokens[i:i + batch_size]
            
            try:
                payload = {
                    "registration_ids": batch_tokens,
                    "notification": {
                        "title": notification.title,
                        "body": notification.body,
                        "sound": notification.sound,
                        "click_action": notification.click_action
                    },
                    "data": notification.data or {}
                }
                
                if notification.image_url:
                    payload["notification"]["image"] = notification.image_url
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.fcm_url,
                        headers=self.headers,
                        json=payload,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Process individual results
                        for j, token in enumerate(batch_tokens):
                            if j < len(result.get("results", [])):
                                token_result = result["results"][j]
                                results[token] = "message_id" in token_result
                            else:
                                results[token] = False
                    else:
                        # Mark all tokens in batch as failed
                        for token in batch_tokens:
                            results[token] = False
                            
            except Exception as e:
                logger.error(f"Error sending multicast notification: {e}")
                for token in batch_tokens:
                    results[token] = False
        
        return results


class ApplePushNotificationService:
    """Apple Push Notification Service (APNS) for iOS devices."""
    
    def __init__(self, key_id: str, team_id: str, bundle_id: str, private_key: str):
        self.key_id = key_id
        self.team_id = team_id
        self.bundle_id = bundle_id
        self.private_key = private_key
        self.apns_url = "https://api.push.apple.com"
    
    async def send_notification(self, device_token: str, notification: PushNotification) -> bool:
        """Send push notification to iOS device via APNS."""
        try:
            # Create JWT token for authentication (simplified - use proper JWT library)
            headers = {
                "authorization": f"bearer {self._create_jwt_token()}",
                "apns-topic": self.bundle_id,
                "apns-push-type": "alert",
                "content-type": "application/json"
            }
            
            payload = {
                "aps": {
                    "alert": {
                        "title": notification.title,
                        "body": notification.body
                    },
                    "sound": notification.sound,
                }
            }
            
            if notification.badge is not None:
                payload["aps"]["badge"] = notification.badge
            
            if notification.data:
                payload.update(notification.data)
            
            url = f"{self.apns_url}/3/device/{device_token}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"APNS notification sent successfully to {device_token[:10]}...")
                    return True
                else:
                    logger.error(f"APNS error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending APNS notification: {e}")
            return False
    
    def _create_jwt_token(self) -> str:
        """Create JWT token for APNS authentication."""
        # This is a placeholder - implement proper JWT token creation
        # using the private key, key_id, and team_id
        return "jwt_token_placeholder"


class PushNotificationService:
    """Main push notification service that handles multiple platforms."""
    
    def __init__(self):
        self.fcm: Optional[FirebaseCloudMessaging] = None
        self.apns: Optional[ApplePushNotificationService] = None
        self.user_devices: Dict[str, List[Dict]] = {}  # user_id -> device info
    
    def initialize_fcm(self, server_key: str):
        """Initialize Firebase Cloud Messaging."""
        self.fcm = FirebaseCloudMessaging(server_key)
        logger.info("FCM initialized successfully")
    
    def initialize_apns(self, key_id: str, team_id: str, bundle_id: str, private_key: str):
        """Initialize Apple Push Notification Service."""
        self.apns = ApplePushNotificationService(key_id, team_id, bundle_id, private_key)
        logger.info("APNS initialized successfully")
    
    async def register_device(self, user_id: str, device_token: str, platform: str, device_info: Dict = None):
        """Register a device for push notifications."""
        if user_id not in self.user_devices:
            self.user_devices[user_id] = []
        
        device_data = {
            "token": device_token,
            "platform": platform.lower(),
            "registered_at": datetime.utcnow().isoformat(),
            "active": True
        }
        
        if device_info:
            device_data.update(device_info)
        
        # Remove existing device if already registered
        self.user_devices[user_id] = [
            d for d in self.user_devices[user_id] 
            if d["token"] != device_token
        ]
        
        # Add new device
        self.user_devices[user_id].append(device_data)
        
        logger.info(f"Device registered for user {user_id}: {platform}")
    
    async def unregister_device(self, user_id: str, device_token: str):
        """Unregister a device from push notifications."""
        if user_id in self.user_devices:
            self.user_devices[user_id] = [
                d for d in self.user_devices[user_id] 
                if d["token"] != device_token
            ]
            logger.info(f"Device unregistered for user {user_id}")
    
    async def send_to_user(self, user_id: str, notification: PushNotification) -> Dict[str, bool]:
        """Send push notification to all devices of a user."""
        if user_id not in self.user_devices:
            logger.warning(f"No devices registered for user {user_id}")
            return {}
        
        results = {}
        devices = [d for d in self.user_devices[user_id] if d["active"]]
        
        for device in devices:
            token = device["token"]
            platform = device["platform"]
            
            try:
                if platform == "android" and self.fcm:
                    success = await self.fcm.send_notification(token, notification)
                elif platform == "ios" and self.apns:
                    success = await self.apns.send_notification(token, notification)
                else:
                    logger.warning(f"Unsupported platform or service not initialized: {platform}")
                    success = False
                
                results[token] = success
                
            except Exception as e:
                logger.error(f"Error sending to device {token}: {e}")
                results[token] = False
        
        return results
    
    async def send_trade_alert(self, user_id: str, trade_data: Dict):
        """Send trading alert notification."""
        notification = PushNotification(
            title=f"🎯 Trade Alert: {trade_data['symbol']}",
            body=f"AI recommends {trade_data['action'].upper()} at ${trade_data['price']:,.2f}",
            data={
                "type": "trade_alert",
                "symbol": trade_data["symbol"],
                "action": trade_data["action"],
                "price": trade_data["price"],
                "timestamp": datetime.utcnow().isoformat()
            },
            click_action="OPEN_TRADING_SCREEN"
        )
        
        return await self.send_to_user(user_id, notification)
    
    async def send_price_alert(self, user_id: str, symbol: str, current_price: float, target_price: float):
        """Send price movement alert."""
        direction = "above" if current_price >= target_price else "below"
        
        notification = PushNotification(
            title=f"📈 Price Alert: {symbol}",
            body=f"Price is now {direction} ${target_price:,.2f} at ${current_price:,.2f}",
            data={
                "type": "price_alert",
                "symbol": symbol,
                "current_price": current_price,
                "target_price": target_price,
                "timestamp": datetime.utcnow().isoformat()
            },
            click_action="OPEN_CHART"
        )
        
        return await self.send_to_user(user_id, notification)
    
    async def send_social_notification(self, user_id: str, notification_type: str, data: Dict):
        """Send social trading notification."""
        titles = {
            "new_follower": "👥 New Follower",
            "trade_copied": "📋 Trade Copied",
            "leader_trade": "🚀 Leader Trade",
            "comment": "💬 New Comment",
            "like": "👍 Trade Liked"
        }
        
        bodies = {
            "new_follower": f"{data.get('username', 'Someone')} started following you",
            "trade_copied": f"Your {data.get('symbol', '')} trade was copied by {data.get('copies', 0)} traders",
            "leader_trade": f"{data.get('username', 'Leader')} just traded {data.get('symbol', '')}",
            "comment": f"{data.get('username', 'Someone')} commented on your trade",
            "like": f"Your {data.get('symbol', '')} trade received a like"
        }
        
        notification = PushNotification(
            title=titles.get(notification_type, "📱 Oracle Trader"),
            body=bodies.get(notification_type, "New activity"),
            data={
                "type": "social",
                "notification_type": notification_type,
                **data,
                "timestamp": datetime.utcnow().isoformat()
            },
            click_action="OPEN_SOCIAL"
        )
        
        return await self.send_to_user(user_id, notification)
    
    async def send_bulk_notification(self, user_ids: List[str], notification: PushNotification) -> Dict[str, Dict[str, bool]]:
        """Send notification to multiple users."""
        results = {}
        
        # Send notifications concurrently
        tasks = [
            self.send_to_user(user_id, notification)
            for user_id in user_ids
        ]
        
        user_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, user_id in enumerate(user_ids):
            if isinstance(user_results[i], dict):
                results[user_id] = user_results[i]
            else:
                logger.error(f"Error sending to user {user_id}: {user_results[i]}")
                results[user_id] = {}
        
        return results


# Global push notification service instance
push_notification_service = PushNotificationService()