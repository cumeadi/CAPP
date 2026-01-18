
import asyncio
import structlog
import sys
import os

# Add current directory to path just in case
sys.path.append(os.getcwd())

async def debug_routing():
    print("Debug: Importing RoutingService...")
    try:
        from applications.capp.capp.services.routing_service import RoutingService
        from applications.capp.capp.models.payments import PaymentPreferences
        print("Debug: Import Successful")
    except Exception as e:
        print(f"Debug: Import Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("Debug: Instantiating RoutingService...")
    try:
        engine = RoutingService()
        print("Debug: Instantiation Successful")
    except Exception as e:
        print(f"Debug: Instantiation Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("Debug: Calculating Route...")
    try:
        prefs = PaymentPreferences(prioritize_cost=False, prioritize_speed=True)
        from decimal import Decimal
        quotes = await engine.calculate_best_route(
            amount=Decimal("100.00"), 
            currency="USDC", 
            destination="0x123", 
            preferences=prefs
        )
        print(f"Debug: Calculation Successful. Quotes: {len(quotes)}")
        print(quotes)
    except Exception as e:
        print(f"Debug: Calculation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_routing())
