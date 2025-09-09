"""
Social features and community system for gamification platform.
Handles friendships, leaderboards, and social interactions.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc

from database import (
    User, Friendship, Leaderboard, LeaderboardEntry, VirtualWallet,
    GameStats, UserInventory, VirtualTransaction, CurrencyType
)
from logger import logger


class SocialManager:
    """Core social features and community management."""
    
    def __init__(self):
        pass
    
    # ==================== FRIENDSHIP SYSTEM ====================
    
    async def send_friend_request(
        self,
        session: AsyncSession,
        sender_id: str,
        receiver_username: str
    ) -> Dict[str, Any]:
        """Send friend request to another user."""
        
        # Find receiver by username
        receiver = await session.execute(
            select(User).where(User.username == receiver_username)
        )
        receiver = receiver.scalar_one_or_none()
        
        if not receiver:
            raise ValueError("User not found")
        
        if receiver.id == sender_id:
            raise ValueError("Cannot add yourself as friend")
        
        # Check if friendship already exists
        existing = await session.execute(
            select(Friendship).where(
                or_(
                    and_(
                        Friendship.sender_id == sender_id,
                        Friendship.receiver_id == receiver.id
                    ),
                    and_(
                        Friendship.sender_id == receiver.id,
                        Friendship.receiver_id == sender_id
                    )
                )
            )
        )
        
        if existing.scalar_one_or_none():
            raise ValueError("Friend request already exists or you are already friends")
        
        # Check receiver's privacy settings
        if not receiver.allow_friend_requests:
            raise ValueError("This user is not accepting friend requests")
        
        # Create friendship request
        friendship = Friendship(
            sender_id=sender_id,
            receiver_id=receiver.id,
            status="PENDING"
        )
        
        session.add(friendship)
        await session.commit()
        
        logger.info(f"Friend request sent from {sender_id} to {receiver.id}")
        
        return {
            "friendship_id": friendship.id,
            "receiver_username": receiver.username,
            "receiver_display_name": receiver.display_name or receiver.username,
            "status": "PENDING",
            "sent_at": friendship.created_at.isoformat()
        }
    
    async def respond_to_friend_request(
        self,
        session: AsyncSession,
        friendship_id: str,
        receiver_id: str,
        accept: bool
    ) -> Dict[str, Any]:
        """Accept or decline friend request."""
        
        friendship = await session.execute(
            select(Friendship).where(
                and_(
                    Friendship.id == friendship_id,
                    Friendship.receiver_id == receiver_id,
                    Friendship.status == "PENDING"
                )
            )
        )
        friendship = friendship.scalar_one_or_none()
        
        if not friendship:
            raise ValueError("Friend request not found")
        
        if accept:
            friendship.status = "ACCEPTED"
            friendship.accepted_at = datetime.utcnow()
            
            # Check for achievement (friend count)
            from achievements import achievement_engine
            await achievement_engine.check_user_achievements(
                session, receiver_id, "friend_added", {}
            )
            await achievement_engine.check_user_achievements(
                session, friendship.sender_id, "friend_added", {}
            )
        else:
            friendship.status = "DECLINED"
        
        await session.commit()
        
        logger.info(f"Friend request {friendship_id}: {'accepted' if accept else 'declined'}")
        
        return {
            "friendship_id": friendship_id,
            "status": friendship.status,
            "accepted": accept
        }
    
    async def remove_friend(
        self,
        session: AsyncSession,
        user_id: str,
        friend_user_id: str
    ) -> bool:
        """Remove friend connection."""
        
        friendship = await session.execute(
            select(Friendship).where(
                and_(
                    or_(
                        and_(
                            Friendship.sender_id == user_id,
                            Friendship.receiver_id == friend_user_id
                        ),
                        and_(
                            Friendship.sender_id == friend_user_id,
                            Friendship.receiver_id == user_id
                        )
                    ),
                    Friendship.status == "ACCEPTED"
                )
            )
        )
        friendship = friendship.scalar_one_or_none()
        
        if not friendship:
            raise ValueError("Friendship not found")
        
        await session.delete(friendship)
        await session.commit()
        
        logger.info(f"Friendship removed between {user_id} and {friend_user_id}")
        
        return True
    
    async def get_user_friends(
        self,
        session: AsyncSession,
        user_id: str,
        include_pending: bool = False
    ) -> List[Dict[str, Any]]:
        """Get user's friends list."""
        
        # Build query for friendships
        query = select(Friendship, User).where(
            or_(
                and_(
                    Friendship.sender_id == user_id,
                    User.id == Friendship.receiver_id
                ),
                and_(
                    Friendship.receiver_id == user_id,
                    User.id == Friendship.sender_id
                )
            )
        )
        
        if include_pending:
            query = query.where(Friendship.status.in_(["ACCEPTED", "PENDING"]))
        else:
            query = query.where(Friendship.status == "ACCEPTED")
        
        query = query.order_by(Friendship.created_at.desc())
        
        result = await session.execute(query)
        
        friends = []
        for friendship, friend_user in result:
            is_sender = friendship.sender_id == user_id
            
            friends.append({
                "friendship_id": friendship.id,
                "user_id": friend_user.id,
                "username": friend_user.username,
                "display_name": friend_user.display_name or friend_user.username,
                "avatar_url": friend_user.avatar_url,
                "level": friend_user.current_level,
                "prestige_level": friend_user.prestige_level,
                "status": friendship.status,
                "is_sender": is_sender,
                "friends_since": friendship.accepted_at.isoformat() if friendship.accepted_at else None,
                "last_seen": friend_user.last_login.isoformat() if friend_user.last_login else None
            })
        
        return friends
    
    async def get_friend_activity_feed(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get activity feed from user's friends."""
        
        # Get friend IDs
        friends = await self.get_user_friends(session, user_id)
        friend_ids = [friend["user_id"] for friend in friends]
        
        if not friend_ids:
            return []
        
        # Get recent activities (simplified - in production, use proper activity tracking)
        activities = []
        
        # Recent level ups (based on user updates)
        recent_users = await session.execute(
            select(User).where(
                and_(
                    User.id.in_(friend_ids),
                    User.updated_at > datetime.utcnow() - timedelta(days=7)
                )
            ).order_by(User.updated_at.desc()).limit(limit)
        )
        
        for user in recent_users.scalars():
            activities.append({
                "type": "level_up",
                "user_id": user.id,
                "username": user.username,
                "display_name": user.display_name or user.username,
                "avatar_url": user.avatar_url,
                "message": f"Reached level {user.current_level}!",
                "timestamp": user.updated_at.isoformat(),
                "data": {"level": user.current_level}
            })
        
        return sorted(activities, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    # ==================== LEADERBOARD SYSTEM ====================
    
    async def update_leaderboard(
        self,
        session: AsyncSession,
        leaderboard_type: str,
        time_period: str = "ALL_TIME"
    ) -> int:
        """Update leaderboard rankings."""
        
        # Get leaderboard
        leaderboard = await session.execute(
            select(Leaderboard).where(
                and_(
                    Leaderboard.leaderboard_type == leaderboard_type,
                    Leaderboard.time_period == time_period,
                    Leaderboard.is_active == True
                )
            )
        )
        leaderboard = leaderboard.scalar_one_or_none()
        
        if not leaderboard:
            return 0
        
        # Clear existing entries
        await session.execute(
            delete(LeaderboardEntry).where(
                LeaderboardEntry.leaderboard_id == leaderboard.id
            )
        )
        
        # Calculate new rankings based on type
        rankings = await self._calculate_rankings(session, leaderboard_type, time_period)
        
        # Create new entries
        for rank, (user_id, score, additional_data) in enumerate(rankings, 1):
            if rank > leaderboard.max_entries:
                break
            
            entry = LeaderboardEntry(
                leaderboard_id=leaderboard.id,
                user_id=user_id,
                current_rank=rank,
                score=score,
                additional_data=additional_data
            )
            session.add(entry)
        
        leaderboard.last_updated = datetime.utcnow()
        await session.commit()
        
        logger.info(f"Updated leaderboard {leaderboard_type}: {len(rankings)} entries")
        
        return len(rankings)
    
    async def get_leaderboard(
        self,
        session: AsyncSession,
        leaderboard_type: str,
        time_period: str = "ALL_TIME",
        limit: int = 100,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get leaderboard rankings."""
        
        # Get leaderboard
        leaderboard = await session.execute(
            select(Leaderboard).where(
                and_(
                    Leaderboard.leaderboard_type == leaderboard_type,
                    Leaderboard.time_period == time_period,
                    Leaderboard.is_active == True
                )
            )
        )
        leaderboard = leaderboard.scalar_one_or_none()
        
        if not leaderboard:
            return {"entries": [], "user_rank": None}
        
        # Get top entries
        entries = await session.execute(
            select(LeaderboardEntry, User)
            .join(User, LeaderboardEntry.user_id == User.id)
            .where(LeaderboardEntry.leaderboard_id == leaderboard.id)
            .order_by(LeaderboardEntry.current_rank.asc())
            .limit(limit)
        )
        
        leaderboard_entries = []
        user_rank = None
        
        for entry, user in entries:
            entry_data = {
                "rank": entry.current_rank,
                "user_id": user.id,
                "username": user.username,
                "display_name": user.display_name or user.username,
                "avatar_url": user.avatar_url,
                "level": user.current_level,
                "prestige_level": user.prestige_level,
                "score": entry.score,
                "additional_data": entry.additional_data or {},
                "last_updated": entry.updated_at.isoformat()
            }
            
            leaderboard_entries.append(entry_data)
            
            if user_id and user.id == user_id:
                user_rank = entry.current_rank
        
        # If user not in top entries, find their rank
        if user_id and user_rank is None:
            user_entry = await session.execute(
                select(LeaderboardEntry).where(
                    and_(
                        LeaderboardEntry.leaderboard_id == leaderboard.id,
                        LeaderboardEntry.user_id == user_id
                    )
                )
            )
            user_entry = user_entry.scalar_one_or_none()
            if user_entry:
                user_rank = user_entry.current_rank
        
        return {
            "leaderboard_info": {
                "id": leaderboard.id,
                "name": leaderboard.name,
                "description": leaderboard.description,
                "type": leaderboard.leaderboard_type,
                "time_period": leaderboard.time_period,
                "last_updated": leaderboard.last_updated.isoformat(),
                "total_entries": len(leaderboard_entries)
            },
            "entries": leaderboard_entries,
            "user_rank": user_rank
        }
    
    async def get_all_leaderboards(
        self,
        session: AsyncSession,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get summary of all leaderboards."""
        
        leaderboards = await session.execute(
            select(Leaderboard).where(Leaderboard.is_active == True)
            .order_by(Leaderboard.created_at.asc())
        )
        
        results = []
        
        for leaderboard in leaderboards.scalars():
            # Get top 3 entries
            top_entries = await session.execute(
                select(LeaderboardEntry, User)
                .join(User, LeaderboardEntry.user_id == User.id)
                .where(LeaderboardEntry.leaderboard_id == leaderboard.id)
                .order_by(LeaderboardEntry.current_rank.asc())
                .limit(3)
            )
            
            top_players = []
            user_rank = None
            
            for entry, user in top_entries:
                top_players.append({
                    "rank": entry.current_rank,
                    "username": user.username,
                    "display_name": user.display_name or user.username,
                    "score": entry.score
                })
                
                if user_id and user.id == user_id:
                    user_rank = entry.current_rank
            
            # Find user rank if not in top 3
            if user_id and user_rank is None:
                user_entry = await session.execute(
                    select(LeaderboardEntry.current_rank).where(
                        and_(
                            LeaderboardEntry.leaderboard_id == leaderboard.id,
                            LeaderboardEntry.user_id == user_id
                        )
                    )
                )
                user_rank = user_entry.scalar()
            
            results.append({
                "id": leaderboard.id,
                "name": leaderboard.name,
                "description": leaderboard.description,
                "type": leaderboard.leaderboard_type,
                "time_period": leaderboard.time_period,
                "last_updated": leaderboard.last_updated.isoformat(),
                "top_players": top_players,
                "user_rank": user_rank,
                "rewards_config": leaderboard.rewards_config
            })
        
        return results
    
    # ==================== GIFT SYSTEM ====================
    
    async def send_gift(
        self,
        session: AsyncSession,
        sender_id: str,
        receiver_id: str,
        gift_type: str,
        amount: float,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send virtual gift to another user."""
        
        # Verify friendship
        friendship = await session.execute(
            select(Friendship).where(
                and_(
                    or_(
                        and_(
                            Friendship.sender_id == sender_id,
                            Friendship.receiver_id == receiver_id
                        ),
                        and_(
                            Friendship.sender_id == receiver_id,
                            Friendship.receiver_id == sender_id
                        )
                    ),
                    Friendship.status == "ACCEPTED"
                )
            )
        )
        
        if not friendship.scalar_one_or_none():
            raise ValueError("Can only send gifts to friends")
        
        # Verify sender has enough currency
        sender_wallet = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == sender_id)
        )
        sender_wallet = sender_wallet.scalar_one_or_none()
        
        if not sender_wallet:
            raise ValueError("Sender wallet not found")
        
        if gift_type == "GEM_COINS":
            if sender_wallet.gem_coins < amount:
                raise ValueError("Insufficient GEM coins")
        else:
            raise ValueError("Invalid gift type")
        
        # Process gift transfer
        receiver_wallet = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == receiver_id)
        )
        receiver_wallet = receiver_wallet.scalar_one()
        
        # Deduct from sender
        sender_old_balance = sender_wallet.gem_coins
        sender_wallet.gem_coins -= amount
        sender_wallet.total_gems_spent += amount
        
        # Add to receiver
        receiver_old_balance = receiver_wallet.gem_coins
        receiver_wallet.gem_coins += amount
        receiver_wallet.total_gems_earned += amount
        
        # Log transactions
        sender_transaction = VirtualTransaction(
            wallet_id=sender_wallet.id,
            transaction_type="SPEND",
            currency_type=CurrencyType.GEM_COINS.value,
            amount=-amount,
            source="gift_sent",
            description=f"Gift to friend: {message}" if message else "Gift to friend",
            balance_before=sender_old_balance,
            balance_after=sender_wallet.gem_coins
        )
        session.add(sender_transaction)
        
        receiver_transaction = VirtualTransaction(
            wallet_id=receiver_wallet.id,
            transaction_type="EARN",
            currency_type=CurrencyType.GEM_COINS.value,
            amount=amount,
            source="gift_received",
            description=f"Gift from friend: {message}" if message else "Gift from friend",
            balance_before=receiver_old_balance,
            balance_after=receiver_wallet.gem_coins
        )
        session.add(receiver_transaction)
        
        await session.commit()
        
        logger.info(f"Gift sent: {sender_id} -> {receiver_id}: {amount} {gift_type}")
        
        return {
            "gift_type": gift_type,
            "amount": amount,
            "message": message,
            "sent_at": datetime.utcnow().isoformat()
        }
    
    # ==================== HELPER METHODS ====================
    
    async def _calculate_rankings(
        self,
        session: AsyncSession,
        leaderboard_type: str,
        time_period: str
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Calculate user rankings for leaderboard."""
        
        if leaderboard_type == "total_winnings":
            results = await session.execute(
                select(
                    GameStats.user_id,
                    GameStats.total_amount_won,
                    GameStats.total_games_played,
                    GameStats.total_amount_bet
                )
                .order_by(GameStats.total_amount_won.desc())
                .limit(1000)
            )
            
            rankings = []
            for user_id, winnings, games, bet in results:
                additional_data = {
                    "total_games": games,
                    "total_bet": bet,
                    "roi": ((winnings - bet) / bet * 100) if bet > 0 else 0
                }
                rankings.append((user_id, winnings, additional_data))
            
            return rankings
        
        elif leaderboard_type == "level":
            results = await session.execute(
                select(
                    User.id,
                    User.current_level,
                    User.prestige_level,
                    User.total_experience
                )
                .order_by(
                    User.prestige_level.desc(),
                    User.current_level.desc(),
                    User.total_experience.desc()
                )
                .limit(1000)
            )
            
            rankings = []
            for user_id, level, prestige, xp in results:
                # Calculate effective level (prestige adds to ranking)
                effective_level = level + (prestige * 100)
                additional_data = {
                    "actual_level": level,
                    "prestige_level": prestige,
                    "total_experience": xp
                }
                rankings.append((user_id, effective_level, additional_data))
            
            return rankings
        
        elif leaderboard_type == "collection_completion":
            # Calculate collection completion percentage
            total_items = await session.execute(
                select(func.count(CollectibleItem.id))
                .where(CollectibleItem.is_active == True)
            )
            total_items = total_items.scalar()
            
            results = await session.execute(
                select(
                    UserInventory.user_id,
                    func.count(func.distinct(UserInventory.item_id)).label('unique_items')
                )
                .group_by(UserInventory.user_id)
                .order_by(func.count(func.distinct(UserInventory.item_id)).desc())
                .limit(1000)
            )
            
            rankings = []
            for user_id, unique_items in results:
                completion_percentage = (unique_items / total_items * 100) if total_items > 0 else 0
                additional_data = {
                    "unique_items": unique_items,
                    "total_items": total_items,
                    "completion_percentage": completion_percentage
                }
                rankings.append((user_id, completion_percentage, additional_data))
            
            return rankings
        
        return []


# Global social manager instance
social_manager = SocialManager()