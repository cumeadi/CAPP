import asyncio
import structlog
from decimal import Decimal
import os

# Use Sync Client
from aptos_sdk.account import Account
from aptos_sdk.client import RestClient, FaucetClient
from applications.capp.capp.core.aptos import AptosClient
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

async def verify_aptos_settlement():
    print("Verifying Real Aptos Integration (Testnet) [Sync SDK Mode]...")
    settings = get_settings()
    
    # 1. Setup Environment (Override to Devnet for Faucet access)
    NODE_URL = "https://fullnode.devnet.aptoslabs.com/v1"
    FAUCET_URL = "https://faucet.devnet.aptoslabs.com"
    print(f"Node: {NODE_URL}")
    print(f"Faucet: {FAUCET_URL}")
    
    # 2. Generate Test Account
    print("\n--- Step 1: Generating Test Account ---")
    alice = Account.generate()
    bob = Account.generate()
    print(f"Alice Address: {alice.address()}")
    print(f"Bob Address: {bob.address()}")
    
    # 3. Fund Alice via Faucet
    print("\n--- Step 2: Funding Alice Account ---")
    # FaucetClient is sync in older SDKs generally, or we wrap it
    try:
        # FaucetClient in 0.5.0 might be sync. Let's assume sync for now.
        faucet_client = FaucetClient(FAUCET_URL, RestClient(NODE_URL))
        
        # Run funding in thread to be safe if it blocks, though top-level script it doesn't matter much
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: faucet_client.fund_account(alice.address(), 100_000_000))
        
        print("Funded Alice with 1 APT")
    except Exception as e:
        print(f"Faucet funding failed: {e}")
        return

    # 4. Initialize CAPP AptosClient with Alice's Key
    print("\n--- Step 3: Initializing CAPP Client ---")
    client = AptosClient(
        node_url=NODE_URL,
        private_key=str(alice.private_key), 
        account_address=str(alice.address())
    )
    
    # 5. Check Balance
    balance_before = await client.get_account_balance(str(alice.address()))
    print(f"Alice Balance Before: {balance_before} APT")
    
    if balance_before < 0.1:
        print("Error: Balance too low to proceed (Faucet might be rate limiting)")
        # Continue mostly to test structure, but transaction will fail
        
    # 6. Execute Transfer (Alice -> Bob)
    print("\n--- Step 4: Executing Settlement (Transfer) ---")
    payload = {
        "type": "payment_settlement",
        "recipient_address": str(bob.address()),
        "amount": 0.1, # 0.1 APT
        "id": "verify_tx_001"
    }
    
    try:
        tx_hash = await client.submit_transaction(payload)
        print(f"Transaction Submitted: {tx_hash}")
        
        print("Waiting for finality...")
        success = await client.wait_for_finality(tx_hash)
        
        if success:
            print("✅ Transaction Finalized!")
            print(f"Explorer: https://explorer.aptoslabs.com/txn/{tx_hash}?network=testnet")
        else:
            print("❌ Transaction timed out or failed")
            
    except Exception as e:
        print(f"Transaction failed: {e}")
    
    # 7. Verify Balance Update
    balance_after = await client.get_account_balance(str(alice.address()))
    print(f"Alice Balance After: {balance_after} APT")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(verify_aptos_settlement())
