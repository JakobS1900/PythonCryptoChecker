"""
Enhanced Authentication System with JWT/OAuth and Web3 Integration
Modern authentication supporting traditional OAuth, JWT tokens, and Web3 wallet connections.
Based on 2024 research for crypto platforms requiring multiple authentication methods.
"""
import asyncio
import hashlib
import secrets
import json
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
import aiohttp
from eth_account.messages import encode_defunct
from eth_account import Account
from web3 import Web3
import re

from database import get_db_session, User, VirtualWallet
from logger import logger

class AuthProvider(Enum):
    EMAIL_PASSWORD = "email_password"
    GOOGLE_OAUTH = "google_oauth"
    DISCORD_OAUTH = "discord_oauth"
    TWITTER_OAUTH = "twitter_oauth"
    METAMASK = "metamask"
    WALLETCONNECT = "walletconnect"
    COINBASE_WALLET = "coinbase_wallet"
    PHANTOM = "phantom"

class SessionType(Enum):
    WEB = "web"
    MOBILE = "mobile"
    API = "api"

@dataclass
class AuthToken:
    """JWT authentication token with metadata"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1 hour
    refresh_expires_in: int = 2592000  # 30 days
    issued_at: datetime = None
    user_id: str = None

@dataclass
class Web3AuthChallenge:
    """Web3 wallet authentication challenge"""
    challenge_id: str
    wallet_address: str
    message: str
    nonce: str
    expires_at: datetime
    provider: AuthProvider

@dataclass
class OAuthConfig:
    """OAuth provider configuration"""
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    user_info_url: str
    scopes: List[str]

class EnhancedAuthManager:
    """
    Multi-modal authentication manager supporting:
    - Traditional email/password with JWT
    - OAuth (Google, Discord, Twitter)
    - Web3 wallet authentication (MetaMask, WalletConnect, etc.)
    - Multi-factor authentication
    - Session management across devices
    """
    
    def __init__(self, jwt_secret: str):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = "HS256"
        self.access_token_expire = timedelta(hours=1)
        self.refresh_token_expire = timedelta(days=30)
        
        # Web3 authentication challenges (temporary storage)
        self.auth_challenges: Dict[str, Web3AuthChallenge] = {}
        
        # OAuth configurations
        self.oauth_configs = {
            AuthProvider.GOOGLE_OAUTH: OAuthConfig(
                client_id="your_google_client_id",
                client_secret="your_google_client_secret",
                authorization_url="https://accounts.google.com/o/oauth2/auth",
                token_url="https://oauth2.googleapis.com/token",
                user_info_url="https://www.googleapis.com/oauth2/v2/userinfo",
                scopes=["openid", "email", "profile"]
            ),
            AuthProvider.DISCORD_OAUTH: OAuthConfig(
                client_id="your_discord_client_id",
                client_secret="your_discord_client_secret",
                authorization_url="https://discord.com/api/oauth2/authorize",
                token_url="https://discord.com/api/oauth2/token",
                user_info_url="https://discord.com/api/users/@me",
                scopes=["identify", "email"]
            ),
            AuthProvider.TWITTER_OAUTH: OAuthConfig(
                client_id="your_twitter_client_id",
                client_secret="your_twitter_client_secret",
                authorization_url="https://twitter.com/i/oauth2/authorize",
                token_url="https://api.twitter.com/2/oauth2/token",
                user_info_url="https://api.twitter.com/2/users/me",
                scopes=["tweet.read", "users.read"]
            )
        }
    
    async def authenticate_email_password(self, email: str, password: str, 
                                        session_type: SessionType = SessionType.WEB,
                                        device_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Traditional email/password authentication with enhanced security.
        """
        try:
            if not self._validate_email(email):
                return {'success': False, 'error': 'Invalid email format'}
            
            if len(password) < 8:
                return {'success': False, 'error': 'Password must be at least 8 characters'}
            
            # Check user credentials
            async with get_db_session() as session:
                # Query user by email (this would use proper user model)
                user_query = select(User).where(User.email == email)
                result = await session.execute(user_query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return {'success': False, 'error': 'Invalid credentials'}
                
                # Verify password (assuming password_hash field exists)
                if not self._verify_password(password, user.password_hash):
                    # Update failed login attempts
                    await self._record_failed_login(user.id, "invalid_password")
                    return {'success': False, 'error': 'Invalid credentials'}
                
                # Check account status
                if user.status != "active":
                    return {'success': False, 'error': 'Account is suspended or inactive'}
                
                # Generate JWT tokens
                tokens = await self._generate_jwt_tokens(user.id, session_type)
                
                # Create session record
                session_id = await self._create_user_session(user.id, session_type, device_info, tokens.access_token)
                
                # Update last login
                user.last_login = datetime.now()
                await session.commit()
                
                # Return authentication success
                return {
                    'success': True,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'level': user.virtual_wallet.level if user.virtual_wallet else 1,
                        'gem_coins': user.virtual_wallet.gem_coins if user.virtual_wallet else 0
                    },
                    'tokens': {
                        'access_token': tokens.access_token,
                        'refresh_token': tokens.refresh_token,
                        'token_type': tokens.token_type,
                        'expires_in': tokens.expires_in
                    },
                    'session_id': session_id,
                    'authentication_method': 'email_password'
                }
                
        except Exception as e:
            logger.error(f"Error in email/password authentication: {e}")
            return {'success': False, 'error': 'Authentication failed'}
    
    async def initiate_web3_auth(self, wallet_address: str, provider: AuthProvider) -> Dict[str, Any]:
        """
        Initiate Web3 wallet authentication by generating a challenge message.
        This is the first step in crypto wallet authentication.
        """
        try:
            if not self._validate_wallet_address(wallet_address, provider):
                return {'success': False, 'error': 'Invalid wallet address format'}
            
            # Generate unique challenge
            challenge_id = secrets.token_urlsafe(32)
            nonce = secrets.token_hex(16)
            
            # Create challenge message
            challenge_message = self._create_web3_challenge_message(wallet_address, nonce)
            
            # Store challenge (expires in 10 minutes)
            challenge = Web3AuthChallenge(
                challenge_id=challenge_id,
                wallet_address=wallet_address.lower(),
                message=challenge_message,
                nonce=nonce,
                expires_at=datetime.now() + timedelta(minutes=10),
                provider=provider
            )
            
            self.auth_challenges[challenge_id] = challenge
            
            return {
                'success': True,
                'challenge_id': challenge_id,
                'message': challenge_message,
                'wallet_address': wallet_address,
                'provider': provider.value,
                'expires_in': 600  # 10 minutes
            }
            
        except Exception as e:
            logger.error(f"Error initiating Web3 auth: {e}")
            return {'success': False, 'error': 'Failed to create authentication challenge'}
    
    async def verify_web3_signature(self, challenge_id: str, signature: str, 
                                  session_type: SessionType = SessionType.WEB,
                                  device_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Verify Web3 wallet signature and complete authentication.
        """
        try:
            if challenge_id not in self.auth_challenges:
                return {'success': False, 'error': 'Invalid or expired challenge'}
            
            challenge = self.auth_challenges[challenge_id]
            
            if datetime.now() > challenge.expires_at:
                del self.auth_challenges[challenge_id]
                return {'success': False, 'error': 'Challenge expired'}
            
            # Verify signature
            is_valid = await self._verify_web3_signature(
                challenge.message, 
                signature, 
                challenge.wallet_address,
                challenge.provider
            )
            
            if not is_valid:
                return {'success': False, 'error': 'Invalid signature'}
            
            # Clean up challenge
            del self.auth_challenges[challenge_id]
            
            # Find or create user with this wallet
            async with get_db_session() as session:
                user = await self._get_or_create_web3_user(
                    challenge.wallet_address, 
                    challenge.provider
                )
                
                # Generate JWT tokens
                tokens = await self._generate_jwt_tokens(user.id, session_type)
                
                # Create session record
                session_id = await self._create_user_session(
                    user.id, session_type, device_info, tokens.access_token
                )
                
                # Update last login
                user.last_login = datetime.now()
                await session.commit()
                
                return {
                    'success': True,
                    'user': {
                        'id': user.id,
                        'wallet_address': challenge.wallet_address,
                        'username': user.username,
                        'level': user.virtual_wallet.level if user.virtual_wallet else 1,
                        'gem_coins': user.virtual_wallet.gem_coins if user.virtual_wallet else 0,
                        'is_new_user': user.created_at > datetime.now() - timedelta(minutes=5)
                    },
                    'tokens': {
                        'access_token': tokens.access_token,
                        'refresh_token': tokens.refresh_token,
                        'token_type': tokens.token_type,
                        'expires_in': tokens.expires_in
                    },
                    'session_id': session_id,
                    'authentication_method': challenge.provider.value
                }
                
        except Exception as e:
            logger.error(f"Error verifying Web3 signature: {e}")
            return {'success': False, 'error': 'Signature verification failed'}
    
    async def oauth_login(self, provider: AuthProvider, authorization_code: str,
                         redirect_uri: str, session_type: SessionType = SessionType.WEB,
                         device_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Complete OAuth authentication flow (Google, Discord, Twitter).
        """
        try:
            if provider not in self.oauth_configs:
                return {'success': False, 'error': 'Unsupported OAuth provider'}
            
            config = self.oauth_configs[provider]
            
            # Exchange authorization code for access token
            token_data = await self._exchange_oauth_code(config, authorization_code, redirect_uri)
            if not token_data:
                return {'success': False, 'error': 'Failed to exchange authorization code'}
            
            # Get user info from OAuth provider
            user_info = await self._get_oauth_user_info(config, token_data['access_token'])
            if not user_info:
                return {'success': False, 'error': 'Failed to retrieve user information'}
            
            # Find or create user
            user = await self._get_or_create_oauth_user(provider, user_info)
            
            # Generate JWT tokens
            tokens = await self._generate_jwt_tokens(user.id, session_type)
            
            # Create session record
            session_id = await self._create_user_session(
                user.id, session_type, device_info, tokens.access_token
            )
            
            # Update last login
            async with get_db_session() as session:
                user.last_login = datetime.now()
                await session.commit()
            
            return {
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'avatar_url': user.avatar_url,
                    'level': user.virtual_wallet.level if user.virtual_wallet else 1,
                    'gem_coins': user.virtual_wallet.gem_coins if user.virtual_wallet else 0,
                    'oauth_provider': provider.value
                },
                'tokens': {
                    'access_token': tokens.access_token,
                    'refresh_token': tokens.refresh_token,
                    'token_type': tokens.token_type,
                    'expires_in': tokens.expires_in
                },
                'session_id': session_id,
                'authentication_method': provider.value
            }
            
        except Exception as e:
            logger.error(f"Error in OAuth login: {e}")
            return {'success': False, 'error': 'OAuth authentication failed'}
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh expired access token using refresh token.
        """
        try:
            # Decode refresh token
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            if payload['type'] != 'refresh':
                return {'success': False, 'error': 'Invalid token type'}
            
            user_id = payload['user_id']
            
            # Verify user still exists and is active
            async with get_db_session() as session:
                user = await session.get(User, user_id)
                if not user or user.status != "active":
                    return {'success': False, 'error': 'User not found or inactive'}
            
            # Generate new access token
            access_token = self._create_access_token(user_id)
            
            return {
                'success': True,
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': 3600
            }
            
        except jwt.ExpiredSignatureError:
            return {'success': False, 'error': 'Refresh token expired'}
        except jwt.InvalidTokenError:
            return {'success': False, 'error': 'Invalid refresh token'}
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return {'success': False, 'error': 'Token refresh failed'}
    
    async def verify_access_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT access token.
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            if payload['type'] != 'access':
                return {'success': False, 'error': 'Invalid token type'}
            
            return {
                'success': True,
                'user_id': payload['user_id'],
                'session_id': payload.get('session_id'),
                'expires_at': payload['exp']
            }
            
        except jwt.ExpiredSignatureError:
            return {'success': False, 'error': 'Token expired'}
        except jwt.InvalidTokenError:
            return {'success': False, 'error': 'Invalid token'}
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return {'success': False, 'error': 'Token verification failed'}
    
    def _create_web3_challenge_message(self, wallet_address: str, nonce: str) -> str:
        """Create a challenge message for Web3 wallet signing"""
        return f"""Welcome to Crypto Gamification Platform!

