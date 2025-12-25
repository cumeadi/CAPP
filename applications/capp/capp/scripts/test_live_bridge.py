
import asyncio
import sys
import os
from decimal import Decimal
import structlog

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.services.bridge_service import bridge_provider
from applications.capp.capp.models.payments import Chain

# Configure logging
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
)
logger = structlog.get_logger()

async def test_live_bridge_quote():
    """
    Test Fetching a Live Quote from Li.Fi (Base Sepolia -> Arbitrum Sepolia)
    """
    logger.info("Starting Live Bridge Quote Verification")
    
    # 1. Setup Request
    from_chain = Chain.BASE
    to_chain = Chain.ARBITRUM
    
    # USDC on Base Mainnet
    from_token = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    
    amount = Decimal("10.0") # 10 USDC
    wallet = "0x5555555555555555555555555555555555555555" # Dummy address for quote
    
    # 2. Get Quote
    logger.info("Requesting Quote from Li.Fi...")
    quote = await bridge_provider.get_quote(from_chain, to_chain, from_token, amount, wallet)
    
    if quote:
        logger.info(
            "✅ Live Quote Received!",
            provider=quote.provider,
            amount_out=quote.amount_out,
            gas_cost=quote.gas_cost_usd,
            eta=quote.estimated_duration_seconds,
            tx_data_present=bool(quote.transaction_request)
        )
        
        print("\n--- Quote Details ---")
        print(f"Provider: {quote.provider}")
        print(f"Route: {quote.from_chain} -> {quote.to_chain}")
        print(f"Amount In: {quote.amount_in} USDC")
        print(f"Amount Out: {quote.amount_out} USDC")
        print(f"Est Time: {quote.estimated_duration_seconds}s")
        if quote.transaction_request:
            print(f"Tx To: {quote.transaction_request.get('to')}")
            print(f"Tx Data Length: {len(quote.transaction_request.get('data', ''))}")
        print("---------------------\n")
    else:
        logger.error("❌ Failed to get quote (Check connectivity or token support)")
        # It's possible the specific testnet tokens aren't supported by Li.Fi testnet API
        # but we want to verify the API call works.

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_live_bridge_quote())
