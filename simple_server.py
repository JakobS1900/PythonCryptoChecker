#!/usr/bin/env python3
"""
Simple server to test if basic functionality works
"""

import os
import sys
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create FastAPI app
app = FastAPI(
    title="CryptoChecker Test Server",
    description="Simple test server",
    version="1.0.0"
)

# Try to mount static files if they exist
try:
    if os.path.exists("web/static"):
        app.mount("/static", StaticFiles(directory="web/static"), name="static")
        print("Static files mounted successfully")
    else:
        print("Static directory not found, skipping")
except Exception as e:
    print(f"Failed to mount static files: {e}")

# Try to setup templates if they exist
try:
    if os.path.exists("web/templates"):
        templates = Jinja2Templates(directory="web/templates")
        print("Templates loaded successfully")
    else:
        templates = None
        print("Templates directory not found")
except Exception as e:
    print(f"Failed to setup templates: {e}")
    templates = None

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CryptoChecker Test Server is running!",
        "status": "healthy",
        "available_endpoints": [
            "/",
            "/health",
            "/test"
        ]
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Server is running properly"
    }

@app.get("/test")
async def test():
    """Test endpoint."""
    return {
        "message": "Test endpoint working",
        "cwd": os.getcwd(),
        "python_version": sys.version
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page."""
    if templates:
        try:
            return templates.TemplateResponse("dashboard.html", {"request": request})
        except Exception as e:
            return HTMLResponse(f"<h1>Dashboard</h1><p>Template error: {e}</p>")
    else:
        return HTMLResponse("<h1>Dashboard</h1><p>Templates not available</p>")

if __name__ == "__main__":
    print("Starting simple test server...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[0]}")
    
    uvicorn.run(
        "simple_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )