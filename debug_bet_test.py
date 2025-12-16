
import requests
import sys

BASE_URL = "http://localhost:8000"
USERNAME = "testuser"
PASSWORD = "testpass"

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"--- Debugging Crash Bet for {USERNAME} ---")
    
    # 1. Login
    print(f"[1] Logging in...")
    try:
        # API expects JSON body for UserLogin model, not form data
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={"username": USERNAME, "password": PASSWORD})
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            # Try registering if login fails
            print(f"[1b] Trying to register instead...")
            resp = requests.post(f"{BASE_URL}/api/auth/register", json={"username": USERNAME, "email": "debug3@example.com", "password": PASSWORD})
            if resp.status_code != 200:
                print(f"Register failed: {resp.text}")
                return
            # Login again
            resp = requests.post(f"{BASE_URL}/api/auth/login", json={"username": USERNAME, "password": PASSWORD})
    except Exception as e:
        print(f"Connection error: {e}")
        return

    data = resp.json()
    token = data.get("access_token")
    if not token:
        print("No access token received.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Login successful. Token acquired.")

    # 2. Check Balance
    print(f"[2] Checking Balance...")
    resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    print(f"Balance check status: {resp.status_code}")
    print(f"Balance check response: {resp.text[:200]}...")
    
    if resp.status_code != 200:
        print("Failed to get user details")
        return
        
    user_data = resp.json()
    balance = user_data.get("gem_balance")
    print(f"Current Balance: {balance} GEM")

    # 3. Place Bet
    bet_amount = 100
    print(f"[3] Attempting to place bet of {bet_amount} GEM...")
    
    resp = requests.post(f"{BASE_URL}/api/crash/bet", json={"bet_amount": bet_amount}, headers=headers)
    print(f"Status Code: {resp.status_code}")
    # print(f"Response: {resp.text}") 
    print(f"Response snippet: {resp.text[:200]}...")

    if resp.status_code == 200:
        result = resp.json()
        if result.get("success"):
            print(">>> BET SUCCESSFUL <<<")
        else:
            print(f">>> BET FAILED (Logic): {result.get('message')}")
    else:
        print(">>> BET FAILED (HTTP Error) <<<")

if __name__ == "__main__":
    main()
