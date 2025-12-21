import asyncio
import structlog
from decimal import Decimal

from applications.capp.capp.agents.routing.route_optimization_agent import RouteOptimizationAgent, RouteOptimizationConfig
from applications.capp.capp.models.payments import CrossBorderPayment, PaymentRoute, Country, Currency, PaymentMethod, PaymentType, SenderInfo, RecipientInfo
from applications.capp.capp.core.aptos import init_aptos_client, close_aptos_client
from applications.capp.capp.core.redis import init_redis, close_redis

logger = structlog.get_logger(__name__)

async def verify_integration():
    print("Verifying RL Integration...")
    
    # Initialize Infrastructure
    await init_redis()
    await init_aptos_client()
    
    try:
        # Initialize Agent
        config = RouteOptimizationConfig()
        agent = RouteOptimizationAgent(config)
        print("Agent initialized")
    
        # Create Mock Payment
        payment = CrossBorderPayment(
            reference_id="TEST_REF_001",
            payment_type=PaymentType.PERSONAL_REMITTANCE,
            payment_method=PaymentMethod.MOBILE_MONEY,
            amount=Decimal("1000.00"),
            from_currency=Currency.USD,
            to_currency=Currency.KES,
            sender=SenderInfo(name="Test Sender", phone_number="+1", country=Country.NIGERIA),
            recipient=RecipientInfo(name="Test Recipient", phone_number="+254", country=Country.KENYA)
        )
        # Fix Country enum if USA is missing. Enum has "USD" currency but Country enum might be African + major.
        # Looking at country enum in previous view_file: I don't see USA. I see Country.NIGERIA etc.
        # Let's use NIGERIA to KENYA
        payment.sender.country = Country.NIGERIA
        payment.from_currency = Currency.NGN
        
        # Create Candidate Routes
        routes = [
            PaymentRoute(
                from_country=Country.NIGERIA, to_country=Country.KENYA,
                from_currency=Currency.NGN, to_currency=Currency.KES,
                fees=Decimal("10.00"), estimated_delivery_time=60, success_rate=0.99,
                exchange_rate=Decimal("0.1"), cost_score=0.9, speed_score=0.9, reliability_score=0.9, total_score=0.0
            ),
            PaymentRoute(
                from_country=Country.NIGERIA, to_country=Country.KENYA,
                from_currency=Currency.NGN, to_currency=Currency.KES,
                fees=Decimal("50.00"), estimated_delivery_time=10, success_rate=0.95,
                exchange_rate=Decimal("0.1"), cost_score=0.5, speed_score=0.95, reliability_score=0.95, total_score=0.0
            ),
            PaymentRoute(
                from_country=Country.NIGERIA, to_country=Country.KENYA,
                from_currency=Currency.NGN, to_currency=Currency.KES,
                fees=Decimal("5.00"), estimated_delivery_time=1440, success_rate=0.80, # Slow but cheap
                exchange_rate=Decimal("0.1"), cost_score=0.95, speed_score=0.1, reliability_score=0.8, total_score=0.0
            )
        ]
        
        print(f"Scoring {len(routes)} routes...")
        
        # Call score_routes
        scored_routes = await agent.score_routes(routes, payment)
        
        # Verify basics
        assert len(scored_routes) == len(routes)
        
        top_route = scored_routes[0]
        print(f"Top Route Selected: Fees={top_route.route.fees}, Time={top_route.route.estimated_delivery_time}")
        print(f"Total Score: {top_route.total_score}")
        print(f"Is RL Selected: {getattr(top_route, 'is_rl_selected', 'Unknown')}")
        
        if getattr(top_route, 'is_rl_selected', False):
             print("✅ RL Model successfully drove the route selection!")
        else:
             print("⚠️ RL Model did not select this route (or logic fallback)")

    finally:
        await close_aptos_client()
        await close_redis()
    
    return True

if __name__ == "__main__":
    asyncio.run(verify_integration())
