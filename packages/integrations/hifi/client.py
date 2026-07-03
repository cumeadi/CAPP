"""
HIFI Africa Rail HTTP Client

Async HTTP client for interacting with the HIFI API.
"""

import asyncio
from typing import Any, Dict, Optional

import httpx
import structlog

from packages.integrations.hifi.config import HifiConfig
from packages.integrations.hifi.exceptions import (
    HifiIntegrationException,
    HifiKYCException,
)
from packages.integrations.hifi.models import (
    HifiKYCPayload,
    HifiKYBPayload,
    HifiTransferRequest,
    HifiTransferResponse,
    HifiTransferStatus,
)

logger = structlog.get_logger(__name__)


class HifiClient:
    """
    Async HTTP client for the HIFI Africa Rail API.

    Handles authentication, retries, and error mapping.
    """

    def __init__(self, config: HifiConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "X-Api-Secret": self.config.api_secret,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an API request with retry logic.

        Raises HifiIntegrationException on failure.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                client = await self._get_client()
                response = await client.request(method, endpoint, json=data)

                if response.status_code >= 400:
                    body = response.json() if response.content else {}
                    raise HifiIntegrationException(
                        message=body.get("message", f"HIFI API error {response.status_code}"),
                        error_code=body.get("code", f"HTTP_{response.status_code}"),
                        details={"status_code": response.status_code, "body": body},
                    )

                return response.json()

            except HifiIntegrationException:
                raise  # Don't retry application-level errors
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("HIFI request timeout", endpoint=endpoint, attempt=attempt)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("HIFI request failed", endpoint=endpoint, attempt=attempt, error=str(exc))

            if attempt < self.config.retry_attempts:
                delay = self.config.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                await asyncio.sleep(delay)

        raise HifiIntegrationException(
            message=f"HIFI API request failed after {self.config.retry_attempts} attempts: {last_error}",
            details={"endpoint": endpoint, "method": method},
        )

    # ------------------------------------------------------------------ #
    # KYC / KYB
    # ------------------------------------------------------------------ #

    async def submit_kyc(self, kyc_payload: HifiKYCPayload) -> Dict[str, Any]:
        """Submit individual KYC to HIFI."""
        logger.info("Submitting HIFI individual KYC", email=kyc_payload.email)
        return await self._request("POST", "/kyc/individual", data=kyc_payload.model_dump(exclude_none=True))

    async def submit_kyb(self, kyb_payload: HifiKYBPayload) -> Dict[str, Any]:
        """Submit business KYB to HIFI."""
        logger.info("Submitting HIFI business KYB", business=kyb_payload.businessName)
        return await self._request("POST", "/kyc/business", data=kyb_payload.model_dump(exclude_none=True))

    # ------------------------------------------------------------------ #
    # Transfers
    # ------------------------------------------------------------------ #

    async def create_transfer(self, transfer: HifiTransferRequest) -> HifiTransferResponse:
        """Create a pay-in or pay-out transfer."""
        logger.info(
            "Creating HIFI transfer",
            direction=transfer.direction,
            amount=transfer.amount,
            currency=transfer.currency,
        )
        resp = await self._request("POST", "/transfers", data=transfer.model_dump(exclude_none=True))
        return HifiTransferResponse(**resp)

    async def get_transfer_status(self, transaction_id: str) -> HifiTransferStatus:
        """Get the status of a transfer."""
        resp = await self._request("GET", f"/transfers/{transaction_id}")
        return HifiTransferStatus(**resp)

    # ------------------------------------------------------------------ #
    # Corridors
    # ------------------------------------------------------------------ #

    async def get_corridors(self) -> Dict[str, Any]:
        """Get supported corridors from HIFI."""
        return await self._request("GET", "/corridors")

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("HIFI client closed")
