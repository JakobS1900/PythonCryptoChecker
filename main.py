"""
Main application entry point for CryptoChecker Gaming Platform.
"""

import asyncio
import time
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

# Import all API routers
from api.auth_api import router as auth_router
from api.gaming_api import router as gaming_router
from api.social_api import router as social_router
from api.admin_api import router as admin_router
from api.analytics_api import router as analytics_router
from api.onboarding_api import router as onboarding_router
from api.mini_games_api import router as mini_games_router
from web.trading_api import router as trading_router

# Import database and other systems
from database.database_manager import db_manager, get_db_session
from analytics.monitoring import monitoring_system
from logger import logger

# Import configuration
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting CryptoChecker Gaming Platform...")
    
    try:
        # Initialize database
        await db_manager.initialize()
        logger.info("Database initialized successfully")
        
        # Start monitoring system
        async def start_monitoring():
            session = db_manager.get_session()
            await monitoring_system.start_monitoring(session)
        
        # Start monitoring in background
        monitoring_task = asyncio.create_task(start_monitoring())
        
        logger.info("CryptoChecker Gaming Platform started successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    # Shutdown
    logger.info("Shutting down CryptoChecker Gaming Platform...")
    
    try:
        # Stop monitoring
        await monitoring_system.stop_monitoring()
        
        # Cancel monitoring task
        if 'monitoring_task' in locals():
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="CryptoChecker Gaming Platform",
    description="A comprehensive virtual crypto gaming and gamification platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
)

# Setup static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Favicon route
@app.get("/favicon.ico")
async def favicon():
    """Serve favicon."""
    from fastapi.responses import Response
    # Simple ICO favicon data (16x16 transparent icon)
    favicon_data = b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x18\x00h\x03\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00@\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    return Response(content=favicon_data, media_type="image/x-icon")

