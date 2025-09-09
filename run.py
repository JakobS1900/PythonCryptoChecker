#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CryptoChecker Gaming Platform - Startup Script
Quick launch script with environment setup and validation.
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform.startswith('win'):
    import locale
    try:
        # Try to set UTF-8 console code page
        os.system('chcp 65001 >nul 2>&1')
    except:
        pass

def check_requirements():
    """Check if all requirements are installed."""
    try:
        import fastapi
        import sqlalchemy
        import pydantic
        import passlib
        import psutil
        import uvicorn
        print(">> All required packages are installed")
        return True
    except ImportError as e:
        print(f">> Missing required package: {e}")
        return False

def setup_environment():
    """Set up environment configuration."""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if not env_path.exists():
        if env_example_path.exists():
            print(">> Creating .env from .env.example...")
            import shutil
            shutil.copy(env_example_path, env_path)
            print(">> Please edit .env file with your configuration")
        else:
            print(">> No .env file found. Creating basic configuration...")
            with open(env_path, 'w') as f:
                f.write("""# CryptoChecker Gaming Platform Configuration
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
HOST=localhost
PORT=8000
DATABASE_URL=sqlite+aiosqlite:///./crypto_gaming.db
JWT_SECRET_KEY=jwt-secret-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
""")
    
    print(">> Environment configuration ready")

def main():
    """Main startup function."""
    print(">> CryptoChecker Gaming Platform - Startup")
    print("=" * 50)
    
    # Check requirements
    print(">> Checking Python packages...")
    if not check_requirements():
        print(">> Install requirements with: pip install -r requirements.txt")
        return
    
    # Setup environment
    print(">> Setting up environment...")
    setup_environment()
    
    # Start application
    print(">> Starting CryptoChecker Gaming Platform...")
    print("   >> Web Interface: http://localhost:8000")
    print("   >> Admin Dashboard: http://localhost:8000/admin/dashboard")  
    print("   >> API Documentation: http://localhost:8000/api/docs")
    print("   >> Database: crypto_gaming.db")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        from main import main as app_main
        app_main()
    except KeyboardInterrupt:
        print("\n\n>> Server stopped by user")
    except Exception as e:
        print(f"\n>> Error starting server: {e}")

if __name__ == "__main__":
    main()