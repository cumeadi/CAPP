
import asyncio
import sys
import os

# Fix path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from applications.capp.capp.services.billing_service import BillingService
from applications.capp.capp.services.relayer_service import RelayerService
from applications.capp.capp.services.oracle_service import OracleService
from applications.capp.capp.core.redis import init_redis
from applications.capp.capp.core.aptos import init_aptos_client

# Disable Chaos
os.environ["CHAOS_ENABLED"] = "false"

async def test_oracle():
    print("\n--- 🔮 CAPP PLATFORM: ORACLE SDK VERIFICATION ---")
    
    # Init Deps
    try:
        await init_redis()
        await init_aptos_client()
    except Exception:
        pass 
        
    billing = BillingService.get_instance()
    relayer = RelayerService()
    oracle = OracleService.get_instance()
    
    # 1. Setup (Funded Account)
    print("\n1️⃣ Setup: Creating Funded Account")
    acc = billing.create_account("Oracle Tester", initial_balance=10.0)
    key = billing.create_api_key(acc.account_id)
    
    route = {
        "bridge_provider": "MockBridge",
        "from_chain": "Aptos",
        "to_chain": "Polygon",
        "token_in": "USDC",
        "amount": 50.0,
        "recipient": "0xOracleTarget"
    }
    
    # 2. Execute Relayer
    print("\n2️⃣ Action: Executing Cross-Chain Tx")
    result = await relayer.execute_route(route, api_key=key)
    tx_hash = result["tx_hash"]
    print(f"   -> Tx Hash: {tx_hash}")
    
    # 3. Query Oracle
    print(f"\n3️⃣ Verification: Querying Oracle for {tx_hash}...")
    # Simulate slight delay (user querying from frontend)
    await asyncio.sleep(0.1)
    
    status_record = await oracle.get_status(tx_hash)
    print(f"   -> Oracle Response: {status_record}")
    
    # 4. Assertions
    if status_record["status"] == "COMPLETED":
        print("✅ SUCCESS: Status is COMPLETED")
    else:
        print(f"❌ FAILURE: Unexpected status {status_record.get('status')}")
        
    if status_record["meta"]["fee"] == 0.5:
        print("✅ SUCCESS: Fee metadata persisted correctly.")
    else:
        print("❌ FAILURE: Fee metadata missing/incorrect.")

if __name__ == "__main__":
    asyncio.run(test_oracle())
