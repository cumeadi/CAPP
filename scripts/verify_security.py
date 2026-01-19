
import requests
import time

BASE_URL = "http://localhost:8000"

def test_rate_limit():
    print("\n--- TEST: RATE LIMITING (5/min) ---")
    url = f"{BASE_URL}/routing/calculate"
    payload = {
        "amount": 100.0,
        "recipient": "0x123",
        "currency": "USDC",
        "preference": "FAST"
    }

    print("🚀 Sending 10 rapid requests...")
    
    success_count = 0
    blocked_count = 0
    
    for i in range(1, 11):
        try:
            res = requests.post(url, json=payload)
            if res.status_code == 200:
                print(f"Request {i}: ✅ 200 OK")
                success_count += 1
            elif res.status_code == 429:
                print(f"Request {i}: 🛑 429 Too Many Requests")
                blocked_count += 1
            else:
                print(f"Request {i}: ⚠️ {res.status_code}")
        except Exception as e:
            print(f"Request {i}: ❌ Error {e}")
            
    print("-" * 20)
    print(f"Summary: {success_count} Passed, {blocked_count} Blocked")
    
    if blocked_count > 0:
        print("✅ PASSED: Rate Limiter is active.")
    else:
        print("❌ FAIL: Rate Limiter did not block excessive requests.")

if __name__ == "__main__":
    test_rate_limit()
