
import asyncio
from decimal import Decimal
from typing import Dict, Any

from applications.capp.capp.adapters.base import BasePaymentRail, AdapterConfig

class MockPaymentRail(BasePaymentRail):
    """
    Generic Mock Payment Rail for testing.
    Configurable fee rate and speed.
    """
    def __init__(self, config: AdapterConfig, fee_rate: Decimal = Decimal("0.01"), speed_seconds: int = 60):
        super().__init__(config)
        self.fee_rate = fee_rate
        self.speed_seconds = speed_seconds

    async def quote_transfer(self, token: str, amount: Decimal, destination: str) -> Dict[str, Any]:
        """
        Return a quote based on configured fees and speed.
        """
        fee = amount * self.fee_rate
        estimated_time_mins = self.speed_seconds / 60
        
        return {
            "rail": self.config.name,
            "token": token,
            "amount": float(amount),
            "fee": float(fee),
            "total_cost": float(amount + fee),
            "estimated_time_minutes": estimated_time_mins,
            "valid_until": "2099-12-31T23:59:59Z"
        }

    async def execute_transfer(self, token: str, amount: Decimal, destination: str) -> str:
        return f"mock_tx_{self.config.name}_{amount}"

    async def verify_status(self, reference_id: str) -> str:
        return "COMPLETED"

# Factory helpers
def create_fast_rail() -> MockPaymentRail:
    config = AdapterConfig(name="FastRail", network="mock", metadata={"type": "premium"})
    return MockPaymentRail(config, fee_rate=Decimal("0.05"), speed_seconds=10) # High fee, Fast

def create_cheap_rail() -> MockPaymentRail:
    config = AdapterConfig(name="CheapRail", network="mock", metadata={"type": "standard"})
    return MockPaymentRail(config, fee_rate=Decimal("0.001"), speed_seconds=3600) # Low fee, Slow
