"""
price_oracle.py — Redis-cached asset price oracle for CAPP

Provides current USD prices for assets used in the wallet statistics endpoint.
Prices are fetched from a configurable upstream source and cached in Redis
with a short TTL to avoid stale values without hammering the upstream.

Fallback chain:
  1. Redis cache (fast, sub-millisecond)
  2. Upstream HTTP price feed (CoinGecko simple-price endpoint)
  3. Hardcoded defaults (last resort — clearly logged)

Usage::

    oracle = PriceOracle()
    apt_price = await oracle.get_price("APT")   # e.g. 10.25
    eth_price = await oracle.get_price("ETH")
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, Optional

import httpx
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded fallback prices (last resort only — logged as warnings)
# These are the original values from wallet.py and are intentionally kept
# as a safety net for environments with no Redis and no network access.
# ---------------------------------------------------------------------------
_FALLBACK_PRICES: Dict[str, float] = {
    "APT":   10.0,
    "MATIC":  0.85,
    "POL":    0.85,
    "ETH":  2500.0,
    "SOL":   150.0,
    "XLM":    0.12,
    "USDC":   1.0,
    "USDT":   1.0,
}

# CoinGecko asset-id mapping for the simple/price endpoint
_COINGECKO_IDS: Dict[str, str] = {
    "APT":   "aptos",
    "MATIC": "matic-network",
    "POL":   "matic-network",
    "ETH":   "ethereum",
    "SOL":   "solana",
    "XLM":   "stellar",
    "USDC":  "usd-coin",
    "USDT":  "tether",
}

_REDIS_KEY_PREFIX = "price_oracle:usd:"
_DEFAULT_TTL = int(os.getenv("PRICE_ORACLE_CACHE_TTL_SECONDS", "60"))
_FALLBACK_ENABLED = os.getenv("PRICE_ORACLE_FALLBACK_ENABLED", "true").lower() == "true"
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_COINGECKO_BASE = "https://api.coingecko.com/api/v3"


class PriceOracle:
    """
    Redis-cached asset price oracle.

    Thread-safe for async use; a single shared instance is recommended
    per process (see module-level ``get_oracle()``).
    """

    def __init__(
        self,
        redis_url: str = _REDIS_URL,
        cache_ttl: int = _DEFAULT_TTL,
    ) -> None:
        self._redis_url = redis_url
        self._cache_ttl = cache_ttl
        self._redis: Optional[aioredis.Redis] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_price(self, symbol: str) -> float:
        """
        Return the current USD price for *symbol* (e.g. ``"ETH"``).

        Checks Redis first, then falls back to upstream, then hardcoded.
        """
        symbol = symbol.upper()

        # 1. Try Redis cache
        cached = await self._get_cached(symbol)
        if cached is not None:
            return cached

        # 2. Try upstream price feed
        fetched = await self._fetch_upstream(symbol)
        if fetched is not None:
            await self._set_cached(symbol, fetched)
            return fetched

        # 3. Hardcoded fallback
        if _FALLBACK_ENABLED and symbol in _FALLBACK_PRICES:
            logger.warning(
                "price_oracle: using hardcoded fallback price for %s = %s USD",
                symbol,
                _FALLBACK_PRICES[symbol],
            )
            return _FALLBACK_PRICES[symbol]

        logger.error("price_oracle: no price available for %s", symbol)
        return 0.0

    async def get_prices(self, symbols: list[str]) -> Dict[str, float]:
        """Return USD prices for all requested symbols in one call."""
        result: Dict[str, float] = {}
        # Batch fetch: first populate from cache, then fetch missing from upstream.
        missing = []
        for sym in symbols:
            sym = sym.upper()
            cached = await self._get_cached(sym)
            if cached is not None:
                result[sym] = cached
            else:
                missing.append(sym)

        if missing:
            upstream = await self._fetch_upstream_batch(missing)
            for sym, price in upstream.items():
                result[sym] = price
                await self._set_cached(sym, price)

            # Fallback for any still-missing symbols
            for sym in missing:
                if sym not in result:
                    if _FALLBACK_ENABLED and sym in _FALLBACK_PRICES:
                        logger.warning(
                            "price_oracle: using hardcoded fallback price for %s", sym
                        )
                        result[sym] = _FALLBACK_PRICES[sym]
                    else:
                        result[sym] = 0.0

        return result

    # ------------------------------------------------------------------
    # Redis helpers
    # ------------------------------------------------------------------

    async def _redis_client(self) -> Optional[aioredis.Redis]:
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                await self._redis.ping()
            except Exception as exc:
                logger.debug("price_oracle: Redis unavailable (%s)", exc)
                self._redis = None
        return self._redis

    async def _get_cached(self, symbol: str) -> Optional[float]:
        client = await self._redis_client()
        if client is None:
            return None
        try:
            val = await client.get(f"{_REDIS_KEY_PREFIX}{symbol}")
            return float(val) if val is not None else None
        except Exception as exc:
            logger.debug("price_oracle: cache get failed (%s)", exc)
            return None

    async def _set_cached(self, symbol: str, price: float) -> None:
        client = await self._redis_client()
        if client is None:
            return
        try:
            await client.setex(f"{_REDIS_KEY_PREFIX}{symbol}", self._cache_ttl, str(price))
        except Exception as exc:
            logger.debug("price_oracle: cache set failed (%s)", exc)

    # ------------------------------------------------------------------
    # Upstream price feed (CoinGecko free tier)
    # ------------------------------------------------------------------

    async def _fetch_upstream(self, symbol: str) -> Optional[float]:
        prices = await self._fetch_upstream_batch([symbol])
        return prices.get(symbol)

    async def _fetch_upstream_batch(self, symbols: list[str]) -> Dict[str, float]:
        ids = [_COINGECKO_IDS.get(s) for s in symbols if _COINGECKO_IDS.get(s)]
        if not ids:
            return {}

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{_COINGECKO_BASE}/simple/price",
                    params={"ids": ",".join(ids), "vs_currencies": "usd"},
                )
                if resp.status_code != 200:
                    logger.warning(
                        "price_oracle: upstream returned HTTP %s", resp.status_code
                    )
                    return {}

                data: Dict = resp.json()
                result: Dict[str, float] = {}
                for sym in symbols:
                    cg_id = _COINGECKO_IDS.get(sym)
                    if cg_id and cg_id in data:
                        price = data[cg_id].get("usd")
                        if price is not None:
                            result[sym] = float(price)
                return result

        except Exception as exc:
            logger.warning("price_oracle: upstream fetch failed (%s)", exc)
            return {}


# ---------------------------------------------------------------------------
# Module-level singleton (lazily created)
# ---------------------------------------------------------------------------
_oracle: Optional[PriceOracle] = None


def get_oracle() -> PriceOracle:
    """Return the shared PriceOracle instance (created on first call)."""
    global _oracle
    if _oracle is None:
        _oracle = PriceOracle()
    return _oracle
