"""
HIFI Africa Rail Payment Adapter

Implements BasePaymentRail for the HIFI Africa Rail, supporting both
bank transfers and mobile money through a unified API.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

import structlog

from applications.capp.capp.adapters.base import AdapterConfig, BasePaymentRail
from packages.integrations.hifi.client import HifiClient
from packages.integrations.hifi.config import HifiConfig
from packages.integrations.hifi.country_config import (
    HIFI_ALL_CORRIDORS,
    HIFI_PAYMENT_METHODS,
    get_corridor,
    get_supported_countries,
    is_country_supported,
    requires_additional_id,
    supports_kyb,
    supports_payin,
    supports_payout,
)
from packages.integrations.hifi.exceptions import (
    HifiBetaLimitExceededException,
    HifiCorridorNotSupportedException,
    HifiIntegrationException,
    HifiKYCException,
)
from packages.integrations.hifi.models import (
    HifiKYBPayload,
    HifiKYCPayload,
    HifiTransferRequest,
    map_sender_to_hifi_kyc,
)

logger = structlog.get_logger(__name__)


class HifiAfricaRailAdapter(BasePaymentRail):
    """
    Unified HIFI Africa Rail adapter.

    Handles both mobile money and bank transfers via HIFI's single API.
    Implements BasePaymentRail for integration with the CAPP routing engine.
    """

    def __init__(self, config: AdapterConfig, hifi_config: HifiConfig):
        super().__init__(config)
        self.hifi_config = hifi_config
        self.client = HifiClient(hifi_config)

    # ------------------------------------------------------------------ #
    # BasePaymentRail interface
    # ------------------------------------------------------------------ #

    async def quote_transfer(
        self, token: str, amount: Decimal, destination: str
    ) -> Dict[str, Any]:
        """
        Get a quote for a HIFI transfer.

        Args:
            token: Currency code (e.g. NGN, KES)
            amount: Transfer amount
            destination: Country code of the destination
        """
        corridor = get_corridor(destination)
        if not corridor:
            raise HifiCorridorNotSupportedException(destination)

        self._check_beta_limits(amount)

        # Estimate based on payment method capabilities
        method_info = HIFI_PAYMENT_METHODS.get("mobile_money", {})
        estimated_minutes = method_info.get("estimated_minutes_max", 1440)

        return {
            "rail": self.config.name,
            "token": token,
            "amount": float(amount),
            "fee": 0.0,  # Actual fee comes from HIFI API at execution time
            "total_cost": float(amount),
            "estimated_time_minutes": estimated_minutes,
            "currency": corridor.currency,
            "supports_payin": corridor.supports_payin,
            "supports_payout": corridor.supports_payout,
            "beta": self.hifi_config.beta_mode,
        }

    async def execute_transfer(
        self, token: str, amount: Decimal, destination: str
    ) -> str:
        """
        Execute a transfer via HIFI.

        Args:
            token: Currency code
            amount: Transfer amount
            destination: Country code

        Returns:
            HIFI transaction ID
        """
        self._check_beta_limits(amount)

        if not is_country_supported(destination):
            raise HifiCorridorNotSupportedException(destination)

        transfer_req = HifiTransferRequest(
            direction="payout",  # Default; overridden by orchestration layer
            amount=str(amount),
            currency=token,
            paymentMethod="mobile_money",
            reference=None,
        )

        response = await self.client.create_transfer(transfer_req)
        logger.info(
            "HIFI transfer executed",
            transaction_id=response.transactionId,
            status=response.status,
        )
        return response.transactionId

    async def verify_status(self, reference_id: str) -> str:
        """Check status of a HIFI transfer."""
        status = await self.client.get_transfer_status(reference_id)
        return status.status

    # ------------------------------------------------------------------ #
    # HIFI-specific methods
    # ------------------------------------------------------------------ #

    async def submit_individual_kyc(
        self, kyc_payload: HifiKYCPayload
    ) -> Dict[str, Any]:
        """
        Submit individual KYC to HIFI.

        Validates required fields before submission.
        """
        missing = self._validate_kyc_fields(kyc_payload)
        if missing:
            raise HifiKYCException(
                f"Missing required KYC fields: {', '.join(missing)}",
                missing_fields=missing,
            )

        return await self.client.submit_kyc(kyc_payload)

    async def submit_business_kyb(
        self, kyb_payload: HifiKYBPayload, country_code: str
    ) -> Dict[str, Any]:
        """
        Submit business KYB to HIFI.

        Raises if KYB is not available for the country (e.g. Nigeria).
        """
        if not supports_kyb(country_code):
            raise HifiKYCException(
                f"KYB is not available for country {country_code}",
                details={"country": country_code},
            )

        return await self.client.submit_kyb(kyb_payload)

    async def execute_directed_transfer(
        self,
        direction: str,
        amount: Decimal,
        currency: str,
        payment_method: str,
        country_code: str,
        sender_kyc: Optional[HifiKYCPayload] = None,
        recipient_kyc: Optional[HifiKYCPayload] = None,
        reference: Optional[str] = None,
    ) -> str:
        """
        Execute a transfer with explicit direction and payment method.

        This is the primary method used by the orchestration layer.

        Args:
            direction: "payin" or "payout"
            amount: Transfer amount
            currency: Currency code
            payment_method: "bank_transfer" or "mobile_money"
            country_code: Target country
            sender_kyc: Sender KYC payload
            recipient_kyc: Recipient KYC payload
            reference: CAPP payment reference

        Returns:
            HIFI transaction ID
        """
        self._check_beta_limits(amount)

        # Validate direction support
        if direction == "payin" and not supports_payin(country_code):
            raise HifiCorridorNotSupportedException(country_code, direction="payin")
        if direction == "payout" and not supports_payout(country_code):
            raise HifiCorridorNotSupportedException(country_code, direction="payout")

        transfer_req = HifiTransferRequest(
            direction=direction,
            amount=str(amount),
            currency=currency,
            paymentMethod=payment_method,
            senderKyc=sender_kyc,
            recipientKyc=recipient_kyc,
            reference=reference,
        )

        response = await self.client.create_transfer(transfer_req)
        logger.info(
            "HIFI directed transfer executed",
            transaction_id=response.transactionId,
            direction=direction,
            country=country_code,
        )
        return response.transactionId

    def get_supported_countries(self) -> List[str]:
        """Get all countries supported by HIFI."""
        return get_supported_countries()

    def supports_direction(self, country_code: str, direction: str) -> bool:
        """Check if HIFI supports a specific direction for a country."""
        if direction == "payin":
            return supports_payin(country_code)
        elif direction == "payout":
            return supports_payout(country_code)
        return False

    def supports_payment_method(self, country_code: str, method: str) -> bool:
        """Check if a payment method is supported for a country."""
        if not is_country_supported(country_code):
            return False
        return method in HIFI_PAYMENT_METHODS

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _check_beta_limits(self, amount: Decimal) -> None:
        """Enforce beta transaction limits."""
        if self.hifi_config.beta_mode and amount > self.hifi_config.max_transaction_amount:
            raise HifiBetaLimitExceededException(
                str(amount), str(self.hifi_config.max_transaction_amount)
            )

    def _validate_kyc_fields(self, kyc: HifiKYCPayload) -> List[str]:
        """Validate that all required KYC fields are present."""
        missing = []
        required = ["firstName", "lastName", "email", "phone", "dateOfBirth", "idType", "idNumber"]
        for field in required:
            if not getattr(kyc, field, None):
                missing.append(field)

        # Address fields
        address_required = ["addressLine1", "city", "stateProvinceRegion", "postalCode", "country"]
        if kyc.address:
            for field in address_required:
                if not getattr(kyc.address, field, None):
                    missing.append(f"address.{field}")
        else:
            missing.extend(f"address.{f}" for f in address_required)

        # Nigeria-specific
        if kyc.address and requires_additional_id(kyc.address.country):
            if not kyc.additionalIdType:
                missing.append("additionalIdType")
            if not kyc.additionalIdNumber:
                missing.append("additionalIdNumber")

        return missing

    async def close(self) -> None:
        """Close the adapter and underlying client."""
        await self.client.close()
