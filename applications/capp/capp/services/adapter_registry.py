
from typing import Dict, List, Optional, Type
import structlog

from applications.capp.capp.adapters.base import BasePaymentRail, BaseYieldAdapter, AdapterConfig

logger = structlog.get_logger(__name__)

class AdapterRegistry:
    """
    Singleton registry for all available adapters.
    Allows dynamic registration and retrieval of Payment Rails and Yield Providers.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AdapterRegistry, cls).__new__(cls)
            cls._instance.payment_rails: Dict[str, BasePaymentRail] = {}
            cls._instance.yield_adapters: Dict[str, BaseYieldAdapter] = {}
        return cls._instance

    def register_payment_rail(self, adapter: BasePaymentRail):
        """Register a Payment Rail instance."""
        name = adapter.config.name
        self.payment_rails[name] = adapter
        logger.info("payment_rail_registered", name=name)

    def register_yield_adapter(self, adapter: BaseYieldAdapter):
        """Register a Yield Adapter instance."""
        name = adapter.config.name
        self.yield_adapters[name] = adapter
        logger.info("yield_adapter_registered", name=name)

    def get_payment_rail(self, name: str) -> Optional[BasePaymentRail]:
        return self.payment_rails.get(name)

    def get_yield_adapter(self, name: str) -> Optional[BaseYieldAdapter]:
        return self.yield_adapters.get(name)

    def get_all_payment_rails(self) -> List[BasePaymentRail]:
        return list(self.payment_rails.values())

    def get_all_yield_adapters(self) -> List[BaseYieldAdapter]:
        return list(self.yield_adapters.values())

    def clear(self):
        """Clear all registered adapters (useful for testing)."""
        self.payment_rails.clear()
        self.yield_adapters.clear()