Please sign this message to verify your wallet ownership.

Wallet: {wallet_address}
Nonce: {nonce}
Timestamp: {datetime.now().isoformat()}

This signature will not trigger any blockchain transaction or cost any gas fees."""
    
    async def _verify_web3_signature(self, message: str, signature: str, 
                                   wallet_address: str, provider: AuthProvider) -> bool:
        """Verify Web3 wallet signature"""
        try:
            if provider in [AuthProvider.METAMASK, AuthProvider.WALLETCONNECT, AuthProvider.COINBASE_WALLET]:
                # Ethereum-style signature verification
                message_hash = encode_defunct(text=message)
                recovered_address = Account.recover_message(message_hash, signature=signature)
                return recovered_address.lower() == wallet_address.lower()
            
            elif provider == AuthProvider.PHANTOM:
                # Solana wallet signature verification (simplified)
                # In real implementation, use solana-py library
                return True  # Placeholder
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying Web3 signature: {e}")
            return False
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_wallet_address(self, address: str, provider: AuthProvider) -> bool:
        """Validate wallet address format"""
        if provider in [AuthProvider.METAMASK, AuthProvider.WALLETCONNECT, AuthProvider.COINBASE_WALLET]:
            # Ethereum address validation
            return len(address) == 42 and address.startswith('0x')
        elif provider == AuthProvider.PHANTOM:
            # Solana address validation (simplified)
            return len(address) >= 32 and len(address) <= 44
        
        return False
    
    async def _generate_jwt_tokens(self, user_id: str, session_type: SessionType) -> AuthToken:
        """Generate JWT access and refresh tokens"""
        now = datetime.utcnow()
        
        # Access token payload
        access_payload = {
            'user_id': user_id,
            'type': 'access',
            'session_type': session_type.value,
            'iat': now,
            'exp': now + self.access_token_expire
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user_id,
            'type': 'refresh',
            'iat': now,
            'exp': now + self.refresh_token_expire
        }
        
        access_token = jwt.encode(access_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        return AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(self.access_token_expire.total_seconds()),
            refresh_expires_in=int(self.refresh_token_expire.total_seconds()),
            issued_at=now,
            user_id=user_id
        )

# Global enhanced auth manager
enhanced_auth = EnhancedAuthManager(jwt_secret="your-super-secret-jwt-key-change-in-production")