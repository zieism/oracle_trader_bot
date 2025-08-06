"""Leaderboard service for Oracle Trader Bot social trading."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import desc, func, and_, or_
from sqlalchemy.orm import Session

from app.social.models import SocialTradeDB, TraderDB, FollowRelationshipDB
from app.db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


class LeaderboardService:
    """Service for managing trader leaderboards and rankings."""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_update = {}
    
    async def get_top_traders(self, timeframe: str = "1M", limit: int = 50) -> List[Dict]:
        """
        Get top traders ranked by performance metrics.
        
        Args:
            timeframe: Time period for ranking (1D, 1W, 1M, 3M, 1Y, ALL)
            limit: Maximum number of traders to return
            
        Returns:
            List of top traders with their performance metrics
        """
        cache_key = f"top_traders_{timeframe}_{limit}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            async with AsyncSessionFactory() as db:
                # Calculate date range
                start_date = self._get_start_date(timeframe)
                
                # Get traders with their performance metrics
                top_traders = await self._calculate_leaderboard(db, start_date, limit)
                
                # Cache results
                self.cache[cache_key] = top_traders
                self.last_update[cache_key] = datetime.utcnow()
                
                return top_traders
                
        except Exception as e:
            logger.error(f"Error getting top traders: {e}")
            return []
    
    async def get_trader_rank(self, trader_id: str, timeframe: str = "1M") -> Dict:
        """Get specific trader's rank and percentile."""
        try:
            top_traders = await self.get_top_traders(timeframe, limit=1000)
            
            for i, trader in enumerate(top_traders):
                if trader["trader_id"] == trader_id:
                    total_traders = len(top_traders)
                    percentile = (total_traders - i) / total_traders * 100
                    
                    return {
                        "rank": i + 1,
                        "total_traders": total_traders,
                        "percentile": round(percentile, 1),
                        "performance_score": trader["performance_score"]
                    }
            
            return {
                "rank": None,
                "total_traders": len(top_traders),
                "percentile": 0,
                "performance_score": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting trader rank for {trader_id}: {e}")
            return {"rank": None, "total_traders": 0, "percentile": 0, "performance_score": 0}
    
    async def calculate_trader_score(self, trader_id: str, timeframe: str = "1M") -> float:
        """
        Calculate composite score based on multiple performance factors.
        
        Args:
            trader_id: ID of the trader
            timeframe: Time period for calculation
            
        Returns:
            Composite performance score (0-100)
        """
        try:
            async with AsyncSessionFactory() as db:
                start_date = self._get_start_date(timeframe)
                
                # Get trader's trade statistics
                stats = await self._get_trader_stats(db, trader_id, start_date)
                
                # Calculate individual metrics (0-100 scale)
                roi_score = min(max(stats["roi"] * 2, 0), 100)  # ROI * 2, capped at 100
                win_rate_score = stats["win_rate"]
                sharpe_score = min(max(stats["sharpe_ratio"] * 20, 0), 100)  # Sharpe * 20
                consistency_score = self._calculate_consistency_score(stats)
                volume_score = min(stats["total_volume"] / 100000 * 10, 100)  # Volume factor
                
                # Weighted composite score
                weights = {
                    "roi": 0.35,
                    "win_rate": 0.25,
                    "sharpe": 0.20,
                    "consistency": 0.15,
                    "volume": 0.05
                }
                
                composite_score = (
                    roi_score * weights["roi"] +
                    win_rate_score * weights["win_rate"] +
                    sharpe_score * weights["sharpe"] +
                    consistency_score * weights["consistency"] +
                    volume_score * weights["volume"]
                )
                
                return round(composite_score, 2)
                
        except Exception as e:
            logger.error(f"Error calculating trader score for {trader_id}: {e}")
            return 0.0
    
    async def get_trending_traders(self, limit: int = 20) -> List[Dict]:
        """Get traders with highest recent growth in followers and performance."""
        try:
            async with AsyncSessionFactory() as db:
                # Get traders with recent follower growth
                one_week_ago = datetime.utcnow() - timedelta(days=7)
                
                # This is a simplified version - in production, you'd track follower growth over time
                trending_query = db.query(TraderDB).join(
                    FollowRelationshipDB, TraderDB.user_id == FollowRelationshipDB.leader_id
                ).filter(
                    FollowRelationshipDB.created_at >= one_week_ago
                ).group_by(TraderDB.id).order_by(
                    desc(func.count(FollowRelationshipDB.id))
                ).limit(limit)
                
                trending_traders = await db.execute(trending_query)
                
                result = []
                for trader_db in trending_traders:
                    trader_data = {
                        "trader_id": trader_db.user_id,
                        "username": trader_db.username,
                        "display_name": trader_db.display_name,
                        "avatar_url": trader_db.avatar_url,
                        "verified": trader_db.verified,
                        "followers_count": trader_db.total_followers,
                        "growth_rate": 0,  # Calculate actual growth rate
                        "recent_performance": await self.calculate_trader_score(trader_db.user_id, "1W")
                    }
                    result.append(trader_data)
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting trending traders: {e}")
            return []
    
    async def get_category_leaders(self, category: str, limit: int = 10) -> List[Dict]:
        """
        Get top traders in specific categories.
        
        Categories: 'roi', 'win_rate', 'volume', 'consistency', 'followers'
        """
        try:
            top_traders = await self.get_top_traders("1M", limit=200)
            
            # Sort by specific category
            if category == "roi":
                sorted_traders = sorted(top_traders, key=lambda x: x.get("roi", 0), reverse=True)
            elif category == "win_rate":
                sorted_traders = sorted(top_traders, key=lambda x: x.get("win_rate", 0), reverse=True)
            elif category == "volume":
                sorted_traders = sorted(top_traders, key=lambda x: x.get("total_volume", 0), reverse=True)
            elif category == "consistency":
                sorted_traders = sorted(top_traders, key=lambda x: x.get("consistency_score", 0), reverse=True)
            elif category == "followers":
                sorted_traders = sorted(top_traders, key=lambda x: x.get("followers_count", 0), reverse=True)
            else:
                sorted_traders = top_traders
            
            return sorted_traders[:limit]
            
        except Exception as e:
            logger.error(f"Error getting category leaders for {category}: {e}")
            return []
    
    async def _calculate_leaderboard(self, db: Session, start_date: datetime, limit: int) -> List[Dict]:
        """Calculate leaderboard with trader performance metrics."""
        # Get all traders with trades in the timeframe
        traders_query = db.query(TraderDB).join(
            SocialTradeDB, TraderDB.user_id == SocialTradeDB.trader_id
        ).filter(
            SocialTradeDB.timestamp >= start_date
        ).distinct()
        
        traders = await db.execute(traders_query)
        
        leaderboard = []
        
        for trader_db in traders:
            try:
                # Calculate performance metrics
                stats = await self._get_trader_stats(db, trader_db.user_id, start_date)
                performance_score = await self.calculate_trader_score(trader_db.user_id)
                
                trader_data = {
                    "trader_id": trader_db.user_id,
                    "username": trader_db.username,
                    "display_name": trader_db.display_name,
                    "avatar_url": trader_db.avatar_url,
                    "verified": trader_db.verified,
                    "performance_score": performance_score,
                    "roi": stats["roi"],
                    "win_rate": stats["win_rate"],
                    "sharpe_ratio": stats["sharpe_ratio"],
                    "total_trades": stats["total_trades"],
                    "total_volume": stats["total_volume"],
                    "followers_count": trader_db.total_followers,
                    "avg_trade_size": stats["avg_trade_size"],
                    "max_drawdown": stats["max_drawdown"],
                    "consistency_score": self._calculate_consistency_score(stats)
                }
                
                leaderboard.append(trader_data)
                
            except Exception as e:
                logger.error(f"Error calculating stats for trader {trader_db.user_id}: {e}")
                continue
        
        # Sort by performance score
        leaderboard.sort(key=lambda x: x["performance_score"], reverse=True)
        
        return leaderboard[:limit]
    
    async def _get_trader_stats(self, db: Session, trader_id: str, start_date: datetime) -> Dict:
        """Get comprehensive trader statistics."""
        # Get all trades for the trader in the timeframe
        trades_query = db.query(SocialTradeDB).filter(
            and_(
                SocialTradeDB.trader_id == trader_id,
                SocialTradeDB.timestamp >= start_date
            )
        ).order_by(SocialTradeDB.timestamp)
        
        trades = await db.execute(trades_query)
        
        if not trades:
            return self._empty_stats()
        
        # Calculate statistics
        total_trades = len(trades)
        total_volume = sum(trade.amount * trade.price for trade in trades)
        avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
        
        # Mock calculations for now - in production, you'd calculate actual P&L
        win_rate = 65.0  # Calculate from actual trade outcomes
        roi = 15.5  # Calculate from actual P&L
        sharpe_ratio = 1.8  # Calculate from returns and volatility
        max_drawdown = -8.2  # Calculate from equity curve
        
        return {
            "total_trades": total_trades,
            "total_volume": total_volume,
            "avg_trade_size": avg_trade_size,
            "win_rate": win_rate,
            "roi": roi,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "daily_returns": []  # Would contain daily return values
        }
    
    def _calculate_consistency_score(self, stats: Dict) -> float:
        """Calculate consistency score based on trading patterns."""
        # Simplified consistency calculation
        if stats["total_trades"] < 10:
            return 0
        
        # Factor in win rate, drawdown, and trade frequency
        consistency = (
            stats["win_rate"] * 0.4 +
            max(0, (100 + stats["max_drawdown"])) * 0.3 +  # Lower drawdown = higher score
            min(100, stats["total_trades"] / 30 * 100) * 0.3  # Trade frequency factor
        )
        
        return round(consistency, 2)
    
    def _get_start_date(self, timeframe: str) -> datetime:
        """Get start date for timeframe."""
        now = datetime.utcnow()
        
        if timeframe == "1D":
            return now - timedelta(days=1)
        elif timeframe == "1W":
            return now - timedelta(weeks=1)
        elif timeframe == "1M":
            return now - timedelta(days=30)
        elif timeframe == "3M":
            return now - timedelta(days=90)
        elif timeframe == "1Y":
            return now - timedelta(days=365)
        else:  # ALL
            return datetime(2020, 1, 1)  # Far back date
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self.cache or cache_key not in self.last_update:
            return False
        
        time_diff = (datetime.utcnow() - self.last_update[cache_key]).total_seconds()
        return time_diff < self.cache_ttl
    
    def _empty_stats(self) -> Dict:
        """Return empty statistics dictionary."""
        return {
            "total_trades": 0,
            "total_volume": 0,
            "avg_trade_size": 0,
            "win_rate": 0,
            "roi": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "daily_returns": []
        }


# Global leaderboard service instance
leaderboard_service = LeaderboardService()