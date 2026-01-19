from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from decimal import Decimal

class BaseBridgeAdapter(ABC):
    """
    Abstract base class for Cross-Chain Bridge Adapters.
    Standardizes interaction with providers like LayerZero, LiFi, Wormhole, etc.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the bridge protocol (e.g., 'LiFi', 'LayerZero')"""
        pass

    @abstractmethod
    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount: Decimal,
        from_chain: str,
        to_chain: str
    ) -> Dict[str, Any]:
        """
        Get a quote for bridging assets.
        
        Returns:
            dict: {
                "fee_usd": float,
                "estimated_time_seconds": int,
                "provider": str,
                "meta": dict  # Protocol specific data
            }
        """
        pass

    @abstractmethod
    async def bridge_assets(
        self,
        quote_id: str,
        private_key: str, 
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Execute the bridge transaction.
        
        Args:
            quote_id: ID returned from get_quote (or reconstructed context)
            private_key: Signer context (careful with handling this)
            wallet_address: Recipient address
            
        Returns:
            dict: {
                "tx_hash": str,
                "status": "PENDING" | "COMPLETED" | "FAILED",
                "explorer_url": str
            }
        """
        pass
