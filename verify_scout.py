import requests
import time

API_URL = "http://localhost:8000"

def test_proactive_opportunity():
    print("1. Triggering Scout Agent...")
    res = requests.post(f"{API_URL}/agents/opportunities/scout")
    if res.status_code != 200:
        print(f"FAILED to scout: {res.text}")
        return
    
    data = res.json()
    req_id = data['request_id']
    opp = data['opportunity']
    print(f"   [OK] Found Opportunity: {opp['protocol']} ({opp['apy']}%) - Request ID: {req_id}")

    print("2. Checking Feed for Opportunity...")
    res = requests.get(f"{API_URL}/agents/feed?limit=5")
    feed = res.json()
    
    found_in_feed = False
    for item in feed:
        if item['metadata'].get('request_id') == req_id:
            print(f"   [OK] Found in Feed: {item['message']}")
            found_in_feed = True
            break
    
    if not found_in_feed:
        print("FAILED: Opportunity not found in feed")
        return

    print("3. Approving Opportunity...")
    res = requests.post(f"{API_URL}/agents/approve/{req_id}")
    if res.status_code == 200:
        print("   [OK] Approved Successfully")
    else:
        print(f"FAILED to approve: {res.text}")

if __name__ == "__main__":
    test_proactive_opportunity()
