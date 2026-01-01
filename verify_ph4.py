import requests
import sys

BASE_URL = "http://localhost:8001"

def test_system_health():
    print(f"Testing {BASE_URL}/system/health...")
    try:
        res = requests.get(f"{BASE_URL}/system/health")
        if res.status_code != 200:
            print(f"❌ Health Check Failed: {res.status_code}")
            sys.exit(1)
        
        data = res.json()
        print(f"Received: {data}")
        
        if data["status"] == "healthy":
            print("✅ System is HEALTHY")
        else:
            print(f"⚠️ System is {data['status']}")
            
        if data["services"]["database"] != "connected":
             print("❌ Database disconnected")
        
        if data["services"]["redis"] != "connected" and data["services"]["redis"] != "connected (mock)":
             print("❌ Redis disconnected")

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_system_health()
