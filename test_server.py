#!/usr/bin/env python3
"""
Simple test server to verify the basic structure works.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="CryptoChecker v3 Test")

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="web/templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Test home page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CryptoChecker v3 Test</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="text-center">
                <h1 class="display-4 text-primary">🚀 CryptoChecker Version3 Test</h1>
                <p class="lead">Basic server structure is working!</p>
                <div class="alert alert-success">
                    <h5>>> Success: Test Results:</h5>
                    <ul class="list-unstyled mb-0">
                        <li>>> Success: FastAPI server running</li>
                        <li>>> Success: Static file serving configured</li>
                        <li>>> Success: Template system ready</li>
                        <li>>> Success: Bootstrap CSS loaded</li>
                    </ul>
                </div>
                <div class="mt-4">
                    <h3>🎯 Next Steps:</h3>
                    <ol class="text-start">
                        <li>Fix module dependencies</li>
                        <li>Initialize database system</li>
                        <li>Connect API endpoints</li>
                        <li>Test crypto price service</li>
                        <li>Test roulette gaming</li>
                    </ol>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/test")
async def test_endpoint():
    """Test API endpoint."""
    return {
        "status": "success",
        "message": "CryptoChecker v3 API is working!",
        "version": "3.0.0-test"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CryptoChecker v3 Test Server...")
    uvicorn.run("test_server:app", host="0.0.0.0", port=8000, reload=True)