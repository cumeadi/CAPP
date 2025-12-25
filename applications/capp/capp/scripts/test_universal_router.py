
import asyncio
import sys
import os
from decimal import Decimal
import uuid
import structlog

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.agents.routing.route_optimization_agent import RouteOptimizationAgent, RouteOptimizationConfig
from applications.capp.capp.models.payments import (
    CrossBorderPayment, PaymentStatus, Currency, Country, 
    PaymentType, PaymentMethod, SenderInfo, RecipientInfo,
    Chain, BridgeProvider
)

from applications.capp.capp.core.aptos import get_aptos_client, init_aptos_client
from applications.capp.capp.core.redis import init_redis
from applications.capp.capp.config.settings import get_settings

# Configure logging
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
)
logger = structlog.get_logger()

async def test_universal_router_flow():
    """
    Test the complete flow of the Universal Liquidity Router (Aptos -> Base)
    """
    logger.info("Starting Universal Router Verification")
    
    # 0. Initialize Client
    # settings = get_settings()
    await init_aptos_client()
    await init_redis()
    
    # 1. Initialize Agent
    config = RouteOptimizationConfig()
    agent = RouteOptimizationAgent(config)
    
    # 2. Create Payment Request (Aptos -> Base)
    payment_id = uuid.uuid4()
    payment = CrossBorderPayment(
        payment_id=payment_id,
        reference_id=f"TX-{str(payment_id)[:8]}".upper(),
        amount=Decimal("500.00"),  # 500 USDC
        from_currency=Currency.USDC,
        to_currency=Currency.USDC,
        payment_type=PaymentType.BUSINESS_PAYMENT,
        payment_method=PaymentMethod.CRYPTO,
        status=PaymentStatus.PENDING,
        sender=SenderInfo(
            name="Treasury Corp",
            phone_number="+1000000000",
            country=Country.UNITED_STATES
        ),
        recipient=RecipientInfo(
            name="Base Vendor Inc",
            phone_number="+1000000001",
            country=Country.UNITED_STATES,
            address="0xBaseVendorAddress123"
        ),
        metadata={
            "target_chain": "base"  # This triggers the Bridge Logic
        }
    )
    
    logger.info("Created Payment Intent", payment_id=str(payment_id), amount=500, target="BASE")
    
    # 3. Find Optimal Route
    logger.info("Finding Optimal Route...")
    route = await agent.find_optimal_route(payment)
    
    if route:
        logger.info(
            "✅ Optimal Route Found!",
            provider=route.bridge_provider,
            from_chain=route.from_chain,
            to_chain=route.to_chain,
            eta_minutes=route.estimated_delivery_time,
            fee_usd=route.fees
        )
        
        # Verify it selected a bridge
        assert route.to_chain == Chain.BASE
        assert route.bridge_provider is not None
        assert route.fees > 0
        
    else:
        logger.error("❌ No Route Found!")
        sys.exit(1)

    print("\n--- Verification Summary ---")
    print(f"Payment ID: {payment_id}")
    print(f"Source: {route.from_chain} (Global Treasury)")
    print(f"Destination: {route.to_chain}")
    print(f"Selected Bridge: {route.bridge_provider} (Fastest/Cheapest)")
    print(f"Est Time: {route.estimated_delivery_time} mins")
    print("----------------------------\n")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_universal_router_flow())
