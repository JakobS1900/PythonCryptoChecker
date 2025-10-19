#!/usr/bin/env python3
"""
CryptoChecker Version3 - Real-Time Crypto Tracker with Gaming
A focused cryptocurrency tracking platform with integrated roulette gaming.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

# Add Python path protection and working directory validation
import sys
from pathlib import Path

# Ensure correct Python path for imports
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Verify we're in the correct directory
if not (current_dir / "database" / "models.py").exists():
    raise RuntimeError(
        f"Error: Server must be started from Version3 directory.\n"
        f"Current: {current_dir}\n"
        f"Run: cd Version3 && python main.py"
    )

print(f">> CryptoChecker Version3 starting from: {current_dir}")

# Import API routers
from api.crypto_api import router as crypto_router
from api.gaming_api import router as gaming_router
from api.auth_api import router as auth_router
from api.trading_api import router as trading_router
from api.clicker_api import router as clicker_router
from api.missions_api import router as missions_router
from api.stocks_api import router as stocks_router
from api.achievements_api import router as achievements_router

# Import database and services
from database.database import init_database, get_db
from crypto.price_service import price_service
from api.bot_system import initialize_bot_population
from gaming.round_manager import round_manager

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    print(">> Starting CryptoChecker Version3...")

    # Initialize database
    await init_database()
    print(">> Database initialized")

    # Start price service
    await price_service.start()
    print(">> Price service started")

    # Initialize bot population for gambling
    await initialize_bot_population()
    print(">> Bot population initialized")

    # Initialize round manager (server-managed rounds)
    await round_manager.initialize()
    print(">> Round manager initialized")

    print(">> CryptoChecker Version3 ready!")
    print("   >> Crypto Tracker: http://localhost:8000")
    print("   >> Roulette Gaming: http://localhost:8000/gaming")
    print("   >> API Docs: http://localhost:8000/docs")

    yield

    # Cleanup
    await price_service.stop()
    print(">> CryptoChecker Version3 stopped")

# Create FastAPI application
app = FastAPI(
    title="CryptoChecker Version3",
    description="Real-Time Cryptocurrency Tracker with Gaming Integration",
    version="3.0.0",
    lifespan=lifespan
)

# Add CORS middleware - restrict to local development only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Cookie", "X-Requested-With", "Accept", "Authorization", "Content-Type"],
    expose_headers=["Set-Cookie"],
)

# Add session middleware for authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "crypto-tracker-secret-key-change-in-production"),
    session_cookie="crypto_session",
    max_age=3600,  # 1 hour
    same_site="strict",
    https_only=False  # Set to True in production
)

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Setup templates with absolute path
import os
template_dir = os.path.join(os.path.dirname(__file__), "web", "templates")
templates = Jinja2Templates(directory=template_dir)

# Add the root web templates directory to the search path for enhanced templates
root_web_dir = os.path.join(os.path.dirname(__file__), "..", "web", "templates")
if root_web_dir not in [str(p) for p in templates.env.loader.searchpath]:
    templates.env.loader.searchpath.insert(0, root_web_dir)  # Insert at beginning to prioritize

# Include API routers
# Mount API routers with proper prefixes
app.include_router(
    crypto_router,
    prefix="/api/crypto",
    tags=["Crypto"]
)
app.include_router(
    gaming_router,
    prefix="/api/gaming",
    tags=["Gaming"]
)
app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"]
)
app.include_router(
    trading_router,
    prefix="/api/trading",  # Ensure trading routes have proper prefix
    tags=["Trading"]
)
app.include_router(
    clicker_router,
    prefix="/api/clicker",
    tags=["Clicker"]
)
app.include_router(
    missions_router,
    tags=["Missions"]  # Prefix already in router definition
)
app.include_router(
    stocks_router,
    tags=["Stocks"]  # Prefix already in router definition (/api/stocks)
)
app.include_router(
    achievements_router,
    prefix="/api/achievements",
    tags=["Achievements"]
)

# Authentication routes
@app.get("/login")
async def login_page(request: Request, redirect: str = None):
    """Show login page with optional redirect."""
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "redirect": redirect
        }
    )

@app.get("/register")
async def register_page(request: Request):
    """Show registration page."""
    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request}
    )

# API base endpoint
@app.get("/api")
@app.post("/api")
async def api_info():
    """API information endpoint - handles base /api requests."""
    return {
        "success": True,
        "message": "CryptoChecker Version3 API",
        "version": "3.0.0",
        "endpoints": {
            "crypto": "/api/crypto/*",
            "gaming": "/api/gaming/*",
            "auth": "/api/auth/*",
            "docs": "/docs"
        }
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with crypto dashboard."""
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/gaming")
async def game_page(request: Request):
    """Main gaming page with enhanced roulette."""
    return templates.TemplateResponse(
        "gaming.html",
        {"request": request}
    )

@app.get("/clicker")
async def clicker_page(request: Request):
    """Crypto clicker game page."""
    return templates.TemplateResponse(
        "crypto_clicker.html",
        {"request": request}
    )

@app.get("/stocks")
async def stocks_page(request: Request):
    """Stock market page."""
    return templates.TemplateResponse(
        "stocks.html",
        {"request": request}
    )

@app.get("/gaming/roulette", response_class=HTMLResponse)
async def gaming_roulette(request: Request):
    """Direct route to roulette gaming page."""
    return templates.TemplateResponse("gaming.html", {"request": request})

@app.get("/converter", response_class=HTMLResponse)
async def converter(request: Request):
    """Currency converter page."""
    return templates.TemplateResponse("converter.html", {"request": request})

@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    """Portfolio management page."""
    return templates.TemplateResponse("portfolio.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    """User profile page with GEM balance and stats."""
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/missions", response_class=HTMLResponse)
async def missions(request: Request):
    """Daily missions and weekly challenges page."""
    return templates.TemplateResponse("missions.html", {"request": request})

@app.get("/achievements", response_class=HTMLResponse)
async def achievements(request: Request):
    """Achievements page - unlock and claim rewards."""
    return templates.TemplateResponse("achievements.html", {"request": request})

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 page."""
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: HTTPException):
    """Custom 500 page."""
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,
        limit_concurrency=100,
        timeout_keep_alive=30
    )
