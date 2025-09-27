"""
Crypto Clicker API - A fun way to earn gems through clicking
"""
import os
import random
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db
from database.models import User
from database.models import Wallet, Transaction
from sqlalchemy import select, update
import time

router = APIRouter()

# JWT config (align with auth_api)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
security = HTTPBearer(auto_error=False)

# Anti-spam protection
MIN_CLICK_INTERVAL = 0.2  # Minimum 200ms between clicks
last_clicks = {}

@router.post("/click")
async def handle_click(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_db)
):
    """Handle a crypto click and award gems"""
    try:
        # Check for JWT in Authorization header first
        user_id = None
        auth_token = None

        if credentials and credentials.credentials:
            try:
                payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("sub")
                auth_token = credentials.credentials
                print(f">> Clicker: JWT validated for user {user_id}")
            except JWTError as e:
                print(f">> Clicker: JWT validation failed: {e}")

        # Fall back to session-based auth
        if not user_id:
            # Try reading token from JSON body as fallback (client may send token in body)
            # Try session-based auth if JWT not present
            user_id = request.session.get("user_id")
            auth_token = request.session.get("auth_token")

        if not user_id or not auth_token:
            print(">> Click auth failed: no user_id/token")
            print(">> Session:", dict(request.session))
            return {
                "status": "error",
                "message": "Not authenticated",
                "details": "Please log in or enter as guest to play"
            }

        # Validate user exists
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return {
                "status": "error",
                "message": "User not found"
            }

        # Anti-spam check
        now = time.time()
        last_click = last_clicks.get(user_id, 0)
        if now - last_click < MIN_CLICK_INTERVAL:
            return {
                "status": "error",
                "message": "Clicking too fast!"
            }
        last_clicks[user_id] = now

        # Get or create wallet
        wallet_result = await session.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()

        if not wallet:
            # Create new wallet
            wallet = Wallet(
                user_id=user_id,
                gem_balance=1000.0,  # Starting bonus
                total_deposited=1000.0
            )
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)

        # Calculate rewards
        base_reward = random.randint(10, 100)
        bonus_roll = random.random()

        if bonus_roll < 0.01:  # 1% chance
            bonus = 100  # MEGA Bonus
            message = f"+{base_reward + bonus} GEM (MEGA BONUS!)"
        elif bonus_roll < 0.05:  # 4% chance
            bonus = 50   # Big Bonus
            message = f"+{base_reward + bonus} GEM (Big Bonus!)"
        elif bonus_roll < 0.15:  # 10% chance
            bonus = 25   # Medium Bonus
            message = f"+{base_reward + bonus} GEM (Medium Bonus!)"
        else:
            bonus = 0
            message = f"+{base_reward} GEM"

        total_reward = base_reward + bonus

        # Update wallet
        await session.execute(
            update(Wallet)
            .where(Wallet.user_id == user_id)
            .values(
                gem_balance=wallet.gem_balance + total_reward,
                total_deposited=wallet.total_deposited + total_reward
            )
        )

        # Record transaction
        transaction = Transaction(
            user_id=user_id,
            amount=total_reward,
            balance_before=wallet.gem_balance - total_reward,
            balance_after=wallet.gem_balance,
            transaction_type="BONUS",
            description=f"Click reward: {message}"
        )
        session.add(transaction)
        
        # Save changes
        await session.commit()
        await session.refresh(wallet)

        return {
            "status": "success",
            "data": {
                "reward": total_reward,
                "new_balance": wallet.gem_balance,
                "message": message
            }
        }

    except Exception as e:
        print(f">> Error in crypto_click: {str(e)}")
        return {
            "status": "error",
            "message": "An error occurred processing your click"
        }


@router.get("/balance")
async def get_balance(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_db)
):
    """Get current user's GEM coin balance."""
    try:
        # Validate authentication
        user_id = None
        if credentials and credentials.credentials:
            try:
                payload = jwt.decode(
                    credentials.credentials,
                    SECRET_KEY,
                    algorithms=[ALGORITHM]
                )
                user_id = payload.get("sub")
            except JWTError as e:
                print(f">> Balance check JWT validation failed: {e}")
        
        if not user_id:
            user_id = request.session.get("user_id")
        
        if not user_id:
            return {
                "status": "error",
                "message": "Not authenticated"
            }

        # Get wallet
        wallet_result = await session.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()

        if not wallet:
            # Create new wallet
            wallet = Wallet(
                user_id=user_id,
                gem_balance=1000.0,  # Starting bonus
                total_deposited=1000.0
            )
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)

        return {
            "status": "success",
            "data": {
                "gem_coins": wallet.gem_balance,
                "total_earned": wallet.total_deposited
            }
        }

    except Exception as e:
        print(f">> Error in get_balance: {str(e)}")
        return {
            "status": "error",
            "message": "Failed to retrieve balance"
        }
