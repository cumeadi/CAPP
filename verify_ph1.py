import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_market_status():
    print(f"Testing GET {BASE_URL}/agents/market/status...")
    try:
        response = requests.get(f"{BASE_URL}/agents/market/status")
        if response.status_code == 200:
            data = response.json()
            print("✅ Market Status OK")
            print(json.dumps(data, indent=2))
            
            if "top_apy" in data and "active_protocols" in data:
                print("✅ Data Structure Valid")
            else:
                print("❌ Missing fields in Market Status")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_scout_opportunities():
    print(f"\nTesting POST {BASE_URL}/agents/opportunities/scout...")
    try:
        response = requests.post(f"{BASE_URL}/agents/opportunities/scout")
        if response.status_code == 200:
            data = response.json()
            print("✅ Scout OK")
            print(json.dumps(data, indent=2))
            
            if data["status"] == "found" and "opportunity" in data:
                print("✅ Opportunity Found")
            else:
                 print("❌ Invalid Scout Response")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_market_status()
    test_scout_opportunities()
