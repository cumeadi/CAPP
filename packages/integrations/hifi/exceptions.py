"""
HIFI Africa Rail Exceptions
"""

from typing import Any, Dict, List, Optional


class HifiIntegrationException(Exception):
    """Base exception for HIFI Africa Rail integration failures"""

    def __init__(
        self,
        message: str,
        error_code: str = "HIFI_INTEGRATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class HifiKYCException(HifiIntegrationException):
    """KYC/KYB submission or validation failure"""

    def __init__(self, message: str, missing_fields: Optional[List[str]] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="HIFI_KYC_ERROR",
            details={**(details or {}), "missing_fields": missing_fields or []},
        )
        self.missing_fields = missing_fields or []


class HifiCorridorNotSupportedException(HifiIntegrationException):
    """Raised when a country/direction is not supported by HIFI"""

    def __init__(self, country_code: str, direction: Optional[str] = None):
        msg = f"HIFI does not support country '{country_code}'"
        if direction:
            msg += f" for {direction}"
        super().__init__(msg, error_code="HIFI_CORRIDOR_NOT_SUPPORTED", details={"country": country_code, "direction": direction})


class HifiBetaLimitExceededException(HifiIntegrationException):
    """Raised when a transaction exceeds beta-mode limits"""

    def __init__(self, amount: str, max_amount: str):
        super().__init__(
            f"Transaction amount {amount} exceeds HIFI beta limit of {max_amount}",
            error_code="HIFI_BETA_LIMIT_EXCEEDED",
            details={"amount": amount, "max_amount": max_amount},
        )
