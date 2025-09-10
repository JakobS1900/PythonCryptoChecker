"""
Tournament System with Prize Pools - Ultimate Competitive Experience
Advanced tournament mechanics with multiple formats, prize distributions, and social features.
Research shows tournaments increase engagement by 500% and create recurring user habits.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc
from dataclasses import dataclass, field
from enum import Enum
import json
import secrets
import math

from database import get_db_session, User, VirtualWallet
from logger import logger

class TournamentType(Enum):
    ELIMINATION = "elimination"      # Single/Double elimination bracket
    ROUND_ROBIN = "round_robin"      # Everyone plays everyone
    LEADERBOARD = "leaderboard"      # Points-based ranking
    SURVIVAL = "survival"            # Last player standing
    TIME_ATTACK = "time_attack"      # Best performance in time limit

class TournamentStatus(Enum):
    REGISTRATION = "registration"    # Players can join
    STARTING = "starting"           # About to begin
    ACTIVE = "active"               # Tournament running
    FINISHED = "finished"           # Completed
    CANCELLED = "cancelled"         # Cancelled/abandoned

class GameMode(Enum):
    DICE = "dice"
    CRASH = "crash" 
    PLINKO = "plinko"
    TOWER = "tower"
    ROULETTE = "roulette"
    MIXED = "mixed"                 # Multiple game types

class EntryType(Enum):
    FREE = "free"                   # No entry fee
    GEM_COINS = "gem_coins"        # GEM coins entry fee
    INVITATION = "invitation"       # Invite-only

@dataclass
class TournamentPrize:
    """Prize structure for tournament positions"""
    position_range: Tuple[int, int]  # (start_position, end_position)
    prize_type: str                  # "gem_coins", "items", "badges"
    amount: int
    description: str

@dataclass
class TournamentParticipant:
    """Tournament participant with stats"""
    user_id: str
    username: str
    avatar_url: Optional[str]
    joined_at: datetime
    
    # Tournament performance
    current_score: float = 0.0
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    best_performance: float = 0.0
    eliminated: bool = False
    final_position: Optional[int] = None
    
    # Bracket info (for elimination tournaments)
    bracket_position: Optional[int] = None
    current_round: int = 1

@dataclass
class Tournament:
    """Complete tournament configuration and state"""
    tournament_id: str
    name: str
    description: str
    tournament_type: TournamentType
    game_mode: GameMode
    
    # Timing
    created_at: datetime
    registration_start: datetime
    registration_end: datetime
    tournament_start: datetime
    tournament_end: datetime
    
    # Configuration
    max_participants: int
    min_participants: int
    entry_type: EntryType
    entry_fee: int
    total_prize_pool: int
    prizes: List[TournamentPrize]
    
    # Rules and settings
    games_per_round: int = 1
    elimination_threshold: float = 0.0
    time_limit_minutes: Optional[int] = None
    
    # Current state
    status: TournamentStatus = TournamentStatus.REGISTRATION
    participants: Dict[str, TournamentParticipant] = field(default_factory=dict)
    current_round: int = 1
    
    # Creator and moderation
    creator_id: str = None
    is_featured: bool = False
    is_recurring: bool = False
    recurring_schedule: Optional[str] = None

class TournamentSystem:
    """
    Comprehensive tournament system designed for maximum engagement.
    
    Key Features:
    - Multiple tournament formats (elimination, leaderboard, survival)
    - Dynamic prize pools that scale with participation
    - Social features (spectating, cheering, sharing)
    - Automated tournament creation and management
    - Achievement systems for tournament performance
    - Seasonal championships and special events
    """
    
    def __init__(self):
        self.active_tournaments: Dict[str, Tournament] = {}
        self.tournament_history: List[Tournament] = []
        
        # Default prize structures (percentage of prize pool)
        self.prize_distributions = {
            'small_tournament': [  # 8-20 players
                TournamentPrize((1, 1), "gem_coins", 50, "🥇 Champion"),
                TournamentPrize((2, 2), "gem_coins", 30, "🥈 Runner-up"),
                TournamentPrize((3, 3), "gem_coins", 20, "🥉 Third Place")
            ],
            'medium_tournament': [  # 21-50 players
                TournamentPrize((1, 1), "gem_coins", 40, "🥇 Champion"),
                TournamentPrize((2, 2), "gem_coins", 25, "🥈 Runner-up"),
                TournamentPrize((3, 3), "gem_coins", 15, "🥉 Third Place"),
                TournamentPrize((4, 8), "gem_coins", 20, "🏆 Top 8")
            ],
            'large_tournament': [  # 51+ players
                TournamentPrize((1, 1), "gem_coins", 35, "🥇 Champion"),
                TournamentPrize((2, 2), "gem_coins", 20, "🥈 Runner-up"),
                TournamentPrize((3, 3), "gem_coins", 12, "🥉 Third Place"),
                TournamentPrize((4, 8), "gem_coins", 18, "🏆 Top 8"),
                TournamentPrize((9, 16), "gem_coins", 15, "💎 Top 16")
            ]
        }
        
        # Featured tournament schedule
        self.featured_schedule = {
            'daily_dice_duel': {
                'name': 'Daily Dice Duel',
                'game_mode': GameMode.DICE,
                'type': TournamentType.LEADERBOARD,
                'duration_hours': 24,
                'entry_fee': 500,
                'max_participants': 100
            },
            'weekly_crash_championship': {
                'name': 'Weekly Crash Championship',
                'game_mode': GameMode.CRASH,
                'type': TournamentType.ELIMINATION,
                'duration_hours': 2,
                'entry_fee': 2000,
                'max_participants': 64
            },
            'plinko_masters': {
                'name': 'Plinko Masters League',
                'game_mode': GameMode.PLINKO,
                'type': TournamentType.SURVIVAL,
                'duration_hours': 4,
                'entry_fee': 1000,
                'max_participants': 50
            }
        }
    
    async def create_tournament(self, creator_id: str, tournament_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new tournament with specified configuration.
        This allows community-driven competitive events.
        """
        try:
            # Validate creator
            async with get_db_session() as session:
                creator = await session.get(User, creator_id)
                if not creator:
                    return {'success': False, 'error': 'Creator not found'}
            
            # Validate configuration
            required_fields = ['name', 'tournament_type', 'game_mode', 'max_participants', 'entry_type']
            if not all(field in tournament_config for field in required_fields):
                return {'success': False, 'error': 'Missing required tournament configuration'}
            
            # Parse and validate tournament type and game mode
            try:
                tournament_type = TournamentType(tournament_config['tournament_type'])
                game_mode = GameMode(tournament_config['game_mode'])
                entry_type = EntryType(tournament_config['entry_type'])
            except ValueError as e:
                return {'success': False, 'error': f'Invalid tournament configuration: {e}'}
            
            # Calculate timing
            now = datetime.now()
            registration_duration = tournament_config.get('registration_duration_hours', 2)
            tournament_duration = tournament_config.get('tournament_duration_hours', 4)
            
            registration_start = now
            registration_end = now + timedelta(hours=registration_duration)
            tournament_start = registration_end + timedelta(minutes=15)  # 15 min prep time
            tournament_end = tournament_start + timedelta(hours=tournament_duration)
            
            # Calculate prize pool
            entry_fee = tournament_config.get('entry_fee', 0) if entry_type == EntryType.GEM_COINS else 0
            base_prize_pool = tournament_config.get('base_prize_pool', entry_fee * 8)  # Assume 8 players minimum
            
            # Generate prizes based on expected participation
            max_participants = min(tournament_config['max_participants'], 200)  # Cap at 200
            prizes = self._generate_prize_structure(base_prize_pool, max_participants)
            
            # Create tournament
            tournament_id = f"tour_{creator_id}_{int(now.timestamp())}"
            tournament = Tournament(
                tournament_id=tournament_id,
                name=tournament_config['name'],
                description=tournament_config.get('description', ''),
                tournament_type=tournament_type,
                game_mode=game_mode,
                created_at=now,
                registration_start=registration_start,
                registration_end=registration_end,
                tournament_start=tournament_start,
                tournament_end=tournament_end,
                max_participants=max_participants,
                min_participants=tournament_config.get('min_participants', 4),
                entry_type=entry_type,
                entry_fee=entry_fee,
                total_prize_pool=base_prize_pool,
                prizes=prizes,
                games_per_round=tournament_config.get('games_per_round', 1),
                time_limit_minutes=tournament_config.get('time_limit_minutes'),
                creator_id=creator_id
            )
            
            # Store tournament
            self.active_tournaments[tournament_id] = tournament
            await self._save_tournament(tournament)
            
            return {
                'success': True,
                'tournament_id': tournament_id,
                'tournament': self._serialize_tournament(tournament),
                'message': 'Tournament created successfully!',
                'registration_opens': registration_start.isoformat(),
                'tournament_begins': tournament_start.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating tournament: {e}")
            return {'success': False, 'error': str(e)}
    
    async def join_tournament(self, user_id: str, tournament_id: str) -> Dict[str, Any]:
        """
        Join an active tournament during registration period.
        This is the commitment step that locks in participation.
        """
        try:
            if tournament_id not in self.active_tournaments:
                return {'success': False, 'error': 'Tournament not found'}
            
            tournament = self.active_tournaments[tournament_id]
            
            # Check tournament status
            if tournament.status != TournamentStatus.REGISTRATION:
                return {'success': False, 'error': 'Registration is closed'}
            
            # Check if already joined
            if user_id in tournament.participants:
                return {'success': False, 'error': 'Already registered for this tournament'}
            
            # Check capacity
            if len(tournament.participants) >= tournament.max_participants:
                return {'success': False, 'error': 'Tournament is full'}
            
            # Check entry requirements
            if tournament.entry_type == EntryType.GEM_COINS:
                async with get_db_session() as session:
                    user = await session.get(User, user_id)
                    if not user or not user.virtual_wallet:
                        return {'success': False, 'error': 'User wallet not found'}
                    
                    if user.virtual_wallet.gem_coins < tournament.entry_fee:
                        return {'success': False, 'error': f'Insufficient GEM coins. Need {tournament.entry_fee:,}'}
                    
                    # Deduct entry fee
                    user.virtual_wallet.gem_coins -= tournament.entry_fee
                    
                    # Add to prize pool
                    tournament.total_prize_pool += tournament.entry_fee
                    
                    await session.commit()
            
            # Create participant
            participant = TournamentParticipant(
                user_id=user_id,
                username=user.username,
                avatar_url=getattr(user, 'avatar_url', None),
                joined_at=datetime.now()
            )
            
            # Add to tournament
            tournament.participants[user_id] = participant
            
            # Update prize structure with new prize pool
            tournament.prizes = self._generate_prize_structure(tournament.total_prize_pool, len(tournament.participants))
            
            # Save tournament
            await self._save_tournament(tournament)
            
            # Generate excitement message
            join_message = self._generate_join_excitement(tournament, len(tournament.participants))
            
            return {
                'success': True,
                'message': 'Successfully joined tournament!',
                'tournament': self._serialize_tournament(tournament),
                'participant_count': len(tournament.participants),
                'prize_pool': tournament.total_prize_pool,
                'your_entry_fee': tournament.entry_fee,
                'excitement_message': join_message,
                'tournament_starts_in': self._calculate_time_until(tournament.tournament_start)
            }
            
        except Exception as e:
            logger.error(f"Error joining tournament {tournament_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def start_tournament(self, tournament_id: str) -> Dict[str, Any]:
        """
        Start tournament when registration period ends.
        This transitions from preparation to active competition.
        """
        try:
            if tournament_id not in self.active_tournaments:
                return {'success': False, 'error': 'Tournament not found'}
            
            tournament = self.active_tournaments[tournament_id]
            
            # Check if ready to start
            if tournament.status != TournamentStatus.REGISTRATION:
                return {'success': False, 'error': 'Tournament not in registration state'}
            
            if datetime.now() < tournament.tournament_start:
                return {'success': False, 'error': 'Tournament start time not reached'}
            
            if len(tournament.participants) < tournament.min_participants:
                # Cancel tournament and refund
                await self._cancel_tournament_and_refund(tournament)
                return {'success': False, 'error': 'Insufficient participants - tournament cancelled and entry fees refunded'}
            
            # Initialize tournament based on type
            tournament.status = TournamentStatus.ACTIVE
            
            if tournament.tournament_type == TournamentType.ELIMINATION:
                await self._setup_elimination_bracket(tournament)
            elif tournament.tournament_type == TournamentType.LEADERBOARD:
                await self._setup_leaderboard_tournament(tournament)
            elif tournament.tournament_type == TournamentType.SURVIVAL:
                await self._setup_survival_tournament(tournament)
            
            # Save updated tournament
            await self._save_tournament(tournament)
            
            # Notify all participants
            await self._notify_tournament_start(tournament)
            
            return {
                'success': True,
                'message': 'Tournament started successfully!',
                'tournament': self._serialize_tournament(tournament),
                'participant_count': len(tournament.participants),
                'tournament_format': self._get_tournament_format_info(tournament),
                'first_round_details': await self._get_current_round_details(tournament)
            }
            
        except Exception as e:
            logger.error(f"Error starting tournament {tournament_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_tournament_standings(self, tournament_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        Get current tournament standings and leaderboard.
        This shows competitive progress and drives continued participation.
        """
        try:
            if tournament_id not in self.active_tournaments:
                return {'success': False, 'error': 'Tournament not found'}
            
            tournament = self.active_tournaments[tournament_id]
            
            # Sort participants by current performance
            sorted_participants = sorted(
                tournament.participants.values(),
                key=lambda p: (p.eliminated, -p.current_score, -p.wins, p.losses),
            )
            
            # Create standings
            standings = []
            for i, participant in enumerate(sorted_participants):
                position = i + 1
                
                # Determine if participant is in prize positions
                in_prize_position = any(
                    prize.position_range[0] <= position <= prize.position_range[1]
                    for prize in tournament.prizes
                )
                
                prize_info = None
                if in_prize_position:
                    for prize in tournament.prizes:
                        if prize.position_range[0] <= position <= prize.position_range[1]:
                            prize_info = {
                                'description': prize.description,
                                'amount': prize.amount,
                                'type': prize.prize_type
                            }
                            break
                
                standing = {
                    'position': position,
                    'user_id': participant.user_id,
                    'username': participant.username,
                    'avatar_url': participant.avatar_url,
                    'score': participant.current_score,
                    'games_played': participant.games_played,
                    'wins': participant.wins,
                    'losses': participant.losses,
                    'best_performance': participant.best_performance,
                    'eliminated': participant.eliminated,
                    'in_prize_position': in_prize_position,
                    'potential_prize': prize_info,
                    'is_current_user': participant.user_id == user_id if user_id else False
                }
                standings.append(standing)
            
            # Get user-specific context
            user_context = None
            if user_id and user_id in tournament.participants:
                user_participant = tournament.participants[user_id]
                user_position = next(i + 1 for i, p in enumerate(sorted_participants) if p.user_id == user_id)
                
                user_context = {
                    'current_position': user_position,
                    'score': user_participant.current_score,
                    'games_left': self._calculate_games_remaining(tournament, user_participant),
                    'can_improve_to': self._calculate_maximum_achievable_position(tournament, user_participant),
                    'elimination_risk': self._calculate_elimination_risk(tournament, user_participant)
                }
            
            return {
                'success': True,
                'tournament': {
                    'tournament_id': tournament.tournament_id,
                    'name': tournament.name,
                    'status': tournament.status.value,
                    'current_round': tournament.current_round,
                    'total_participants': len(tournament.participants),
                    'prize_pool': tournament.total_prize_pool
                },
                'standings': standings,
                'user_context': user_context,
                'prize_structure': [
                    {
                        'positions': f"{p.position_range[0]}-{p.position_range[1]}" if p.position_range[0] != p.position_range[1] else str(p.position_range[0]),
                        'description': p.description,
                        'amount': p.amount,
                        'type': p.prize_type
                    }
                    for p in tournament.prizes
                ],
                'tournament_progress': {
                    'time_remaining': self._calculate_time_until(tournament.tournament_end) if tournament.status == TournamentStatus.ACTIVE else None,
                    'completion_percentage': self._calculate_tournament_completion(tournament)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting tournament standings: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_featured_tournaments(self) -> Dict[str, Any]:
        """
        Get list of featured/upcoming tournaments.
        This drives discovery and participation in high-quality events.
        """
        try:
            featured_tournaments = []
            
            # Get currently active tournaments
            for tournament in self.active_tournaments.values():
                if tournament.status in [TournamentStatus.REGISTRATION, TournamentStatus.ACTIVE]:
                    tournament_data = self._serialize_tournament(tournament)
                    tournament_data['participant_count'] = len(tournament.participants)
                    tournament_data['spots_remaining'] = tournament.max_participants - len(tournament.participants)
                    tournament_data['time_until_start'] = self._calculate_time_until(tournament.tournament_start)
                    featured_tournaments.append(tournament_data)
            
            # Sort by various factors (prize pool, participants, time to start)
            featured_tournaments.sort(
                key=lambda t: (t['status'] == 'active', t['total_prize_pool'], t['participant_count']),
                reverse=True
            )
            
            # Get tournament statistics
            stats = await self._get_tournament_statistics()
            
            return {
                'success': True,
                'featured_tournaments': featured_tournaments[:10],  # Top 10 featured
                'daily_schedule': await self._get_daily_tournament_schedule(),
                'statistics': stats,
                'quick_join_options': await self._get_quick_join_tournaments()
            }
            
        except Exception as e:
            logger.error(f"Error getting featured tournaments: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_prize_structure(self, total_prize_pool: int, participant_count: int) -> List[TournamentPrize]:
        """Generate dynamic prize structure based on prize pool and participants"""
        if participant_count <= 20:
            template = self.prize_distributions['small_tournament']
        elif participant_count <= 50:
            template = self.prize_distributions['medium_tournament']  
        else:
            template = self.prize_distributions['large_tournament']
        
        prizes = []
        for prize_template in template:
            amount = int(total_prize_pool * prize_template.amount / 100)
            if amount > 0:  # Only include prizes with actual value
                prize = TournamentPrize(
                    position_range=prize_template.position_range,
                    prize_type=prize_template.prize_type,
                    amount=amount,
                    description=prize_template.description
                )
                prizes.append(prize)
        
        return prizes
    
    def _generate_join_excitement(self, tournament: Tournament, participant_count: int) -> str:
        """Generate excitement message for joining tournament"""
        if tournament.total_prize_pool > 100000:
            return f"🚀 Welcome to the BIG LEAGUES! {tournament.total_prize_pool:,} GEM coin prize pool with {participant_count} competitors!"
        elif participant_count > 50:
            return f"⚡ MASSIVE TOURNAMENT! You're one of {participant_count} brave competitors fighting for {tournament.total_prize_pool:,} GEM coins!"
        elif tournament.game_mode == GameMode.CRASH:
            return f"💥 Crash Championship joined! {participant_count} pilots ready to fly for {tournament.total_prize_pool:,} GEM coins!"
        else:
            return f"🎯 Tournament entry confirmed! {participant_count} players, {tournament.total_prize_pool:,} GEM coin prize pool. Good luck!"
    
    def _calculate_time_until(self, target_time: datetime) -> str:
        """Calculate human-readable time until target"""
        diff = target_time - datetime.now()
        
        if diff.total_seconds() < 0:
            return "Now"
        elif diff.days > 0:
            return f"{diff.days}d {diff.seconds//3600}h"
        elif diff.seconds > 3600:
            return f"{diff.seconds//3600}h {(diff.seconds%3600)//60}m"
        else:
            return f"{diff.seconds//60}m"
    
    def _serialize_tournament(self, tournament: Tournament) -> Dict[str, Any]:
        """Convert tournament object to dictionary"""
        return {
            'tournament_id': tournament.tournament_id,
            'name': tournament.name,
            'description': tournament.description,
            'tournament_type': tournament.tournament_type.value,
            'game_mode': tournament.game_mode.value,
            'status': tournament.status.value,
            'max_participants': tournament.max_participants,
            'min_participants': tournament.min_participants,
            'entry_type': tournament.entry_type.value,
            'entry_fee': tournament.entry_fee,
            'total_prize_pool': tournament.total_prize_pool,
            'registration_end': tournament.registration_end.isoformat(),
            'tournament_start': tournament.tournament_start.isoformat(),
            'tournament_end': tournament.tournament_end.isoformat(),
            'is_featured': tournament.is_featured,
            'current_round': tournament.current_round
        }

# Global tournament system
tournament_system = TournamentSystem()