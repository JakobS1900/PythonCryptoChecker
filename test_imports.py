#!/usr/bin/env python3
"""
Test script to check for import issues
"""

print("Testing imports...")

try:
    print("1. Testing FastAPI...")
    from fastapi import FastAPI
    print("   ✓ FastAPI imported successfully")
except Exception as e:
    print(f"   ✗ FastAPI import failed: {e}")

try:
    print("2. Testing database imports...")
    from database import init_database, close_database, get_db_session
    print("   ✓ Database imports successful")
except Exception as e:
    print(f"   ✗ Database import failed: {e}")

try:
    print("3. Testing config...")
    from config import config
    print("   ✓ Config imported successfully")
except Exception as e:
    print(f"   ✗ Config import failed: {e}")

try:
    print("4. Testing logger...")
    from logger import logger
    print("   ✓ Logger imported successfully")
except Exception as e:
    print(f"   ✗ Logger import failed: {e}")

try:
    print("5. Testing auth API...")
    from api.auth_api import router as auth_router
    print("   ✓ Auth API imported successfully")
except Exception as e:
    print(f"   ✗ Auth API import failed: {e}")

try:
    print("6. Testing gaming API...")
    from api.gaming_api import router as gaming_router
    print("   ✓ Gaming API imported successfully")
except Exception as e:
    print(f"   ✗ Gaming API import failed: {e}")

try:
    print("7. Testing inventory API...")
    from api.inventory_api import router as inventory_router
    print("   ✓ Inventory API imported successfully")
except Exception as e:
    print(f"   ✗ Inventory API import failed: {e}")

try:
    print("8. Testing social API...")
    from api.social_api import router as social_router
    print("   ✓ Social API imported successfully")
except Exception as e:
    print(f"   ✗ Social API import failed: {e}")

try:
    print("9. Testing admin API...")
    from api.admin_api import router as admin_router
    print("   ✓ Admin API imported successfully")
except Exception as e:
    print(f"   ✗ Admin API import failed: {e}")

print("\nImport test completed!")