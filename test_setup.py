#!/usr/bin/env python3
"""
Quick setup test for Crypto Analytics Platform.
Tests virtual environment setup and basic imports.
"""
import sys
import os

def test_setup():
    """Test that the setup is working correctly."""
    print("Testing Crypto Analytics Platform Setup...")
    
    # Test Python version
    print(f"+ Python version: {sys.version}")
    
    # Test imports
    try:
        import requests
        print(f"+ requests library: {requests.__version__}")
    except ImportError:
        print("- requests library not found")
        return False
    
    try:
        from models import CoinData, ApplicationState
        from data_providers import DataManager
        from config import COLORS, config
        from ui import UserInterface
        from utils import detect_platform
        print("+ All modules import successfully")
    except ImportError as e:
        print(f"- Import error: {e}")
        return False
    
    # Test configuration
    try:
        platform = detect_platform()
        print(f"+ Platform detection: {platform}")
        
        refresh_rate = config.get('REFRESH_RATE')
        print(f"+ Configuration loading: {refresh_rate}s refresh rate")
    except Exception as e:
        print(f"- Configuration error: {e}")
        return False
    
    # Test API connectivity (basic)
    try:
        data_manager = DataManager()
        print("+ DataManager initialization successful")
    except Exception as e:
        print(f"- DataManager error: {e}")
        return False
    
    print("\nSETUP TEST COMPLETED SUCCESSFULLY!")
    print("\nYou can now run the application with:")
    if os.name == 'nt':
        print("    .venv\\Scripts\\python main.py")
        print("Or double-click: run.bat")
    else:
        print("    .venv/bin/python main.py")
        print("Or run: ./run.sh")
    
    return True

if __name__ == "__main__":
    success = test_setup()
    sys.exit(0 if success else 1)