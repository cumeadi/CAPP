
import asyncio
import sys
import os
from decimal import Decimal
import structlog
from datetime import datetime

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.agents.routing.route_optimization_agent import RouteOptimizationAgent, RouteOptimizationConfig
from applications.capp.capp.models.payments import CrossBorderPayment, PaymentType, PaymentMethod, Currency, Country, SenderInfo, RecipientInfo, Chain
from applications.capp.capp.core.aptos import init_aptos_client
from applications.capp.capp.core.redis import init_redis

# Configure logging
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
)
logger = structlog.get_logger()

async def test_integrated_router():
    """
    Test the Hybrid Route Optimization Agent:
    1. Base -> Arbitrum (Expect Real Li.Fi Quote)
    2. Aptos -> Base (Expect Mock Quote)
    """
    logger.info("Starting Integrated Router Verification")
    
    # 0. Init
    await init_aptos_client()
    await init_redis()
    
    config = RouteOptimizationConfig(
        name="IntegrationRouter",
        agent_type="routing",
        version="0.9.0",
        capabilities=["routing", "optimization", "bridge_aggregation"]
    )
    agent = RouteOptimizationAgent(config)
    await agent.start()
    
    # --- Test Case 1: EVM to EVM (Real Li.Fi) ---
    logger.info("\n--- TEST CASE 1: Base -> Arbitrum (Real) ---")
    payment_evm = CrossBorderPayment(
        reference_id="TEST-REAL-001",
        payment_type=PaymentType.PERSONAL_REMITTANCE,
        payment_method=PaymentMethod.CRYPTO,
        amount=Decimal("15.00"),
        from_currency=Currency.USDC,
        to_currency=Currency.USDC,
        sender=SenderInfo(
            name="Alice Base",
            phone_number="+1234567890",
            country=Country.UNITED_STATES,
            address="0x5555555555555555555555555555555555555555", # Source Wallet
            id_type="passport",
            id_number="A1234567"
        ),
        recipient=RecipientInfo(
            name="Bob Arb",
            phone_number="+0987654321",
            country=Country.UNITED_STATES,
            address="0xTargetAddress",
            id_type="national_id",
            id_number="B7654321"
        ),
        metadata={
            "source_chain": "base",
            "target_chain": "arbitrum"
        }
    )
    
    routes_evm = await agent.discover_routes(payment_evm)
    logger.info("EVM Routes Discovered", count=len(routes_evm))
    
    for r in routes_evm:
        logger.info("Route Details", provider=r.bridge_provider, type=type(r.bridge_provider))
        print(f"Debug: Provider={r.bridge_provider} value={r.bridge_provider.value if hasattr(r.bridge_provider, 'value') else 'N/A'}")

    has_lifi = any(r.bridge_provider == "li.fi" or (hasattr(r.bridge_provider, "value") and r.bridge_provider.value == "li.fi") for r in routes_evm)
    if has_lifi:
        logger.info("✅ SUCCESS: Found Real Li.Fi Route for Base->Arb")
        for r in routes_evm:
             if "li.fi" in str(r.bridge_provider).lower():
                 print(f"  > Provider: {r.bridge_provider}")
                 print(f"  > Est Time: {r.estimated_duration_seconds}s")
                 print(f"  > Gas Cost: ${r.gas_cost_usd}")
    else:
        logger.error("❌ FAILURE: No Li.Fi route found for EVM-EVM")

    # --- Test Case 2: Aptos to Base (Mock Fallback) ---
    logger.info("\n--- TEST CASE 2: Aptos -> Base (Mock) ---")
    payment_aptos = CrossBorderPayment(
        reference_id="TEST-MOCK-001",
        payment_type=PaymentType.PERSONAL_REMITTANCE,
        payment_method=PaymentMethod.CRYPTO,
        amount=Decimal("50.00"),
        from_currency=Currency.USDC, # Aptos USDC
        to_currency=Currency.USDC,
        sender=SenderInfo(
            name="Charlie Aptos",
            phone_number="+111222333",
            country=Country.UNITED_STATES,
            id_type="passport",
            id_number="C123"
        ),
        recipient=RecipientInfo(
            name="Dave Base",
            phone_number="+444555666",
            country=Country.UNITED_STATES,
            id_type="passport",
            id_number="D456"
        ),
        metadata={
            "source_chain": "aptos", # Explicit or default
            "target_chain": "base"
        }
    )
    
    routes_aptos = await agent.discover_routes(payment_aptos)
    logger.info("Aptos Routes Discovered", count=len(routes_aptos))
    
    has_mock = any(r.bridge_provider in ["stargate", "across", "hop"] for r in routes_aptos) 
    # Mock usually returns these strings
    
    if has_mock:
        logger.info("✅ SUCCESS: Found Mock Route for Aptos->Base (Fallback working)")
    else:
        logger.error("❌ FAILURE: No Mock route found for Aptos-Base")
        
    await agent.stop()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_integrated_router())
