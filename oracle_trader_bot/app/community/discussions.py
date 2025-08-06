"""Community discussion features for Oracle Trader Bot."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base, AsyncSessionFactory

logger = logging.getLogger(__name__)


class DiscussionCategory(Enum):
    """Discussion categories."""
    GENERAL = "general"
    ANALYSIS = "analysis"
    STRATEGIES = "strategies"
    NEWS = "news"
    EDUCATION = "education"
    SUPPORT = "support"


class PostType(Enum):
    """Types of posts."""
    DISCUSSION = "discussion"
    ANALYSIS = "analysis"
    QUESTION = "question"
    POLL = "poll"
    ANNOUNCEMENT = "announcement"


@dataclass
class Discussion:
    """Discussion thread model."""
    id: Optional[str] = None
    title: str = ""
    content: str = ""
    author_id: str = ""
    category: DiscussionCategory = DiscussionCategory.GENERAL
    post_type: PostType = PostType.DISCUSSION
    tags: List[str] = None
    likes: int = 0
    replies: int = 0
    views: int = 0
    pinned: bool = False
    locked: bool = False
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class Reply:
    """Reply to a discussion."""
    id: Optional[str] = None
    discussion_id: str = ""
    author_id: str = ""
    content: str = ""
    parent_reply_id: Optional[str] = None
    likes: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class CommunityService:
    """Service for managing community discussions and interactions."""
    
    def __init__(self):
        self.trending_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def create_discussion(self, discussion: Discussion) -> str:
        """Create a new discussion thread."""
        try:
            async with AsyncSessionFactory() as db:
                discussion_db = DiscussionDB(
                    title=discussion.title,
                    content=discussion.content,
                    author_id=discussion.author_id,
                    category=discussion.category.value,
                    post_type=discussion.post_type.value,
                    tags=discussion.tags,
                    pinned=discussion.pinned,
                    locked=discussion.locked,
                    created_at=discussion.created_at,
                    updated_at=discussion.updated_at
                )
                
                db.add(discussion_db)
                await db.commit()
                await db.refresh(discussion_db)
                
                # Award points for creating discussion
                from app.gamification.rewards import gamification_engine
                await gamification_engine.award_points(
                    discussion.author_id, 
                    "shared_analysis",
                    {"discussion_id": discussion_db.id}
                )
                
                logger.info(f"Discussion created: {discussion_db.id} by {discussion.author_id}")
                return str(discussion_db.id)
                
        except Exception as e:
            logger.error(f"Error creating discussion: {e}")
            return None
    
    async def get_discussions(self, category: Optional[DiscussionCategory] = None, 
                            limit: int = 20, offset: int = 0,
                            sort_by: str = "latest") -> List[Dict]:
        """Get list of discussions with optional filtering."""
        try:
            async with AsyncSessionFactory() as db:
                query = db.query(DiscussionDB)
                
                if category:
                    query = query.filter(DiscussionDB.category == category.value)
                
                # Sorting
                if sort_by == "popular":
                    query = query.order_by(DiscussionDB.likes.desc())
                elif sort_by == "trending":
                    # Sort by recent activity
                    query = query.order_by(DiscussionDB.updated_at.desc())
                else:  # latest
                    query = query.order_by(DiscussionDB.created_at.desc())
                
                # Pinned posts first
                query = query.order_by(DiscussionDB.pinned.desc())
                
                results = await db.execute(query.offset(offset).limit(limit))
                discussions = results.all()
                
                discussion_list = []
                for disc in discussions:
                    # Get author info (would join with user table in real implementation)
                    discussion_data = {
                        "id": disc.id,
                        "title": disc.title,
                        "content": disc.content[:200] + "..." if len(disc.content) > 200 else disc.content,
                        "author": {
                            "id": disc.author_id,
                            "username": f"User{disc.author_id[:8]}",  # Placeholder
                            "avatar": None
                        },
                        "category": disc.category,
                        "post_type": disc.post_type,
                        "tags": disc.tags,
                        "likes": disc.likes,
                        "replies": disc.replies,
                        "views": disc.views,
                        "pinned": disc.pinned,
                        "locked": disc.locked,
                        "created_at": disc.created_at.isoformat(),
                        "updated_at": disc.updated_at.isoformat()
                    }
                    discussion_list.append(discussion_data)
                
                return discussion_list
                
        except Exception as e:
            logger.error(f"Error getting discussions: {e}")
            return []
    
    async def get_discussion(self, discussion_id: str) -> Optional[Dict]:
        """Get a specific discussion with replies."""
        try:
            async with AsyncSessionFactory() as db:
                # Get discussion
                discussion = await db.get(DiscussionDB, int(discussion_id))
                if not discussion:
                    return None
                
                # Increment view count
                discussion.views += 1
                await db.commit()
                
                # Get replies
                replies = await db.execute(
                    db.query(ReplyDB).filter(ReplyDB.discussion_id == int(discussion_id))
                    .order_by(ReplyDB.created_at.asc())
                )
                
                replies_list = []
                for reply in replies:
                    reply_data = {
                        "id": reply.id,
                        "content": reply.content,
                        "author": {
                            "id": reply.author_id,
                            "username": f"User{reply.author_id[:8]}",
                            "avatar": None
                        },
                        "parent_reply_id": reply.parent_reply_id,
                        "likes": reply.likes,
                        "created_at": reply.created_at.isoformat()
                    }
                    replies_list.append(reply_data)
                
                return {
                    "id": discussion.id,
                    "title": discussion.title,
                    "content": discussion.content,
                    "author": {
                        "id": discussion.author_id,
                        "username": f"User{discussion.author_id[:8]}",
                        "avatar": None
                    },
                    "category": discussion.category,
                    "post_type": discussion.post_type,
                    "tags": discussion.tags,
                    "likes": discussion.likes,
                    "replies": discussion.replies,
                    "views": discussion.views,
                    "pinned": discussion.pinned,
                    "locked": discussion.locked,
                    "created_at": discussion.created_at.isoformat(),
                    "updated_at": discussion.updated_at.isoformat(),
                    "reply_list": replies_list
                }
                
        except Exception as e:
            logger.error(f"Error getting discussion {discussion_id}: {e}")
            return None
    
    async def create_reply(self, discussion_id: str, author_id: str, content: str, 
                          parent_reply_id: Optional[str] = None) -> str:
        """Create a reply to a discussion."""
        try:
            async with AsyncSessionFactory() as db:
                # Check if discussion exists and is not locked
                discussion = await db.get(DiscussionDB, int(discussion_id))
                if not discussion or discussion.locked:
                    return None
                
                reply_db = ReplyDB(
                    discussion_id=int(discussion_id),
                    author_id=author_id,
                    content=content,
                    parent_reply_id=int(parent_reply_id) if parent_reply_id else None,
                    created_at=datetime.utcnow()
                )
                
                db.add(reply_db)
                
                # Update discussion reply count and last activity
                discussion.replies += 1
                discussion.updated_at = datetime.utcnow()
                
                await db.commit()
                await db.refresh(reply_db)
                
                # Award points for helpful comment
                from app.gamification.rewards import gamification_engine
                await gamification_engine.award_points(
                    author_id, 
                    "helpful_comment",
                    {"reply_id": reply_db.id, "discussion_id": discussion_id}
                )
                
                logger.info(f"Reply created: {reply_db.id} in discussion {discussion_id}")
                return str(reply_db.id)
                
        except Exception as e:
            logger.error(f"Error creating reply: {e}")
            return None
    
    async def like_discussion(self, discussion_id: str, user_id: str) -> bool:
        """Like/unlike a discussion."""
        try:
            async with AsyncSessionFactory() as db:
                # Check if already liked
                existing_like = await db.execute(
                    db.query(DiscussionLikeDB).filter(
                        DiscussionLikeDB.discussion_id == int(discussion_id),
                        DiscussionLikeDB.user_id == user_id
                    )
                )
                
                discussion = await db.get(DiscussionDB, int(discussion_id))
                if not discussion:
                    return False
                
                if existing_like.first():
                    # Unlike
                    await db.execute(
                        db.query(DiscussionLikeDB).filter(
                            DiscussionLikeDB.discussion_id == int(discussion_id),
                            DiscussionLikeDB.user_id == user_id
                        ).delete()
                    )
                    discussion.likes = max(0, discussion.likes - 1)
                else:
                    # Like
                    like = DiscussionLikeDB(
                        discussion_id=int(discussion_id),
                        user_id=user_id,
                        created_at=datetime.utcnow()
                    )
                    db.add(like)
                    discussion.likes += 1
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error liking discussion {discussion_id}: {e}")
            return False
    
    async def get_trending_topics(self, limit: int = 10) -> List[str]:
        """Get trending discussion topics and hashtags."""
        cache_key = f"trending_topics_{limit}"
        
        if self._is_cache_valid(cache_key):
            return self.trending_cache[cache_key]
        
        try:
            async with AsyncSessionFactory() as db:
                # Get popular tags from recent discussions
                one_week_ago = datetime.utcnow() - timedelta(days=7)
                
                # This is a simplified query - in production, you'd use proper tag counting
                recent_discussions = await db.execute(
                    db.query(DiscussionDB).filter(
                        DiscussionDB.created_at >= one_week_ago
                    ).order_by(DiscussionDB.likes.desc()).limit(100)
                )
                
                # Extract and count tags
                tag_counts = {}
                for discussion in recent_discussions:
                    for tag in discussion.tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                # Sort by popularity
                trending = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
                trending_topics = [tag for tag, count in trending[:limit]]
                
                # Cache results
                self.trending_cache[cache_key] = trending_topics
                
                return trending_topics
                
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return []
    
    async def search_discussions(self, query: str, category: Optional[DiscussionCategory] = None,
                               limit: int = 20) -> List[Dict]:
        """Search discussions by title, content, or tags."""
        try:
            async with AsyncSessionFactory() as db:
                # Simple text search (in production, use full-text search)
                search_query = db.query(DiscussionDB).filter(
                    db.or_(
                        DiscussionDB.title.ilike(f"%{query}%"),
                        DiscussionDB.content.ilike(f"%{query}%")
                    )
                )
                
                if category:
                    search_query = search_query.filter(DiscussionDB.category == category.value)
                
                results = await db.execute(
                    search_query.order_by(DiscussionDB.created_at.desc()).limit(limit)
                )
                
                discussions = []
                for disc in results:
                    discussion_data = {
                        "id": disc.id,
                        "title": disc.title,
                        "content": disc.content[:200] + "..." if len(disc.content) > 200 else disc.content,
                        "author": {
                            "id": disc.author_id,
                            "username": f"User{disc.author_id[:8]}",
                        },
                        "category": disc.category,
                        "tags": disc.tags,
                        "likes": disc.likes,
                        "replies": disc.replies,
                        "created_at": disc.created_at.isoformat()
                    }
                    discussions.append(discussion_data)
                
                return discussions
                
        except Exception as e:
            logger.error(f"Error searching discussions: {e}")
            return []
    
    async def get_user_activity(self, user_id: str, limit: int = 20) -> Dict:
        """Get user's community activity."""
        try:
            async with AsyncSessionFactory() as db:
                # Get user's discussions
                discussions = await db.execute(
                    db.query(DiscussionDB).filter(DiscussionDB.author_id == user_id)
                    .order_by(DiscussionDB.created_at.desc()).limit(limit)
                )
                
                # Get user's replies
                replies = await db.execute(
                    db.query(ReplyDB).filter(ReplyDB.author_id == user_id)
                    .order_by(ReplyDB.created_at.desc()).limit(limit)
                )
                
                return {
                    "discussions_count": len(discussions.all()),
                    "replies_count": len(replies.all()),
                    "recent_discussions": [
                        {
                            "id": disc.id,
                            "title": disc.title,
                            "likes": disc.likes,
                            "replies": disc.replies,
                            "created_at": disc.created_at.isoformat()
                        }
                        for disc in discussions.all()[:5]
                    ],
                    "recent_replies": [
                        {
                            "id": reply.id,
                            "discussion_id": reply.discussion_id,
                            "content": reply.content[:100] + "..." if len(reply.content) > 100 else reply.content,
                            "created_at": reply.created_at.isoformat()
                        }
                        for reply in replies.all()[:5]
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting user activity for {user_id}: {e}")
            return {"discussions_count": 0, "replies_count": 0, "recent_discussions": [], "recent_replies": []}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self.trending_cache:
            return False
        
        # For simplicity, assuming we store timestamp with cached data
        return True  # Implement proper cache expiry


# Database models
class DiscussionDB(Base):
    """Database model for discussions."""
    __tablename__ = "discussions"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    author_id = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, default="general")
    post_type = Column(String, nullable=False, default="discussion")
    tags = Column(JSON, default=list)
    likes = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    views = Column(Integer, default=0)
    pinned = Column(Boolean, default=False)
    locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reply_list = relationship("ReplyDB", back_populates="discussion")


class ReplyDB(Base):
    """Database model for discussion replies."""
    __tablename__ = "discussion_replies"
    
    id = Column(Integer, primary_key=True, index=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=False, index=True)
    author_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_reply_id = Column(Integer, ForeignKey("discussion_replies.id"), nullable=True)
    likes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    discussion = relationship("DiscussionDB", back_populates="reply_list")


class DiscussionLikeDB(Base):
    """Database model for discussion likes."""
    __tablename__ = "discussion_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=False)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# Global community service instance
community_service = CommunityService()