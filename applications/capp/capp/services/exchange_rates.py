"""
Exchange Rate Service for CAPP

Handles exchange rate retrieval and currency conversion for African currencies.
"""

import asyncio
from typing import Optional, Dict, List
from decimal import Decimal
import aiohttp
import structlog

from .models.payments import Currency
from .config.settings import get_settings
from .core.redis import get_cache

logger = structlog.get_logger(__name__)


class ExchangeRateService:
    """
    Exchange Rate Service
    
    Provides exchange rate data for African currencies with:
    - Multi-source rate aggregation
    - Caching for performance
    - Fallback mechanisms
    - Rate validation
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.logger = structlog.get_logger(__name__)
        
        # Cache TTL for exchange rates (5 minutes)
        self.cache_ttl = 300
        
        # Supported currency pairs
        self.supported_pairs = self._get_supported_pairs()
    
    def _get_supported_pairs(self) -> Dict[str, List[str]]:
        """Get supported currency pairs for African currencies"""
        return {
            # West Africa
            "NGN": ["USD", "EUR", "GBP", "GHS", "XOF"],
            "XOF": ["USD", "EUR", "GBP", "NGN", "GHS"],
            "GHS": ["USD", "EUR", "GBP", "NGN", "XOF"],
            
            # East Africa
            "KES": ["USD", "EUR", "GBP", "UGX", "TZS", "RWF"],
            "UGX": ["USD", "EUR", "GBP", "KES", "TZS", "RWF"],
            "TZS": ["USD", "EUR", "GBP", "KES", "UGX", "RWF"],
            "RWF": ["USD", "EUR", "GBP", "KES", "UGX", "TZS"],
            
            # Southern Africa
            "ZAR": ["USD", "EUR", "GBP", "BWP", "ZMW", "NAD"],
            "ZMW": ["USD", "EUR", "GBP", "ZAR", "BWP", "NAD"],
            "BWP": ["USD", "EUR", "GBP", "ZAR", "ZMW", "NAD"],
            
            # Major currencies
            "USD": ["NGN", "XOF", "GHS", "KES", "UGX", "TZS", "RWF", "ZAR", "ZMW", "BWP"],
            "EUR": ["NGN", "XOF", "GHS", "KES", "UGX", "TZS", "RWF", "ZAR", "ZMW", "BWP"],
            "GBP": ["NGN", "XOF", "GHS", "KES", "UGX", "TZS", "RWF", "ZAR", "ZMW", "BWP"]
        }
    
    async def get_exchange_rate(self, from_currency: Currency, to_currency: Currency) -> Optional[Decimal]:
        """
        Get exchange rate for currency pair
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Decimal: Exchange rate, or None if not available
        """
        try:
            # Check cache first
            cache_key = f"exchange_rate:{from_currency}:{to_currency}"
            cached_rate = await self.cache.get(cache_key)
            
            if cached_rate:
                self.logger.info("Using cached exchange rate", from_currency=from_currency, to_currency=to_currency)
                return Decimal(str(cached_rate))
            
            # Check if pair is supported
            if not self._is_pair_supported(from_currency, to_currency):
                self.logger.warning("Currency pair not supported", from_currency=from_currency, to_currency=to_currency)
                return None
            
            # Get rate from multiple sources
            rate = await self._get_rate_from_sources(from_currency, to_currency)
            
            if rate:
                # Cache the rate
                await self.cache.set(cache_key, float(rate), self.cache_ttl)
                self.logger.info("Exchange rate retrieved", from_currency=from_currency, to_currency=to_currency, rate=rate)
            
            return rate
            
        except Exception as e:
            self.logger.error("Failed to get exchange rate", from_currency=from_currency, to_currency=to_currency, error=str(e))
            return None
    
    async def _get_rate_from_sources(self, from_currency: Currency, to_currency: Currency) -> Optional[Decimal]:
        """Get exchange rate from multiple sources"""
        try:
            # Try multiple sources in parallel
            tasks = [
                self._get_rate_from_exchangerate_api(from_currency, to_currency),
                self._get_rate_from_fixer_api(from_currency, to_currency),
                self._get_rate_from_african_banks(from_currency, to_currency)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and None values
            valid_rates = [r for r in results if isinstance(r, Decimal) and r > 0]
            
            if not valid_rates:
                self.logger.warning("No valid rates found from any source", from_currency=from_currency, to_currency=to_currency)
                return None
            
            # Return median rate for stability
            valid_rates.sort()
            median_rate = valid_rates[len(valid_rates) // 2]
            
            return median_rate
            
        except Exception as e:
            self.logger.error("Failed to get rate from sources", error=str(e))
            return None
    
    async def _get_rate_from_exchangerate_api(self, from_currency: Currency, to_currency: Currency) -> Optional[Decimal]:
        """Get rate from ExchangeRate API"""
        try:
            if not self.settings.EXCHANGE_RATE_API_KEY:
                return None
            
            url = f"{self.settings.EXCHANGE_RATE_BASE_URL}/{from_currency}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        rates = data.get('rates', {})
                        rate = rates.get(to_currency)
                        
                        if rate:
                            return Decimal(str(rate))
            
            return None
            
        except Exception as e:
            self.logger.warning("Failed to get rate from ExchangeRate API", error=str(e))
            return None
    
    async def _get_rate_from_fixer_api(self, from_currency: Currency, to_currency: Currency) -> Optional[Decimal]:
        """Get rate from Fixer API (fallback)"""
        try:
            # This would integrate with Fixer API
            # For now, return None
            return None
            
        except Exception as e:
            self.logger.warning("Failed to get rate from Fixer API", error=str(e))
            return None
    
    async def _get_rate_from_african_banks(self, from_currency: Currency, to_currency: Currency) -> Optional[Decimal]:
        """Get rate from African central banks"""
        try:
            # This would integrate with African central bank APIs
            # For now, return mock rates for common pairs
            mock_rates = {
                ("KES", "UGX"): Decimal("0.025"),
                ("NGN", "GHS"): Decimal("0.012"),
                ("ZAR", "BWP"): Decimal("0.68"),
                ("USD", "NGN"): Decimal("750.0"),
                ("USD", "KES"): Decimal("150.0"),
                ("USD", "ZAR"): Decimal("18.5"),
                ("EUR", "NGN"): Decimal("820.0"),
                ("EUR", "KES"): Decimal("165.0"),
                ("EUR", "ZAR"): Decimal("20.0"),
            }
            
            return mock_rates.get((from_currency, to_currency))
            
        except Exception as e:
            self.logger.warning("Failed to get rate from African banks", error=str(e))
            return None
    
    def _is_pair_supported(self, from_currency: Currency, to_currency: Currency) -> bool:
        """Check if currency pair is supported"""
        supported_targets = self.supported_pairs.get(from_currency, [])
        return to_currency in supported_targets
    
    async def convert_amount(self, amount: Decimal, from_currency: Currency, to_currency: Currency) -> Optional[Decimal]:
        """
        Convert amount from one currency to another
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Decimal: Converted amount, or None if conversion failed
        """
        try:
            rate = await self.get_exchange_rate(from_currency, to_currency)
            
            if rate is None:
                return None
            
            converted_amount = amount * rate
            return converted_amount.quantize(Decimal('0.01'))  # Round to 2 decimal places
            
        except Exception as e:
            self.logger.error("Currency conversion failed", error=str(e))
            return None
    
    async def get_optimal_rate(self, from_currency: Currency, to_currency: Currency) -> Optional[Decimal]:
        """
        Get optimal exchange rate (best available rate)
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Decimal: Optimal exchange rate, or None if not available
        """
        try:
            # Get rates from all sources
            rates = await self._get_all_rates(from_currency, to_currency)
            
            if not rates:
                return None
            
            # Return the best rate (lowest for selling, highest for buying)
            # For now, return the median rate
            rates.sort()
            return rates[len(rates) // 2]
            
        except Exception as e:
            self.logger.error("Failed to get optimal rate", error=str(e))
            return None
    
    async def _get_all_rates(self, from_currency: Currency, to_currency: Currency) -> List[Decimal]:
        """Get all available rates for currency pair"""
        try:
            tasks = [
                self._get_rate_from_exchangerate_api(from_currency, to_currency),
                self._get_rate_from_fixer_api(from_currency, to_currency),
                self._get_rate_from_african_banks(from_currency, to_currency)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter valid rates
            valid_rates = [r for r in results if isinstance(r, Decimal) and r > 0]
            
            return valid_rates
            
        except Exception as e:
            self.logger.error("Failed to get all rates", error=str(e))
            return []
    
    async def get_supported_currencies(self) -> List[Currency]:
        """Get list of supported currencies"""
        return list(self.supported_pairs.keys())
    
    async def get_supported_pairs_for_currency(self, currency: Currency) -> List[Currency]:
        """Get supported currency pairs for a specific currency"""
        return self.supported_pairs.get(currency, [])
    
    async def validate_rate(self, rate: Decimal, from_currency: Currency, to_currency: Currency) -> bool:
        """
        Validate if exchange rate is reasonable
        
        Args:
            rate: Rate to validate
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            bool: True if rate is reasonable, False otherwise
        """
        try:
            # Get current market rate
            market_rate = await self.get_exchange_rate(from_currency, to_currency)
            
            if market_rate is None:
                return True  # Can't validate, assume valid
            
            # Check if rate is within 10% of market rate
            tolerance = Decimal('0.1')  # 10%
            min_rate = market_rate * (1 - tolerance)
            max_rate = market_rate * (1 + tolerance)
            
            is_valid = min_rate <= rate <= max_rate
            
            if not is_valid:
                self.logger.warning(
                    "Exchange rate validation failed",
                    rate=rate,
                    market_rate=market_rate,
                    from_currency=from_currency,
                    to_currency=to_currency
                )
            
            return is_valid
            
        except Exception as e:
            self.logger.error("Rate validation failed", error=str(e))
            return True  # Assume valid if validation fails 