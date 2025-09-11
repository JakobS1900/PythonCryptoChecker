#!/usr/bin/env python3
"""
Test server startup to identify issues
"""

import traceback
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing server startup...")

try:
    print("1. Testing FastAPI app creation...")
    from fastapi import FastAPI
    
    app = FastAPI(title="Test App")
    print("   OK - FastAPI app created")
    
except Exception as e:
    print(f"   ERROR - FastAPI app creation failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("2. Testing database imports...")
    from database import init_database, close_database
    print("   OK - Database imports successful")
    
except Exception as e:
    print(f"   ERROR - Database imports failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("3. Testing API module imports...")
    from api.main import app as main_app
    print("   OK - Main API app imported successfully")
    
except Exception as e:
    print(f"   ERROR - Main API import failed: {e}")
    print("Detailed error:")
    traceback.print_exc()

try:
    print("4. Testing simple server start...")
    import uvicorn
    
    # Create a minimal app for testing
    test_app = FastAPI(title="Minimal Test App")
    
    @test_app.get("/")
    async def root():
        return {"message": "Test server is working!"}
    
    print("   OK - Test app created successfully")
    print("   Use: uvicorn test_server:test_app --host 0.0.0.0 --port 8000")
    
except Exception as e:
    print(f"   ERROR - Test server creation failed: {e}")
    traceback.print_exc()

print("\nServer test completed!")