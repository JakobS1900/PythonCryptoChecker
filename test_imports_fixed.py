#!/usr/bin/env python3
"""
Test script to check for import issues
"""

print("Testing imports...")

try:
    print("1. Testing FastAPI...")
    from fastapi import FastAPI
    print("   OK - FastAPI imported successfully")
except Exception as e:
    print(f"   ERROR - FastAPI import failed: {e}")

try:
    print("2. Testing database imports...")
    from database import init_database, close_database, get_db_session
    print("   OK - Database imports successful")
except Exception as e:
    print(f"   ERROR - Database import failed: {e}")

try:
    print("3. Testing config...")
    from config import config
    print("   OK - Config imported successfully")
except Exception as e:
    print(f"   ERROR - Config import failed: {e}")

try:
    print("4. Testing logger...")
    from logger import logger
    print("   OK - Logger imported successfully")
except Exception as e:
    print(f"   ERROR - Logger import failed: {e}")

try:
    print("5. Testing auth API...")
    from api.auth_api import router as auth_router
    print("   OK - Auth API imported successfully")
except Exception as e:
    print(f"   ERROR - Auth API import failed: {e}")

try:
    print("6. Testing gaming API...")
    from api.gaming_api import router as gaming_router
    print("   OK - Gaming API imported successfully")
except Exception as e:
    print(f"   ERROR - Gaming API import failed: {e}")

try:
    print("7. Testing inventory API...")
    from api.inventory_api import router as inventory_router
    print("   OK - Inventory API imported successfully")
except Exception as e:
    print(f"   ERROR - Inventory API import failed: {e}")

try:
    print("8. Testing social API...")
    from api.social_api import router as social_router
    print("   OK - Social API imported successfully")
except Exception as e:
    print(f"   ERROR - Social API import failed: {e}")

try:
    print("9. Testing admin API...")
    from api.admin_api import router as admin_router
    print("   OK - Admin API imported successfully")
except Exception as e:
    print(f"   ERROR - Admin API import failed: {e}")

print("\nImport test completed!")