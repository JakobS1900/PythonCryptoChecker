__all__ = ["get_current_user"]
"""
Authentication API endpoints with guest mode support.
Clean JWT-based authentication system.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from dotenv import load_dotenv

from database.database import get_db, create_user_with_wallet, get_user_by_username, get_user_by_email
from database.models import User, UserRole
from crypto.portfolio import portfolio_manager

load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

router = APIRouter()
security = HTTPBearer(auto_error=False)

@router.get("/check")
async def check_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Check if the current session or provided JWT is authenticated.

    This endpoint supports either a Bearer token in the Authorization header
    or a legacy server-side session containing `user_id` and `auth_token`.
    """
    # Debug: log incoming auth header and session for troubleshooting
    try:
        incoming_auth = None
        if credentials and credentials.credentials:
            incoming_auth = credentials.credentials
        print(f">> Auth Check: Received Authorization token: {incoming_auth}")
    except Exception as _e:
        print(f">> Auth Check: Error reading credentials: {_e}")

    # 1) If an Authorization header is present, validate the JWT
    if credentials and credentials.credentials:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            print(f">> Auth Check: Decoded JWT payload sub={user_id}")
            if user_id:
                # Verify user exists
                user = await db.get(User, user_id)
                if user:
                    print(f">> Auth Check: JWT validated for user {user_id}")
                    return {"status": "success", "authenticated": True}
        except JWTError as e:
            # Token invalid or expired - fall through to session check
            print(f">> Auth Check: JWT validation failed: {e}")
            pass

    # 2) Fall back to session-based validation (legacy behavior)
    user_id = request.session.get("user_id")
    auth_token = request.session.get("auth_token")
    print(f">> Auth Check: Session contents: user_id={user_id}, auth_token_present={bool(auth_token)}")
    if user_id and auth_token:
        return {"status": "success", "authenticated": True}

    raise HTTPException(status_code=401, detail="Not authenticated")

# ==================== REQUEST/RESPONSE MODELS ====================

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[str]
    wallet_balance: float

# ==================== HELPER FUNCTIONS ====================

def format_datetime(dt):
    """Safely format datetime to ISO string."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt  # Already a string
    return dt.isoformat()

# ==================== AUTHENTICATION FUNCTIONS ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user or None for guest mode."""
    if not credentials:
        return None

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    # Get user from database
    user = await db.get(User, user_id)
    return user

async def require_authentication(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Require authentication, raise 401 if not authenticated."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

async def get_guest_user_data() -> Dict[str, Any]:
    """Get guest user data for unauthenticated users."""
    guest_gems = int(os.getenv("GUEST_MODE_GEMS", "5000"))
    return {
        "id": "guest",
        "username": "Guest",
        "email": "guest@example.com",
        "role": UserRole.PLAYER.value,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "wallet_balance": guest_gems,
        "is_guest": True
    }

# ==================== API ENDPOINTS ====================

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account."""
    try:
        # Check if username already exists
        existing_user = await get_user_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        # Check if email already exists
        existing_email = await get_user_by_email(db, user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user with wallet
        user = await create_user_with_wallet(
            session=db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            initial_gems=1000.0
        )

        # Verify wallet creation and ensure balance is correct
        wallet_balance = await portfolio_manager.get_user_balance(user.id)
        if wallet_balance == 0:
            # Wallet creation might have failed, try to create it manually
            print(f">> Warning: Wallet not found for new user {user.id}, creating manually")
            await portfolio_manager.create_wallet(user.id, 1000.0)
            wallet_balance = 1000.0

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": format_datetime(user.created_at),
                "wallet_balance": wallet_balance
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login_user(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return access token."""
    try:
        # Get user by username or create test user
        user = await get_user_by_username(db, login_data.username)
        if not user and login_data.username == "testuser" and login_data.password == "testpass":
            # Create test user for development
            print(">> Creating test user account")
            user = await create_user_with_wallet(
                db,
                username="testuser",
                email="test@example.com",
                password="testpass",
                role=UserRole.USER
            )
        elif not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Verify password
        if not user.verify_password(login_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )

        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id},
            expires_delta=access_token_expires
        )

        # Get wallet balance with fallback creation
        wallet_balance = await portfolio_manager.get_user_balance(str(user.id))
        if wallet_balance == 0:
            # Check if wallet exists, create if needed
            wallet = await portfolio_manager.get_user_wallet(str(user.id))
            if not wallet:
                print(f">> Warning: Wallet not found for user {user.id} during login, creating")
                await portfolio_manager.create_wallet(str(user.id), 1000.0)
                wallet_balance = 1000.0

        # Set session data
        request.session["user_id"] = str(user.id)
        request.session["auth_token"] = access_token
        print(f">> Login Success: Set session for user {user.id}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": format_datetime(user.created_at),
                "wallet_balance": wallet_balance
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error logging in: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get current user information or guest data."""
    if not current_user:
        # Return guest user data
        guest_data = await get_guest_user_data()
        return UserResponse(**guest_data)

    # Get wallet balance for authenticated user
    wallet_balance = await portfolio_manager.get_user_balance(current_user.id)

    return UserResponse(
        id=str(current_user.id),
        username=str(current_user.username),
        email=str(current_user.email),
        role=str(current_user.role),
        is_active=bool(current_user.is_active),
        created_at=format_datetime(current_user.created_at),
        wallet_balance=wallet_balance
    )

@router.post("/logout")
async def logout_user():
    """Logout user (client-side token removal)."""
    return {"message": "Successfully logged out"}

@router.get("/guest")
async def get_guest_mode_info():
    """Get guest mode information."""
    guest_data = await get_guest_user_data()
    return {
        "message": "Guest mode activated",
        "features": {
            "crypto_tracking": True,
            "currency_converter": True,
            "roulette_gaming": True,
            "portfolio_saving": False,
            "transaction_history": False
        },
        "guest_user": guest_data,
        "limitations": [
            "Balance is temporary and not saved",
            "No transaction history",
            "Cannot save portfolio data",
            "Limited to guest GEM balance"
        ]
    }

@router.get("/status")
async def get_auth_status(
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get authentication status with guaranteed balance information."""
    if current_user:
        try:
            # Get wallet balance with fallback logic
            wallet_balance = await portfolio_manager.get_user_balance(current_user.id)

            # If balance is 0, check if wallet exists and create if needed
            if wallet_balance == 0:
                wallet = await portfolio_manager.get_user_wallet(str(current_user.id))
                if not wallet:
                    # Create wallet with initial balance if it doesn't exist
                    await portfolio_manager.create_wallet(str(current_user.id), 1000.0)
                    wallet_balance = 1000.0

            return {
                "authenticated": True,
                "user": {
                    "id": current_user.id,
                    "username": current_user.username,
                    "email": current_user.email,
                    "role": current_user.role,
                    "is_active": current_user.is_active,
                    "wallet_balance": wallet_balance
                }
            }
        except Exception as e:
            # If there's any issue with balance retrieval, log and use fallback
            print(f">> Warning: Balance retrieval failed for user {current_user.id}: {e}")
            return {
                "authenticated": True,
                "user": {
                    "id": current_user.id,
                    "username": current_user.username,
                    "email": current_user.email,
                    "role": current_user.role,
                    "is_active": current_user.is_active,
                    "wallet_balance": 1000.0  # Fallback balance
                }
            }
    else:
        guest_data = await get_guest_user_data()
        return {
            "authenticated": False,
            "guest_mode": True,
            "guest_user": guest_data
        }

@router.get("/debug")
async def debug_users(db: AsyncSession = Depends(get_db)):
    """Debug endpoint to see all users (remove in production)."""
    from sqlalchemy import select
    users = await db.execute(select(User).limit(10))
    user_list = []
    for user in users.scalars():
        user_list.append({
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "role": str(user.role) if user.role else None
        })
    return {"users": user_list, "total": len(user_list)}
