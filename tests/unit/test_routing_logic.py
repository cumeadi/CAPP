
import pytest
from decimal import Decimal
from applications.capp.capp.services.routing_service import RoutingService
from applications.capp.capp.models.payments import PaymentPreferences

@pytest.mark.asyncio
async def test_routing_prioritize_cost():
    service = RoutingService()
    
    # User wants CHEAP
    prefs = PaymentPreferences(prioritize_cost=True, prioritize_speed=False)
    
    # 100 USDC transfer
    best_quote = await service.calculate_best_route(
        amount=Decimal("100.00"), 
        currency="USDC", 
        destination="0x123", 
        preferences=prefs
    )
    
    assert best_quote is not None
    # CheapRail (fee 0.001) should win over FastRail (fee 0.05)
    assert best_quote["rail"] == "CheapRail"
    assert best_quote["fee"] == 0.1 # 100 * 0.001

@pytest.mark.asyncio
async def test_routing_prioritize_speed():
    service = RoutingService()
    
    # User wants FAST
    prefs = PaymentPreferences(prioritize_cost=False, prioritize_speed=True)
    
    # 100 USDC transfer
    best_quote = await service.calculate_best_route(
        amount=Decimal("100.00"), 
        currency="USDC", 
        destination="0x123", 
        preferences=prefs
    )
    
    assert best_quote is not None
    # FastRail (10s) should win over CheapRail (3600s)
    assert best_quote["rail"] == "FastRail"
    assert best_quote["estimated_time_minutes"] < 1.0 
