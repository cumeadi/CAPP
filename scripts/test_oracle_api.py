
import asyncio
import sys
import os
import json
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Mock missing ML libs
sys.modules["stable_baselines3"] = MagicMock()
sys.modules["gym"] = MagicMock() # Likely used by SB3 users too

# Fix path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "applications/capp")) # Support 'from capp...' imports

from applications.capp.capp.main import app
from applications.capp.capp.services.oracle_service import OracleService, TransactionStatus
from applications.capp.capp.core.redis import init_redis

# Disable Chaos
os.environ["CHAOS_ENABLED"] = "false"

async def test_oracle_api():
    print("\n--- 🔮 CAPP PLATFORM: ORACLE API & REDIS VERIFICATION ---")
    
    # 1. Init Dependencies
    try:
        await init_redis()
    except Exception as e:
        print(f"⚠️ Redis Init Warning: {e}")
        
    client = TestClient(app)
    oracle = OracleService.get_instance()
    
    # 2. Simulate Relayer Writing to Oracle
    test_hash = "0xAPI_TEST_HASH_12345"
    print(f"\n1️⃣ Action: Simulating Relayer Write for {test_hash}")
    
    await oracle.update_index(
        tx_hash=test_hash,
        status=TransactionStatus.COMPLETED,
        meta={"source": "scripts/test_oracle_api.py", "fee": 1.0}
    )
    
    # 3. Verify via API
    print(f"\n2️⃣ Verification: Querying Public API /api/v1/oracle/status/{test_hash}")
    
    response = client.get(f"/api/v1/oracle/status/{test_hash}")
    
    print(f"   -> Status Code: {response.status_code}")
    print(f"   -> Body: {json.dumps(response.json(), indent=2)}")
    
    data = response.json()
    
    # 4. Assertions
    if response.status_code == 200 and data["status"] == "COMPLETED":
        print("✅ SUCCESS: API retrieved correct COMPLETED status.")
    else:
        print("❌ FAILURE: API did not return expected status.")
        
    if data["meta"].get("fee") == 1.0:
        print("✅ SUCCESS: Metadata (fee) persisted via Redis.")
    else:
        print("❌ FAILURE: Metadata missing.")

    # 5. Verify 404/Unknown
    print("\n3️⃣ Verification: Querying Non-Existent Hash")
    resp_404 = client.get("/api/v1/oracle/status/0xNON_EXISTENT")
    print(f"   -> Status: {resp_404.json()['status']}")
    
    if resp_404.json()['status'] == "UNKNOWN":
        print("✅ SUCCESS: Unknown hash handled correctly.")
    else:
        print("❌ FAILURE: Unknown hash incorrect handling.")

if __name__ == "__main__":
    asyncio.run(test_oracle_api())
