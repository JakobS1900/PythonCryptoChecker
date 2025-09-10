#!/usr/bin/env python3
"""
Simple route validation test for CryptoChecker Gaming Platform
Tests if all expected routes are properly defined
"""

import re

def test_routes():
    """Test that all expected routes exist in main.py"""
    
    expected_routes = [
        "/",
        "/login", 
        "/register",
        "/dashboard",
        "/gaming/roulette",
        "/gaming/dice", 
        "/tournaments",
        "/portfolio",
        "/gaming/crash",
        "/gaming/plinko", 
        "/gaming/tower",
        "/leaderboards",
        "/inventory",
        "/social"
    ]
    
    # Read main.py content
    try:
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ main.py not found!")
        return False
    
    # Check for route definitions
    missing_routes = []
    for route in expected_routes:
        # Look for route pattern in main.py
        route_pattern = f'@app.get\\("{re.escape(route)}"'
        if not re.search(route_pattern, content):
            missing_routes.append(route)
    
    if missing_routes:
        print("ERROR: Missing routes found:")
        for route in missing_routes:
            print(f"   - {route}")
        return False
    
    print(f"SUCCESS: All {len(expected_routes)} expected routes are defined!")
    
    # Check for template references
    template_count = len(re.findall(r'templates\.TemplateResponse', content))
    print(f"SUCCESS: Found {template_count} template references")
    
    # Check for API endpoints
    api_count = len(re.findall(r'@app\.(get|post)\("/api/', content))
    print(f"SUCCESS: Found {api_count} API endpoints")
    
    print("\nRoute validation completed successfully!")
    return True

if __name__ == "__main__":
    test_routes()