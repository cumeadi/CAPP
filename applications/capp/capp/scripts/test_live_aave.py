
import asyncio
import sys
import os
import structlog

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.services.defi_service import aave_service

# Configure logging
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
)
logger = structlog.get_logger()

async def test_aave_read():
    """
    Test Reading from Aave V3 Contract on Arbitrum Mainnet
    """
    logger.info("Starting Aave V3 Verification")
    
    # Use a random address (or a known whale if we want non-zero data)
    # Random address:
    target_user = "0x5555555555555555555555555555555555555555"
    
    logger.info("Fetching User Account Data...", user=target_user)
    
    data = await aave_service.get_user_data(target_user)
    
    if data:
        logger.info(
            "✅ Successfully read from Aave V3!",
            healthFactor=data.get("healthFactor"),
            totalCollateral=data.get("totalCollateralBase")
        )
        print("\n--- Aave Data ---")
        print(f"User: {target_user}")
        print(f"Total Collateral: {data.get('totalCollateralBase')}")
        print(f"Health Factor: {data.get('healthFactor')}")
        print("-----------------\n")
    else:
        logger.error("❌ Failed to read Aave data")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_aave_read())
