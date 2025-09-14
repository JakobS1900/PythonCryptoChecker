"""
Main application entry point for CryptoChecker Gaming Platform.
"""

import asyncio
import random
from datetime import datetime
import time
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, WebSocket, UploadFile, File
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
from api.inventory_api import router as inventory_router
from web.trading_api import router as trading_router

# Import database and other systems
from database.database_manager import db_manager, get_db_session
from analytics.monitoring import monitoring_system
from logger import logger

# Import configuration
import os
from dotenv import load_dotenv
from sqlalchemy import select
from database.unified_models import User, Friendship

# Load environment variables
load_dotenv()

# ---- Runtime configuration defaults (prevent NameError and 500s) ----
# Enable/disable background social bots (disabled by default)
BOT_ENABLED = os.getenv("BOT_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}

# Max avatar upload size (bytes). Default: 4MB
MAX_AVATAR_BYTES = int(os.getenv("MAX_AVATAR_BYTES", str(4 * 1024 * 1024)))

# Stub background tasks for bots (safe no-ops if not implemented elsewhere)
async def seed_bots(session):
    try:
        # Optionally import real implementation if present
        from social.bots import seed_bots as real_seed_bots  # type: ignore
        return await real_seed_bots(session)
    except Exception:
        # No-op if module not available
        return None

async def bots_friend_request_loop():
    try:
        from social.bots import bots_friend_request_loop as real_loop  # type: ignore
        return await real_loop()
    except Exception:
        # No-op loop placeholder
        return None


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

        # Seed social bots and start background friend-request loop
        async def init_bots_and_loop():
            async with db_manager.get_session() as session:
                await seed_bots(session)
            await bots_friend_request_loop()

        bots_task = None
        if BOT_ENABLED:
            bots_task = asyncio.create_task(init_bots_and_loop())
        
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
        # Cancel bots task
        if 'bots_task' in locals() and bots_task is not None:
            bots_task.cancel()
            try:
                await bots_task
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
app.include_router(inventory_router, prefix="/api/inventory")
# Trading API already declares '/api/trading' in its router prefix; include without extra prefix
app.include_router(trading_router)


# ==================== WEB ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - restore classic dashboard. Fallback to enhanced home if unavailable."""
    try:
        return templates.TemplateResponse("dashboard.html", {"request": request})
    except Exception as e:
        try:
            logger.error(f"Dashboard template error: {e}")
        except Exception:
            pass
        try:
            return templates.TemplateResponse("home.html", {"request": request})
        except Exception:
            return HTMLResponse("<h1>CryptoChecker</h1><p>Welcome.</p>", status_code=200)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Enhanced login page."""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Enhanced registration page."""
    return templates.TemplateResponse("auth/register.html", {"request": request})


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


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page (uses base layout and auth.js to populate data)."""
    return templates.TemplateResponse("profile.html", {"request": request})


@app.post("/api/profile/update")
async def update_profile(request: Request):
    """Update profile fields (demo stores in session; tries to persist to DB)."""
    try:
        if not request.session.get("is_authenticated"):
            return {"status": "error", "message": "Not authenticated"}

        data = await request.json()
        display_name = (data.get("display_name") or "").strip()
        bio = (data.get("bio") or "").strip()

        if display_name:
            request.session["display_name"] = display_name
        request.session["bio"] = bio

        # Best-effort persistence to DB if user exists
        try:
            async with db_manager.get_session() as session:
                user_id = request.session.get("user_id")
                username = request.session.get("username")
                db_user = None
                if user_id:
                    result = await session.execute(select(User).where(User.id == user_id))
                    db_user = result.scalars().first()
                if not db_user and username:
                    result = await session.execute(select(User).where(User.username == username))
                    db_user = result.scalars().first()
                if db_user:
                    if display_name:
                        db_user.display_name = display_name
                    db_user.bio = bio
                    await session.commit()
        except Exception as e:
            logger.warning(f"DB persistence skipped for profile update: {e}")

        return {
            "status": "success",
            "message": "Profile updated",
            "user": {
                "id": request.session.get("user_id"),
                "username": request.session.get("username"),
                "display_name": request.session.get("display_name", request.session.get("username")),
                "bio": request.session.get("bio", ""),
                "avatar_url": request.session.get("avatar_url", "/static/images/default-avatar.png"),
            }
        }
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        return {"status": "error", "message": "Failed to update profile"}


@app.post("/api/profile/avatar")
async def upload_avatar(request: Request, avatar: UploadFile = File(...)):
    """Upload and set a new profile avatar (demo)."""
    try:
        if not request.session.get("is_authenticated"):
            return {"status": "error", "message": "Not authenticated"}

        # Basic validation (MIME and extension)
        allowed_ext = {"png", "jpg", "jpeg", "gif", "webp"}
        allowed_mime = {"image/png", "image/jpeg", "image/gif", "image/webp"}
        filename = avatar.filename or "avatar.png"
        ext = filename.split(".")[-1].lower()
        content_type = (getattr(avatar, 'content_type', None) or '').lower()
        if content_type and content_type not in allowed_mime:
            return {"status": "error", "message": "Unsupported MIME type"}
        if ext not in allowed_ext:
            return {"status": "error", "message": "Unsupported file type"}

        # Ensure upload directory exists
        import os
        os.makedirs("web/static/uploads/avatars", exist_ok=True)

        user_id = request.session.get("user_id", "anonymous")
        save_path = f"web/static/uploads/avatars/{user_id}.{ext}"
        url_path = f"/static/uploads/avatars/{user_id}.{ext}"

        # Save file with size + signature check
        content = await avatar.read()
        if len(content) > MAX_AVATAR_BYTES:
            return {"status": "error", "message": "File too large. Max 4MB."}

        # Detect image type from content (prefer imghdr; fallback to magic bytes)
        import imghdr
        detected = imghdr.what(None, h=content)
        imghdr_to_ext = {"jpeg": "jpg", "png": "png", "gif": "gif"}
        detected_ext = imghdr_to_ext.get(detected)
        if not detected_ext:
            if content.startswith(b"\x89PNG\r\n\x1a\n"):
                detected_ext = "png"
            elif content[:2] == b"\xff\xd8":
                detected_ext = "jpg"
            elif content.startswith(b"GIF8"):
                detected_ext = "gif"
            elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
                detected_ext = "webp"
        if not detected_ext or detected_ext not in allowed_ext:
            return {"status": "error", "message": "Unsupported or corrupted image"}

        # Normalize extension to detected content
        ext = detected_ext
        with open(save_path, "wb") as f:
            f.write(content)

        # Optionally generate thumbnail (if Pillow available)
        try:
            from PIL import Image  # optional
            from io import BytesIO
            img = Image.open(BytesIO(content))
            if ext in {"jpg", "jpeg"}:
                img = img.convert('RGB')
            img.thumbnail((256, 256))
            thumb_ext = ext if ext != 'gif' else 'png'
            thumb_path = f"web/static/uploads/avatars/{user_id}_thumb.{thumb_ext}"
            img.save(thumb_path)
            url_path = f"/static/uploads/avatars/{user_id}_thumb.{thumb_ext}"
        except Exception as e:
            logger.info(f"Thumbnail generation skipped: {e}")

        # Update session
        request.session["avatar_url"] = url_path

        # Best-effort persistence to DB if user exists
        try:
            async with db_manager.get_session() as session:
                uid = request.session.get("user_id")
                if uid:
                    result = await session.execute(select(User).where(User.id == uid))
                    db_user = result.scalars().first()
                    if db_user:
                        db_user.avatar_url = url_path
                        await session.commit()
        except Exception as e:
            logger.warning(f"DB persistence skipped for avatar: {e}")

        return {"status": "success", "message": "Avatar updated", "avatar_url": url_path}
    except Exception as e:
        logger.error(f"Avatar upload error: {e}")
        return {"status": "error", "message": "Failed to upload avatar"}


@app.post("/api/profile/avatar/remove")
async def remove_avatar(request: Request):
    """Remove custom avatar and reset to default."""
    try:
        if not request.session.get("is_authenticated"):
            return {"status": "error", "message": "Not authenticated"}

        user_id = request.session.get("user_id", "anonymous")
        default_url = "/static/images/default-avatar.png"

        # Attempt to remove files
        import os, glob
        for path in glob.glob(f"web/static/uploads/avatars/{user_id}.*"):
            try:
                os.remove(path)
            except Exception:
                pass
        for path in glob.glob(f"web/static/uploads/avatars/{user_id}_thumb.*"):
            try:
                os.remove(path)
            except Exception:
                pass

        # Update session
        request.session["avatar_url"] = default_url

        # Persist to DB if exists
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                db_user = result.scalars().first()
                if db_user:
                    db_user.avatar_url = default_url
                    await session.commit()
        except Exception as e:
            logger.warning(f"DB persistence skipped for remove avatar: {e}")

        return {"status": "success", "message": "Avatar removed", "avatar_url": default_url}
    except Exception as e:
        logger.error(f"Avatar remove error: {e}")
        return {"status": "error", "message": "Failed to remove avatar"}


@app.get("/inventory", response_class=HTMLResponse)  
async def inventory(request: Request):
    """User inventory and gaming items."""
    return templates.TemplateResponse("inventory/inventory.html", {"request": request})


@app.get("/gaming/inventory")
async def gaming_inventory_redirect(request: Request):
    """Compatibility redirect from old /gaming/inventory to canonical /inventory."""
    return RedirectResponse(url="/inventory")


@app.get("/social", response_class=HTMLResponse)
async def social(request: Request):
    """Social features - friends, leaderboards, activity."""
    return templates.TemplateResponse("social/social.html", {"request": request})


@app.get("/achievements", response_class=HTMLResponse)
async def achievements(request: Request):
    """Achievements and progress tracking."""
    return templates.TemplateResponse("achievements.html", {"request": request})


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


@app.get("/trading", response_class=HTMLResponse)
async def trading_page(request: Request):
    """Trading dashboard page (paper trading with GEM-integrated inventory hooks)."""
    try:
        import os as _os
        gem_rate = float(_os.getenv("GEM_USD_RATE_USD_PER_GEM", "0.01"))
        return templates.TemplateResponse("trading_unified.html", {"request": request, "gem_usd_rate": gem_rate})
    except Exception as e:
        try:
            logger.error(f"Error loading trading page: {e}")
        except Exception:
            pass
        # Fallback to original trading template if unified version fails
        try:
            return templates.TemplateResponse("trading.html", {"request": request})
        except Exception:
            return templates.TemplateResponse("trading-simple.html", {"request": request})


@app.post("/api/auth/demo-login")
async def demo_login(request: Request):
    """Demo login endpoint for testing - MOCK AUTHENTICATION."""
    # Prepare mock user with complete stats
    mock_user = {
        "id": "demo-user-123",
        "username": "emuroot",  # Match the actual logged in user
        "display_name": "emuroot",
        "email": "demo@cryptochecker.com",
        "avatar_url": "/static/images/default-avatar.png",
        "gem_coins": 5000,  # Match the actual balance shown in navbar
        "current_level": 1,
        "total_experience": 250,
        "total_wins": 42,
        "total_games": 87,
        "achievements_count": 12,
        "win_rate": 48.3,
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
        request.session["display_name"] = mock_user.get("display_name", mock_user["username"])
        request.session["display_name"] = mock_user["display_name"]
        # Set financial and progression data
        request.session["gem_coins"] = mock_user["gem_coins"]
        request.session["current_level"] = mock_user["current_level"]
        request.session["total_experience"] = mock_user["total_experience"]
        request.session["wallet_balance"] = mock_user["gem_coins"]  # Keep for compatibility
        
        # Set gaming statistics for dashboard
        request.session["total_wins"] = mock_user["total_wins"]
        request.session["total_games"] = mock_user["total_games"]
        request.session["achievements_count"] = mock_user["achievements_count"]

        return {
            "success": True,
            "status": "success",
            "message": "Demo login successful!",
            "data": {
                "access_token": f"demo-token-{mock_user['id']}",
                "refresh_token": f"demo-refresh-{mock_user['id']}",
                "user": mock_user
            }
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
                "email": request.session.get("email", "demo@cryptochecker.com"),
                "display_name": request.session.get("display_name", request.session.get("username")),
                "avatar_url": request.session.get("avatar_url", "/static/images/default-avatar.png"),
                "current_level": request.session.get("current_level", 1)
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


@app.websocket("/ws/roulette/{session_id}")
async def websocket_roulette_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time roulette gaming."""
    try:
        # Import the websocket handler
        from api.websocket_endpoints import websocket_roulette_game
        
        # Accept the connection first
        await websocket.accept()
        
        # Handle the roulette game WebSocket connection
        await websocket_roulette_game(websocket, session_id)
        
    except Exception as e:
        logger.error(f"Roulette WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
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
            return JSONResponse({"status": "error", "message": "Username must be at least 3 characters long"}, status_code=400)
        
        if not email or "@" not in email:
            return JSONResponse({"status": "error", "message": "Please enter a valid email address"}, status_code=400)
        
        if not password or len(password) < 6:
            return JSONResponse({"status": "error", "message": "Password must be at least 6 characters long"}, status_code=400)
        
        # For demo purposes, we'll create a simple user
        user_id = f"user-{username}-{int(time.time())}"
        
        # Set session with initial user data
        request.session["user_id"] = user_id
        request.session["username"] = username
        request.session["email"] = email
        request.session["is_authenticated"] = True
        request.session["display_name"] = username
        request.session["avatar_url"] = "/static/images/default-avatar.png"
        
        # Set initial gaming/financial data for new users
        request.session["gem_coins"] = 1000
        request.session["current_level"] = 1
        request.session["total_experience"] = 0
        request.session["total_wins"] = 0
        request.session["total_games"] = 0
        request.session["achievements_count"] = 0
        
        return {
            "success": True,
            "status": "success",
            "message": "Account created successfully!",
            "data": {
                "access_token": f"token-{user_id}",
                "refresh_token": f"refresh-{user_id}",
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "display_name": username,
                    "avatar_url": "/static/images/default-avatar.png",
                    "gem_coins": 1000,
                    "current_level": 1,
                    "total_experience": 0
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return JSONResponse({"status": "error", "message": "Registration failed. Please try again."}, status_code=500)


@app.post("/api/auth/login")
async def simple_login(request: Request):
    """Simple login endpoint for demo purposes."""
    try:
        data = await request.json()
        # Accept either 'username' or 'username_or_email' or 'email'
        username = (data.get("username") or data.get("username_or_email") or data.get("email") or "").strip()
        password = data.get("password", "")
        
        # Basic validation
        if not username:
            return JSONResponse({"status": "error", "message": "Please enter your username or email"}, status_code=400)
        
        if not password:
            return JSONResponse({"status": "error", "message": "Please enter your password"}, status_code=400)
        
        # For demo purposes, accept any valid credentials
        if len(password) >= 6:
            user_id = f"user-{username}-{int(time.time())}"
            
            # Set session with complete user data
            request.session["user_id"] = user_id
            request.session["username"] = username
            request.session["email"] = f"{username}@cryptochecker.com"
            request.session["is_authenticated"] = True
            request.session["display_name"] = username
            request.session["avatar_url"] = "/static/images/default-avatar.png"
            
            # Set initial gaming/financial data for new users
            request.session["gem_coins"] = request.session.get("gem_coins", 1000)
            request.session["current_level"] = request.session.get("current_level", 1)
            request.session["total_experience"] = request.session.get("total_experience", 0)
            request.session["total_wins"] = request.session.get("total_wins", 0)
            request.session["total_games"] = request.session.get("total_games", 0)
            request.session["achievements_count"] = request.session.get("achievements_count", 0)
            
            return {
                "success": True,
                "status": "success", 
                "message": "Login successful!",
                "data": {
                    "access_token": f"token-{user_id}",
                    "refresh_token": f"refresh-{user_id}",
                    "user": {
                        "id": user_id,
                        "username": username,
                        "email": f"{username}@cryptochecker.com",
                        "display_name": username,
                        "avatar_url": "/static/images/default-avatar.png",
                        "gem_coins": request.session.get("gem_coins", 1000),
                        "current_level": request.session.get("current_level", 1),
                        "total_experience": request.session.get("total_experience", 0)
                    }
                }
            }
        else:
            return JSONResponse({"status": "error", "message": "Invalid username or password"}, status_code=401)
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return JSONResponse({"status": "error", "message": "Login failed. Please try again."}, status_code=500)


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


# ====================== TRADING API ENDPOINTS ======================

@app.get("/api/trading/portfolio/demo/summary")
async def get_demo_portfolio_summary(request: Request):
    """Get portfolio summary for demo user."""
    if not request.session.get("is_authenticated"):
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
    
    try:
        # Demo portfolio data - in real implementation, this would query the database
        return {
            "status": "success",
            "data": {
                "portfolio_value": 12500.50,
                "total_return": 2500.50,
                "return_percentage": 25.01,
                "available_cash": 7500.00,
                "open_positions": 3,
                "gem_coins": request.session.get("gem_coins", 1000)
            }
        }
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        return JSONResponse({"status": "error", "message": "Failed to get portfolio summary"}, status_code=500)

@app.get("/api/trading/prices")
async def get_crypto_prices(ids: str = "bitcoin"):
    """Get current cryptocurrency prices."""
    try:
        # Demo price data - in real implementation, this would fetch from CoinGecko or similar API
        demo_prices = {
            "bitcoin": {"price": 43250.75, "change_24h": 2.35},
            "ethereum": {"price": 2680.40, "change_24h": -1.25},
            "cardano": {"price": 0.485, "change_24h": 0.85},
            "solana": {"price": 98.75, "change_24h": 4.20},
            "polkadot": {"price": 7.85, "change_24h": -0.95}
        }
        
        coin_list = ids.split(",")
        result = {}
        for coin_id in coin_list:
            if coin_id in demo_prices:
                result[coin_id] = demo_prices[coin_id]
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting crypto prices: {e}")
        return JSONResponse({"status": "error", "message": "Failed to get prices"}, status_code=500)

@app.get("/api/trading/quick-trade/{action}/{coin_id}")
async def quick_trade(action: str, coin_id: str, amount: float, request: Request):
    """Execute a quick market trade."""
    if not request.session.get("is_authenticated"):
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
    
    try:
        if action.upper() not in ["BUY", "SELL"]:
            return JSONResponse({"status": "error", "message": "Invalid action"}, status_code=400)
        
        if amount <= 0:
            return JSONResponse({"status": "error", "message": "Invalid amount"}, status_code=400)
        
        # Demo trade execution - in real implementation, this would use the trading engine
        gem_reward = int(amount * 0.001)  # 0.1% of trade value as GEM reward
        current_gems = request.session.get("gem_coins", 1000)
        request.session["gem_coins"] = current_gems + gem_reward
        
        return {
            "status": "success",
            "data": {
                "trade_id": f"trade-{int(time.time())}",
                "action": action.upper(),
                "coin_id": coin_id,
                "amount": amount,
                "gem_reward": gem_reward,
                "message": f"{action.upper()} order executed successfully! +{gem_reward} GEM coins earned."
            }
        }
    except Exception as e:
        logger.error(f"Error executing quick trade: {e}")
        return JSONResponse({"status": "error", "message": "Trade execution failed"}, status_code=500)

@app.post("/api/trading/orders")
async def place_order(request: Request):
    """Place a limit, stop-loss, or take-profit order."""
    if not request.session.get("is_authenticated"):
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
    
    try:
        data = await request.json()
        
        # Validate required fields
        required_fields = ["side", "type", "coin_id", "quantity", "price"]
        for field in required_fields:
            if field not in data:
                return JSONResponse({"status": "error", "message": f"Missing field: {field}"}, status_code=400)
        
        order_type = data["type"].upper()
        if order_type not in ["LIMIT", "STOP_LOSS", "TAKE_PROFIT"]:
            return JSONResponse({"status": "error", "message": "Invalid order type"}, status_code=400)
        
        # Demo order placement - in real implementation, this would use the trading engine
        order_id = f"order-{int(time.time())}"
        
        return {
            "status": "success",
            "data": {
                "order_id": order_id,
                "type": order_type,
                "side": data["side"].upper(),
                "coin_id": data["coin_id"],
                "quantity": data["quantity"],
                "price": data["price"],
                "status": "PENDING",
                "message": f"{order_type} order placed successfully!"
            }
        }
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return JSONResponse({"status": "error", "message": "Order placement failed"}, status_code=500)

@app.get("/api/trading/gamification/wallet")
async def get_wallet_info(request: Request):
    """Get user's GEM wallet information."""
    if not request.session.get("is_authenticated"):
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
    
    try:
        gem_coins = request.session.get("gem_coins", 1000)
        return {
            "status": "success",
            "data": {
                "gem_coins": gem_coins,
                "usd_value": gem_coins * 0.01,  # 1 GEM = $0.01
                "total_earned": request.session.get("total_gems_earned", 0),
                "total_spent": request.session.get("total_gems_spent", 0)
            }
        }
    except Exception as e:
        logger.error(f"Error getting wallet info: {e}")
        return JSONResponse({"status": "error", "message": "Failed to get wallet info"}, status_code=500)

# ====================== END TRADING API ENDPOINTS ======================

# ====================== ROULETTE GAMING API ENDPOINTS ======================

@app.post("/api/roulette/spin")
async def roulette_spin(request: Request):
    """Execute a roulette spin with bets - Demo mode supported."""
    # Demo mode support - Allow both authenticated and unauthenticated users
    is_demo_mode = not request.session.get("is_authenticated")
    
    try:
        data = await request.json()
        bets = data.get("bets", [])
        client_balance = data.get("current_balance", None)  # Balance sent from client
        
        # Enhanced validation and logging
        if not bets:
            logger.error(f"Roulette spin failed: No bets provided. Request data: {data}")
            return JSONResponse({"status": "error", "message": "No bets placed"}, status_code=400)
        
        # Validate bet structure
        for i, bet in enumerate(bets):
            if not isinstance(bet, dict):
                logger.error(f"Roulette spin failed: Bet {i} is not a dict. Bet: {bet}, All bets: {bets}")
                return JSONResponse({"status": "error", "message": f"Invalid bet structure at position {i}"}, status_code=400)
            
            required_fields = ["type", "value", "amount"]
            for field in required_fields:
                if field not in bet:
                    logger.error(f"Roulette spin failed: Missing field '{field}' in bet {i}. Bet: {bet}")
                    return JSONResponse({"status": "error", "message": f"Missing field '{field}' in bet {i}"}, status_code=400)
            
            # Validate data types
            if not isinstance(bet["amount"], (int, float)) or bet["amount"] <= 0:
                logger.error(f"Roulette spin failed: Invalid amount in bet {i}. Amount: {bet['amount']}")
                return JSONResponse({"status": "error", "message": f"Invalid bet amount in bet {i}"}, status_code=400)
        
        # Validate total bet amount
        total_bet = sum(bet.get("amount", 0) for bet in bets)
        
        # Unified balance synchronization for both demo and authenticated users
        # Prioritize client-sent balance over session for consistency, but validate it
        if client_balance is not None and isinstance(client_balance, (int, float)) and client_balance > 0:
            # Accept positive client balance
            current_gems = client_balance
            # Update session to match client for both demo and authenticated users
            request.session["gem_coins"] = client_balance
            logger.info(f"Balance synchronized from client: {client_balance} (is_demo_mode={is_demo_mode})")
        elif client_balance is not None and isinstance(client_balance, (int, float)) and client_balance <= 0:
            # Reject negative or zero client balance, use session default
            logger.warning(f"Invalid client_balance (negative/zero): {client_balance}. Using session fallback.")
            if is_demo_mode:
                current_gems = request.session.get("gem_coins", 5000)
            else:
                current_gems = max(request.session.get("gem_coins", 1000), request.session.get("wallet_balance", 1000))
        else:
            # Fallback to session balance with appropriate defaults
            if is_demo_mode:
                current_gems = request.session.get("gem_coins", 5000)  # Demo users start with 5000 GEM
            else:
                # For authenticated users, check wallet_balance as fallback if gem_coins is 0
                session_gems = request.session.get("gem_coins", 1000)
                if session_gems == 0:
                    # Check if wallet_balance can be used as fallback
                    wallet_balance = request.session.get("wallet_balance", 1000)
                    if wallet_balance > 0:
                        current_gems = wallet_balance
                        request.session["gem_coins"] = wallet_balance  # Sync gem_coins with wallet_balance
                        logger.warning(f"Authenticated user had gem_coins=0, using wallet_balance={wallet_balance} as fallback")
                    else:
                        current_gems = session_gems
                else:
                    current_gems = session_gems
            
            if client_balance is not None:
                logger.warning(f"Invalid client_balance received: {client_balance} (type: {type(client_balance)}). Using session default: {current_gems}")
        
        # Enhanced logging for balance validation debugging
        logger.info(f"Roulette spin balance check: is_demo_mode={is_demo_mode}, current_gems={current_gems}, total_bet={total_bet}, session_gems={request.session.get('gem_coins', 'NOT_SET')}, wallet_balance={request.session.get('wallet_balance', 'NOT_SET')}, client_balance={client_balance}, session_keys={list(request.session.keys())}")
        
        if total_bet > current_gems:
            logger.error(f"Roulette spin failed - insufficient balance: current_gems={current_gems}, total_bet={total_bet}, is_demo_mode={is_demo_mode}, client_balance={client_balance}, wallet_balance={request.session.get('wallet_balance')}, gem_coins_before={request.session.get('gem_coins')}, session_user_id={request.session.get('user_id')}")
            return JSONResponse({"status": "error", "message": "Insufficient GEM coins"}, status_code=400)
        
        # Generate random winning number (0-36)
        import random
        winning_number = random.randint(0, 36)
        
        # Calculate payouts
        total_payout = 0
        winning_bets = []
        
        for bet in bets:
            bet_type = bet.get("type")
            bet_value = bet.get("value")
            bet_amount = bet.get("amount", 0)
            
            won = False
            payout_multiplier = 0
            
            if bet_type == "single" and bet_value == winning_number:
                won = True
                payout_multiplier = 35  # 35:1 payout for single number
            elif bet_type == "red" and winning_number != 0 and winning_number in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]:
                won = True
                payout_multiplier = 1  # 1:1 payout for color
            elif bet_type == "black" and winning_number != 0 and winning_number in [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]:
                won = True
                payout_multiplier = 1  # 1:1 payout for color
            elif bet_type == "green" and winning_number == 0:
                won = True
                payout_multiplier = 35  # 35:1 payout for green (0)
            elif bet_type == "even" and winning_number != 0 and winning_number % 2 == 0:
                won = True
                payout_multiplier = 1  # 1:1 payout for even/odd
            elif bet_type == "odd" and winning_number != 0 and winning_number % 2 == 1:
                won = True
                payout_multiplier = 1  # 1:1 payout for even/odd
            elif bet_type == "high" and 19 <= winning_number <= 36:
                won = True
                payout_multiplier = 1  # 1:1 payout for high/low
            elif bet_type == "low" and 1 <= winning_number <= 18:
                won = True
                payout_multiplier = 1  # 1:1 payout for high/low
            
            if won:
                payout = bet_amount * (payout_multiplier + 1)  # Return bet + winnings
                total_payout += payout
                winning_bets.append({
                    "type": bet_type,
                    "value": bet_value,
                    "amount": bet_amount,
                    "payout": payout
                })
        
        # Update user balance
        new_balance = current_gems - total_bet + total_payout
        request.session["gem_coins"] = new_balance
        
        # Log balance update for debugging
        logger.info(f"Roulette spin balance updated: old_balance={current_gems}, total_bet={total_bet}, total_payout={total_payout}, new_balance={new_balance}, session_updated={request.session.get('gem_coins')}")
        
        # Update session stats (both demo and authenticated users)
        current_games = request.session.get("total_games", 0)
        current_wins = request.session.get("total_wins", 0)
        request.session["total_games"] = current_games + 1
        
        if total_payout > total_bet:
            request.session["total_wins"] = current_wins + 1
        
        return {
            "status": "success",
            "data": {
                "winning_number": winning_number,
                "total_bet": total_bet,
                "total_payout": total_payout,
                "net_result": total_payout - total_bet,
                "winning_bets": winning_bets,
                "new_balance": new_balance,
                "is_winner": total_payout > total_bet
            }
        }
    except Exception as e:
        logger.error(f"Error executing roulette spin: {e}. Request data: {data if 'data' in locals() else 'Not parsed'}, session_data={dict(request.session) if hasattr(request, 'session') else 'NO_SESSION'}")
        return JSONResponse({"status": "error", "message": "Spin execution failed", "error": str(e)}, status_code=500)

@app.get("/api/roulette/stats")
async def get_roulette_stats(request: Request):
    """Get user's roulette gaming statistics."""
    if not request.session.get("is_authenticated"):
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
    
    try:
        total_games = request.session.get("total_games", 0)
        total_wins = request.session.get("total_wins", 0)
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
        
        return {
            "status": "success",
            "data": {
                "total_games": total_games,
                "total_wins": total_wins,
                "total_losses": total_games - total_wins,
                "win_rate": round(win_rate, 2),
                "current_level": request.session.get("current_level", 1),
                "total_experience": request.session.get("total_experience", 0),
                "gem_balance": request.session.get("gem_coins", 1000)
            }
        }
    except Exception as e:
        logger.error(f"Error getting roulette stats: {e}")
        return JSONResponse({"status": "error", "message": "Failed to get stats"}, status_code=500)

@app.post("/api/roulette/validate-bet")
async def validate_roulette_bet(request: Request):
    """Validate a roulette bet before placing."""
    if not request.session.get("is_authenticated"):
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
    
    try:
        data = await request.json()
        bet_amount = data.get("amount", 0)
        
        current_gems = request.session.get("gem_coins", 1000)
        
        if bet_amount <= 0:
            return JSONResponse({"status": "error", "message": "Invalid bet amount"}, status_code=400)
        
        if bet_amount > current_gems:
            return JSONResponse({"status": "error", "message": "Insufficient GEM coins"}, status_code=400)
        
        return {
            "status": "success",
            "data": {
                "valid": True,
                "current_balance": current_gems,
                "max_bet": current_gems
            }
        }
    except Exception as e:
        logger.error(f"Error validating bet: {e}")
        return JSONResponse({"status": "error", "message": "Bet validation failed"}, status_code=500)

@app.get("/api/roulette/balance")
async def get_current_balance(request: Request):
    """Get current user balance for roulette game - supports both demo and authenticated users."""
    try:
        is_demo_mode = not request.session.get("is_authenticated")
        
        if is_demo_mode:
            # Demo users: use session if set; otherwise initialize with minimal platform default
            session_gems = request.session.get("gem_coins")
            if isinstance(session_gems, (int, float)) and session_gems >= 0:
                current_balance = session_gems
            else:
                # Initialize a sane default once and persist to session for consistency
                current_balance = 1000
                request.session["gem_coins"] = current_balance
        else:
            # Authenticated users: prioritize gem_coins, fallback to wallet_balance
            session_gems = request.session.get("gem_coins", 0)
            if session_gems <= 0:
                # Use wallet_balance as fallback if gem_coins is 0 or missing
                wallet_balance = request.session.get("wallet_balance", 1000)
                current_balance = wallet_balance
                # Sync gem_coins with wallet_balance for consistency
                request.session["gem_coins"] = wallet_balance
                logger.info(f"Authenticated user balance synced from wallet_balance: {wallet_balance}")
            else:
                current_balance = session_gems
        
        logger.info(f"Balance request: is_demo_mode={is_demo_mode}, balance={current_balance}, user_id={request.session.get('user_id', 'anonymous')}")
        
        return {
            "status": "success",
            "data": {
                "balance": current_balance,
                "is_demo_mode": is_demo_mode,
                "user_id": request.session.get("user_id", "anonymous")
            }
        }
    except Exception as e:
        logger.error(f"Error getting current balance: {e}")
        return JSONResponse({"status": "error", "message": "Failed to get balance"}, status_code=500)

# ====================== END ROULETTE GAMING API ENDPOINTS ======================

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard - enhanced interface."""
    return templates.TemplateResponse("home.html", {"request": request})


# ==================== SOCIAL & GAMING APIs (MOCK IMPLEMENTATION) ====================

MAX_AVATAR_BYTES = 4 * 1024 * 1024  # 4MB limit

# ==================== PLATFORM STATS (TIME-BASED, EVER-RISING) ====================

from datetime import datetime, timezone

PLATFORM_BASE = datetime(2025, 1, 1, tzinfo=timezone.utc)
PLATFORM_BASELINES = {
    "total_users": 5000,
    "total_games": 200_000,
    "total_bets": 450_000,
    "gems_awarded": 1_000_000,
}
PLATFORM_RATES_PER_SEC = {
    # Tunable growth rates per second
    "total_users": 0.05,     # ~4320/day
    "total_games": 2.5,      # ~216k/day
    "total_bets": 3.8,       # ~328k/day
    "gems_awarded": 50.0,    # ~4.32M/day
}


def compute_platform_stats():
    now = datetime.now(timezone.utc)
    delta = (now - PLATFORM_BASE).total_seconds()
    stats = {}
    for k in PLATFORM_BASELINES:
        base = PLATFORM_BASELINES[k]
        rate = PLATFORM_RATES_PER_SEC[k]
        stats[k] = int(base + max(0, delta) * rate)
    # Derive active players as a function of users
    stats["active_players"] = int(max(150, stats["total_users"] * 0.12))
    return stats


@app.get("/api/platform/stats")
async def platform_stats():
    """Return time-based ever-rising platform stats."""
    return {"status": "success", "data": compute_platform_stats()}


# ==================== SOCIAL BOTS ====================

BOT_USERNAMES = [
    "Bot_Satoshi", "Bot_Vitalik", "Bot_Ada", "Bot_Solana", "Bot_Avax",
    "Bot_Doge", "Bot_Polkadot", "Bot_Chainlink", "Bot_Uniswap", "Bot_Luna"
]

# Bot settings (configurable via env)
BOT_ENABLED = os.getenv("BOTS_ENABLED", "true").lower() == "true"
BOT_MIN_SEC = int(os.getenv("BOTS_MIN_SEC", "30"))
BOT_MAX_SEC = int(os.getenv("BOTS_MAX_SEC", "90"))
BOT_PENDING_CAP = int(os.getenv("BOTS_PENDING_CAP", "5"))
BOT_SEED_ACCEPTED = int(os.getenv("BOTS_SEED_ACCEPTED", "2"))
BOT_SEED_PENDING = int(os.getenv("BOTS_SEED_PENDING", "1"))


async def seed_bots(session):
    """Create bot users if they don't exist."""
    from sqlalchemy import select
    existing = await session.execute(select(User).where(User.username.in_(BOT_USERNAMES)))
    existing_map = {u.username: u for u in existing.scalars().all()}
    created = 0
    for uname in BOT_USERNAMES:
        if uname in existing_map:
            continue
        user = User(
            username=uname,
            email=f"{uname.lower()}@cryptochecker.com",
            hashed_password="demo",
            display_name=uname.replace("_", " "),
            avatar_url="/static/images/default-avatar.png",
            current_level=random.randint(3, 12),
            total_experience=random.randint(500, 5000)
        )
        session.add(user)
        created += 1
    if created:
        await session.commit()


async def ensure_user_seeded_social(user_id: str):
    """Seed initial friendships for a user if none exist."""
    if BOT_SEED_ACCEPTED <= 0 and BOT_SEED_PENDING <= 0:
        return
    async with db_manager.get_session() as session:
        # Check existing friendships
        res = await session.execute(
            select(Friendship).where(
                (Friendship.sender_id == user_id) | (Friendship.receiver_id == user_id)
            )
        )
        if res.scalars().first():
            return
        # Load bots
        res_bots = await session.execute(select(User).where(User.username.in_(BOT_USERNAMES)))
        bots = res_bots.scalars().all()
        if not bots:
            return
        random.shuffle(bots)
        created = 0
        # Accepted friendships
        for bot in bots[:BOT_SEED_ACCEPTED]:
            session.add(Friendship(sender_id=bot.id, receiver_id=user_id, status="ACCEPTED", accepted_at=datetime.utcnow()))
            created += 1
        # Pending requests from next bots
        for bot in bots[BOT_SEED_ACCEPTED:BOT_SEED_ACCEPTED + BOT_SEED_PENDING]:
            session.add(Friendship(sender_id=bot.id, receiver_id=user_id, status="PENDING"))
            created += 1
        if created:
            await session.commit()


async def bots_friend_request_loop():
    """Background loop where bots occasionally send friend requests to real users."""
    from sqlalchemy import select
    while True:
        try:
            async with db_manager.get_session() as session:
                # Load bots and humans
                res_bots = await session.execute(select(User).where(User.username.in_(BOT_USERNAMES)))
                bots = res_bots.scalars().all()
                res_hum = await session.execute(select(User).where(~User.username.in_(BOT_USERNAMES)))
                humans = res_hum.scalars().all()
                if not bots or not humans:
                    await asyncio.sleep(30)
                    continue
                bot = random.choice(bots)
                target = random.choice(humans)
                if not target or not bot:
                    await asyncio.sleep(30)
                    continue
                # Skip if friendship exists
                res = await session.execute(
                    select(Friendship).where(
                        ((Friendship.sender_id == bot.id) & (Friendship.receiver_id == target.id)) |
                        ((Friendship.sender_id == target.id) & (Friendship.receiver_id == bot.id))
                    )
                )
                f = res.scalars().first()
                if not f:
                    # Skip if user opted out of friend requests
                    res_u = await session.execute(select(User).where(User.id == target.id))
                    target_u = res_u.scalars().first()
                    if target_u and hasattr(target_u, 'allow_friend_requests') and target_u.allow_friend_requests is False:
                        await asyncio.sleep(BOT_MIN_SEC)
                        continue
                    # Limit pending for target to avoid spam
                    res_p = await session.execute(
                        select(Friendship).where(
                            (Friendship.receiver_id == target.id) & (Friendship.status == "PENDING")
                        )
                    )
                    pending_count = len(res_p.scalars().all())
                    if pending_count < BOT_PENDING_CAP:
                        fr = Friendship(sender_id=bot.id, receiver_id=target.id, status="PENDING")
                        session.add(fr)
                        await session.commit()
        except asyncio.CancelledError:
            break
        except Exception:
            # Swallow errors to keep loop alive
            pass
        # Randomized delay between bot actions
        await asyncio.sleep(max(BOT_MIN_SEC, min(BOT_MAX_SEC, random.randint(BOT_MIN_SEC, BOT_MAX_SEC))))


@app.post("/api/social/bots/nudge")
async def social_bots_nudge(request: Request):
    """Send a few bot friend requests to the current user immediately."""
    if not request.session.get("is_authenticated"):
        return {"status": "error", "message": "Not authenticated"}
    from sqlalchemy import select
    try:
        async with db_manager.get_session() as session:
            # Ensure current user exists
            user = await _ensure_db_user(request)
            # Respect opt-out
            res_user = await session.execute(select(User).where(User.id == user.id))
            db_user = res_user.scalars().first()
            if db_user and hasattr(db_user, 'allow_friend_requests') and db_user.allow_friend_requests is False:
                return {"status": "error", "message": "User opted out"}
            # Load bots
            res_bots = await session.execute(select(User).where(User.username.in_(BOT_USERNAMES)))
            bots = res_bots.scalars().all()
            random.shuffle(bots)
            created = 0
            for bot in bots[:3]:
                # Check existing friendship
                res = await session.execute(
                    select(Friendship).where(
                        ((Friendship.sender_id == bot.id) & (Friendship.receiver_id == user.id)) |
                        ((Friendship.sender_id == user.id) & (Friendship.receiver_id == bot.id))
                    )
                )
                f = res.scalars().first()
                if not f:
                    fr = Friendship(sender_id=bot.id, receiver_id=user.id, status="PENDING")
                    session.add(fr)
                    created += 1
            if created:
                await session.commit()
            return {"status": "success", "created": created}
    except Exception as e:
        logger.error(f"Bots nudge failed: {e}")
        return {"status": "error", "message": "Failed to nudge bots"}


@app.get("/api/social/bots/settings")
async def get_bots_settings(request: Request):
    """Return bot settings and user's opt-out preference."""
    if not request.session.get("is_authenticated"):
        return {"status": "error", "message": "Not authenticated"}
    async with db_manager.get_session() as session:
        user = await _ensure_db_user(request)
        res = await session.execute(select(User).where(User.id == user.id))
        db_user = res.scalars().first()
        allow = True
        if db_user and hasattr(db_user, 'allow_friend_requests'):
            allow = bool(db_user.allow_friend_requests)
        return {
            "status": "success",
            "data": {
                "bots_enabled": BOT_ENABLED,
                "min_seconds": BOT_MIN_SEC,
                "max_seconds": BOT_MAX_SEC,
                "pending_cap": BOT_PENDING_CAP,
                "allow_bots": allow
            }
        }


@app.put("/api/social/bots/settings")
async def put_bots_settings(request: Request):
    """Update user's preference for receiving bot friend requests."""
    if not request.session.get("is_authenticated"):
        return {"status": "error", "message": "Not authenticated"}
    data = await request.json()
    allow = bool(data.get("allow_bots", True))
    async with db_manager.get_session() as session:
        user = await _ensure_db_user(request)
        res = await session.execute(select(User).where(User.id == user.id))
        db_user = res.scalars().first()
        if db_user and hasattr(db_user, 'allow_friend_requests'):
            db_user.allow_friend_requests = allow
            await session.commit()
        return {"status": "success", "allow_bots": allow}

# -------- Social (public/mock) endpoints to power UI without token auth --------

async def _get_or_create_db_user_from_session():
    """Helper: map session user to DB user; create if missing (demo-safe)."""
    async with db_manager.get_session() as session:
        # In some flows, we call without a Request; get from context via closure
        raise RuntimeError("Not used directly")

async def _ensure_db_user(request: Request) -> User:
    async with db_manager.get_session() as session:
        user_id = request.session.get("user_id")
        username = request.session.get("username")
        email = request.session.get("email") or (f"{username}@cryptochecker.com" if username else None)
        if not username:
            raise HTTPException(status_code=401, detail="Not authenticated")
        db_user = None
        if user_id:
            res = await session.execute(select(User).where(User.id == user_id))
            db_user = res.scalars().first()
        if not db_user:
            res = await session.execute(select(User).where(User.username == username))
            db_user = res.scalars().first()
        if not db_user:
            # Create minimal user for demo
            db_user = User(
                username=username,
                email=(email or f"{username}@cryptochecker.com").lower(),
                hashed_password="demo",  # placeholder for demo sessions
                display_name=request.session.get("display_name", username),
                avatar_url=request.session.get("avatar_url", "/static/images/default-avatar.png"),
                current_level=request.session.get("current_level", 1),
                total_experience=request.session.get("total_experience", 0)
            )
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)
        return db_user


def _serialize_user_public(u: User):
    return {
        "id": u.id,
        "username": u.username,
        "display_name": u.display_name or u.username,
        "avatar_url": u.avatar_url or "/static/images/default-avatar.png",
    }


@app.get("/api/social/stats")
async def social_stats(request: Request):
    """Basic social stats for the sidebar based on DB (demo)."""
    try:
        user = await _ensure_db_user(request)
        async with db_manager.get_session() as session:
            # Total friends = accepted friendships where user is sender or receiver
            res = await session.execute(
                select(Friendship).where(
                    ((Friendship.sender_id == user.id) | (Friendship.receiver_id == user.id)) &
                    (Friendship.status == "ACCEPTED")
                )
            )
            friends = res.scalars().all()
            return {
                "total_friends": len(friends),
                "online_friends": 0,  # no presence system yet
                "global_rank": 0,
                "achievements_shared": 0
            }
    except Exception as e:
        logger.warning(f"social_stats fallback: {e}")
        return {"total_friends": 0, "online_friends": 0, "global_rank": 0, "achievements_shared": 0}


@app.get("/api/social/friends")
async def get_friends_public(request: Request):
    """Return DB-backed friends list (accepted friendships)."""
    user = await _ensure_db_user(request)
    async with db_manager.get_session() as session:
        res = await session.execute(
            select(Friendship).where(
                ((Friendship.sender_id == user.id) | (Friendship.receiver_id == user.id)) &
                (Friendship.status == "ACCEPTED")
            )
        )
        relations = res.scalars().all()
        # Collect friend IDs
        friend_ids = [r.receiver_id if r.sender_id == user.id else r.sender_id for r in relations]
        if not friend_ids:
            return []
        res_u = await session.execute(select(User).where(User.id.in_(friend_ids)))
        users = res_u.scalars().all()
        return [_serialize_user_public(u) for u in users]


@app.get("/api/social/friends/requests")
async def get_friend_requests_public(request: Request):
    user = await _ensure_db_user(request)
    async with db_manager.get_session() as session:
        res = await session.execute(
            select(Friendship).where(
                (Friendship.receiver_id == user.id) & (Friendship.status == "PENDING")
            )
        )
        pending = res.scalars().all()
        # Load senders
        sender_ids = list({p.sender_id for p in pending})
        senders = {}
        if sender_ids:
            res_u = await session.execute(select(User).where(User.id.in_(sender_ids)))
            for u in res_u.scalars().all():
                senders[u.id] = _serialize_user_public(u)
        return [
            {
                "id": p.id,
                "from_user": senders.get(p.sender_id, {"id": p.sender_id}),
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in pending
        ]


@app.post("/api/social/friends/request")
async def send_friend_request_public(request: Request):
    data = await request.json()
    to_username = (data.get("username") or "").strip()
    if not to_username:
        return {"status": "error", "message": "Username required"}
    me = await _ensure_db_user(request)
    if to_username.lower() == me.username.lower():
        return {"status": "error", "message": "Cannot add yourself"}
    async with db_manager.get_session() as session:
        # Find or create receiver
        res = await session.execute(select(User).where(User.username == to_username))
        other = res.scalars().first()
        if not other:
            # For demo, create a minimal user record
            other = User(
                username=to_username,
                email=f"{to_username}@cryptochecker.com",
                hashed_password="demo",
                display_name=to_username,
            )
            session.add(other)
            await session.commit()
            await session.refresh(other)
        # Respect opt-out on receiver
        if hasattr(other, 'allow_friend_requests') and other.allow_friend_requests is False:
            return {"status": "error", "message": "User is not accepting requests"}
        # Check existing friendship
        res = await session.execute(
            select(Friendship).where(
                ((Friendship.sender_id == me.id) & (Friendship.receiver_id == other.id)) |
                ((Friendship.sender_id == other.id) & (Friendship.receiver_id == me.id))
            )
        )
        f = res.scalars().first()
        if f:
            if f.status == "PENDING" and f.sender_id == other.id:
                # Auto-accept reverse pending
                f.status = "ACCEPTED"
                f.accepted_at = datetime.utcnow()
                await session.commit()
                return {"status": "success", "message": "Friend request accepted"}
            return {"status": "error", "message": f"Request already {f.status.lower()}"}
        # Create new request
        fr = Friendship(sender_id=me.id, receiver_id=other.id, status="PENDING")
        session.add(fr)
        await session.commit()
        return {"status": "success", "message": f"Friend request sent to {to_username}"}


@app.post("/api/social/friends/requests/{request_id}")
async def respond_friend_request_public(request_id: str, request: Request):
    data = await request.json()
    action = (data.get("action") or "").upper()
    if action not in {"ACCEPT", "DECLINE"}:
        return {"status": "error", "message": "Invalid action"}
    me = await _ensure_db_user(request)
    async with db_manager.get_session() as session:
        res = await session.execute(select(Friendship).where(Friendship.id == request_id))
        fr = res.scalars().first()
        if not fr or fr.receiver_id != me.id:
            return {"status": "error", "message": "Request not found"}
        if action == "ACCEPT":
            fr.status = "ACCEPTED"
            fr.accepted_at = datetime.utcnow()
        else:
            fr.status = "DECLINED"
        await session.commit()
        return {"status": "success", "message": f"Request {action.lower()}ed"}


@app.delete("/api/social/friends/{friend_id}")
async def remove_friend_public(friend_id: str, request: Request):
    me = await _ensure_db_user(request)
    async with db_manager.get_session() as session:
        res = await session.execute(
            select(Friendship).where(
                ((Friendship.sender_id == me.id) & (Friendship.receiver_id == friend_id)) |
                ((Friendship.sender_id == friend_id) & (Friendship.receiver_id == me.id))
            )
        )
        fr = res.scalars().first()
        if not fr:
            return {"status": "error", "message": "Friendship not found"}
        await session.delete(fr)
        await session.commit()
        return {"status": "success", "message": "Friend removed"}


@app.post("/api/social/gifts/send")
async def send_gift_public(request: Request):
    data = await request.json()
    return {"status": "success", "message": "Gift sent", "data": data}


@app.get("/api/social/gifts/received")
async def get_received_gifts_public(limit: int = 20):
    gifts = [
        {
            "id": "gift-1",
            "from_user": {
                "id": "friend-2",
                "username": "DiamondHands",
                "avatar_url": "/static/images/default-avatar.png"
            },
            "currency_type": "GEM_COINS",
            "amount": 250,
            "message": "GG!",
            "created_at": "2025-01-12T14:00:00Z"
        }
    ]
    return gifts[:limit]


@app.put("/api/social/status")
async def update_status_public(request: Request):
    data = await request.json()
    status_msg = (data.get("status") or "").strip()
    mood = (data.get("mood") or "").strip() or None
    request.session["status_message"] = status_msg
    request.session["current_mood"] = mood or "HAPPY"
    return {"status": "success", "message": "Status updated"}

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

# ==================== LEVELING SYSTEM FUNCTIONS ====================

def calculate_required_exp(level):
    """Calculate XP required to reach the next level."""
    # Standard gaming formula: exponential growth
    return int(100 * (level ** 1.5))

def calculate_level_progress(current_exp, current_level):
    """Calculate percentage progress to next level."""
    if current_level == 1:
        exp_for_current_level = 0
    else:
        exp_for_current_level = int(100 * ((current_level - 1) ** 1.5))
    
    exp_for_next_level = calculate_required_exp(current_level)
    exp_progress = current_exp - exp_for_current_level
    exp_needed = exp_for_next_level - exp_for_current_level
    
    if exp_needed <= 0:
        return 100.0
    
    progress = (exp_progress / exp_needed) * 100
    return round(max(0, min(100, progress)), 1)

def calculate_level_from_exp(total_exp):
    """Calculate level based on total experience."""
    level = 1
    while calculate_required_exp(level) <= total_exp:
        level += 1
    return level

@app.get("/api/gaming/stats")
async def get_gaming_stats(request: Request):
    """Get user gaming statistics from session data."""
    # Check authentication
    if not request.session.get("is_authenticated"):
        return {"success": False, "error": "Not authenticated"}
    
    # Get stats from session data
    total_games = request.session.get("total_games", 0)
    total_wins = request.session.get("total_wins", 0)
    total_losses = total_games - total_wins
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
    
    return {
        "success": True,
        "data": {
            "total_games": total_games,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "win_rate": round(win_rate, 1),
            "total_winnings": request.session.get("gem_coins", 0),
            "biggest_win": 1250,  # Could be stored in session later
            "current_streak": 3,  # Could be tracked in session
            "longest_win_streak": 8,  # Could be tracked in session
            "longest_loss_streak": 4,  # Could be tracked in session
            "favorite_game": "roulette",
            "achievements_count": request.session.get("achievements_count", 0),
            "level_progress": {
                "current_level": request.session.get("current_level", 1),
                "current_exp": request.session.get("total_experience", 0),
                "required_exp": calculate_required_exp(request.session.get("current_level", 1)),
                "progress_percentage": calculate_level_progress(request.session.get("total_experience", 0), request.session.get("current_level", 1))
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
                return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
        
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


# --- Compatibility: implement item routes expected by front-end client ---
def _ensure_session_inventory(request: Request):
    """Ensure session has an 'inventory' list; return it."""
    default_items = [
        {
            "id": 1,
            "name": "Lucky Crypto Charm",
            "type": "consumables",
            "category": "consumables",
            "rarity": "uncommon",
            "icon": "🍀",
            "quantity": 3,
            "description": "Increases your luck in the next 5 games. +10% chance of winning.",
            "effects": "Luck Boost: +10% win chance for 5 games",
            "value": 500,
            "usable": True,
            "equipped": False,
            "is_equipped": False,
            "is_tradeable": False,
            "market_value": 500,
            "obtained_at": datetime.utcnow().isoformat(),
            "max_stack_size": 99
        },
        {
            "id": 2,
            "name": "Golden Bitcoin",
            "type": "collectibles",
            "category": "collectibles",
            "rarity": "legendary",
            "icon": "🪙",
            "quantity": 1,
            "description": "A rare golden Bitcoin collectible. Extremely valuable and sought after.",
            "effects": "Passive: +5% GEM earnings from all activities",
            "value": 10000,
            "usable": False,
            "equipped": False,
            "is_equipped": False,
            "is_tradeable": False,
            "market_value": 10000,
            "obtained_at": datetime.utcnow().isoformat(),
            "max_stack_size": 1
        },
        {
            "id": 3,
            "name": "Energy Drink",
            "type": "consumables",
            "category": "consumables",
            "rarity": "common",
            "icon": "⚡",
            "quantity": 8,
            "description": "Restores energy and provides a temporary boost to all activities.",
            "effects": "Energy Boost: +20% XP gain for 1 hour",
            "value": 100,
            "usable": True,
            "equipped": False,
            "is_equipped": False,
            "is_tradeable": False,
            "market_value": 100,
            "obtained_at": datetime.utcnow().isoformat(),
            "max_stack_size": 20
        }
    ]

    inv = request.session.get('inventory')
    if not inv:
        request.session['inventory'] = default_items
        inv = request.session['inventory']
    return inv


@app.get("/api/inventory/items/{item_id}")
async def api_get_item(request: Request, item_id: int):
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)

        items = _ensure_session_inventory(request)
        item = next((i for i in items if i['id'] == item_id), None)
        if not item:
            return {"status": "error", "message": "Item not found"}

        return {"status": "success", "data": item}
    except Exception as e:
        logger.error(f"Get item error: {e}")
        return {"status": "error", "message": "Failed to get item"}


@app.post("/api/inventory/items/{item_id}/equip")
async def api_equip_item(request: Request, item_id: int):
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}

        items = _ensure_session_inventory(request)
        item = next((i for i in items if i['id'] == item_id), None)
        if not item:
            return {"status": "error", "message": "Item not found"}

        # simple toggle/equip behavior
        item['equipped'] = True
        request.session['inventory'] = items
        return JSONResponse(
            {"status": "success", "data": {"item_id": item_id, "equipped": True}},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Equip item error: {e}")
        return {"status": "error", "message": "Failed to equip item"}


@app.post("/api/inventory/items/{item_id}/unequip")
async def api_unequip_item(request: Request, item_id: int):
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}

        items = _ensure_session_inventory(request)
        item = next((i for i in items if i['id'] == item_id), None)
        if not item:
            return {"status": "error", "message": "Item not found"}

        item['equipped'] = False
        request.session['inventory'] = items
        return JSONResponse(
            {"status": "success", "data": {"item_id": item_id, "equipped": False}},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Unequip item error: {e}")
        return {"status": "error", "message": "Failed to unequip item"}


@app.post("/api/inventory/items/{item_id}/use")
async def api_use_item(request: Request, item_id: int):
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)

        data = await request.json()
        qty = int(data.get('quantity', 1))

        items = _ensure_session_inventory(request)
        item = next((i for i in items if i['id'] == item_id), None)
        if not item or item.get('quantity', 0) < qty:
            return JSONResponse({"status": "error", "message": "Insufficient quantity"}, status_code=400)

        item['quantity'] -= qty
        request.session['inventory'] = items

        # effects: optionally modify wallet or other session state
        return JSONResponse(
            {"status": "success", "data": {"item_id": item_id, "used": qty, "remaining": item['quantity']}},
            status_code=200
        )
    except Exception as e:
        logger.error(f"API use item error: {e}")
        return {"status": "error", "message": "Failed to use item"}


@app.post("/api/inventory/items/{item_id}/sell")
async def api_sell_item(request: Request, item_id: int):
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            return {"status": "error", "message": "Not authenticated"}

        data = await request.json()
        qty = int(data.get('quantity', 1))

        items = _ensure_session_inventory(request)
        item = next((i for i in items if i['id'] == item_id), None)
        if not item or item.get('quantity', 0) < qty:
            return JSONResponse({"status": "error", "message": "Insufficient quantity"}, status_code=400)

        # Deduct quantity and credit wallet_balance
        item['quantity'] -= qty
        value = item.get('value', 0) * qty
        current_balance = request.session.get('wallet_balance', 5000)
        new_balance = current_balance + value
        request.session['wallet_balance'] = new_balance
        request.session['inventory'] = items

        logger.info(
            f"User {user_id} sold item {item_id} x{qty} for {value} (new balance {request.session['wallet_balance']})"
        )

        return JSONResponse(
            {
                "status": "success",
                "data": {
                    "item_id": item_id,
                    "sold": qty,
                    "credited": value,
                    "total_value": value,
                    "new_balance": request.session['wallet_balance']
                }
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Sell item error: {e}")
        return {"status": "error", "message": "Failed to sell item"}


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
async def _ensure_db_user(request: Request) -> User:
    """Ensure session user has a DB record; create minimal if missing, and seed social if empty."""
    async with db_manager.get_session() as session:
        user_id = request.session.get("user_id")
        username = request.session.get("username")
        email = request.session.get("email") or (f"{username}@cryptochecker.com" if username else None)
        if not username:
            raise HTTPException(status_code=401, detail="Not authenticated")
        db_user = None
        if user_id:
            res = await session.execute(select(User).where(User.id == user_id))
            db_user = res.scalars().first()
        if not db_user:
            res = await session.execute(select(User).where(User.username == username))
            db_user = res.scalars().first()
        if not db_user:
            # Create minimal user for demo
            db_user = User(
                username=username,
                email=(email or f"{username}@cryptochecker.com").lower(),
                hashed_password="demo",
                display_name=request.session.get("display_name", username),
                avatar_url=request.session.get("avatar_url", "/static/images/default-avatar.png"),
                current_level=request.session.get("current_level", 1),
                total_experience=request.session.get("total_experience", 0)
            )
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)
        # Seed initial friendships if none exist
        try:
            res2 = await session.execute(
                select(Friendship).where((Friendship.sender_id == db_user.id) | (Friendship.receiver_id == db_user.id))
            )
            if not res2.scalars().first():
                # seed using helper
                await ensure_user_seeded_social(db_user.id)
        except Exception:
            pass
        return db_user
