"""
Main application entry point for CryptoChecker Gaming Platform.
Fixed version with proper imports and variable definitions.
"""

import asyncio
import random
from datetime import datetime
import time
import uvicorn
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, WebSocket, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Bot settings (define early to avoid NameError)
BOT_ENABLED = os.getenv("BOTS_ENABLED", "true").lower() == "true"
BOT_MIN_SEC = int(os.getenv("BOTS_MIN_SEC", "30"))
BOT_MAX_SEC = int(os.getenv("BOTS_MAX_SEC", "90"))
BOT_PENDING_CAP = int(os.getenv("BOTS_PENDING_CAP", "5"))
BOT_SEED_ACCEPTED = int(os.getenv("BOTS_SEED_ACCEPTED", "2"))
BOT_SEED_PENDING = int(os.getenv("BOTS_SEED_PENDING", "1"))

BOT_USERNAMES = [
    "Bot_Satoshi", "Bot_Vitalik", "Bot_Ada", "Bot_Solana", "Bot_Avax",
    "Bot_Doge", "Bot_Polkadot", "Bot_Chainlink", "Bot_Uniswap", "Bot_Luna"
]

MAX_AVATAR_BYTES = 4 * 1024 * 1024  # 4MB limit

# Try to import all API routers - with fallbacks for missing ones
try:
    from api.auth_api import router as auth_router
except ImportError as e:
    print(f"Warning: Could not import auth_api: {e}")
    auth_router = None

try:
    from api.gaming_api import router as gaming_router
except ImportError as e:
    print(f"Warning: Could not import gaming_api: {e}")
    gaming_router = None

try:
    from api.social_api import router as social_router
except ImportError as e:
    print(f"Warning: Could not import social_api: {e}")
    social_router = None

try:
    from api.admin_api import router as admin_router
except ImportError as e:
    print(f"Warning: Could not import admin_api: {e}")
    admin_router = None

try:
    from api.analytics_api import router as analytics_router
except ImportError as e:
    print(f"Warning: Could not import analytics_api: {e}")
    analytics_router = None

try:
    from api.onboarding_api import router as onboarding_router
except ImportError as e:
    print(f"Warning: Could not import onboarding_api: {e}")
    onboarding_router = None

try:
    from api.mini_games_api import router as mini_games_router
except ImportError as e:
    print(f"Warning: Could not import mini_games_api: {e}")
    mini_games_router = None

try:
    from web.trading_api import router as trading_router
except ImportError as e:
    print(f"Warning: Could not import trading_api: {e}")
    trading_router = None

# Import database and other systems with fallbacks
try:
    from database.database_manager import db_manager, get_db_session
    from database.unified_models import User, Friendship
    database_available = True
except ImportError as e:
    print(f"Warning: Could not import database: {e}")
    database_available = False
    db_manager = None
    get_db_session = None

try:
    from analytics.monitoring import monitoring_system
    monitoring_available = True
except ImportError as e:
    print(f"Warning: Could not import monitoring: {e}")
    monitoring_available = False
    monitoring_system = None

try:
    from logger import logger
except ImportError as e:
    print(f"Warning: Could not import logger: {e}")
    import logging
    logger = logging.getLogger(__name__)

# Import SQL operations
try:
    from sqlalchemy import select
    sqlalchemy_available = True
