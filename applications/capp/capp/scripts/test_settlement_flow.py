
import asyncio
import sys
import os
import uuid

# Path Fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.core.aptos import init_aptos_client, get_aptos_client
from applications.capp.capp.config.settings import get_settings

async def test_settlement_flow():
    print("🚀 Starting Settlement Flow verification...")
    
    # 1. Initialize
    await init_aptos_client()
    client = get_aptos_client()
    
    payment_id = str(uuid.uuid4())
    recipient = "0x123"
    amount = 100.0
    
    # 2. Test Escrow
    print(f"\nTesting Escrow (Payment ID: {payment_id})...")
    tx_hash = await client.escrow_funds(payment_id, amount, recipient)
    print(f"✅ Escrow Transaction Submitted: {tx_hash}")
    
    # 3. Test Release
    print(f"\nTesting Release...")
    tx_hash = await client.release_funds(payment_id, recipient)
    print(f"✅ Release Transaction Submitted: {tx_hash}")

    # 4. Test Refund (on a new payment)
    payment_id_refund = str(uuid.uuid4())
    print(f"\nTesting Refund (Payment ID: {payment_id_refund})...")
    tx_hash = await client.refund_sender(payment_id_refund)
    print(f"✅ Refund Transaction Submitted: {tx_hash}")
    
    print("\n🎉 Verification Complete!")

if __name__ == "__main__":
    asyncio.run(test_settlement_flow())
