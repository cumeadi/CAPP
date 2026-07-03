"""
HIFI Africa Rail Request/Response Models

Maps between CAPP's internal models and HIFI's API format.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from packages.integrations.hifi.country_config import (
    HIFI_ACCEPTED_ID_TYPES,
    requires_additional_id,
)


class HifiAddress(BaseModel):
    """Address payload for HIFI KYC"""
    addressLine1: str
    addressLine2: Optional[str] = None
    city: str
    stateProvinceRegion: str
    postalCode: str
    country: str  # ISO 3166-1 alpha-2


class HifiKYCPayload(BaseModel):
    """Individual KYC payload matching HIFI's API format"""
    firstName: str
    lastName: str
    email: str
    phone: str
    dateOfBirth: str  # YYYY-MM-DD
    idType: str  # DRIVERS, ID_CARD, PASSPORT, RESIDENCE_PERMIT
    idNumber: str
    address: HifiAddress
    # Nigeria-specific
    additionalIdType: Optional[str] = None
    additionalIdNumber: Optional[str] = None


class HifiKYBPayload(BaseModel):
    """Business KYB payload matching HIFI's API format"""
    businessName: str
    taxIdentificationNumber: str


class HifiTransferRequest(BaseModel):
    """Transfer request payload for HIFI API"""
    direction: str  # payin, payout
    amount: str  # String representation of decimal amount
    currency: str  # ISO 4217
    paymentMethod: str  # bank_transfer, mobile_money
    senderKyc: Optional[HifiKYCPayload] = None
    recipientKyc: Optional[HifiKYCPayload] = None
    reference: Optional[str] = None
    metadata: Optional[dict] = None


class HifiTransferResponse(BaseModel):
    """Transfer response from HIFI API"""
    transactionId: str
    status: str  # pending, processing, completed, failed
    fees: Optional[str] = None
    exchangeRate: Optional[str] = None
    estimatedDeliveryMinutes: Optional[int] = None
    reference: Optional[str] = None


class HifiTransferStatus(BaseModel):
    """Transfer status response from HIFI API"""
    transactionId: str
    status: str
    updatedAt: Optional[str] = None
    completedAt: Optional[str] = None
    failureReason: Optional[str] = None


def map_sender_to_hifi_kyc(
    name: str,
    phone_number: str,
    country_code: str,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    date_of_birth: Optional[date] = None,
    id_type: Optional[str] = None,
    id_number: Optional[str] = None,
    address_line1: Optional[str] = None,
    address_line2: Optional[str] = None,
    city: Optional[str] = None,
    state_province_region: Optional[str] = None,
    postal_code: Optional[str] = None,
    additional_id_type: Optional[str] = None,
    additional_id_number: Optional[str] = None,
) -> HifiKYCPayload:
    """
    Map CAPP sender/recipient fields to HIFI KYC payload.

    Falls back to splitting `name` into first/last if explicit fields are absent.
    """
    # Derive first/last name from full name if not provided
    resolved_first = first_name
    resolved_last = last_name
    if not resolved_first or not resolved_last:
        parts = name.split(maxsplit=1)
        resolved_first = resolved_first or parts[0]
        resolved_last = resolved_last or (parts[1] if len(parts) > 1 else parts[0])

    address = HifiAddress(
        addressLine1=address_line1 or "",
        addressLine2=address_line2,
        city=city or "",
        stateProvinceRegion=state_province_region or "",
        postalCode=postal_code or "",
        country=country_code,
    )

    payload = HifiKYCPayload(
        firstName=resolved_first,
        lastName=resolved_last,
        email=email or "",
        phone=phone_number,
        dateOfBirth=date_of_birth.isoformat() if date_of_birth else "",
        idType=id_type or "",
        idNumber=id_number or "",
        address=address,
    )

    # Nigeria-specific additional ID
    if requires_additional_id(country_code):
        payload.additionalIdType = additional_id_type
        payload.additionalIdNumber = additional_id_number

    return payload
