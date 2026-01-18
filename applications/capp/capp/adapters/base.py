
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal
from pydantic import BaseModel

class AdapterConfig(BaseModel):
    """Configuration for adapters"""
    name: str
    network: str
    enabled: bool = True
    metadata: Dict[str, Any] = {}

class BaseYieldAdapter(ABC):
    """
    Abstract Base Class for Yield Providers (e.g., Yearn, Aave, Compound).
    Enforces a standard interface for deposit/withdrawal operations.
    """
    
    def __init__(self, config: AdapterConfig):
        self.config = config

    @abstractmethod
    async def get_apy(self, asset: str) -> Decimal:
        """Fetch current APY for the given asset."""
        pass

    @abstractmethod
    async def deposit(self, asset: str, amount: Decimal) -> str:
        """
        Deposit assets into the yield protocol.
        Returns the transaction hash.
        """
        pass

    @abstractmethod
    async def withdraw(self, asset: str, amount: Decimal) -> str:
        """
        Withdraw assets from the yield protocol.
        Returns the transaction hash.
        """
        pass
    
    @abstractmethod
    async def get_balance(self, asset: str) -> Decimal:
        """Get the current balance deposited in the protocol."""
        pass

class BasePaymentRail(ABC):
    """
    Abstract Base Class for Payment Rails (e.g., Aptos, Polygon, Stellar, SWIFT).
    """

    def __init__(self, config: AdapterConfig):
        self.config = config

    @abstractmethod
    async def quote_transfer(self, token: str, amount: Decimal, destination: str) -> Dict[str, Any]:
        """Get a quote for transfer fees and time."""
        pass

    @abstractmethod
    async def execute_transfer(self, token: str, amount: Decimal, destination: str) -> str:
        """
        Execute the payment.
        Returns the transaction hash or reference ID.
        """
        pass
    
    @abstractmethod
    async def verify_status(self, reference_id: str) -> str:
        """Check status of a transfer."""
        pass