except ImportError as e:
    print(f"Warning: SQLAlchemy not available: {e}")
    sqlalchemy_available = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting CryptoChecker Gaming Platform...")
    
    try:
        # Initialize database if available
        if database_available and db_manager:
            await db_manager.initialize()
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database not available, running in limited mode")
        
        # Start monitoring system if available
        if monitoring_available and monitoring_system:
            async def start_monitoring():
                if db_manager:
                    session = db_manager.get_session()
                    await monitoring_system.start_monitoring(session)
            
            monitoring_task = asyncio.create_task(start_monitoring())
        else:
            logger.warning("Monitoring system not available")
            monitoring_task = None

        # Start bots if enabled and database available
        bots_task = None
        if BOT_ENABLED and database_available:
            async def init_bots_and_loop():
                if db_manager:
                    async with db_manager.get_session() as session:
                        await seed_bots(session)
                    await bots_friend_request_loop()

            bots_task = asyncio.create_task(init_bots_and_loop())
        
        logger.info("CryptoChecker Gaming Platform started successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        # Don't raise to allow server to start in limited mode
    
    # Shutdown
    logger.info("Shutting down CryptoChecker Gaming Platform...")
    
    try:
        # Stop monitoring if available
        if monitoring_available and monitoring_system:
            await monitoring_system.stop_monitoring()
        
        # Cancel tasks
        if 'monitoring_task' in locals() and monitoring_task:
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
                
        if 'bots_task' in locals() and bots_task:
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
try:
    if os.path.exists("web/static"):
        app.mount("/static", StaticFiles(directory="web/static"), name="static")
    else:
        logger.warning("Static files directory not found")
except Exception as e:
    logger.error(f"Failed to mount static files: {e}")

try:
    if os.path.exists("web/templates"):
        templates = Jinja2Templates(directory="web/templates")
    else:
        logger.warning("Templates directory not found")
        templates = None
except Exception as e:
    logger.error(f"Failed to setup templates: {e}")
    templates = None

# Favicon route
@app.get("/favicon.ico")
async def favicon():
    """Serve favicon."""
    from fastapi.responses import Response
    # Simple ICO favicon data (16x16 transparent icon)
    favicon_data = b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x18\x00h\x03\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00@\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    return Response(content=favicon_data, media_type="image/x-icon")

# Include API routers with safety checks
if auth_router:
    app.include_router(auth_router, prefix="/api/v1")
if gaming_router:
    app.include_router(gaming_router, prefix="/api")
if social_router:
    app.include_router(social_router, prefix="/api/social-secure")
if admin_router:
    app.include_router(admin_router, prefix="/api")
if analytics_router:
    app.include_router(analytics_router, prefix="/api")
if onboarding_router:
    app.include_router(onboarding_router, prefix="/api")
if mini_games_router:
    app.include_router(mini_games_router, prefix="/api/mini-games")
if trading_router:
    app.include_router(trading_router, prefix="/api/trading")

# Basic routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page."""
    if templates:
        try:
            return templates.TemplateResponse("home.html", {"request": request})
        except Exception as e:
            logger.error(f"Template error: {e}")
            return HTMLResponse("<h1>CryptoChecker Gaming Platform</h1><p>Welcome! Templates are loading...</p>")
    else:
        return HTMLResponse("<h1>CryptoChecker Gaming Platform</h1><p>Welcome to the crypto gaming platform!</p>")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    status = "healthy"
    checks = {}
    
    # Check database
    if database_available and db_manager:
        checks["database"] = "available"
    else:
        checks["database"] = "unavailable"
        status = "degraded"
    
    # Check monitoring
    if monitoring_available and monitoring_system:
        checks["monitoring"] = "available"
    else:
        checks["monitoring"] = "unavailable"
    
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "CryptoChecker Gaming Platform",
        "checks": checks
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint."""
    return {
        "message": "Server is working!",
        "timestamp": time.time(),
        "database_available": database_available,
        "monitoring_available": monitoring_available,
        "bots_enabled": BOT_ENABLED
    }

# Placeholder functions for bot system (only if database available)
async def seed_bots(session):
    """Create bot users if they don't exist."""
    if not database_available or not sqlalchemy_available:
        return
    
    try:
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
    except Exception as e:
        logger.error(f"Failed to seed bots: {e}")

async def bots_friend_request_loop():
    """Background loop for bot friend requests."""
    if not database_available:
        return
        
    while True:
        try:
            # Bot logic here
            await asyncio.sleep(BOT_MIN_SEC)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Bot loop error: {e}")
            await asyncio.sleep(60)

# Startup function
def main():
    """Main application startup function."""
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main_fixed:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )

if __name__ == "__main__":
    main()