"""Social trading models for Oracle Trader Bot."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Trader(BaseModel):
    """Social trader model."""
    user_id: str
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    performance_stats: Dict = Field(default_factory=dict)
    followers: List[str] = Field(default_factory=list)
    following: List[str] = Field(default_factory=list)
    public_strategies: List[str] = Field(default_factory=list)
    verified: bool = False
    total_followers: int = 0
    total_following: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SocialTrade(BaseModel):
    """Social trade signal model."""
    id: Optional[str] = None
    trader_id: str
    symbol: str
    action: str  # 'buy' or 'sell'
    price: float
    amount: float
    leverage: Optional[float] = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    followers_copied: int = 0
    likes: int = 0
    comments: int = 0
    is_public: bool = True
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FollowRelationship(BaseModel):
    """Follower/following relationship model."""
    follower_id: str
    leader_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    copy_trading_enabled: bool = False
    copy_ratio: float = 1.0  # Percentage of leader's position size to copy
    max_copy_amount: Optional[float] = None
    risk_multiplier: float = 1.0


class SocialPost(BaseModel):
    """Social media post model."""
    id: Optional[str] = None
    author_id: str
    content: str
    trade_id: Optional[str] = None  # Link to a trade if applicable
    images: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    likes: int = 0
    comments: int = 0
    shares: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_pinned: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Comment(BaseModel):
    """Comment on social posts or trades."""
    id: Optional[str] = None
    author_id: str
    post_id: Optional[str] = None
    trade_id: Optional[str] = None
    content: str
    likes: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    parent_comment_id: Optional[str] = None  # For nested comments
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# SQLAlchemy models for database persistence
class TraderDB(Base):
    """Database model for traders."""
    __tablename__ = "social_traders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    performance_stats = Column(JSON, default=dict)
    verified = Column(Boolean, default=False)
    total_followers = Column(Integer, default=0)
    total_following = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trades = relationship("SocialTradeDB", back_populates="trader")
    posts = relationship("SocialPostDB", back_populates="author")


class SocialTradeDB(Base):
    """Database model for social trades."""
    __tablename__ = "social_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    trader_id = Column(String, ForeignKey("social_traders.user_id"), nullable=False)
    symbol = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    leverage = Column(Float, default=1.0)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    reasoning = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    followers_copied = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    is_public = Column(Boolean, default=True)
    
    # Relationships
    trader = relationship("TraderDB", back_populates="trades")


class FollowRelationshipDB(Base):
    """Database model for follow relationships."""
    __tablename__ = "follow_relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(String, nullable=False, index=True)
    leader_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    copy_trading_enabled = Column(Boolean, default=False)
    copy_ratio = Column(Float, default=1.0)
    max_copy_amount = Column(Float, nullable=True)
    risk_multiplier = Column(Float, default=1.0)


class SocialPostDB(Base):
    """Database model for social posts."""
    __tablename__ = "social_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(String, ForeignKey("social_traders.user_id"), nullable=False)
    content = Column(String, nullable=False)
    trade_id = Column(Integer, ForeignKey("social_trades.id"), nullable=True)
    images = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    is_pinned = Column(Boolean, default=False)
    
    # Relationships
    author = relationship("TraderDB", back_populates="posts")
    trade = relationship("SocialTradeDB")


class CommentDB(Base):
    """Database model for comments."""
    __tablename__ = "social_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(String, nullable=False)
    post_id = Column(Integer, ForeignKey("social_posts.id"), nullable=True)
    trade_id = Column(Integer, ForeignKey("social_trades.id"), nullable=True)
    content = Column(String, nullable=False)
    likes = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    parent_comment_id = Column(Integer, ForeignKey("social_comments.id"), nullable=True)