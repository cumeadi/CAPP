"""
ExchangeRate-API Client

Real-time forex rates from ExchangeRate-API.com
Supports 160+ currencies including all African currencies.
"""

from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime, timezone
import asyncio

import httpx
import structlog
from pydantic import BaseModel

from ...config.settings import get_settings
from ...core.exceptions import ExchangeRateException

logger = structlog.get_logger(__name__)


class ExchangeRateResponse(BaseModel):
    """Exchange rate API response model"""
    result: str  # "success" or "error"
    documentation: str
    terms_of_use: str
    time_last_update_unix: int
    time_last_update_utc: str
    time_next_update_unix: int
    time_next_update_utc: str
    base_code: str
    conversion_rates: Dict[str, float]


class ExchangeRatePair(BaseModel):
    """Exchange rate for a currency pair"""
    from_currency: str
    to_currency: str
    rate: Decimal
    inverse_rate: Decimal
    fetched_at: datetime
    source: str = "exchangerate-api.com"


class ExchangeRateAPIClient:
    """
    Client for ExchangeRate-API.com

    Provides real-time exchange rates for 160+ currencies.
    Free tier: 1,500 requests/month
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.EXCHANGE_RATE_API_KEY
        self.base_url = self.settings.EXCHANGE_RATE_BASE_URL
        self.logger = structlog.get_logger(__name__)

        # HTTP client with timeout
        self.client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

        # Cache for rates (in-memory)
        self._rate_cache: Dict[str, ExchangeRatePair] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 300  # 5 minutes

    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """
        Get exchange rate from one currency to another.

        Args:
            from_currency: Source currency code (e.g., "USD")
            to_currency: Target currency code (e.g., "KES")

        Returns:
            Decimal: Exchange rate

        Raises:
            ExchangeRateException: If rate fetch fails
        """
        try:
            # Check cache first
            cache_key = f"{from_currency}_{to_currency}"
            if self._is_cache_valid() and cache_key in self._rate_cache:
                self.logger.info(
                    "Using cached exchange rate",
                    from_currency=from_currency,
                    to_currency=to_currency
                )
                return self._rate_cache[cache_key].rate

            # Fetch fresh rates
            rates = await self._fetch_rates(from_currency)

            if to_currency not in rates:
                raise ExchangeRateException(
                    f"Exchange rate not available for {from_currency}/{to_currency}",
                    currency_pair=f"{from_currency}/{to_currency}"
                )

            rate = Decimal(str(rates[to_currency]))

            # Cache the rate
            rate_pair = ExchangeRatePair(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                inverse_rate=Decimal("1") / rate if rate > 0 else Decimal("0"),
                fetched_at=datetime.now(timezone.utc)
            )
            self._rate_cache[cache_key] = rate_pair

            self.logger.info(
                "Fetched exchange rate",
                from_currency=from_currency,
                to_currency=to_currency,
                rate=float(rate)
            )

            return rate

        except httpx.HTTPError as e:
            self.logger.error(
                "HTTP error fetching exchange rate",
                from_currency=from_currency,
                to_currency=to_currency,
                error=str(e)
            )
            raise ExchangeRateException(
                f"Failed to fetch exchange rate: {str(e)}",
                currency_pair=f"{from_currency}/{to_currency}"
            )
        except Exception as e:
            self.logger.error(
                "Unexpected error fetching exchange rate",
                from_currency=from_currency,
                to_currency=to_currency,
                error=str(e),
                exc_info=True
            )
            raise ExchangeRateException(
                f"Unexpected error: {str(e)}",
                currency_pair=f"{from_currency}/{to_currency}"
            )

    async def get_multiple_rates(
        self,
        from_currency: str,
        to_currencies: List[str]
    ) -> Dict[str, Decimal]:
        """
        Get multiple exchange rates from one currency to many.

        Args:
            from_currency: Source currency code
            to_currencies: List of target currency codes

        Returns:
            Dict[str, Decimal]: Map of currency code to exchange rate
        """
        try:
            # Fetch all rates for the base currency
            rates = await self._fetch_rates(from_currency)

            # Extract requested rates
            result = {}
            for to_currency in to_currencies:
                if to_currency in rates:
                    result[to_currency] = Decimal(str(rates[to_currency]))
                else:
                    self.logger.warning(
                        "Exchange rate not available",
                        from_currency=from_currency,
                        to_currency=to_currency
                    )

            self.logger.info(
                "Fetched multiple exchange rates",
                from_currency=from_currency,
                count=len(result)
            )

            return result

        except Exception as e:
            self.logger.error(
                "Failed to fetch multiple rates",
                from_currency=from_currency,
                error=str(e)
            )
            raise ExchangeRateException(
                f"Failed to fetch multiple rates: {str(e)}",
                currency_pair=f"{from_currency}/multiple"
            )

    async def get_all_rates(self, base_currency: str = "USD") -> Dict[str, Decimal]:
        """
        Get all available exchange rates for a base currency.

        Args:
            base_currency: Base currency code

        Returns:
            Dict[str, Decimal]: All available exchange rates
        """
        try:
            rates = await self._fetch_rates(base_currency)

            # Convert to Decimal
            result = {
                currency: Decimal(str(rate))
                for currency, rate in rates.items()
            }

            self.logger.info(
                "Fetched all exchange rates",
                base_currency=base_currency,
                count=len(result)
            )

            return result

        except Exception as e:
            self.logger.error(
                "Failed to fetch all rates",
                base_currency=base_currency,
                error=str(e)
            )
            raise ExchangeRateException(
                f"Failed to fetch all rates: {str(e)}",
                currency_pair=f"{base_currency}/all"
            )

    async def _fetch_rates(self, base_currency: str) -> Dict[str, float]:
        """
        Fetch exchange rates from ExchangeRate-API.com.

        Args:
            base_currency: Base currency code

        Returns:
            Dict[str, float]: Map of currency code to rate

        Raises:
            ExchangeRateException: If API call fails
        """
        if not self.api_key:
            raise ExchangeRateException(
                "Exchange rate API key not configured",
                currency_pair=base_currency
            )

        # Build URL: https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{BASE_CODE}
        url = f"{self.base_url}/{self.api_key}/latest/{base_currency}"

        self.logger.debug("Fetching rates from API", url=url, base_currency=base_currency)

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()

            # Validate response
            if data.get("result") != "success":
                error_type = data.get("error-type", "unknown")
                raise ExchangeRateException(
                    f"API returned error: {error_type}",
                    currency_pair=base_currency
                )

            # Parse response
            rate_response = ExchangeRateResponse(**data)

            # Update cache timestamp
            self._cache_timestamp = datetime.now(timezone.utc)

            return rate_response.conversion_rates

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise ExchangeRateException(
                    "Invalid API key or quota exceeded",
                    currency_pair=base_currency
                )
            elif e.response.status_code == 404:
                raise ExchangeRateException(
                    f"Currency not supported: {base_currency}",
                    currency_pair=base_currency
                )
            else:
                raise ExchangeRateException(
                    f"API request failed: {e.response.status_code}",
                    currency_pair=base_currency
                )
        except httpx.TimeoutException:
            raise ExchangeRateException(
                "API request timed out",
                currency_pair=base_currency
            )

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cache_timestamp:
            return False

        age = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
        return age < self._cache_ttl

    def clear_cache(self) -> None:
        """Clear the rate cache"""
        self._rate_cache.clear()
        self._cache_timestamp = None
        self.logger.info("Exchange rate cache cleared")

    async def close(self) -> None:
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Global client instance
_exchange_rate_client: Optional[ExchangeRateAPIClient] = None


def get_exchange_rate_client() -> ExchangeRateAPIClient:
    """Get or create global exchange rate client"""
    global _exchange_rate_client
    if _exchange_rate_client is None:
        _exchange_rate_client = ExchangeRateAPIClient()
    return _exchange_rate_client


async def test_exchange_rate_api():
    """
    Test function for exchange rate API.

    Usage:
        python -m applications.capp.capp.services.external.exchange_rate_client
    """
    client = ExchangeRateAPIClient()

    try:
        print("Testing ExchangeRate-API Client...")
        print("-" * 50)

        # Test 1: Single rate
        print("\nTest 1: Get USD → KES rate")
        usd_to_kes = await client.get_rate("USD", "KES")
        print(f"  USD → KES: {usd_to_kes}")

        # Test 2: Multiple African currencies
        print("\nTest 2: Get USD rates for African currencies")
        african_currencies = ["KES", "NGN", "GHS", "ZAR", "UGX", "TZS"]
        rates = await client.get_multiple_rates("USD", african_currencies)
        for currency, rate in rates.items():
            print(f"  USD → {currency}: {rate}")

        # Test 3: Cache test
        print("\nTest 3: Test caching (should be instant)")
        usd_to_kes_cached = await client.get_rate("USD", "KES")
        print(f"  USD → KES (cached): {usd_to_kes_cached}")

        # Test 4: Cross-rate (Kenya → Nigeria)
        print("\nTest 4: Get KES → NGN rate")
        kes_to_ngn = await client.get_rate("KES", "NGN")
        print(f"  KES → NGN: {kes_to_ngn}")

        print("\n" + "=" * 50)
        print("✅ All tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_exchange_rate_api())
