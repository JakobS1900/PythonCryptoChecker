"""
Main application entry point for CryptoChecker Gaming Platform.
"""

import asyncio
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

# Include API routers
app.include_router(auth_router, prefix="/api")
app.include_router(gaming_router, prefix="/api")
app.include_router(social_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(trading_router, prefix="/api/trading")


# ==================== WEB ROUTES ====================

@app.get("/")
async def home(request: Request):
    """Home page - redirect to gaming platform."""
    return RedirectResponse(url="/trading", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page."""
    return templates.TemplateResponse("auth/register.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """User dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/gaming", response_class=HTMLResponse)
async def gaming(request: Request):
    """Gaming section."""
    return templates.TemplateResponse("gaming/roulette.html", {"request": request})


@app.get("/gaming/roulette", response_class=HTMLResponse)
async def roulette(request: Request):
    """Crypto roulette game."""
    return templates.TemplateResponse("gaming/roulette.html", {"request": request})


@app.get("/inventory", response_class=HTMLResponse)
async def inventory(request: Request):
    """User inventory."""
    return templates.TemplateResponse("trading.html", {"request": request})


@app.get("/gaming/inventory", response_class=HTMLResponse)
async def gaming_inventory(request: Request):
    """Gaming inventory page."""
    return templates.TemplateResponse("trading.html", {"request": request})


@app.get("/social", response_class=HTMLResponse)
async def social(request: Request):
    """Social features."""
    return templates.TemplateResponse("trading.html", {"request": request})


@app.get("/achievements", response_class=HTMLResponse)
async def achievements(request: Request):
    """Achievements page."""
    return templates.TemplateResponse("trading.html", {"request": request})


@app.get("/daily-quests", response_class=HTMLResponse)
async def daily_quests(request: Request):
    """Daily quests page."""
    return templates.TemplateResponse("trading.html", {"request": request})


@app.get("/onboarding/welcome", response_class=HTMLResponse)
async def onboarding_welcome(request: Request):
    """Onboarding welcome page."""
    return templates.TemplateResponse("trading.html", {"request": request})


@app.get("/trading", response_class=HTMLResponse)
async def trading_page(request: Request):
    """Trading interface page."""
    return templates.TemplateResponse("trading.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_redirect(request: Request):
    """Redirect to admin dashboard."""
    return RedirectResponse(url="/admin/dashboard")


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard."""
    return templates.TemplateResponse("trading.html", {"request": request})


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