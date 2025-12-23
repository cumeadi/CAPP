from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import random
from enum import Enum

class MMOStatus(Enum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    DEGRADED = "DEGRADED"

class MMOProvider(ABC):
    """Abstract Base Class for Mobile Money Operators"""
    
    def __init__(self, name: str, country: str):
        self.name = name
        self.country = country
        self.api_url = f"https://api.{name.lower()}.{country.lower()}.com"  # Mock URL base

    @abstractmethod
    async def check_availability(self) -> Dict[str, Any]:
        """Check if the MMO service is up and accepting transactions"""
        pass

    @abstractmethod
    def calculate_fees(self, amount: float) -> float:
        """Calculate transaction fees based on provider's tiered structure"""
        pass

class MPesaProvider(MMOProvider):
    """Simulator for M-Pesa (Safaricom) Daraja API"""
    
    def __init__(self, country: str = "KENYA"):
        super().__init__("MPESA", country)
        # M-Pesa Tiered Fee Structure (Approximate USD Mock)
        # 0-50: 0.5%
        # 50-500: 1.0%
        # 500+: 1.5%
        self.fee_tiers = [
            (50, 0.005),
            (500, 0.010),
            (float('inf'), 0.015)
        ]

    async def check_availability(self) -> Dict[str, Any]:
        # Simulate Daraja API Health Check
        # In production this would hit: GET /mpesa/health
        is_up = random.random() > 0.05  # 95% Uptime
        return {
            "status": MMOStatus.ACTIVE if is_up else MMOStatus.MAINTENANCE,
            "latency_ms": random.randint(50, 200) if is_up else 0
        }

    def calculate_fees(self, amount: float) -> float:
        for limit, rate in self.fee_tiers:
            if amount <= limit:
                return round(amount * rate, 2)
        return round(amount * 0.015, 2) # Default max tier

class MTNProvider(MMOProvider):
    """Simulator for MTN Mobile Money (MoMo) API"""
    
    def __init__(self, country: str = "NIGERIA"):
        super().__init__("MTN", country)
        # MTN Flat + % Fee Structure Mock
        # Base fee $0.10 + 1%
        self.base_fee = 0.10
        self.variable_rate = 0.01

    async def check_availability(self) -> Dict[str, Any]:
        # Simulate MoMo API Health Check
        is_up = random.random() > 0.10  # 90% Uptime (slightly less reliable in sim)
        return {
            "status": MMOStatus.ACTIVE if is_up else MMOStatus.MAINTENANCE,
            "latency_ms": random.randint(100, 400) if is_up else 0
        }

    def calculate_fees(self, amount: float) -> float:
        return round(self.base_fee + (amount * self.variable_rate), 2)
