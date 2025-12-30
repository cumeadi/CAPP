import requests
import time
import sys

API_URL = "http://localhost:8000"

def verify_bridge():
    print("1. Initiating Withdrawal (Plasma Exit)...")
    res = requests.post(f"{API_URL}/bridge/withdraw", json={
        "amount": 100,
        "user_address": "0xUser",
        "token": "USDC"
    })
    
    if res.status_code != 200:
        print(f"FAILED to withdraw: {res.text}")
        return

    data = res.json()
    exit_id = data['exit_id']
    eta = data['estimated_completion']
    print(f"   [OK] Exit Started. ID: {exit_id}")
    print(f"   [OK] ETA: {eta}")

    print("2. Checking Status (Immediately)...")
    res = requests.get(f"{API_URL}/bridge/exit/{exit_id}")
    status = res.json()
    print(f"   Status: {status['status']}")
    print(f"   Time Remaining: {status.get('time_remaining_seconds')}s")

    if status['status'] != "CHALLENGE_PERIOD":
        print("FAILED: Should be in CHALLENGE_PERIOD")
        return

    print("3. Waiting for Challenge Period (30s)...")
    for i in range(35):
        sys.stdout.write(f"\r   Waiting... {35-i}s")
        sys.stdout.flush()
        time.sleep(1)
    print("\n")

    print("4. Checking Status (After Wait)...")
    res = requests.get(f"{API_URL}/bridge/exit/{exit_id}")
    status = res.json()
    print(f"   Status: {status['status']}")

    if status['status'] != "READY_TO_FINALIZE":
        print(f"FAILED: Should be READY_TO_FINALIZE, got {status['status']}")
        return

    print("5. Finalizing Exit...")
    res = requests.post(f"{API_URL}/bridge/finalize", json={"exit_id": exit_id})
    if res.status_code == 200:
        final_data = res.json()
        print(f"   [OK] Finalized! Tx: {final_data.get('finalize_tx')}")
    else:
        print(f"FAILED to finalize: {res.text}")

if __name__ == "__main__":
    verify_bridge()
