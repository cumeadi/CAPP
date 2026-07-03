"""
HIFI Africa Rail Country and Corridor Configuration

Maps supported countries to currencies, directions, and payment methods.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class CorridorInfo:
    """Configuration for a single HIFI corridor"""
    currency: str
    supports_payin: bool
    supports_payout: bool


# Countries with full pay-in and pay-out support
HIFI_FULL_CORRIDORS: Dict[str, CorridorInfo] = {
    "BJ": CorridorInfo(currency="XOF", supports_payin=True, supports_payout=True),   # Benin
    "BW": CorridorInfo(currency="BWP", supports_payin=True, supports_payout=True),   # Botswana
    "CM": CorridorInfo(currency="XAF", supports_payin=True, supports_payout=True),   # Cameroon
    "CI": CorridorInfo(currency="XOF", supports_payin=True, supports_payout=True),   # Côte d'Ivoire
    "MW": CorridorInfo(currency="MWK", supports_payin=True, supports_payout=True),   # Malawi
    "NG": CorridorInfo(currency="NGN", supports_payin=True, supports_payout=True),   # Nigeria
    "TZ": CorridorInfo(currency="TZS", supports_payin=True, supports_payout=True),   # Tanzania
    "TG": CorridorInfo(currency="XOF", supports_payin=True, supports_payout=True),   # Togo
    "UG": CorridorInfo(currency="UGX", supports_payin=True, supports_payout=True),   # Uganda
    "ZM": CorridorInfo(currency="ZMW", supports_payin=True, supports_payout=True),   # Zambia
}

# Countries with payout-only support
HIFI_PAYOUT_ONLY_CORRIDORS: Dict[str, CorridorInfo] = {
    "BF": CorridorInfo(currency="XOF", supports_payin=False, supports_payout=True),  # Burkina Faso
    "KE": CorridorInfo(currency="KES", supports_payin=False, supports_payout=True),  # Kenya
    "ML": CorridorInfo(currency="XOF", supports_payin=False, supports_payout=True),  # Mali
    "SN": CorridorInfo(currency="XOF", supports_payin=False, supports_payout=True),  # Senegal
    "ZA": CorridorInfo(currency="ZAR", supports_payin=False, supports_payout=True),  # South Africa
}

# Combined corridor lookup
HIFI_ALL_CORRIDORS: Dict[str, CorridorInfo] = {**HIFI_FULL_CORRIDORS, **HIFI_PAYOUT_ONLY_CORRIDORS}

# Payment method capabilities
HIFI_PAYMENT_METHODS = {
    "bank_transfer": {
        "supports_payin": True,
        "supports_payout": True,
        "speed": "1-3 business days",
        "estimated_minutes_min": 1440,   # 1 day
        "estimated_minutes_max": 4320,   # 3 days
    },
    "mobile_money": {
        "supports_payin": True,
        "supports_payout": True,
        "speed": "instant to 1 day",
        "estimated_minutes_min": 1,      # instant
        "estimated_minutes_max": 1440,   # 1 day
    },
}

# Nigeria-specific requirements
NIGERIA_COUNTRY_CODE = "NG"
NIGERIA_REQUIREMENTS = {
    "individual_requires_additional_id": True,
    "kyb_available": False,
}

# HIFI-accepted ID types
HIFI_ACCEPTED_ID_TYPES = ["DRIVERS", "ID_CARD", "PASSPORT", "RESIDENCE_PERMIT"]


def get_corridor(country_code: str) -> Optional[CorridorInfo]:
    """Get corridor info for a country, or None if unsupported."""
    return HIFI_ALL_CORRIDORS.get(country_code)


def is_country_supported(country_code: str) -> bool:
    """Check if a country is supported by HIFI."""
    return country_code in HIFI_ALL_CORRIDORS


def supports_payin(country_code: str) -> bool:
    """Check if a country supports pay-in via HIFI."""
    corridor = get_corridor(country_code)
    return corridor.supports_payin if corridor else False


def supports_payout(country_code: str) -> bool:
    """Check if a country supports pay-out via HIFI."""
    corridor = get_corridor(country_code)
    return corridor.supports_payout if corridor else False


def get_supported_countries() -> List[str]:
    """Get all country codes supported by HIFI."""
    return list(HIFI_ALL_CORRIDORS.keys())


def requires_additional_id(country_code: str) -> bool:
    """Check if a country requires additional ID (Nigeria-specific)."""
    return country_code == NIGERIA_COUNTRY_CODE


def supports_kyb(country_code: str) -> bool:
    """Check if KYB (business verification) is available for a country."""
    if country_code == NIGERIA_COUNTRY_CODE:
        return False
    return is_country_supported(country_code)
