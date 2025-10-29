"""
External Service Clients

Clients for integrating with external APIs:
- Exchange rate APIs
- Mobile Money Operators (MMOs)
- Banking APIs
- Compliance APIs
"""

from .exchange_rate_client import (
    ExchangeRateAPIClient,
    ExchangeRatePair,
    get_exchange_rate_client,
)

__all__ = [
    "ExchangeRateAPIClient",
    "ExchangeRatePair",
    "get_exchange_rate_client",
]
