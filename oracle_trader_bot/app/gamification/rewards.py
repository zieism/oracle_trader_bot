"""Gamification system for Oracle Trader Bot."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base, AsyncSessionFactory

logger = logging.getLogger(__name__)


class AchievementType(Enum):
    """Types of achievements users can unlock."""
    TRADING_MILESTONE = "trading_milestone"
    PERFORMANCE = "performance" 
    SOCIAL = "social"
    CONSISTENCY = "consistency"
    RISK_MANAGEMENT = "risk_management"
    COMMUNITY = "community"


@dataclass
class Achievement:
    """Achievement definition."""
    id: str
    name: str
    description: str
    icon: str
    achievement_type: AchievementType
    requirements: Dict
    points: int
    rarity: str = "common"  # common, rare, epic, legendary
    hidden: bool = False


@dataclass
class UserAchievement:
    """User's unlocked achievement."""
    user_id: str
    achievement_id: str
    unlocked_at: datetime
    progress: Dict = None


class GamificationEngine:
    """Engine for managing gamification features like points, achievements, and rewards."""
    
    def __init__(self):
        self.achievements = self._initialize_achievements()
        self.point_values = {
            'successful_trade': 10,
            'profitable_day': 25,
            'week_streak': 50,
            'month_positive': 100,
            'shared_analysis': 5,
            'helpful_comment': 3,
            'trade_copied': 15,
            'follower_gained': 8,
            'accurate_prediction': 20,
            'risk_management': 30,
            'community_contribution': 12
        }
    
    async def award_points(self, user_id: str, action: str, reward_metadata: Dict = None) -> int:
        """
        Award points to a user for specific actions.
        
        Args:
            user_id: The user's ID
            action: The action that earned points
            reward_metadata: Additional data about the action
            
        Returns:
            Points awarded
        """
        try:
            points = self.point_values.get(action, 0)
            
            # Apply multipliers based on reward_metadata
            if reward_metadata:
                multiplier = reward_metadata.get('multiplier', 1.0)
                streak_bonus = reward_metadata.get('streak_bonus', 0)
                points = int(points * multiplier) + streak_bonus
            
            async with AsyncSessionFactory() as db:
                # Update user's total points
                await self._add_points_to_user(db, user_id, points, action, reward_metadata)
                
                # Check for new achievements
                await self._check_achievements(db, user_id, action, reward_metadata)
                
                logger.info(f"Awarded {points} points to user {user_id} for {action}")
                return points
                
        except Exception as e:
            logger.error(f"Error awarding points to {user_id}: {e}")
            return 0
    
    async def unlock_achievement(self, user_id: str, achievement_id: str) -> bool:
        """Unlock an achievement for a user."""
        try:
            async with AsyncSessionFactory() as db:
                # Check if already unlocked
                existing = await db.execute(
                    db.query(UserAchievementDB).filter(
                        UserAchievementDB.user_id == user_id,
                        UserAchievementDB.achievement_id == achievement_id
                    )
                )
                
                if existing.first():
                    return False
                
                # Create achievement record
                user_achievement = UserAchievementDB(
                    user_id=user_id,
                    achievement_id=achievement_id,
                    unlocked_at=datetime.utcnow()
                )
                
                db.add(user_achievement)
                
                # Award points for the achievement
                achievement = self.achievements.get(achievement_id)
                if achievement:
                    await self._add_points_to_user(
                        db, user_id, achievement.points, 
                        "achievement_unlocked", {"achievement_id": achievement_id}
                    )
                
                await db.commit()
                
                # Send notification
                await self._send_achievement_notification(user_id, achievement)
                
                logger.info(f"Achievement {achievement_id} unlocked for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error unlocking achievement {achievement_id} for {user_id}: {e}")
            return False
    
    async def get_user_stats(self, user_id: str) -> Dict:
        """Get comprehensive gamification stats for a user."""
        try:
            async with AsyncSessionFactory() as db:
                # Get user points
                user_points = await db.execute(
                    db.query(UserPointsDB).filter(UserPointsDB.user_id == user_id)
                )
                points_record = user_points.first()
                total_points = points_record.total_points if points_record else 0
                
                # Get achievements
                achievements = await db.execute(
                    db.query(UserAchievementDB).filter(UserAchievementDB.user_id == user_id)
                )
                unlocked_achievements = achievements.all()
                
                # Calculate level and rank
                level = self._calculate_level(total_points)
                rank = await self._get_user_rank(db, user_id)
                
                return {
                    "total_points": total_points,
                    "level": level,
                    "rank": rank,
                    "achievements_unlocked": len(unlocked_achievements),
                    "achievements_total": len(self.achievements),
                    "recent_achievements": [
                        {
                            "achievement_id": ach.achievement_id,
                            "unlocked_at": ach.unlocked_at.isoformat(),
                            "name": self.achievements.get(ach.achievement_id, {}).get("name", "Unknown")
                        }
                        for ach in sorted(unlocked_achievements, key=lambda x: x.unlocked_at, reverse=True)[:5]
                    ],
                    "next_level_points": self._points_for_level(level + 1) - total_points,
                    "level_progress": self._calculate_level_progress(total_points)
                }
                
        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return {"total_points": 0, "level": 1, "rank": None}
    
    async def get_leaderboard(self, timeframe: str = "all_time", limit: int = 100) -> List[Dict]:
        """Get points leaderboard."""
        try:
            async with AsyncSessionFactory() as db:
                if timeframe == "weekly":
                    start_date = datetime.utcnow() - timedelta(weeks=1)
                    # Query weekly points
                    query = db.query(UserPointsDB).filter(
                        UserPointsDB.last_updated >= start_date
                    ).order_by(UserPointsDB.weekly_points.desc()).limit(limit)
                elif timeframe == "monthly":
                    start_date = datetime.utcnow() - timedelta(days=30)
                    query = db.query(UserPointsDB).filter(
                        UserPointsDB.last_updated >= start_date
                    ).order_by(UserPointsDB.monthly_points.desc()).limit(limit)
                else:  # all_time
                    query = db.query(UserPointsDB).order_by(
                        UserPointsDB.total_points.desc()
                    ).limit(limit)
                
                results = await db.execute(query)
                
                leaderboard = []
                for i, user_points in enumerate(results):
                    # Get user info (this would join with user table in real implementation)
                    leaderboard.append({
                        "rank": i + 1,
                        "user_id": user_points.user_id,
                        "username": f"User{user_points.user_id[:8]}",  # Placeholder
                        "points": user_points.total_points,
                        "level": self._calculate_level(user_points.total_points),
                        "achievements": await self._count_user_achievements(db, user_points.user_id)
                    })
                
                return leaderboard
                
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    async def get_available_achievements(self, user_id: str) -> List[Dict]:
        """Get list of achievements and their progress for a user."""
        try:
            async with AsyncSessionFactory() as db:
                # Get unlocked achievements
                unlocked = await db.execute(
                    db.query(UserAchievementDB).filter(UserAchievementDB.user_id == user_id)
                )
                unlocked_ids = {ach.achievement_id for ach in unlocked.all()}
                
                achievements_list = []
                for achievement_id, achievement in self.achievements.items():
                    is_unlocked = achievement_id in unlocked_ids
                    progress = await self._calculate_achievement_progress(db, user_id, achievement)
                    
                    # Hide secret achievements unless unlocked
                    if achievement.hidden and not is_unlocked:
                        continue
                    
                    achievements_list.append({
                        "id": achievement_id,
                        "name": achievement.name,
                        "description": achievement.description,
                        "icon": achievement.icon,
                        "type": achievement.achievement_type.value,
                        "points": achievement.points,
                        "rarity": achievement.rarity,
                        "unlocked": is_unlocked,
                        "progress": progress,
                        "unlocked_at": None  # Would be filled from database
                    })
                
                # Sort by rarity and unlock status
                rarity_order = {"legendary": 4, "epic": 3, "rare": 2, "common": 1}
                achievements_list.sort(key=lambda x: (x["unlocked"], rarity_order.get(x["rarity"], 0)), reverse=True)
                
                return achievements_list
                
        except Exception as e:
            logger.error(f"Error getting achievements for {user_id}: {e}")
            return []
    
    def _initialize_achievements(self) -> Dict[str, Achievement]:
        """Initialize all available achievements."""
        achievements = {
            "first_trade": Achievement(
                id="first_trade",
                name="First Steps",
                description="Execute your first trade",
                icon="🎯",
                achievement_type=AchievementType.TRADING_MILESTONE,
                requirements={"trades_count": 1},
                points=50
            ),
            "profitable_week": Achievement(
                id="profitable_week",
                name="Week Winner",
                description="Have a profitable week",
                icon="📈",
                achievement_type=AchievementType.PERFORMANCE,
                requirements={"profitable_weeks": 1},
                points=100
            ),
            "social_butterfly": Achievement(
                id="social_butterfly",
                name="Social Butterfly",
                description="Get 100 followers",
                icon="👥",
                achievement_type=AchievementType.SOCIAL,
                requirements={"followers_count": 100},
                points=200
            ),
            "consistency_king": Achievement(
                id="consistency_king",
                name="Consistency King",
                description="Trade for 30 consecutive days",
                icon="👑",
                achievement_type=AchievementType.CONSISTENCY,
                requirements={"consecutive_trading_days": 30},
                points=500,
                rarity="epic"
            ),
            "risk_master": Achievement(
                id="risk_master",
                name="Risk Master",
                description="Maintain max 5% drawdown for a month",
                icon="🛡️",
                achievement_type=AchievementType.RISK_MANAGEMENT,
                requirements={"max_drawdown_period": 30, "max_drawdown": 0.05},
                points=300,
                rarity="rare"
            ),
            "community_helper": Achievement(
                id="community_helper",
                name="Community Helper",
                description="Help 50 community members",
                icon="🤝",
                achievement_type=AchievementType.COMMUNITY,
                requirements={"helpful_actions": 50},
                points=150
            ),
            "legendary_trader": Achievement(
                id="legendary_trader",
                name="Legendary Trader",
                description="Achieve 100% annual return",
                icon="🏆",
                achievement_type=AchievementType.PERFORMANCE,
                requirements={"annual_return": 1.0},
                points=1000,
                rarity="legendary",
                hidden=True
            )
        }
        
        return achievements
    
    async def _check_achievements(self, db, user_id: str, action: str, reward_metadata: Dict):
        """Check if any achievements should be unlocked."""
        # Get user's current stats
        user_stats = await self._get_user_trading_stats(db, user_id)
        
        for achievement_id, achievement in self.achievements.items():
            # Skip if already unlocked
            existing = await db.execute(
                db.query(UserAchievementDB).filter(
                    UserAchievementDB.user_id == user_id,
                    UserAchievementDB.achievement_id == achievement_id
                )
            )
            
            if existing.first():
                continue
            
            # Check if requirements are met
            if self._check_achievement_requirements(achievement, user_stats, action, reward_metadata):
                await self.unlock_achievement(user_id, achievement_id)
    
    def _check_achievement_requirements(self, achievement: Achievement, user_stats: Dict, action: str, reward_metadata: Dict) -> bool:
        """Check if achievement requirements are satisfied."""
        requirements = achievement.requirements
        
        for req_key, req_value in requirements.items():
            user_value = user_stats.get(req_key, 0)
            
            if isinstance(req_value, (int, float)):
                if user_value < req_value:
                    return False
            elif isinstance(req_value, dict):
                # Complex requirements
                pass
        
        return True
    
    async def _add_points_to_user(self, db, user_id: str, points: int, action: str, reward_metadata: Dict):
        """Add points to user's total."""
        # Get or create user points record
        user_points = await db.execute(
            db.query(UserPointsDB).filter(UserPointsDB.user_id == user_id)
        )
        points_record = user_points.first()
        
        if not points_record:
            points_record = UserPointsDB(
                user_id=user_id,
                total_points=0,
                weekly_points=0,
                monthly_points=0
            )
            db.add(points_record)
        
        # Update points
        points_record.total_points += points
        points_record.weekly_points += points  # Would need proper weekly reset logic
        points_record.monthly_points += points  # Would need proper monthly reset logic
        points_record.last_updated = datetime.utcnow()
        
        # Create points transaction record
        transaction = PointsTransactionDB(
            user_id=user_id,
            action=action,
            points=points,
            reward_metadata=reward_metadata or {},
            timestamp=datetime.utcnow()
        )
        db.add(transaction)
    
    def _calculate_level(self, total_points: int) -> int:
        """Calculate user level based on total points."""
        # Simple level calculation: level = sqrt(points / 100)
        import math
        level = int(math.sqrt(total_points / 100)) + 1
        return max(1, min(level, 100))  # Cap at level 100
    
    def _points_for_level(self, level: int) -> int:
        """Calculate points required for a specific level."""
        return (level - 1) ** 2 * 100
    
    def _calculate_level_progress(self, total_points: int) -> float:
        """Calculate progress towards next level (0-1)."""
        current_level = self._calculate_level(total_points)
        current_level_points = self._points_for_level(current_level)
        next_level_points = self._points_for_level(current_level + 1)
        
        progress = (total_points - current_level_points) / (next_level_points - current_level_points)
        return max(0, min(1, progress))
    
    async def _get_user_rank(self, db, user_id: str) -> Optional[int]:
        """Get user's rank in the global leaderboard."""
        # Count users with higher points
        rank_query = db.query(UserPointsDB).filter(
            UserPointsDB.total_points > db.query(UserPointsDB).filter(
                UserPointsDB.user_id == user_id
            ).subquery().c.total_points
        ).count()
        
        rank = await db.execute(rank_query)
        return rank + 1 if rank is not None else None
    
    async def _get_user_trading_stats(self, db, user_id: str) -> Dict:
        """Get user's trading statistics for achievement checking."""
        # This would query actual trading data
        # For now, return mock data
        return {
            "trades_count": 0,
            "profitable_weeks": 0,
            "followers_count": 0,
            "consecutive_trading_days": 0,
            "helpful_actions": 0,
            "annual_return": 0.0,
            "max_drawdown": 0.0
        }
    
    async def _calculate_achievement_progress(self, db, user_id: str, achievement: Achievement) -> Dict:
        """Calculate progress towards an achievement."""
        user_stats = await self._get_user_trading_stats(db, user_id)
        progress = {}
        
        for req_key, req_value in achievement.requirements.items():
            current_value = user_stats.get(req_key, 0)
            progress[req_key] = {
                "current": current_value,
                "required": req_value,
                "percentage": min(100, (current_value / req_value) * 100) if req_value > 0 else 0
            }
        
        return progress
    
    async def _count_user_achievements(self, db, user_id: str) -> int:
        """Count total achievements for a user."""
        count_query = db.query(UserAchievementDB).filter(
            UserAchievementDB.user_id == user_id
        ).count()
        
        count = await db.execute(count_query)
        return count or 0
    
    async def _send_achievement_notification(self, user_id: str, achievement: Achievement):
        """Send notification for unlocked achievement."""
        try:
            from app.notifications.push_service import push_notification_service, PushNotification
            
            notification = PushNotification(
                title=f"🏆 Achievement Unlocked!",
                body=f"You earned '{achievement.name}' (+{achievement.points} points)",
                data={
                    "type": "achievement",
                    "achievement_id": achievement.id,
                    "points": achievement.points
                }
            )
            
            await push_notification_service.send_to_user(user_id, notification)
            
        except Exception as e:
            logger.error(f"Error sending achievement notification: {e}")


# Database models
class UserPointsDB(Base):
    """Database model for user points."""
    __tablename__ = "user_points"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    total_points = Column(Integer, default=0)
    weekly_points = Column(Integer, default=0)
    monthly_points = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class UserAchievementDB(Base):
    """Database model for user achievements."""
    __tablename__ = "user_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    achievement_id = Column(String, nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    progress = Column(JSON, default=dict)


class PointsTransactionDB(Base):
    """Database model for points transactions."""
    __tablename__ = "points_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False)
    points = Column(Integer, nullable=False)
    reward_metadata = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# Global gamification engine instance
gamification_engine = GamificationEngine()