"""
Security manager for roulette gaming system.
Enhanced security features inspired by professional gaming platforms.
"""

import asyncio
import hashlib
import ipaddress
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from .models import GameSession, GameBet
from auth.models import User, UserSession
from logger import logger


class SecurityLevel(Enum):
    """Security threat levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security event record."""
    user_id: Optional[str]
    ip_address: str
    event_type: str
    severity: SecurityLevel
    details: Dict[str, Any]
    timestamp: datetime
    action_taken: Optional[str] = None


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    max_requests: int
    time_window: int  # seconds
    blocked_duration: int  # seconds


class EnhancedSecurityManager:
    """Enhanced security manager with comprehensive protection."""
    
    def __init__(self):
        # Rate limiting configuration
        self.rate_limits = {
            "bet_placement": RateLimitRule(20, 60, 300),      # 20 bets per minute
            "game_creation": RateLimitRule(10, 300, 600),     # 10 games per 5 minutes
            "spin_requests": RateLimitRule(15, 60, 300),      # 15 spins per minute
            "websocket_messages": RateLimitRule(100, 60, 180), # 100 messages per minute
            "api_requests": RateLimitRule(200, 60, 120),      # 200 API calls per minute
            "login_attempts": RateLimitRule(5, 300, 900)      # 5 login attempts per 5 minutes
        }
        
        # Track user activity
        self.user_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.ip_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.blocked_ips: Dict[str, datetime] = {}
        self.blocked_users: Dict[str, datetime] = {}
        
        # Security events
        self.security_events: deque = deque(maxlen=10000)
        
        # Pattern detection
        self.suspicious_patterns = {
            "rapid_betting": {"threshold": 10, "window": 30},
            "consistent_amounts": {"threshold": 20, "tolerance": 0.1},
            "timing_patterns": {"threshold": 15, "variance": 2.0},
            "unusual_wins": {"threshold": 5, "win_rate": 0.8}
        }
        
        # Anti-bot measures
        self.bot_detection_enabled = True
        self.captcha_required_events = {"high_volume_betting", "suspicious_pattern"}
        
    async def validate_bet_request(
        self,
        session: AsyncSession,
        user_id: str,
        ip_address: str,
        bet_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Comprehensive bet request validation."""
        
        # Rate limiting check
        if not await self._check_rate_limit(user_id, ip_address, "bet_placement"):
            await self._log_security_event(
                user_id, ip_address, "rate_limit_exceeded",
                SecurityLevel.MEDIUM, {"action": "bet_placement"}
            )
            return False, "Rate limit exceeded. Please slow down your betting."
        
        # Input validation
        validation_result = self._validate_bet_input(bet_data)
        if not validation_result[0]:
            await self._log_security_event(
                user_id, ip_address, "invalid_input",
                SecurityLevel.LOW, {"error": validation_result[1], "data": bet_data}
            )
            return False, validation_result[1]
        
        # Pattern detection
        pattern_result = await self._detect_betting_patterns(session, user_id, bet_data)
        if not pattern_result[0]:
            await self._log_security_event(
                user_id, ip_address, "suspicious_pattern",
                SecurityLevel.HIGH, {"pattern": pattern_result[1], "data": bet_data}
            )
            return False, f"Suspicious betting pattern detected: {pattern_result[1]}"
        
        # Anti-bot verification
        if await self._requires_verification(user_id, ip_address):
            return False, "Additional verification required. Please complete captcha."
        
        # Record activity
        self._record_activity(user_id, ip_address, "bet_placement", bet_data)
        
        return True, None
    
    async def validate_game_session(
        self,
        session: AsyncSession,
        user_id: str,
        ip_address: str,
        game_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate game session creation."""
        
        # Rate limiting
        if not await self._check_rate_limit(user_id, ip_address, "game_creation"):
            return False, "Too many game sessions created. Please wait before creating a new game."
        
        # Check for concurrent games
        active_games = await self._count_active_games(session, user_id)
        if active_games >= 3:  # Limit concurrent games
            await self._log_security_event(
                user_id, ip_address, "excessive_concurrent_games",
                SecurityLevel.MEDIUM, {"active_games": active_games}
            )
            return False, "Too many active games. Please complete existing games first."
        
        # Validate session parameters
        if game_data.get("client_seed_input"):
            if not self._validate_client_seed(game_data["client_seed_input"]):
                return False, "Invalid client seed format."
        
        self._record_activity(user_id, ip_address, "game_creation", game_data)
        
        return True, None
    
    async def validate_spin_request(
        self,
        session: AsyncSession,
        user_id: str,
        ip_address: str,
        game_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate wheel spin request."""
        
        # Rate limiting
        if not await self._check_rate_limit(user_id, ip_address, "spin_requests"):
            return False, "Spinning too frequently. Please wait between spins."
        
        # Validate game state
        game_validation = await self._validate_game_state(session, user_id, game_id)
        if not game_validation[0]:
            await self._log_security_event(
                user_id, ip_address, "invalid_game_state",
                SecurityLevel.MEDIUM, {"game_id": game_id, "error": game_validation[1]}
            )
            return False, game_validation[1]
        
        # Check minimum bet requirement
        bet_validation = await self._validate_minimum_bets(session, game_id)
        if not bet_validation[0]:
            return False, bet_validation[1]
        
        self._record_activity(user_id, ip_address, "spin_request", {"game_id": game_id})
        
        return True, None
    
    async def validate_websocket_message(
        self,
        user_id: str,
        ip_address: str,
        message: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate WebSocket message."""
        
        # Rate limiting for WebSocket messages
        if not await self._check_rate_limit(user_id, ip_address, "websocket_messages"):
            return False, "Message rate limit exceeded."
        
        # Message validation
        if not self._validate_websocket_message_format(message):
            await self._log_security_event(
                user_id, ip_address, "invalid_websocket_message",
                SecurityLevel.LOW, {"message": message}
            )
            return False, "Invalid message format."
        
        # Content filtering
        if message.get("type") == "chat_message":
            if not self._validate_chat_message(message.get("message", "")):
                return False, "Message contains inappropriate content."
        
        self._record_activity(user_id, ip_address, "websocket_message", message)
        
        return True, None
    
    async def check_user_security_status(
        self,
        session: AsyncSession,
        user_id: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """Check comprehensive user security status."""
        
        # Check if user or IP is blocked
        user_blocked = await self._is_user_blocked(user_id)
        ip_blocked = await self._is_ip_blocked(ip_address)
        
        # Get recent security events
        recent_events = self._get_recent_security_events(user_id, ip_address)
        
        # Calculate risk score
        risk_score = await self._calculate_risk_score(session, user_id, ip_address)
        
        # Check required actions
        required_actions = await self._get_required_security_actions(user_id, risk_score)
        
        return {
            "user_id": user_id,
            "ip_address": ip_address,
            "blocked": user_blocked or ip_blocked,
            "risk_score": risk_score,
            "recent_events_count": len(recent_events),
            "required_actions": required_actions,
            "restrictions": self._get_current_restrictions(user_id, ip_address),
            "last_checked": datetime.utcnow().isoformat()
        }
    
    # Private helper methods
    
    async def _check_rate_limit(
        self,
        user_id: str,
        ip_address: str,
        action_type: str
    ) -> bool:
        """Check if action is within rate limits."""
        
        if action_type not in self.rate_limits:
            return True
        
        rule = self.rate_limits[action_type]
        current_time = time.time()
        
        # Check user-based rate limit
        user_actions = self.user_activity[f"{user_id}:{action_type}"]
        
        # Remove old actions outside time window
        while user_actions and current_time - user_actions[0] > rule.time_window:
            user_actions.popleft()
        
        # Check if limit exceeded
        if len(user_actions) >= rule.max_requests:
            # Block user temporarily
            self.blocked_users[user_id] = datetime.utcnow() + timedelta(seconds=rule.blocked_duration)
            return False
        
        # Record current action
        user_actions.append(current_time)
        
        # Also check IP-based rate limit
        ip_actions = self.ip_activity[f"{ip_address}:{action_type}"]
        
        while ip_actions and current_time - ip_actions[0] > rule.time_window:
            ip_actions.popleft()
        
        if len(ip_actions) >= rule.max_requests * 2:  # More lenient for IP
            self.blocked_ips[ip_address] = datetime.utcnow() + timedelta(seconds=rule.blocked_duration)
            return False
        
        ip_actions.append(current_time)
        
        return True
    
    def _validate_bet_input(self, bet_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate bet input data."""
        
        required_fields = ["bet_type", "bet_value", "bet_amount"]
        
        # Check required fields
        for field in required_fields:
            if field not in bet_data:
                return False, f"Missing required field: {field}"
        
        # Validate bet amount
        try:
            amount = float(bet_data["bet_amount"])
            if amount <= 0:
                return False, "Bet amount must be positive"
            if amount > 50000:  # Maximum bet limit
                return False, "Bet amount exceeds maximum limit"
        except (ValueError, TypeError):
            return False, "Invalid bet amount format"
        
        # Validate bet type
        valid_bet_types = [
            "SINGLE_CRYPTO", "CRYPTO_COLOR", "CRYPTO_CATEGORY", 
            "EVEN_ODD", "HIGH_LOW", "DOZEN", "COLUMN"
        ]
        if bet_data["bet_type"] not in valid_bet_types:
            return False, "Invalid bet type"
        
        # Validate bet value format
        bet_value = str(bet_data["bet_value"])
        if len(bet_value) > 50:  # Reasonable limit
            return False, "Bet value too long"
        
        # Check for SQL injection patterns
        dangerous_patterns = ["'", "\"", ";", "--", "/*", "*/", "xp_", "sp_"]
        if any(pattern in bet_value.lower() for pattern in dangerous_patterns):
            return False, "Invalid characters in bet value"
        
        return True, None
    
    async def _detect_betting_patterns(
        self,
        session: AsyncSession,
        user_id: str,
        bet_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Detect suspicious betting patterns."""
        
        # Get recent bets for pattern analysis
        recent_bets = await session.execute(
            select(GameBet)
            .join(GameSession)
            .where(
                and_(
                    GameBet.user_id == user_id,
                    GameBet.placed_at >= datetime.utcnow() - timedelta(hours=1)
                )
            )
            .order_by(desc(GameBet.placed_at))
            .limit(50)
        )
        
        bets = recent_bets.scalars().all()
        
        if len(bets) < 5:  # Not enough data for pattern detection
            return True, None
        
        # Check for rapid betting pattern
        if len(bets) >= self.suspicious_patterns["rapid_betting"]["threshold"]:
            time_span = (bets[0].placed_at - bets[-1].placed_at).total_seconds()
            if time_span < self.suspicious_patterns["rapid_betting"]["window"]:
                return False, "rapid_betting"
        
        # Check for consistent bet amounts (possible bot behavior)
        bet_amounts = [bet.bet_amount for bet in bets[-20:]]  # Last 20 bets
        if len(set(bet_amounts)) == 1 and len(bet_amounts) >= self.suspicious_patterns["consistent_amounts"]["threshold"]:
            return False, "consistent_amounts"
        
        # Check for timing patterns
        time_intervals = []
        for i in range(1, min(len(bets), 15)):
            interval = (bets[i-1].placed_at - bets[i].placed_at).total_seconds()
            time_intervals.append(interval)
        
        if len(time_intervals) >= 10:
            avg_interval = sum(time_intervals) / len(time_intervals)
            variance = sum((x - avg_interval) ** 2 for x in time_intervals) / len(time_intervals)
            if variance < self.suspicious_patterns["timing_patterns"]["variance"]:
                return False, "timing_patterns"
        
        return True, None
    
    async def _requires_verification(self, user_id: str, ip_address: str) -> bool:
        """Check if user requires additional verification."""
        
        # Check recent security events
        recent_events = self._get_recent_security_events(user_id, ip_address, hours=24)
        
        # Require verification if there are high-severity events
        high_severity_events = [
            event for event in recent_events 
            if event.severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]
        ]
        
        if len(high_severity_events) >= 3:
            return True
        
        # Check bot detection score
        if self._calculate_bot_probability(user_id) > 0.7:
            return True
        
        return False
    
    def _record_activity(
        self,
        user_id: str,
        ip_address: str,
        action_type: str,
        data: Dict[str, Any]
    ):
        """Record user activity for monitoring."""
        
        activity_record = {
            "timestamp": time.time(),
            "user_id": user_id,
            "ip_address": ip_address,
            "action_type": action_type,
            "data": data
        }
        
        # Store in appropriate queues
        self.user_activity[user_id].append(activity_record)
        self.ip_activity[ip_address].append(activity_record)
    
    async def _log_security_event(
        self,
        user_id: Optional[str],
        ip_address: str,
        event_type: str,
        severity: SecurityLevel,
        details: Dict[str, Any],
        action_taken: Optional[str] = None
    ):
        """Log security event."""
        
        event = SecurityEvent(
            user_id=user_id,
            ip_address=ip_address,
            event_type=event_type,
            severity=severity,
            details=details,
            timestamp=datetime.utcnow(),
            action_taken=action_taken
        )
        
        self.security_events.append(event)
        
        # Log to system logger
        logger.warning(
            f"Security Event: {event_type} | "
            f"User: {user_id} | IP: {ip_address} | "
            f"Severity: {severity.value} | Details: {details}"
        )
        
        # Take automatic action for critical events
        if severity == SecurityLevel.CRITICAL:
            await self._handle_critical_security_event(event)
    
    async def _handle_critical_security_event(self, event: SecurityEvent):
        """Handle critical security events automatically."""
        
        if event.user_id:
            # Temporarily block user
            self.blocked_users[event.user_id] = datetime.utcnow() + timedelta(hours=1)
        
        # Block IP for repeated offenses
        self.blocked_ips[event.ip_address] = datetime.utcnow() + timedelta(minutes=30)
        
        logger.critical(f"Critical security event handled: {event.event_type}")
    
    def _get_recent_security_events(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        hours: int = 1
    ) -> List[SecurityEvent]:
        """Get recent security events for user or IP."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        events = []
        for event in self.security_events:
            if event.timestamp < cutoff_time:
                continue
            
            if user_id and event.user_id == user_id:
                events.append(event)
            elif ip_address and event.ip_address == ip_address:
                events.append(event)
        
        return events
    
    async def _calculate_risk_score(
        self,
        session: AsyncSession,
        user_id: str,
        ip_address: str
    ) -> float:
        """Calculate user risk score (0-100)."""
        
        risk_factors = []
        
        # Recent security events
        recent_events = self._get_recent_security_events(user_id, ip_address, hours=24)
        event_score = min(50, len(recent_events) * 5)
        risk_factors.append(event_score)
        
        # Bot probability
        bot_score = self._calculate_bot_probability(user_id) * 30
        risk_factors.append(bot_score)
        
        # Activity patterns
        activity_score = self._calculate_activity_risk(user_id) * 20
        risk_factors.append(activity_score)
        
        # Calculate weighted average
        total_risk = sum(risk_factors)
        return min(100, total_risk)
    
    def _calculate_bot_probability(self, user_id: str) -> float:
        """Calculate probability that user is a bot (0-1)."""
        
        user_actions = list(self.user_activity[user_id])
        if len(user_actions) < 10:
            return 0.0
        
        # Analyze timing patterns
        intervals = []
        for i in range(1, min(len(user_actions), 20)):
            interval = user_actions[i]["timestamp"] - user_actions[i-1]["timestamp"]
            intervals.append(interval)
        
        if not intervals:
            return 0.0
        
        # Calculate variance in timing
        avg_interval = sum(intervals) / len(intervals)
        variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
        
        # Low variance suggests bot behavior
        bot_probability = max(0, 1 - (variance / avg_interval))
        
        return min(1, bot_probability)


# Global security manager instance
security_manager = EnhancedSecurityManager()