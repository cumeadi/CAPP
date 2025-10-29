"""
Test Fixtures for CAPP Test Suite

Provides reusable test data and fixtures for testing.
"""

from .mpesa_callbacks import MpesaCallbackFixtures, MPESA_RESULT_CODES, get_result_description
from .mtn_callbacks import (
    MTNMoMoCallbackFixtures,
    MTN_MOMO_STATUS_CODES,
    MTN_MOMO_ERROR_REASONS,
    get_status_description as get_mtn_status_description,
    get_error_description as get_mtn_error_description
)
from .airtel_callbacks import (
    AirtelMoneyCallbackFixtures,
    AIRTEL_MONEY_STATUS_CODES,
    AIRTEL_MONEY_ERROR_CODES,
    get_status_description as get_airtel_status_description,
    get_error_description as get_airtel_error_description
)

__all__ = [
    # M-Pesa
    "MpesaCallbackFixtures",
    "MPESA_RESULT_CODES",
    "get_result_description",
    # MTN MoMo
    "MTNMoMoCallbackFixtures",
    "MTN_MOMO_STATUS_CODES",
    "MTN_MOMO_ERROR_REASONS",
    "get_mtn_status_description",
    "get_mtn_error_description",
    # Airtel Money
    "AirtelMoneyCallbackFixtures",
    "AIRTEL_MONEY_STATUS_CODES",
    "AIRTEL_MONEY_ERROR_CODES",
    "get_airtel_status_description",
    "get_airtel_error_description",
]
