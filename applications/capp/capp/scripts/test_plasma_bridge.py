
import asyncio
import sys
import os

# Ad-hoc path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.core.bridge import PlasmaBridgeService

async def test_plasma_flow():
    print("🚀 Testing Plasma Bridge Logic...")
    
    service = PlasmaBridgeService()
    
    # 1. Deposit
    print("\n[1] Depositing 100 USDC...")
    deposit = await service.deposit(100.0, "0xUser", "USDC")
    print(f"✅ Deposited: {deposit['status']}, L1 Lock: {deposit['root_tx']}, L2 Mint: {deposit['child_tx']}")
    
    # 2. Withdraw (Start Exit)
    print("\n[2] Initiating Withdraw (Exit)...")
    exit_data = await service.initiate_withdraw(50.0, "0xUser", "USDC")
    exit_id = exit_data['exit_id']
    print(f"✅ Exit Started: ID={exit_id}, ETA={exit_data['estimated_completion']}")
    
    # 3. Check Status (Should be locked)
    print("\n[3] Checking Status (Immediate)...")
    status = await service.check_exit_status(exit_id)
    print(f"ℹ️ Status: {status['status']}")
    
    # 4. Try Finalize (Should Fail)
    print("\n[4] Attempting Early Finalize...")
    final = await service.finalize_exit(exit_id)
    if "error" in final:
        print(f"✅ Early Finalize Blocked: {final['error']}")
        
    # 5. Fast Forward (Hack for test: change ETA in memory)
    print("\n[5] Fast Forwarding Challenge Period...")
    from datetime import datetime
    service.exits[exit_id]["eta"] = datetime.utcnow() # Expire timer instantly
    
    # 6. Finalize Success
    print("\n[6] Retrying Finalize...")
    final_success = await service.finalize_exit(exit_id)
    print(f"✅ Finalized! Tx: {final_success['finalize_tx']}")
    print(f"ℹ️ Final Status: {final_success['status']}")

if __name__ == "__main__":
    asyncio.run(test_plasma_flow())
