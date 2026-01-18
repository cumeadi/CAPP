
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_routing_api():
    print("\n--- TEST: INTELLIGENT ROUTING API ---")
    
    # Test 1: Prioritize Speed (expect FastRail)
    print("1. Requesting Route (Preference: FAST)...")
    payload_fast = {
        "amount": 100.0,
        "recipient": "0x123",
        "preference": "FAST"
    }
    
    try:
        res = requests.post(f"{BASE_URL}/routing/calculate", json=payload_fast)
        if res.status_code == 200:
            data = res.json()
            rec = data.get("recommended_route")
            
            if rec:
                print(f"✅ Implementation: {rec['chain']}")
                print(f"   Score: {rec['recommendation_score']}")
                
                if rec["chain"] == "FastRail":
                    print("✅ PASSED: Correctly selected FastRail for speed.")
                else:
                    print(f"❌ FAIL: Expected FastRail, got {rec['chain']}")
            else:
                print("⚠️  No recommended route returned (Test 1).")
                print("   Full Response:", json.dumps(data, indent=2))
        else:
            print(f"❌ API Error: {res.status_code} - {res.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

    print("-" * 30)

    # Test 2: Prioritize Cost (expect CheapRail)
    print("2. Requesting Route (Preference: CHEAP)...")
    payload_cheap = {
        "amount": 100.0,
        "recipient": "0x123",
        "preference": "CHEAP"
    }
    
    try:
        res = requests.post(f"{BASE_URL}/routing/calculate", json=payload_cheap)
        if res.status_code == 200:
            data = res.json()
            rec = data.get("recommended_route")
            
            if rec:
                print(f"✅ Recommended: {rec['chain']}")
                
                if rec["chain"] == "CheapRail":
                    print("✅ PASSED: Correctly selected CheapRail for cost.")
                else:
                     print(f"❌ FAIL: Expected CheapRail, got {rec['chain']}")
            else:
                print("⚠️  No recommended route returned (Test 2).")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_routing_api()
