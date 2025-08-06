"""API endpoints for social trading features."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.social import (
    copy_trading_engine, 
    leaderboard_service,
    SocialTrade,
    FollowRelationship
)
from app.community.discussions import community_service, Discussion, DiscussionCategory
from app.gamification.rewards import gamification_engine
from app.notifications.push_service import push_notification_service, PushNotification
from app.alerts.smart_alerts import smart_alert_engine

router = APIRouter()


# Social Trading Endpoints
@router.get("/leaderboard")
async def get_leaderboard(
    timeframe: str = Query("1M", regex="^(1D|1W|1M|3M|1Y|ALL)$"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get trader leaderboard."""
    try:
        leaderboard = await leaderboard_service.get_top_traders(timeframe, limit)
        return {"leaderboard": leaderboard, "timeframe": timeframe}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending-traders")
async def get_trending_traders(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get trending traders."""
    try:
        trending = await leaderboard_service.get_trending_traders(limit)
        return {"trending_traders": trending}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/follow/{leader_id}")
async def follow_trader(
    leader_id: str,
    follower_id: str,
    copy_settings: dict = None,
    db: Session = Depends(get_db)
):
    """Follow a trader and optionally enable copy trading."""
    try:
        success = await copy_trading_engine.follow_trader(
            follower_id, leader_id, copy_settings or {}
        )
        
        if success:
            # Send notification to leader
            await push_notification_service.send_social_notification(
                leader_id, "new_follower", {"username": f"User{follower_id[:8]}"}
            )
            
            return {"success": True, "message": "Successfully followed trader"}
        else:
            raise HTTPException(status_code=400, detail="Failed to follow trader")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/follow/{leader_id}")
async def unfollow_trader(
    leader_id: str,
    follower_id: str,
    db: Session = Depends(get_db)
):
    """Unfollow a trader."""
    try:
        success = await copy_trading_engine.unfollow_trader(follower_id, leader_id)
        
        if success:
            return {"success": True, "message": "Successfully unfollowed trader"}
        else:
            raise HTTPException(status_code=400, detail="Failed to unfollow trader")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/copy-trading/stats/{trader_id}")
async def get_copy_trading_stats(trader_id: str, db: Session = Depends(get_db)):
    """Get copy trading statistics for a trader."""
    try:
        stats = await copy_trading_engine.get_copy_trading_stats(trader_id)
        return {"trader_id": trader_id, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Community Endpoints
@router.get("/discussions")
async def get_discussions(
    category: Optional[str] = None,
    sort_by: str = Query("latest", regex="^(latest|popular|trending)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get community discussions."""
    try:
        category_enum = DiscussionCategory(category) if category else None
        discussions = await community_service.get_discussions(
            category_enum, limit, offset, sort_by
        )
        return {"discussions": discussions, "category": category, "sort_by": sort_by}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discussions")
async def create_discussion(
    discussion_data: dict,
    author_id: str,
    db: Session = Depends(get_db)
):
    """Create a new discussion."""
    try:
        discussion = Discussion(
            title=discussion_data.get("title", ""),
            content=discussion_data.get("content", ""),
            author_id=author_id,
            category=DiscussionCategory(discussion_data.get("category", "general")),
            tags=discussion_data.get("tags", [])
        )
        
        discussion_id = await community_service.create_discussion(discussion)
        
        if discussion_id:
            return {"success": True, "discussion_id": discussion_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to create discussion")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discussions/{discussion_id}")
async def get_discussion(discussion_id: str, db: Session = Depends(get_db)):
    """Get a specific discussion with replies."""
    try:
        discussion = await community_service.get_discussion(discussion_id)
        
        if discussion:
            return {"discussion": discussion}
        else:
            raise HTTPException(status_code=404, detail="Discussion not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discussions/{discussion_id}/reply")
async def create_reply(
    discussion_id: str,
    reply_data: dict,
    author_id: str,
    db: Session = Depends(get_db)
):
    """Create a reply to a discussion."""
    try:
        reply_id = await community_service.create_reply(
            discussion_id,
            author_id,
            reply_data.get("content", ""),
            reply_data.get("parent_reply_id")
        )
        
        if reply_id:
            return {"success": True, "reply_id": reply_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to create reply")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending-topics")
async def get_trending_topics(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get trending discussion topics."""
    try:
        topics = await community_service.get_trending_topics(limit)
        return {"trending_topics": topics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Gamification Endpoints
@router.get("/gamification/stats/{user_id}")
async def get_user_gamification_stats(user_id: str, db: Session = Depends(get_db)):
    """Get user's gamification statistics."""
    try:
        stats = await gamification_engine.get_user_stats(user_id)
        return {"user_id": user_id, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gamification/achievements/{user_id}")
async def get_user_achievements(user_id: str, db: Session = Depends(get_db)):
    """Get user's achievements."""
    try:
        achievements = await gamification_engine.get_available_achievements(user_id)
        return {"user_id": user_id, "achievements": achievements}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gamification/leaderboard")
async def get_points_leaderboard(
    timeframe: str = Query("all_time", regex="^(weekly|monthly|all_time)$"),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get points leaderboard."""
    try:
        leaderboard = await gamification_engine.get_leaderboard(timeframe, limit)
        return {"leaderboard": leaderboard, "timeframe": timeframe}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gamification/award-points")
async def award_points(
    user_id: str,
    action: str,
    metadata: dict = None,
    db: Session = Depends(get_db)
):
    """Award points to a user for an action."""
    try:
        points = await gamification_engine.award_points(user_id, action, metadata)
        return {"success": True, "points_awarded": points}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Notification Endpoints
@router.post("/notifications/register-device")
async def register_device(
    device_data: dict,
    db: Session = Depends(get_db)
):
    """Register a device for push notifications."""
    try:
        await push_notification_service.register_device(
            device_data.get("user_id"),
            device_data.get("device_token"),
            device_data.get("platform"),
            device_data.get("device_info", {})
        )
        return {"success": True, "message": "Device registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/send")
async def send_notification(
    notification_data: dict,
    db: Session = Depends(get_db)
):
    """Send a push notification to a user."""
    try:
        notification = PushNotification(
            title=notification_data.get("title"),
            body=notification_data.get("body"),
            data=notification_data.get("data", {})
        )
        
        results = await push_notification_service.send_to_user(
            notification_data.get("user_id"),
            notification
        )
        
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Alert Endpoints
@router.get("/alerts/personalized/{user_id}")
async def get_personalized_alerts(user_id: str, db: Session = Depends(get_db)):
    """Get personalized alerts for a user."""
    try:
        alerts = await smart_alert_engine.personalized_alerts(user_id)
        alert_data = [
            {
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "type": alert.alert_type.value,
                "symbol": alert.symbol,
                "priority": alert.priority,
                "created_at": alert.created_at.isoformat(),
                "data": alert.data
            }
            for alert in alerts
        ]
        return {"alerts": alert_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/preferences/{user_id}")
async def set_alert_preferences(
    user_id: str,
    preferences: dict,
    db: Session = Depends(get_db)
):
    """Set alert preferences for a user."""
    try:
        await smart_alert_engine.set_user_preferences(user_id, preferences)
        return {"success": True, "message": "Alert preferences updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/price-alert")
async def add_price_alert(
    alert_data: dict,
    db: Session = Depends(get_db)
):
    """Add a price alert for a user."""
    try:
        await smart_alert_engine.add_price_alert(
            alert_data.get("user_id"),
            alert_data.get("symbol"),
            alert_data.get("target_price"),
            alert_data.get("condition", "above")
        )
        return {"success": True, "message": "Price alert added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoints for real-time updates would be implemented separately