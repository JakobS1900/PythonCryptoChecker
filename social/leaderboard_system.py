"""
Competitive Leaderboard System - Social Engagement Driver
Multi-category leaderboards with real-time updates and competitive mechanics.
Research shows leaderboards increase user engagement by 200%+ through social proof and competition.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, desc, text
from dataclasses import dataclass
from enum import Enum
import json

from database import get_db_session, User, VirtualWallet
from logger import logger

class LeaderboardCategory(Enum):
    DAILY_PROFIT = "daily_profit"           # Best daily profit/loss
    WEEKLY_PROFIT = "weekly_profit"         # Best weekly profit/loss
    MONTHLY_PROFIT = "monthly_profit"       # Best monthly profit/loss
    ALL_TIME_PROFIT = "all_time_profit"     # Best all-time profit
    
    BIGGEST_WIN = "biggest_win"             # Largest single win
    WIN_STREAK = "win_streak"               # Longest current win streak
    GAMES_PLAYED = "games_played"           # Most games played
    ACCURACY_RATE = "accuracy_rate"         # Highest win percentage
    
    LEVEL_RANKING = "level_ranking"         # User levels
    GEM_COINS = "gem_coins"                 # Total GEM coins
    PORTFOLIO_VALUE = "portfolio_value"     # Real portfolio value
    PREDICTION_ACCURACY = "prediction_accuracy"  # Market prediction accuracy
    
    SOCIAL_INFLUENCE = "social_influence"   # Most friends/followers
    ACHIEVEMENT_COUNT = "achievement_count" # Most achievements unlocked

class TimeFrame(Enum):
    REAL_TIME = "real_time"    # Live updates
    DAILY = "daily"            # Daily reset at midnight
    WEEKLY = "weekly"          # Weekly reset on Sunday
    MONTHLY = "monthly"        # Monthly reset on 1st
    ALL_TIME = "all_time"      # Never resets

@dataclass
class LeaderboardEntry:
    """Individual leaderboard entry with user data"""
    rank: int
    user_id: str
    username: str
    avatar_url: Optional[str]
    value: float
    display_value: str
    change_since_last: Optional[float] = None  # Rank change
    badge: Optional[str] = None  # Special badge for top performers
    is_current_user: bool = False

@dataclass
class LeaderboardStats:
    """Overall leaderboard statistics"""
    total_participants: int
    average_value: float
    top_1_percent_threshold: float
    last_updated: datetime
    next_reset: Optional[datetime] = None

class CompetitiveLeaderboardSystem:
    """
    Advanced leaderboard system designed for maximum social engagement.
    
    Key Features:
    - Multiple competitive categories
    - Real-time ranking updates  
    - Social proof through public rankings
    - FOMO through position changes
    - Achievement recognition for top performers
    - Anonymous option for privacy-conscious users
    """
    
    def __init__(self):
        self.leaderboard_cache: Dict[str, List[LeaderboardEntry]] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_duration = timedelta(minutes=5)  # Cache for 5 minutes
        
        # Top performer badges
        self.rank_badges = {
            1: "👑",  # Crown for #1
            2: "🥈",  # Silver medal  
            3: "🥉",  # Bronze medal
            "top_10": "⭐",  # Star for top 10
            "top_100": "💎",  # Diamond for top 100
        }
    
    async def get_leaderboard(self, category: LeaderboardCategory, 
                            timeframe: TimeFrame = TimeFrame.ALL_TIME,
                            limit: int = 100, offset: int = 0,
                            user_id: str = None) -> Dict[str, Any]:
        """
        Get leaderboard with rankings and social context.
        This is the main engagement driver - seeing where you rank vs others.
        """
        try:
            cache_key = f"{category.value}_{timeframe.value}_{limit}_{offset}"
            
            # Check cache first
            if (cache_key in self.leaderboard_cache and 
                cache_key in self.cache_expiry and
                datetime.now() < self.cache_expiry[cache_key]):
                
                entries = self.leaderboard_cache[cache_key]
            else:
                # Generate fresh leaderboard
                entries = await self._generate_leaderboard(category, timeframe, limit, offset)
                
                # Cache results
                self.leaderboard_cache[cache_key] = entries
                self.cache_expiry[cache_key] = datetime.now() + self.cache_duration
            
            # Add user-specific context
            user_context = None
            if user_id:
                user_context = await self._get_user_leaderboard_context(user_id, category, timeframe, entries)
            
            # Get leaderboard statistics
            stats = await self._get_leaderboard_stats(category, timeframe)
            
            return {
                'success': True,
                'category': category.value,
                'timeframe': timeframe.value,
                'entries': [self._serialize_entry(entry) for entry in entries],
                'stats': {
                    'total_participants': stats.total_participants,
                    'average_value': stats.average_value,
                    'top_1_percent_threshold': stats.top_1_percent_threshold,
                    'last_updated': stats.last_updated.isoformat(),
                    'next_reset': stats.next_reset.isoformat() if stats.next_reset else None
                },
                'user_context': user_context,
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'has_more': len(entries) == limit
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting leaderboard {category.value}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_user_rankings(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's position across all leaderboard categories.
        Shows user their competitive standing - powerful motivation.
        """
        try:
            rankings = {}
            
            # Get rankings for each major category
            for category in [
                LeaderboardCategory.ALL_TIME_PROFIT,
                LeaderboardCategory.BIGGEST_WIN,
                LeaderboardCategory.WIN_STREAK,
                LeaderboardCategory.ACCURACY_RATE,
                LeaderboardCategory.LEVEL_RANKING,
                LeaderboardCategory.GEM_COINS
            ]:
                try:
                    rank_data = await self._get_user_rank(user_id, category, TimeFrame.ALL_TIME)
                    rankings[category.value] = rank_data
                except Exception as e:
                    logger.error(f"Error getting rank for {category.value}: {e}")
                    rankings[category.value] = None
            
            # Find user's best categories (top performance)
            best_categories = []
            for cat, data in rankings.items():
                if data and data['rank'] <= 100:  # Top 100 in any category
                    best_categories.append({
                        'category': cat,
                        'rank': data['rank'],
                        'percentile': data['percentile'],
                        'badge': self._get_rank_badge(data['rank'])
                    })
            
            # Sort by best rank
            best_categories.sort(key=lambda x: x['rank'])
            
            return {
                'success': True,
                'user_id': user_id,
                'rankings': rankings,
                'best_categories': best_categories[:3],  # Top 3 best rankings
                'overall_score': await self._calculate_overall_score(rankings),
                'rank_progression': await self._get_rank_progression(user_id),
                'next_rank_targets': await self._get_next_rank_targets(user_id, rankings)
            }
            
        except Exception as e:
            logger.error(f"Error getting user rankings for {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_competitive_challenges(self, user_id: str) -> Dict[str, Any]:
        """
        Generate personalized competitive challenges based on user's current rankings.
        Creates specific goals to improve leaderboard positions.
        """
        try:
            user_rankings = await self.get_user_rankings(user_id)
            if not user_rankings['success']:
                return user_rankings
            
            challenges = []
            
            # Generate rank-based challenges
            for category, data in user_rankings['rankings'].items():
                if not data:
                    continue
                
                current_rank = data['rank']
                current_value = data['value']
                
                # Create different types of challenges based on current position
                if current_rank > 1000:
                    # For low-ranked users: achievable goals
                    target_rank = min(500, current_rank - 100)
                    challenges.append({
                        'type': 'rank_improvement',
                        'category': category,
                        'description': f"Break into top 500 in {category.replace('_', ' ').title()}",
                        'current_rank': current_rank,
                        'target_rank': target_rank,
                        'reward': 500,  # GEM coins
                        'difficulty': 'easy'
                    })
                
                elif current_rank > 100:
                    # For mid-ranked users: competitive goals
                    target_rank = max(50, current_rank - 25)
                    challenges.append({
                        'type': 'rank_improvement',
                        'category': category,
                        'description': f"Climb {current_rank - target_rank} positions in {category.replace('_', ' ').title()}",
                        'current_rank': current_rank,
                        'target_rank': target_rank,
                        'reward': 1000,
                        'difficulty': 'medium'
                    })
                
                elif current_rank > 10:
                    # For high-ranked users: elite goals
                    target_rank = max(5, current_rank - 5)
                    challenges.append({
                        'type': 'rank_improvement',
                        'category': category,
                        'description': f"Enter TOP 10 in {category.replace('_', ' ').title()}!",
                        'current_rank': current_rank,
                        'target_rank': target_rank,
                        'reward': 2500,
                        'difficulty': 'hard'
                    })
                
                else:
                    # For top 10 users: championship goals
                    challenges.append({
                        'type': 'maintain_dominance',
                        'category': category,
                        'description': f"Maintain TOP 10 position in {category.replace('_', ' ').title()}",
                        'current_rank': current_rank,
                        'target_rank': current_rank,
                        'reward': 5000,
                        'difficulty': 'expert'
                    })
            
            # Add special challenges
            challenges.extend(await self._generate_special_challenges(user_id, user_rankings))
            
            # Sort by potential impact and reward
            challenges.sort(key=lambda x: (x['reward'], -x.get('current_rank', 999)), reverse=True)
            
            return {
                'success': True,
                'challenges': challenges[:10],  # Limit to top 10 challenges
                'weekly_bonus_available': await self._check_weekly_bonus_eligibility(user_id),
                'rival_suggestions': await self._suggest_rivals(user_id, user_rankings)
            }
            
        except Exception as e:
            logger.error(f"Error generating competitive challenges for {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_leaderboard_battles(self, user_id: str) -> Dict[str, Any]:
        """
        Create head-to-head battles between users of similar skill levels.
        Intense 1v1 competition drives maximum engagement.
        """
        try:
            # Get user's current rankings to find similar players
            user_rankings = await self.get_user_rankings(user_id)
            if not user_rankings['success']:
                return user_rankings
            
            battles = []
            
            # Find rivals in each category (players within 10 ranks)
            for category, data in user_rankings['rankings'].items():
                if not data or data['rank'] > 1000:  # Skip if unranked or very low
                    continue
                
                rivals = await self._find_nearby_rivals(user_id, category, data['rank'], range_size=10)
                
                for rival in rivals[:3]:  # Max 3 rivals per category
                    battle = {
                        'battle_id': f"{category}_{user_id}_{rival['user_id']}",
                        'category': category,
                        'rival': {
                            'user_id': rival['user_id'],
                            'username': rival['username'],
                            'rank': rival['rank'],
                            'value': rival['value']
                        },
                        'your_stats': {
                            'rank': data['rank'],
                            'value': data['value']
                        },
                        'battle_type': 'weekly_showdown',
                        'prize_pool': self._calculate_battle_prize(data['rank'], rival['rank']),
                        'time_remaining': self._get_weekly_reset_time(),
                        'winning_condition': self._get_battle_condition(category)
                    }
                    battles.append(battle)
            
            # Sort battles by potential excitement/rewards
            battles.sort(key=lambda x: x['prize_pool'], reverse=True)
            
            return {
                'success': True,
                'active_battles': battles[:15],  # Limit to prevent overwhelm
                'battle_history': await self._get_battle_history(user_id, limit=5),
                'season_record': await self._get_season_battle_record(user_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting leaderboard battles for {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _generate_leaderboard(self, category: LeaderboardCategory, 
                                  timeframe: TimeFrame, limit: int, offset: int) -> List[LeaderboardEntry]:
        """Generate leaderboard entries for a specific category and timeframe"""
        entries = []
        
        try:
            async with get_db_session() as session:
                # Build the query based on category
                query = await self._build_leaderboard_query(session, category, timeframe)
                
                # Apply pagination
                query = query.limit(limit).offset(offset)
                
                # Execute query
                result = await session.execute(query)
                rows = result.fetchall()
                
                # Convert to leaderboard entries
                for i, row in enumerate(rows):
                    rank = offset + i + 1
                    
                    entry = LeaderboardEntry(
                        rank=rank,
                        user_id=row.user_id,
                        username=row.username or f"Player{row.user_id[:8]}",
                        avatar_url=getattr(row, 'avatar_url', None),
                        value=float(row.value),
                        display_value=self._format_display_value(row.value, category),
                        badge=self._get_rank_badge(rank)
                    )
                    
                    entries.append(entry)
                
        except Exception as e:
            logger.error(f"Error generating leaderboard for {category.value}: {e}")
        
        return entries
    
    def _format_display_value(self, value: float, category: LeaderboardCategory) -> str:
        """Format value for display based on category type"""
        if category in [LeaderboardCategory.GEM_COINS, LeaderboardCategory.BIGGEST_WIN, 
                       LeaderboardCategory.DAILY_PROFIT, LeaderboardCategory.WEEKLY_PROFIT,
                       LeaderboardCategory.MONTHLY_PROFIT, LeaderboardCategory.ALL_TIME_PROFIT]:
            if value >= 1000000:
                return f"{value/1000000:.1f}M"
            elif value >= 1000:
                return f"{value/1000:.1f}K"
            else:
                return f"{int(value):,}"
        
        elif category == LeaderboardCategory.ACCURACY_RATE:
            return f"{value:.1f}%"
        
        elif category == LeaderboardCategory.PORTFOLIO_VALUE:
            return f"${value:,.2f}"
        
        else:
            return str(int(value))
    
    def _get_rank_badge(self, rank: int) -> Optional[str]:
        """Get badge emoji for rank"""
        if rank == 1:
            return self.rank_badges[1]
        elif rank == 2:
            return self.rank_badges[2]
        elif rank == 3:
            return self.rank_badges[3]
        elif rank <= 10:
            return self.rank_badges["top_10"]
        elif rank <= 100:
            return self.rank_badges["top_100"]
        else:
            return None
    
    def _serialize_entry(self, entry: LeaderboardEntry) -> Dict[str, Any]:
        """Convert leaderboard entry to dictionary"""
        return {
            'rank': entry.rank,
            'user_id': entry.user_id,
            'username': entry.username,
            'avatar_url': entry.avatar_url,
            'value': entry.value,
            'display_value': entry.display_value,
            'change_since_last': entry.change_since_last,
            'badge': entry.badge,
            'is_current_user': entry.is_current_user
        }

# Global leaderboard system
leaderboard_system = CompetitiveLeaderboardSystem()