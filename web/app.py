"""
Web application server for Crypto Gamification Platform
Serves the HTML templates and static files
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path

# Get the directory containing this file
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Crypto Gamification Web App",
    description="Web interface for the crypto gamification platform",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ===== ROUTE HANDLERS =====

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - redirects to dashboard if authenticated, otherwise shows landing page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    """Login page."""
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    """Registration page."""
    return templates.TemplateResponse("auth/register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """User dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/gaming", response_class=HTMLResponse)
async def gaming(request: Request):
    """Gaming hub - roulette and other games."""
    return templates.TemplateResponse("gaming/roulette.html", {"request": request})

@app.get("/gaming/roulette", response_class=HTMLResponse)
async def roulette(request: Request):
    """Crypto roulette game."""
    return templates.TemplateResponse("gaming/roulette.html", {"request": request})

@app.get("/inventory", response_class=HTMLResponse)
async def inventory(request: Request):
    """User inventory and trading."""
    return templates.TemplateResponse("inventory/inventory.html", {"request": request})

@app.get("/social", response_class=HTMLResponse)
async def social(request: Request):
    """Social hub - friends, leaderboards, activity feed."""
    return templates.TemplateResponse("social/social.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    """User profile page."""
    # For now, redirect to dashboard
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/achievements", response_class=HTMLResponse)
async def achievements(request: Request):
    """Achievements page."""
    # For now, redirect to dashboard
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/leaderboards", response_class=HTMLResponse)
async def leaderboards(request: Request):
    """Leaderboards page."""
    return templates.TemplateResponse("social/social.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    """User settings page."""
    # For now, redirect to dashboard
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ===== ERROR HANDLERS =====

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404 error handler."""
    return templates.TemplateResponse("errors/404.html", {
        "request": request
    }, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """500 error handler."""
    return templates.TemplateResponse("errors/500.html", {
        "request": request
    }, status_code=500)

# ===== HEALTH CHECK =====

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "crypto-gamification-web",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="127.0.0.1", 
        port=3000,
        reload=True,
        log_level="info"
    )