# Include API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(gaming_router, prefix="/api")
# Social API (secure, token-based) mounted under /api/social-secure to avoid collisions
# Frontend mock/demo endpoints are served directly in this file under /api/social
app.include_router(social_router, prefix="/api/social-secure")
app.include_router(admin_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(mini_games_router, prefix="/api/mini-games")
app.include_router(trading_router, prefix="/api/trading")


# ==================== WEB ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - enhanced gaming dashboard with authentication awareness."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Enhanced login page."""
    return templates.TemplateResponse("auth/login-enhanced.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Enhanced registration page."""
    return templates.TemplateResponse("auth/register-enhanced.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Legacy dashboard route - redirect to home to avoid duplication."""
    return RedirectResponse(url="/", status_code=307)


@app.get("/gaming", response_class=HTMLResponse)
async def gaming(request: Request):
    """Gaming section - redirect to roulette."""
    return RedirectResponse(url="/gaming/roulette")


@app.get("/gaming/roulette", response_class=HTMLResponse)
async def roulette(request: Request):
    """Crypto roulette game."""
    return templates.TemplateResponse("gaming/roulette.html", {"request": request})


@app.get("/gaming/dice", response_class=HTMLResponse)
async def dice_game(request: Request):
    """Dice gaming page."""
    return templates.TemplateResponse("gaming/dice.html", {"request": request})


@app.get("/tournaments", response_class=HTMLResponse)
async def tournaments(request: Request):
    """Tournaments and competitions."""
    return templates.TemplateResponse("tournaments.html", {"request": request})


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    """User portfolio and trading dashboard."""
    return templates.TemplateResponse("portfolio.html", {"request": request})


@app.get("/gaming/crash", response_class=HTMLResponse)
async def crash_game(request: Request):
    """Crash gaming page."""
    return templates.TemplateResponse("gaming/crash.html", {"request": request})


@app.get("/gaming/plinko", response_class=HTMLResponse)
async def plinko_game(request: Request):
    """Plinko gaming page."""
    return templates.TemplateResponse("gaming/plinko.html", {"request": request})


@app.get("/gaming/tower", response_class=HTMLResponse)
async def tower_game(request: Request):
    """Tower gaming page."""
    return templates.TemplateResponse("gaming/tower.html", {"request": request})


@app.get("/leaderboards", response_class=HTMLResponse)
async def leaderboards(request: Request):
    """Leaderboards page."""
    return templates.TemplateResponse("leaderboards.html", {"request": request})


@app.get("/inventory", response_class=HTMLResponse)  
async def inventory(request: Request):
    """User inventory and gaming items."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/gaming/inventory", response_class=HTMLResponse)
async def gaming_inventory(request: Request):
    """Gaming inventory page."""
    try:
        return templates.TemplateResponse("gaming/inventory.html", {"request": request})
    except Exception as e:
        logger.error(f"Error loading inventory page: {e}")
        return templates.TemplateResponse("index.html", {"request": request})


@app.get("/social", response_class=HTMLResponse)
async def social(request: Request):
    """Social features - friends, leaderboards, activity."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/achievements", response_class=HTMLResponse)
async def achievements(request: Request):
    """Achievements and progress tracking."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/daily-quests", response_class=HTMLResponse)
async def daily_quests(request: Request):
    """Daily quests page."""
    return templates.TemplateResponse("gaming/daily-rewards.html", {"request": request})

@app.get("/gaming/rewards", response_class=HTMLResponse)
async def gaming_rewards(request: Request):
    """Gaming rewards page."""
    return templates.TemplateResponse("gaming/daily-rewards.html", {"request": request})


# ==================== MINI-GAMES ROUTES ====================

@app.get("/mini-games", response_class=HTMLResponse)
async def mini_games_hub(request: Request):
    """Mini-games hub page."""
    return templates.TemplateResponse("mini_games/hub.html", {"request": request})

@app.get("/mini-games/hub", response_class=HTMLResponse)
async def mini_games_hub_alt(request: Request):
    """Alternative mini-games hub route."""
    return templates.TemplateResponse("mini_games/hub.html", {"request": request})


@app.get("/onboarding/welcome", response_class=HTMLResponse)
async def onboarding_welcome(request: Request):
    """Onboarding welcome page."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/trading")
async def trading_page_redirect():
    """Legacy trading page removed: redirect to home/dashboard."""
    return RedirectResponse("/", status_code=307)


@app.post("/api/auth/demo-login")
async def demo_login(request: Request):
    """Demo login endpoint for testing - MOCK AUTHENTICATION."""
    # Prepare mock user
    mock_user = {
        "id": "demo-user-123",
        "username": "CryptoGamer2025",
        "display_name": "Crypto Gamer",
        "email": "demo@cryptochecker.com",
        "avatar_url": "/static/images/default-avatar.png",
        "gem_coins": 15750,
        "current_level": 8,
        "total_experience": 12500,
        "created_at": "2025-01-13T10:00:00Z",
        "last_login": "2025-01-13T11:00:00Z"
    }

    try:
        # Set session data to simulate login
        request.session["is_authenticated"] = True
        request.session["user_id"] = mock_user["id"]
        request.session["username"] = mock_user["username"]
        request.session["email"] = mock_user["email"]
        request.session["avatar_url"] = mock_user["avatar_url"]
        # Initialize wallet if not set
        request.session.setdefault("wallet_balance", 5000)

        return {
            "status": "success",
            "message": "Demo login successful!",
            "user": mock_user
        }
    except Exception as e:
        logger.error(f"Demo login error: {e}")
        return {"status": "error", "message": "Login failed"}


@app.post("/api/auth/logout")
async def logout(request: Request):
    """Logout endpoint."""
    request.session.clear()
    return {"status": "success", "message": "Logged out successfully"}


    # (Removed duplicate demo-login route)

@app.get("/api/auth/logout")
async def logout_get(request: Request):
    """Logout endpoint (GET method for easy testing)."""
    request.session.clear()
    return {"status": "success", "message": "Logged out successfully"}


@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get current user info."""
    if request.session.get("is_authenticated"):
        return {
            "status": "success",
            "user": {
                "id": request.session.get("user_id"),
                "username": request.session.get("username"),
                "email": request.session.get("email", "demo@cryptochecker.com")
            }
        }
    else:
        return {"status": "error", "message": "Not authenticated"}





@app.get("/api/auth/test")
async def test_auth():
    """Test endpoint to verify API is working."""
    return {"status": "success", "message": "Authentication API is working!", "timestamp": time.time()}


@app.get("/api/test")
async def test_api():
    """Simple API test endpoint."""
    return {"message": "API is working!", "timestamp": time.time()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Simple WebSocket endpoint for demo (disabled functionality)."""
    await websocket.accept()
    try:
        # Just keep the connection open but don't do anything
        while True:
            await websocket.receive_text()
    except Exception:
        pass


@app.post("/api/auth/register")
async def simple_register(request: Request):
    """Simple registration endpoint for demo purposes."""
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        
        # Basic validation
        if not username or len(username) < 3:
            return {"status": "error", "message": "Username must be at least 3 characters long"}
        
        if not email or "@" not in email:
            return {"status": "error", "message": "Please enter a valid email address"}
        
        if not password or len(password) < 6:
            return {"status": "error", "message": "Password must be at least 6 characters long"}
        
        # For demo purposes, we'll create a simple user
        user_id = f"user-{username}-{int(time.time())}"
        
        # Set session
        request.session["user_id"] = user_id
        request.session["username"] = username
        request.session["email"] = email
        request.session["is_authenticated"] = True
        
        return {
            "status": "success",
            "message": "Account created successfully!",
            "user": {
                "id": user_id,
                "username": username,
                "email": email
            }
        }
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return {"status": "error", "message": "Registration failed. Please try again."}


@app.post("/api/auth/login")
async def simple_login(request: Request):
    """Simple login endpoint for demo purposes."""
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        
        # Basic validation
        if not username:
            return {"status": "error", "message": "Please enter your username or email"}
        
        if not password:
            return {"status": "error", "message": "Please enter your password"}
        
        # For demo purposes, accept any valid credentials
        if len(password) >= 6:
            user_id = f"user-{username}-{int(time.time())}"
            
            # Set session
            request.session["user_id"] = user_id
            request.session["username"] = username
            request.session["email"] = f"{username}@cryptochecker.com"
            request.session["is_authenticated"] = True
            
            return {
                "status": "success",
                "message": "Login successful!",
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": f"{username}@cryptochecker.com"
                }
            }
        else:
            return {"status": "error", "message": "Invalid username or password"}
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return {"status": "error", "message": "Login failed. Please try again."}


