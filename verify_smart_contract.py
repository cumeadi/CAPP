import asyncio
import structlog
from applications.capp.capp.core.aptos import AptosClient
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

async def verify_smart_contract_integration():
    print("Verifying Smart Contract Integration (Payload Generation)...")
    settings = get_settings()
    
    # Generate temporary account for signing
    from aptos_sdk.account import Account
    alice = Account.generate()
    
    # Initialize Client with Alice's key
    client = AptosClient(
        node_url=settings.APTOS_NODE_URL,
        private_key=str(alice.private_key),
        account_address=str(alice.address())
    )
    
    payment_id = "pymt_123456"
    amount = 10.5
    recipient = "0x1"
    
    print("\n--- Test 1: Escrow Funds Payload ---")
    try:
        # This will construct EntryFunction and call _submit_entry_function
        # returning our mocked hash
        tx_hash = await client.escrow_funds(payment_id, amount, recipient)
        print(f"✅ Escrow Payload Generated Successfully. TxHash: {tx_hash}")
    except Exception as e:
        print(f"❌ Escrow Payload Failed: {e}")
        
    print("\n--- Test 2: Release Funds Payload ---")
    try:
        tx_hash = await client.release_funds(payment_id, recipient)
        print(f"✅ Release Payload Generated Successfully. TxHash: {tx_hash}")
    except Exception as e:
        print(f"❌ Release Payload Failed: {e}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(verify_smart_contract_integration())
