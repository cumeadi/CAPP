import requests
import time
import uuid

BASE_URL = "http://localhost:8000"

def test_config_update():
    print("Testing Config Update...")
    # Set to COPILOT
    resp = requests.post(f"{BASE_URL}/agents/config", json={
        "risk_profile": "BALANCED",
        "autonomy_level": "COPILOT",
        "hedge_threshold": 5,
        "network": "TESTNET"
    })
    data = resp.json()
    assert data['autonomy_level'] == "COPILOT"
    print("✅ Set to COPILOT")

def test_copilot_transaction_interception():
    print("Testing Copilot Interception...")
    # Should trigger approval
    tx_req = {
        "from_currency": "USD",
        "to_currency": "KES",
        "amount": 500,
        "recipient_name": "Test User",
        "recipient_country": "KE",
        "recipient_address": "0x123",
        "sender_id": "tester"
    }
    resp = requests.post(f"{BASE_URL}/wallet/send", json=tx_req)
    data = resp.json()
    
    # Expect PENDING_APPROVAL
    if data['status'] == "PENDING_APPROVAL":
        print(f"✅ Transaction Intercepted: {data['status']}")
    else:
        print(f"❌ Transaction NOT Intercepted: {data['status']}")
        return

    # Check Feed for Approval Request
    print("Checking Feed...")
    feed = requests.get(f"{BASE_URL}/agents/feed").json()
    approval_item = None
    for item in feed:
        if item['action_type'] == 'APPROVAL':
            approval_item = item
            break
            
    if approval_item:
        print(f"✅ Approval Request Found in Feed: {approval_item['id']}")
        req_id = approval_item['metadata']['request_id']
        
        # Approve it
        print(f"Approving Request {req_id}...")
        res = requests.post(f"{BASE_URL}/agents/approve/{req_id}")
        assert res.status_code == 200
        print("✅ Request Approved via API")
    else:
        print("❌ No Approval Item found in feed")

def test_autonomy_switch_to_sovereign():
    print("Testing Switch to Sovereign...")
    requests.post(f"{BASE_URL}/agents/config", json={
        "risk_profile": "BALANCED",
        "autonomy_level": "SOVEREIGN",
        "hedge_threshold": 5,
        "network": "TESTNET"
    })
    
    # Transaction should pass
    tx_req = {
        "from_currency": "USD",
        "to_currency": "KES",
        "amount": 100,
        "recipient_name": "Test User",
        "recipient_country": "KE",
        "recipient_address": "0x123",
        "sender_id": "tester"
    }
    resp = requests.post(f"{BASE_URL}/wallet/send", json=tx_req)
    data = resp.json()
    if data['status'] == "SUBMITTED":
         print("✅ Transaction Executed Immediately (Sovereign Mode)")
    else:
         print(f"❌ Transaction Intercepted in Sovereign Mode: {data['status']}")

if __name__ == "__main__":
    try:
        test_config_update()
        time.sleep(1)
        test_copilot_transaction_interception()
        time.sleep(1)
        test_autonomy_switch_to_sovereign()
    except Exception as e:
        print(f"❌ Test Failed: {e}")