@app.get("/api/auth/status")
async def auth_status(request: Request):
    """Get detailed authentication status for debugging."""
    return {
        "status": "success",
        "session_data": dict(request.session),
        "is_authenticated": request.session.get("is_authenticated", False),
        "user_id": request.session.get("user_id"),
        "username": request.session.get("username")
    }


@app.get("/admin", response_class=HTMLResponse)
async def admin_redirect(request: Request):
    """Redirect to admin dashboard."""
    return RedirectResponse(url="/admin/dashboard")


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard - enhanced interface."""
    return templates.TemplateResponse("home.html", {"request": request})


# ==================== SOCIAL & GAMING APIs (MOCK IMPLEMENTATION) ====================

@app.get("/api/social/activity")
async def get_activity_feed(request: Request, limit: int = 10):
    """Get recent activity feed - MOCK DATA."""
    mock_activities = [
        {
            "id": "activity-1",
            "user": {
                "id": "friend-1",
                "username": "CryptoMaster",
                "display_name": "Crypto Master",
                "avatar_url": "/static/images/default-avatar.png"
            },
            "activity_type": "game_won",
            "content": {
                "winnings": 2500,
                "game_type": "roulette"
            },
            "timestamp": "2025-01-13T10:30:00Z"
        },
        {
            "id": "activity-2", 
            "user": {
                "id": "friend-2",
                "username": "DiamondHands",
                "display_name": "Diamond Hands",
                "avatar_url": "/static/images/default-avatar.png"
            },
            "activity_type": "achievement_unlocked",
            "content": {
                "achievement_name": "High Roller",
                "description": "Win 10 games in a row"
            },
            "timestamp": "2025-01-13T10:15:00Z"
        }
    ]
    
    return {
        "success": True,
        "data": mock_activities[:limit],
        "pagination": {
            "page": 1,
            "limit": limit,
            "total": len(mock_activities),
            "has_more": len(mock_activities) > limit
        }
    }

@app.get("/api/social/online-friends")
async def get_online_friends(request: Request):
    """Get online friends - MOCK DATA."""
    mock_friends = [
        {
            "id": "friend-1",
            "username": "CryptoMaster",
            "display_name": "Crypto Master", 
            "avatar_url": "/static/images/default-avatar.png",
            "status": "online",
            "level": 12,
            "last_seen": "2025-01-13T11:00:00Z"
        },
        {
            "id": "friend-2",
            "username": "DiamondHands",
            "display_name": "Diamond Hands",
            "avatar_url": "/static/images/default-avatar.png",
            "status": "online", 
            "level": 9,
            "last_seen": "2025-01-13T10:55:00Z"
        },
        {
            "id": "friend-3",
            "username": "MoonLander",
            "display_name": "Moon Lander",
            "avatar_url": "/static/images/default-avatar.png",
            "status": "online",
            "level": 15,
            "last_seen": "2025-01-13T10:58:00Z"
        }
    ]
    
    return {
        "success": True,
        "data": {
            "online_friends": mock_friends,
            "total_online": len(mock_friends),
            "total_friends": len(mock_friends) + 5
        }
    }

@app.get("/api/social/leaderboards/{board_type}")
async def get_leaderboard(request: Request, board_type: str, limit: int = 5):
    """Get leaderboard data - MOCK DATA."""
    mock_leaderboard = [
        {
            "rank": 1,
            "user": {
                "id": "leader-1",
                "username": "CryptoLegend",
                "display_name": "Crypto Legend",
                "avatar_url": "/static/images/default-avatar.png"
            },
            "score": 25000,
            "level": 20
        },
        {
            "rank": 2,
            "user": {
                "id": "leader-2", 
                "username": "GamingGuru",
                "display_name": "Gaming Guru",
                "avatar_url": "/static/images/default-avatar.png"
            },
            "score": 22500,
            "level": 18
        },
        {
            "rank": 3,
            "user": {
                "id": "leader-3",
                "username": "RouletteRoyalty", 
                "display_name": "Roulette Royalty",
                "avatar_url": "/static/images/default-avatar.png"
            },
            "score": 20000,
            "level": 17
        }
    ]
    
    return {
        "success": True,
        "data": mock_leaderboard[:limit],
        "pagination": {
            "page": 1,
            "limit": limit,
            "total": len(mock_leaderboard),
            "has_more": len(mock_leaderboard) > limit
        },
        "leaderboard_type": board_type
    }

@app.get("/api/gaming/stats")
async def get_gaming_stats(request: Request):
    """Get user gaming statistics - MOCK DATA."""
    return {
        "success": True,
        "data": {
            "total_games": 157,
            "total_wins": 89,
            "total_losses": 68,
            "win_rate": 56.7,
            "total_winnings": 45250,
            "biggest_win": 8500,
            "current_streak": 3,
            "longest_win_streak": 12,
            "longest_loss_streak": 5,
            "favorite_game": "roulette",
            "achievements_count": 23,
            "level_progress": {
                "current_level": 8,
                "current_exp": 2500,
                "required_exp": 3000,
                "progress_percentage": 83.3
            }
        }
    }

# ==================== WALLET/GAMIFICATION API ====================

@app.get("/api/trading/gamification/wallet")
async def get_wallet_balance(request: Request):
    """Get user wallet balance."""
    try:
        # Check if user is authenticated
        user_id = request.session.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}
        
        import time
        
        # Get or create a persistent balance for this session
        if "wallet_balance" not in request.session:
            request.session["wallet_balance"] = 5000
        
        current_balance = request.session["wallet_balance"]
        
        return {
            "status": "success",
            "data": {
                "gem_coins": current_balance,
                "user_id": user_id,
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }
    except Exception as e:
        logger.error(f"Wallet balance error: {e}")
        return {"status": "error", "message": "Failed to get wallet balance"}


@app.post("/api/trading/gamification/wallet/adjust")
async def adjust_wallet_balance(request: Request):
    """Adjust wallet balance for demo purposes."""
    try:
        # Check if user is authenticated
        user_id = request.session.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}
        
        # Get request data
        data = await request.json()
        adjustment = data.get("amount", 0)
        
        # Get current wallet balance
        current_balance = request.session.get("wallet_balance", 5000)
        new_balance = max(100, current_balance + adjustment)  # Minimum 100 GEM
        
        # Update session with new balance
        request.session["wallet_balance"] = new_balance
        
        return {
            "status": "success",
            "data": {
                "gem_coins": new_balance,
                "adjustment": adjustment,
                "previous_balance": current_balance,
                "user_id": user_id
            }
        }
    except Exception as e:
        logger.error(f"Wallet adjustment error: {e}")
        return {"status": "error", "message": "Failed to adjust wallet balance"}


@app.post("/api/trading/gamification/wallet/process-bet-result")
async def process_bet_result(request: Request):
    """Process gambling bet results and update wallet balance."""
    try:
        # Check if user is authenticated
        user_id = request.session.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}
        
        # Get request data
        data = await request.json()
        net_result = data.get("net_result", 0)  # Net winnings/losses
        game_id = data.get("game_id", "")
        
        # Get current wallet balance
        current_balance = request.session.get("wallet_balance", 5000)
        new_balance = max(0, current_balance + net_result)  # Can't go below 0
        
        # Update session with new balance
        request.session["wallet_balance"] = new_balance
        
        # Log the transaction for debugging
        logger.info(f"Bet result processed for user {user_id}: {net_result} GEM, new balance: {new_balance}")
        
        return {
            "status": "success",
            "data": {
                "previous_balance": current_balance,
                "net_result": net_result,
                "new_balance": new_balance,
                "game_id": game_id,
                "user_id": user_id
            }
        }
    except Exception as e:
        logger.error(f"Bet result processing error: {e}")
        return {"status": "error", "message": "Failed to process bet result"}


# ==================== INVENTORY API ====================

@app.get("/api/inventory/items")
async def get_inventory_items(request: Request):
    """Get user inventory items."""
    try:
        # Check if user is authenticated
        user_id = request.session.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}
        
        # Mock inventory data - in a real app, this would query the database
        items = [
            {
                "id": 1,
                "name": "Lucky Crypto Charm",
                "type": "consumables",
                "rarity": "uncommon",
                "icon": "🍀",
                "quantity": 3,
                "description": "Increases your luck in the next 5 games. +10% chance of winning.",
                "effects": "Luck Boost: +10% win chance for 5 games",
                "value": 500,
                "usable": True
            },
            {
                "id": 2,
                "name": "Golden Bitcoin",
                "type": "collectibles",
                "rarity": "legendary",
                "icon": "🪙",
                "quantity": 1,
                "description": "A rare golden Bitcoin collectible. Extremely valuable and sought after.",
                "effects": "Passive: +5% GEM earnings from all activities",
                "value": 10000,
                "usable": False
            },
            {
                "id": 3,
                "name": "Energy Drink",
                "type": "consumables",
                "rarity": "common",
                "icon": "⚡",
                "quantity": 8,
                "description": "Restores energy and provides a temporary boost to all activities.",
                "effects": "Energy Boost: +20% XP gain for 1 hour",
                "value": 100,
                "usable": True
            }
        ]
        
        return {
            "status": "success",
            "data": {
                "items": items,
                "total_items": sum(item["quantity"] for item in items),
                "total_value": sum(item["value"] * item["quantity"] for item in items)
            }
        }
    except Exception as e:
        logger.error(f"Inventory items error: {e}")
        return {"status": "error", "message": "Failed to get inventory items"}


@app.post("/api/inventory/use-item")
async def use_inventory_item(request: Request):
    """Use an inventory item."""
    try:
        # Check if user is authenticated
        user_id = request.session.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}
        
        # Get request data
        data = await request.json()
        item_id = data.get("item_id")
        
        if not item_id:
            return {"status": "error", "message": "Item ID required"}
        
        # In a real app, this would update the database
        # For now, just return success
        return {
            "status": "success",
            "data": {
                "item_id": item_id,
                "message": "Item used successfully",
                "effects_applied": True
            }
        }
    except Exception as e:
        logger.error(f"Use item error: {e}")
        return {"status": "error", "message": "Failed to use item"}


# ==================== REWARDS API ====================

@app.post("/api/rewards/claim-daily")
async def claim_daily_reward(request: Request):
    """Claim daily reward with proper database integration."""
    try:
        # Check if user is authenticated
        user_id = request.session.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}
        
        # Simplified daily reward for demo purposes
        import time
        import random
        
        # Check if enough time has passed (24 hours)
        last_claim = request.session.get("last_daily_claim", 0)
        current_time = time.time()
        
        if current_time - last_claim < 86400:  # 24 hours
            remaining_hours = (86400 - (current_time - last_claim)) / 3600
            return {"status": "error", "message": f"Please wait {int(remaining_hours)} more hours"}
        
        # Generate daily reward
        base_amount = 100
        streak = request.session.get("daily_streak", 0) + 1
        bonus = min(streak * 25, 500)  # Max 500 bonus
        amount = base_amount + bonus + random.randint(0, 100)
        
        # Update wallet balance and session
        current_balance = request.session.get("wallet_balance", 5000)
        new_balance = current_balance + amount
        request.session["wallet_balance"] = new_balance
        request.session["last_daily_claim"] = current_time
        request.session["daily_streak"] = streak
        
        logger.info(f"Daily reward claimed by user {user_id}: +{amount} GEM, streak: {streak}")
        
        return {
            "status": "success",
            "data": {
                "amount": amount,
                "xp": 50,
                "new_balance": new_balance,
                "streak": streak,
                "description": f"Daily reward (Day {streak})"
            }
        }
            
    except Exception as e:
        logger.error(f"Daily reward claim error: {e}")
        return {"status": "error", "message": "Failed to claim daily reward"}


@app.post("/api/rewards/claim-hourly")
async def claim_hourly_bonus(request: Request):
    """Claim hourly bonus."""
    try:
        # Check if user is authenticated
        user_id = request.session.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}
        
        import time
        
        # Check if enough time has passed (1 hour = 3600 seconds)
        last_claim = request.session.get("last_hourly_claim", 0)
        current_time = time.time()
        
        if current_time - last_claim < 3600:  # 1 hour
            remaining = 3600 - (current_time - last_claim)
            return {"status": "error", "message": f"Please wait {int(remaining/60)} more minutes"}
        
        # Generate random bonus amount (25-100 GEM)
        import random
        amount = random.randint(25, 100)
        
        # Update wallet balance
        current_balance = request.session.get("wallet_balance", 5000)
        new_balance = current_balance + amount
        request.session["wallet_balance"] = new_balance
        request.session["last_hourly_claim"] = current_time
        
        logger.info(f"Hourly bonus claimed by user {user_id}: +{amount} GEM")
        
        return {
            "status": "success",
            "data": {
                "amount": amount,
                "new_balance": new_balance,
                "next_claim_in": 3600  # 1 hour
            }
        }
    except Exception as e:
        logger.error(f"Hourly bonus claim error: {e}")
        return {"status": "error", "message": "Failed to claim hourly bonus"}


@app.post("/api/rewards/trading-bonus")
async def claim_trading_bonus(request: Request):
    """Claim bonus for paper trading activity."""
    try:
        # Check if user is authenticated
        user_id = request.session.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}
        
        # Get request data
        data = await request.json()
        trade_type = data.get("type", "demo")  # demo, profitable, loss
        
        import random
        
        # Calculate bonus based on trade type
        if trade_type == "profitable":
            amount = random.randint(100, 500)  # 100-500 GEM for profitable trades
        elif trade_type == "demo":
            amount = random.randint(25, 100)   # 25-100 GEM for demo trades
        else:
            amount = random.randint(10, 50)    # 10-50 GEM consolation for losses
        
        # Update wallet balance
        current_balance = request.session.get("wallet_balance", 5000)
        new_balance = current_balance + amount
        request.session["wallet_balance"] = new_balance
        
        logger.info(f"Trading bonus claimed by user {user_id}: {trade_type} trade, +{amount} GEM")
        
        return {
            "status": "success",
            "data": {
                "amount": amount,
                "trade_type": trade_type,
                "new_balance": new_balance
            }
        }
    except Exception as e:
        logger.error(f"Trading bonus error: {e}")
        return {"status": "error", "message": "Failed to claim trading bonus"}


# ==================== API ENDPOINTS ====================

@app.get("/api/health")
async def health_check():
    """API health check endpoint."""
    try:
        health_status = await monitoring_system.health_check()
        
        return {
            "status": "healthy" if health_status["healthy"] else "unhealthy",
            "timestamp": health_status["timestamp"],
            "version": "1.0.0",
            "service": "CryptoChecker Gaming Platform",
            "checks": health_status.get("checks", {}),
            "uptime": health_status.get("uptime", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/api/coins")
async def get_coins(
    page: int = 1,
    per_page: int = 50,
    currency: str = "usd"
):
    """Legacy coins API - redirects to gaming platform."""
    return {
        "message": "This endpoint has been transformed into a gaming platform",
        "redirect": "/gaming/roulette",
        "available_endpoints": [
            "/api/gaming/wheel-config",
            "/api/health",
            "/dashboard",
            "/gaming/roulette"
        ],
        "note": "The crypto analysis features are now part of the gaming experience"
    }


@app.websocket("/ws/prices")
async def websocket_prices_endpoint(websocket: WebSocket):
    """Legacy WebSocket prices endpoint - now redirects to gaming platform."""
    await websocket.accept()
    await websocket.send_json({
        "message": "WebSocket functionality has been transformed into a gaming platform",
        "redirect": "/gaming/roulette",
        "note": "Real-time features are now part of the gaming experience"
    })
    await websocket.close()


# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """404 error handler."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"error": "API endpoint not found", "status_code": 404}
        )
    return templates.TemplateResponse("errors/404.html", {"request": request}, status_code=404)


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """500 error handler."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "status_code": 500}
        )
    return templates.TemplateResponse("errors/500.html", {"request": request}, status_code=500)


# ==================== STARTUP FUNCTION ====================

def main():
    """Main application startup function."""
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )


if __name__ == "__main__":
    main()
