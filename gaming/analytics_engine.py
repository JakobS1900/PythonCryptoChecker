"""
Advanced analytics engine for roulette gaming system.
Provides comprehensive statistics, trends, and insights.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text

from .models import GameSession, GameBet, GameStats, CryptoRouletteWheel
from auth.models import User
from database.unified_models import LeaderboardEntry, Achievement
from logger import logger


class AdvancedAnalyticsEngine:
    """Enhanced analytics engine with CS:GO-inspired features."""
    
    def __init__(self):
        self.hot_cold_threshold = 10  # Games to consider for hot/cold analysis
        self.trend_analysis_days = 7  # Days for trend analysis
        self.pattern_detection_games = 50  # Recent games for pattern detection
    
    async def get_comprehensive_user_stats(
        self,
        session: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive user statistics with enhanced metrics."""
        
        # Basic stats
        basic_stats = await self._get_basic_user_stats(session, user_id)
        
        # Advanced performance metrics
        performance_metrics = await self._get_performance_metrics(session, user_id)
        
        # Betting patterns
        betting_patterns = await self._get_betting_patterns(session, user_id)
        
        # Time-based analysis
        time_analysis = await self._get_time_based_analysis(session, user_id)
        
        # Achievement progress
        achievement_progress = await self._get_achievement_progress(session, user_id)
        
        # Streaks and records
        streaks_records = await self._get_streaks_and_records(session, user_id)
        
        return {
            "user_id": user_id,
            "basic_stats": basic_stats,
            "performance_metrics": performance_metrics,
            "betting_patterns": betting_patterns,
            "time_analysis": time_analysis,
            "achievement_progress": achievement_progress,
            "streaks_records": streaks_records,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def get_global_statistics(
        self,
        session: AsyncSession,
        time_range: str = "24h"
    ) -> Dict[str, Any]:
        """Get comprehensive global platform statistics."""
        
        # Parse time range
        time_filter = self._parse_time_range(time_range)
        
        # Global game statistics
        global_stats = await self._get_global_game_stats(session, time_filter)
        
        # Popular betting patterns
        popular_patterns = await self._get_popular_betting_patterns(session, time_filter)
        
        # Hot and cold numbers
        hot_cold_analysis = await self._get_hot_cold_numbers(session, time_filter)
        
        # Platform economics
        economics = await self._get_platform_economics(session, time_filter)
        
        # Active users metrics
        user_metrics = await self._get_user_activity_metrics(session, time_filter)
        
        return {
            "time_range": time_range,
            "global_stats": global_stats,
            "popular_patterns": popular_patterns,
            "hot_cold_analysis": hot_cold_analysis,
            "economics": economics,
            "user_metrics": user_metrics,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def get_number_frequency_analysis(
        self,
        session: AsyncSession,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """Analyze number frequency and patterns."""
        
        # Get recent game results
        recent_games = await session.execute(
            select(GameSession)
            .where(GameSession.winning_number.isnot(None))
            .order_by(desc(GameSession.completed_at))
            .limit(limit)
        )
        
        games = recent_games.scalars().all()
        
        if not games:
            return {"error": "No completed games found"}
        
        # Number frequency analysis
        number_frequency = Counter(game.winning_number for game in games)
        crypto_frequency = Counter(game.winning_crypto for game in games)
        
        # Calculate expected vs actual frequency
        expected_frequency = len(games) / 37  # 37 numbers on wheel
        
        # Hot and cold numbers
        hot_numbers = []
        cold_numbers = []
        
        for number in range(37):
            actual_count = number_frequency.get(number, 0)
            deviation = actual_count - expected_frequency
            
            crypto_name = CryptoRouletteWheel.WHEEL_POSITIONS[number]["crypto"]
            
            number_data = {
                "number": number,
                "crypto": crypto_name,
                "frequency": actual_count,
                "expected": expected_frequency,
                "deviation": deviation,
                "percentage": (actual_count / len(games)) * 100
            }
            
            if actual_count > expected_frequency * 1.2:  # 20% above expected
                hot_numbers.append(number_data)
            elif actual_count < expected_frequency * 0.8:  # 20% below expected
                cold_numbers.append(number_data)
        
        # Sort by deviation
        hot_numbers.sort(key=lambda x: x["deviation"], reverse=True)
        cold_numbers.sort(key=lambda x: x["deviation"])
        
        # Pattern analysis
        patterns = await self._analyze_number_patterns(games)
        
        return {
            "analysis_scope": {
                "total_games": len(games),
                "time_range": f"Last {limit} games",
                "expected_frequency": expected_frequency
            },
            "number_frequency": dict(number_frequency),
            "crypto_frequency": dict(crypto_frequency),
            "hot_numbers": hot_numbers[:10],  # Top 10 hot numbers
            "cold_numbers": cold_numbers[:10],  # Top 10 cold numbers
            "patterns": patterns,
            "statistical_summary": {
                "most_frequent": max(number_frequency, key=number_frequency.get),
                "least_frequent": min(number_frequency, key=number_frequency.get),
                "variance": self._calculate_frequency_variance(number_frequency, expected_frequency),
                "distribution_score": self._calculate_distribution_score(number_frequency)
            }
        }
    
    async def get_betting_trend_analysis(
        self,
        session: AsyncSession,
        days: int = 7
    ) -> Dict[str, Any]:
        """Analyze betting trends over time."""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Get betting data
        betting_data = await session.execute(
            select(GameBet, GameSession)
            .join(GameSession)
            .where(
                and_(
                    GameSession.created_at >= start_time,
                    GameSession.created_at <= end_time,
                    GameSession.status == "COMPLETED"
                )
            )
            .order_by(GameSession.created_at)
        )
        
        bets = betting_data.all()
        
        if not bets:
            return {"error": "No betting data found for the specified period"}
        
        # Daily trend analysis
        daily_trends = defaultdict(lambda: {
            "total_bets": 0,
            "total_amount": 0.0,
            "unique_users": set(),
            "bet_types": defaultdict(int),
            "avg_bet_size": 0.0,
            "win_rate": 0.0,
            "wins": 0
        })
        
        for bet, game in bets:
            day_key = game.created_at.date().isoformat()
            
            daily_trends[day_key]["total_bets"] += 1
            daily_trends[day_key]["total_amount"] += bet.bet_amount
            daily_trends[day_key]["unique_users"].add(bet.user_id)
            daily_trends[day_key]["bet_types"][bet.bet_type] += 1
            
            if bet.is_winner:
                daily_trends[day_key]["wins"] += 1
        
        # Process daily trends
        processed_trends = {}
        for day, data in daily_trends.items():
            unique_user_count = len(data["unique_users"])
            
            processed_trends[day] = {
                "total_bets": data["total_bets"],
                "total_amount": data["total_amount"],
                "unique_users": unique_user_count,
                "avg_bet_size": data["total_amount"] / data["total_bets"] if data["total_bets"] > 0 else 0,
                "win_rate": (data["wins"] / data["total_bets"]) * 100 if data["total_bets"] > 0 else 0,
                "bet_types": dict(data["bet_types"]),
                "bets_per_user": data["total_bets"] / unique_user_count if unique_user_count > 0 else 0
            }
        
        # Overall trends
        total_bets = sum(data["total_bets"] for data in processed_trends.values())
        total_amount = sum(data["total_amount"] for data in processed_trends.values())
        all_users = set()
        for bet, game in bets:
            all_users.add(bet.user_id)
        
        return {
            "period": {
                "start_date": start_time.date().isoformat(),
                "end_date": end_time.date().isoformat(),
                "days": days
            },
            "daily_trends": processed_trends,
            "overall_summary": {
                "total_bets": total_bets,
                "total_amount": total_amount,
                "unique_users": len(all_users),
                "avg_daily_bets": total_bets / days,
                "avg_daily_amount": total_amount / days,
                "avg_bet_size": total_amount / total_bets if total_bets > 0 else 0
            },
            "trend_indicators": await self._calculate_trend_indicators(processed_trends)
        }
    
    async def get_leaderboard_data(
        self,
        session: AsyncSession,
        category: str = "total_winnings",
        time_range: str = "all_time",
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get comprehensive leaderboard data."""
        
        time_filter = self._parse_time_range(time_range) if time_range != "all_time" else None
        
        # Build query based on category
        if category == "total_winnings":
            query = select(
                GameStats.user_id,
                GameStats.total_amount_won,
                func.sum(GameSession.total_winnings).label("recent_winnings")
            ).join(GameSession, GameStats.user_id == GameSession.user_id)
            
        elif category == "biggest_win":
            query = select(
                GameStats.user_id,
                GameStats.biggest_single_win,
                func.max(GameSession.total_winnings - GameSession.total_bet_amount).label("recent_biggest")
            ).join(GameSession, GameStats.user_id == GameSession.user_id)
            
        elif category == "win_streak":
            query = select(
                GameStats.user_id,
                GameStats.longest_win_streak,
                GameStats.current_win_streak
            )
            
        elif category == "games_played":
            query = select(
                GameStats.user_id,
                GameStats.total_games_played,
                func.count(GameSession.id).label("recent_games")
            ).join(GameSession, GameStats.user_id == GameSession.user_id)
        
        else:
            raise ValueError(f"Unknown leaderboard category: {category}")
        
        # Add time filter if specified
        if time_filter and "GameSession" in str(query):
            query = query.where(GameSession.created_at >= time_filter)
        
        # Add user information
        query = query.join(User, GameStats.user_id == User.id).add_columns(
            User.username,
            User.level
        )
        
        # Group and order
        if "GameSession" in str(query):
            query = query.group_by(GameStats.user_id, User.username, User.level, GameStats.total_amount_won)
        
        # Order by appropriate column
        if category == "total_winnings":
            query = query.order_by(desc(GameStats.total_amount_won))
        elif category == "biggest_win":
            query = query.order_by(desc(GameStats.biggest_single_win))
        elif category == "win_streak":
            query = query.order_by(desc(GameStats.longest_win_streak))
        elif category == "games_played":
            query = query.order_by(desc(GameStats.total_games_played))
        
        query = query.limit(limit)
        
        result = await session.execute(query)
        leaderboard_data = result.all()
        
        # Format leaderboard
        leaderboard = []
        for i, row in enumerate(leaderboard_data, 1):
            entry = {
                "rank": i,
                "user_id": row.user_id,
                "username": row.username,
                "level": row.level,
                "primary_value": getattr(row, self._get_primary_column(category)),
                "badge": self._get_rank_badge(i),
                "trend": "stable"  # Would be calculated based on historical data
            }
            
            leaderboard.append(entry)
        
        return {
            "category": category,
            "time_range": time_range,
            "total_entries": len(leaderboard),
            "leaderboard": leaderboard,
            "category_info": {
                "title": self._get_category_title(category),
                "description": self._get_category_description(category),
                "unit": self._get_category_unit(category)
            },
            "last_updated": datetime.utcnow().isoformat()
        }
    
    # Helper methods
    
    async def _get_basic_user_stats(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get basic user statistics."""
        
        stats_result = await session.execute(
            select(GameStats).where(GameStats.user_id == user_id)
        )
        stats = stats_result.scalar_one_or_none()
        
        if not stats:
            return {"games_played": 0, "total_winnings": 0.0, "win_rate": 0.0}
        
        return {
            "games_played": stats.total_games_played,
            "games_won": stats.total_games_won,
            "total_amount_bet": stats.total_amount_bet,
            "total_amount_won": stats.total_amount_won,
            "net_profit_loss": stats.net_profit_loss,
            "win_rate": stats.win_rate,
            "roi_percentage": stats.roi_percentage,
            "biggest_single_win": stats.biggest_single_win,
            "biggest_single_loss": stats.biggest_single_loss
        }
    
    async def _get_performance_metrics(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Calculate advanced performance metrics."""
        
        # Get recent games for performance analysis
        recent_games = await session.execute(
            select(GameSession)
            .where(
                and_(
                    GameSession.user_id == user_id,
                    GameSession.status == "COMPLETED"
                )
            )
            .order_by(desc(GameSession.completed_at))
            .limit(50)
        )
        
        games = recent_games.scalars().all()
        
        if not games:
            return {"insufficient_data": True}
        
        # Calculate performance metrics
        recent_results = [game.total_winnings - game.total_bet_amount for game in games]
        
        return {
            "recent_games_count": len(games),
            "recent_avg_profit": sum(recent_results) / len(recent_results),
            "recent_win_rate": len([r for r in recent_results if r > 0]) / len(recent_results) * 100,
            "volatility": self._calculate_volatility(recent_results),
            "consistency_score": self._calculate_consistency_score(recent_results),
            "risk_score": self._calculate_risk_score(recent_results),
            "performance_trend": self._calculate_performance_trend(recent_results)
        }
    
    async def _get_betting_patterns(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Analyze user betting patterns."""
        
        # Get betting data
        bets_result = await session.execute(
            select(GameBet)
            .join(GameSession)
            .where(
                and_(
                    GameBet.user_id == user_id,
                    GameSession.status == "COMPLETED"
                )
            )
            .order_by(desc(GameSession.created_at))
            .limit(200)
        )
        
        bets = bets_result.scalars().all()
        
        if not bets:
            return {"insufficient_data": True}
        
        # Analyze patterns
        bet_types = Counter(bet.bet_type for bet in bets)
        bet_values = Counter(bet.bet_value for bet in bets)
        bet_amounts = [bet.bet_amount for bet in bets]
        
        return {
            "favorite_bet_types": dict(bet_types.most_common(5)),
            "favorite_bet_values": dict(bet_values.most_common(10)),
            "avg_bet_amount": sum(bet_amounts) / len(bet_amounts),
            "min_bet_amount": min(bet_amounts),
            "max_bet_amount": max(bet_amounts),
            "bet_amount_variance": self._calculate_variance(bet_amounts),
            "betting_frequency": len(bets),
            "risk_preference": self._calculate_risk_preference(bets)
        }
    
    def _calculate_volatility(self, results: List[float]) -> float:
        """Calculate result volatility."""
        if len(results) < 2:
            return 0.0
        
        mean = sum(results) / len(results)
        variance = sum((x - mean) ** 2 for x in results) / len(results)
        return variance ** 0.5
    
    def _calculate_consistency_score(self, results: List[float]) -> float:
        """Calculate consistency score (0-100)."""
        if not results:
            return 0.0
        
        volatility = self._calculate_volatility(results)
        mean_abs = sum(abs(x) for x in results) / len(results) if results else 1
        
        # Lower volatility relative to mean = higher consistency
        consistency = max(0, 100 - (volatility / mean_abs * 100))
        return min(100, consistency)
    
    def _calculate_risk_score(self, results: List[float]) -> float:
        """Calculate risk score based on betting patterns."""
        if not results:
            return 50.0  # Neutral risk
        
        # Risk factors: volatility, max loss, loss frequency
        volatility = self._calculate_volatility(results)
        max_loss = abs(min(results)) if results else 0
        loss_rate = len([r for r in results if r < 0]) / len(results)
        
        # Combine factors (0-100 scale)
        risk_score = min(100, (volatility * 10 + max_loss * 0.1 + loss_rate * 100) / 3)
        return risk_score
    
    def _calculate_performance_trend(self, results: List[float]) -> str:
        """Calculate performance trend direction."""
        if len(results) < 5:
            return "insufficient_data"
        
        # Compare recent vs older results
        recent = results[:len(results)//2]
        older = results[len(results)//2:]
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        if recent_avg > older_avg * 1.1:
            return "improving"
        elif recent_avg < older_avg * 0.9:
            return "declining"
        else:
            return "stable"
    
    def _parse_time_range(self, time_range: str) -> datetime:
        """Parse time range string to datetime filter."""
        now = datetime.utcnow()
        
        if time_range == "1h":
            return now - timedelta(hours=1)
        elif time_range == "24h":
            return now - timedelta(days=1)
        elif time_range == "7d":
            return now - timedelta(days=7)
        elif time_range == "30d":
            return now - timedelta(days=30)
        elif time_range == "90d":
            return now - timedelta(days=90)
        else:
            return now - timedelta(days=1)  # Default to 24h


# Global analytics engine instance
analytics_engine = AdvancedAnalyticsEngine()