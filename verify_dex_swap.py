import asyncio
import structlog
from applications.capp.capp.core.aptos import AptosClient
from applications.capp.capp.config.settings import get_settings
from aptos_sdk.account import Account

logger = structlog.get_logger(__name__)

async def verify_dex_swap():
    print("Verifying DEX Integration (LiquidSwap Payload)...")
    settings = get_settings()
    
    # Generate temporary account for signing
    alice = Account.generate()
    
    # Initialize Client with Alice's key
    client = AptosClient(
        node_url=settings.APTOS_NODE_URL,
        private_key=str(alice.private_key),
        account_address=str(alice.address())
    )
    
    from_asset = "APT"
    to_asset = "USDC"
    amount = 5.0 # 5 APT
    
    print("\n--- Test 1: Swap APT -> USDC Payload ---")
    try:
        # This will construct EntryFunction and call _submit_entry_function
        # returning our mocked hash (but validation happens during construction)
        tx_hash = await client.swap_tokens(from_asset, to_asset, amount)
        print(f"✅ Swap Payload Generated Successfully. TxHash: {tx_hash}")
    except Exception as e:
        print(f"❌ Swap Payload Failed: {e}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(verify_dex_swap())
