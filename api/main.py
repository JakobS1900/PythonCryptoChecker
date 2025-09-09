"""
Main FastAPI application for crypto gamification platform.
Comprehensive REST API with all gamification features.
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from database import init_database, close_database, get_db_session
from config import config
from logger import logger

# Import API routers
from .auth_api import router as auth_router
from .gaming_api import router as gaming_router
from .inventory_api import router as inventory_router
from .social_api import router as social_router
from .admin_api import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Crypto Gamification Platform API...")
    
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")
    await close_database()


# Create FastAPI app
app = FastAPI(
    title="Crypto Gamification Platform API",
    description="Virtual crypto gambling and gaming platform with comprehensive gamification",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(gaming_router, prefix="/api/gaming", tags=["Gaming"])
app.include_router(inventory_router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(social_router, prefix="/api/social", tags=["Social"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """API health check."""
    return {
        "status": "healthy",
        "service": "crypto-gamification-api",
        "version": "2.0.0",
        "timestamp": "2025-09-08T12:00:00Z"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Crypto Gamification Platform</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; display: flex; align-items: center; justify-content: center;
                color: white;
            }
            .container { text-align: center; max-width: 600px; }
            .logo { font-size: 3rem; margin-bottom: 1rem; }
            .title { font-size: 2.5rem; font-weight: bold; margin-bottom: 1rem; }
            .description { font-size: 1.2rem; margin-bottom: 2rem; opacity: 0.9; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 2rem 0; }
            .feature { background: rgba(255,255,255,0.1); padding: 1.5rem; border-radius: 12px; }
            .buttons { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }
            .btn { 
                padding: 12px 24px; border: none; border-radius: 8px; font-size: 1rem;
                cursor: pointer; text-decoration: none; display: inline-block;
                transition: all 0.3s ease;
            }
            .btn-primary { background: #4CAF50; color: white; }
            .btn-secondary { background: rgba(255,255,255,0.2); color: white; }
            .btn:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.3); }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🎰💎</div>
            <h1 class="title">Crypto Gamification Platform</h1>
            <p class="description">
                The ultimate virtual crypto gambling experience with roulette games, 
                collectible items, achievements, and social features - all completely virtual and risk-free!
            </p>
            
            <div class="features">
                <div class="feature">
                    <h3>🎲 Crypto Roulette</h3>
                    <p>Provably fair roulette with 37 cryptocurrencies</p>
                </div>
                <div class="feature">
                    <h3>🎒 Virtual Inventory</h3>
                    <p>Collect rare crypto-themed trading cards</p>
                </div>
                <div class="feature">
                    <h3>🏆 Achievements</h3>
                    <p>Unlock rewards and progress through levels</p>
                </div>
                <div class="feature">
                    <h3>👥 Social Features</h3>
                    <p>Friends, leaderboards, and competitions</p>
                </div>
            </div>
            
            <div class="buttons">
                <a href="/dashboard" class="btn btn-primary">🚀 Launch Dashboard</a>
                <a href="/api/docs" class="btn btn-secondary">📖 API Documentation</a>
            </div>
        </div>
    </body>
    </html>
    """)


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return {
        "error": "Internal server error",
        "message": "An unexpected error occurred",
        "status_code": 500
    }


if __name__ == "__main__":
    import uvicorn
    
    host = config.get("API_HOST", "127.0.0.1")
    port = config.get("API_PORT", 8000)
    debug = config.get("DEBUG_MODE", False)
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )