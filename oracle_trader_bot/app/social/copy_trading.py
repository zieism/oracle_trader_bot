"""Copy trading engine for Oracle Trader Bot."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.social.models import (
    SocialTrade, 
    FollowRelationship, 
    SocialTradeDB, 
    FollowRelationshipDB
)
from app.db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


class CopyTradingEngine:
    """Engine for copy trading functionality."""
    
    def __init__(self):
        self.active_copy_trades: Dict[str, List[str]] = {}  # leader_id -> [follower_ids]
        self.copy_settings: Dict[str, Dict] = {}  # follower_id -> copy settings
    
    async def copy_trade(self, leader_trade: SocialTrade, follower_id: str) -> bool:
        """
        Automatically replicate leader's trades for a follower.
        
        Args:
            leader_trade: The trade to copy
            follower_id: ID of the follower who will copy the trade
            
        Returns:
            bool: Success status
        """
        try:
            async with AsyncSessionFactory() as db:
                # Get follow relationship and copy settings
                relationship = await self._get_follow_relationship(
                    db, follower_id, leader_trade.trader_id
                )
                
                if not relationship or not relationship.copy_trading_enabled:
                    logger.warning(f"Copy trading not enabled for {follower_id} -> {leader_trade.trader_id}")
                    return False
                
                # Calculate scaled position size
                scaled_trade = await self._scale_trade_for_follower(
                    leader_trade, relationship
                )
                
                # Validate trade before execution
                if not await self._validate_copy_trade(db, scaled_trade, follower_id):
                    return False
                
                # Execute the copy trade
                success = await self._execute_copy_trade(scaled_trade, follower_id)
                
                if success:
                    # Update copy statistics
                    await self._update_copy_stats(db, leader_trade.id, follower_id)
                    logger.info(f"Successfully copied trade {leader_trade.id} for follower {follower_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Error copying trade {leader_trade.id} for {follower_id}: {e}")
            return False
    
    async def follow_trader(self, follower_id: str, leader_id: str, copy_settings: Dict = None) -> bool:
        """
        Subscribe to leader's trading signals and set copy trading parameters.
        
        Args:
            follower_id: ID of the follower
            leader_id: ID of the leader to follow
            copy_settings: Copy trading configuration
            
        Returns:
            bool: Success status
        """
        try:
            async with AsyncSessionFactory() as db:
                # Check if already following
                existing = await db.execute(
                    db.query(FollowRelationshipDB).filter(
                        and_(
                            FollowRelationshipDB.follower_id == follower_id,
                            FollowRelationshipDB.leader_id == leader_id
                        )
                    )
                )
                
                if existing.first():
                    logger.warning(f"User {follower_id} already follows {leader_id}")
                    return False
                
                # Create follow relationship
                default_settings = {
                    "copy_trading_enabled": copy_settings.get("copy_trading_enabled", False),
                    "copy_ratio": copy_settings.get("copy_ratio", 0.1),  # 10% of leader's position
                    "max_copy_amount": copy_settings.get("max_copy_amount", 1000.0),
                    "risk_multiplier": copy_settings.get("risk_multiplier", 1.0)
                }
                
                relationship = FollowRelationshipDB(
                    follower_id=follower_id,
                    leader_id=leader_id,
                    **default_settings
                )
                
                db.add(relationship)
                await db.commit()
                
                # Add to active copy trades if enabled
                if default_settings["copy_trading_enabled"]:
                    if leader_id not in self.active_copy_trades:
                        self.active_copy_trades[leader_id] = []
                    self.active_copy_trades[leader_id].append(follower_id)
                    self.copy_settings[follower_id] = default_settings
                
                logger.info(f"User {follower_id} now follows {leader_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating follow relationship {follower_id} -> {leader_id}: {e}")
            return False
    
    async def unfollow_trader(self, follower_id: str, leader_id: str) -> bool:
        """Stop following a trader and disable copy trading."""
        try:
            async with AsyncSessionFactory() as db:
                # Remove follow relationship
                await db.execute(
                    db.query(FollowRelationshipDB).filter(
                        and_(
                            FollowRelationshipDB.follower_id == follower_id,
                            FollowRelationshipDB.leader_id == leader_id
                        )
                    ).delete()
                )
                await db.commit()
                
                # Remove from active copy trades
                if leader_id in self.active_copy_trades:
                    if follower_id in self.active_copy_trades[leader_id]:
                        self.active_copy_trades[leader_id].remove(follower_id)
                
                if follower_id in self.copy_settings:
                    del self.copy_settings[follower_id]
                
                logger.info(f"User {follower_id} unfollowed {leader_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error removing follow relationship {follower_id} -> {leader_id}: {e}")
            return False
    
    async def process_leader_trade(self, leader_trade: SocialTrade) -> int:
        """
        Process a new trade from a leader and trigger copy trades for followers.
        
        Args:
            leader_trade: The leader's trade to process
            
        Returns:
            int: Number of successful copy trades
        """
        leader_id = leader_trade.trader_id
        
        if leader_id not in self.active_copy_trades:
            return 0
        
        followers = self.active_copy_trades[leader_id]
        successful_copies = 0
        
        # Process copy trades concurrently
        copy_tasks = [
            self.copy_trade(leader_trade, follower_id)
            for follower_id in followers
        ]
        
        results = await asyncio.gather(*copy_tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, bool) and result:
                successful_copies += 1
            elif isinstance(result, Exception):
                logger.error(f"Copy trade failed for follower {followers[i]}: {result}")
        
        # Update followers_copied count
        if successful_copies > 0:
            async with AsyncSessionFactory() as db:
                trade_db = await db.get(SocialTradeDB, leader_trade.id)
                if trade_db:
                    trade_db.followers_copied = successful_copies
                    await db.commit()
        
        return successful_copies
    
    async def get_copy_trading_stats(self, trader_id: str) -> Dict:
        """Get copy trading statistics for a trader."""
        async with AsyncSessionFactory() as db:
            # Get followers count
            followers_count = await db.execute(
                db.query(FollowRelationshipDB).filter(
                    FollowRelationshipDB.leader_id == trader_id
                ).count()
            )
            
            # Get following count
            following_count = await db.execute(
                db.query(FollowRelationshipDB).filter(
                    FollowRelationshipDB.follower_id == trader_id
                ).count()
            )
            
            # Get total copies of their trades
            total_copies = await db.execute(
                db.query(SocialTradeDB).filter(
                    SocialTradeDB.trader_id == trader_id
                ).with_entities(db.func.sum(SocialTradeDB.followers_copied))
            ).scalar() or 0
            
            return {
                "followers_count": followers_count,
                "following_count": following_count,
                "total_copies": total_copies,
                "copy_success_rate": 0.95  # Calculate based on actual success rate
            }
    
    async def _get_follow_relationship(self, db: Session, follower_id: str, leader_id: str) -> Optional[FollowRelationshipDB]:
        """Get follow relationship from database."""
        result = await db.execute(
            db.query(FollowRelationshipDB).filter(
                and_(
                    FollowRelationshipDB.follower_id == follower_id,
                    FollowRelationshipDB.leader_id == leader_id
                )
            )
        )
        return result.first()
    
    async def _scale_trade_for_follower(self, leader_trade: SocialTrade, relationship: FollowRelationshipDB) -> SocialTrade:
        """Scale trade size based on follower's copy settings."""
        scaled_amount = leader_trade.amount * relationship.copy_ratio
        
        # Apply maximum copy amount limit
        if relationship.max_copy_amount and scaled_amount > relationship.max_copy_amount:
            scaled_amount = relationship.max_copy_amount
        
        # Apply risk multiplier
        scaled_amount *= relationship.risk_multiplier
        
        # Create scaled trade
        scaled_trade = leader_trade.copy()
        scaled_trade.amount = scaled_amount
        scaled_trade.trader_id = relationship.follower_id  # Change trader to follower
        
        return scaled_trade
    
    async def _validate_copy_trade(self, db: Session, trade: SocialTrade, follower_id: str) -> bool:
        """Validate copy trade before execution."""
        # Check follower's balance
        # Check risk management rules
        # Check position limits
        # For now, return True (implement actual validation)
        return True
    
    async def _execute_copy_trade(self, trade: SocialTrade, follower_id: str) -> bool:
        """Execute the actual copy trade."""
        try:
            # This would integrate with the trading engine
            # For now, we'll just log the trade
            logger.info(f"Executing copy trade for {follower_id}: {trade.action} {trade.amount} {trade.symbol} @ {trade.price}")
            
            # Store the copy trade in database
            async with AsyncSessionFactory() as db:
                copy_trade_db = SocialTradeDB(
                    trader_id=follower_id,
                    symbol=trade.symbol,
                    action=trade.action,
                    price=trade.price,
                    amount=trade.amount,
                    leverage=trade.leverage,
                    stop_loss=trade.stop_loss,
                    take_profit=trade.take_profit,
                    reasoning=f"Copy trade from leader",
                    timestamp=datetime.utcnow()
                )
                db.add(copy_trade_db)
                await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute copy trade: {e}")
            return False
    
    async def _update_copy_stats(self, db: Session, leader_trade_id: str, follower_id: str):
        """Update copy trading statistics."""
        # Update leader's trade with copy count
        # Update follower's copy trading stats
        pass


# Global copy trading engine instance
copy_trading_engine = CopyTradingEngine()