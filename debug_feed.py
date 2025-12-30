import requests
import json

API_URL = "http://localhost:8000"

def debug_feed():
    print("Fetching Feed...")
    res = requests.get(f"{API_URL}/agents/feed?limit=10")
    if res.status_code != 200:
        print(f"Error: {res.status_code}")
        return

    feed = res.json()
    print(f"Found {len(feed)} items.")
    
    for item in feed:
        print("-" * 40)
        print(f"ID: {item['id']}")
        print(f"Type: {item['action_type']}")
        print(f"Message: {item['message']}")
        print(f"Metadata: {json.dumps(item.get('metadata', {}), indent=2)}")
        
        if item['action_type'] == 'OPPORTUNITY' or item['action_type'] == 'APPROVAL':
            req_id = item.get('metadata', {}).get('request_id')
            print(f"-> Target Request ID: {req_id}")
            if not req_id:
                print("   [WARNING] MISSING REQUEST ID IN METADATA")

if __name__ == "__main__":
    debug_feed()
