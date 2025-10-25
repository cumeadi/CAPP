"""
Custom Exception Classes for CAPP

Defines application-specific exceptions for better error handling and clarity.
"""

from typing import Any, Dict, Optional
from uuid import UUID


class CAPPException(Exception):
    """Base exception for all CAPP-specific errors"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or "CAPP_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


# ============================================================================
# Database Exceptions
# ============================================================================

class DatabaseException(CAPPException):
    """Base exception for database-related errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class RecordNotFoundException(DatabaseException):
    """Exception raised when a database record is not found"""

    def __init__(self, resource: str, identifier: Any):
        message = f"{resource} not found: {identifier}"
        super().__init__(message, details={"resource": resource, "identifier": str(identifier)})
        self.error_code = "RECORD_NOT_FOUND"


class DuplicateRecordException(DatabaseException):
    """Exception raised when attempting to create a duplicate record"""

    def __init__(self, resource: str, field: str, value: Any):
        message = f"{resource} with {field}='{value}' already exists"
        super().__init__(message, details={"resource": resource, "field": field, "value": str(value)})
        self.error_code = "DUPLICATE_RECORD"


class DatabaseConnectionException(DatabaseException):
    """Exception raised when database connection fails"""

    def __init__(self, message: str = "Database connection failed"):
        super().__init__(message)
        self.error_code = "DATABASE_CONNECTION_ERROR"


# ============================================================================
# Payment Exceptions
# ============================================================================

class PaymentException(CAPPException):
    """Base exception for payment-related errors"""

    def __init__(self, message: str, payment_id: Optional[UUID] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if payment_id:
            details["payment_id"] = str(payment_id)
        super().__init__(message, error_code="PAYMENT_ERROR", details=details)


class PaymentNotFoundException(PaymentException):
    """Exception raised when a payment is not found"""

    def __init__(self, payment_id: UUID):
        super().__init__(
            f"Payment not found: {payment_id}",
            payment_id=payment_id
        )
        self.error_code = "PAYMENT_NOT_FOUND"


class PaymentProcessingException(PaymentException):
    """Exception raised when payment processing fails"""

    def __init__(self, message: str, payment_id: Optional[UUID] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, payment_id=payment_id, details=details)
        self.error_code = "PAYMENT_PROCESSING_ERROR"


class PaymentCancellationException(PaymentException):
    """Exception raised when payment cancellation fails"""

    def __init__(self, message: str, payment_id: UUID, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, payment_id=payment_id, details=details)
        self.error_code = "PAYMENT_CANCELLATION_ERROR"


class InsufficientFundsException(PaymentException):
    """Exception raised when sender has insufficient funds"""

    def __init__(self, required: float, available: float, payment_id: Optional[UUID] = None):
        message = f"Insufficient funds: required {required}, available {available}"
        super().__init__(
            message,
            payment_id=payment_id,
            details={"required": required, "available": available}
        )
        self.error_code = "INSUFFICIENT_FUNDS"


class InvalidPaymentStatusException(PaymentException):
    """Exception raised when attempting invalid status transition"""

    def __init__(self, current_status: str, new_status: str, payment_id: Optional[UUID] = None):
        message = f"Invalid status transition from '{current_status}' to '{new_status}'"
        super().__init__(
            message,
            payment_id=payment_id,
            details={"current_status": current_status, "new_status": new_status}
        )
        self.error_code = "INVALID_PAYMENT_STATUS"


# ============================================================================
# Route Optimization Exceptions
# ============================================================================

class RouteOptimizationException(CAPPException):
    """Base exception for route optimization errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="ROUTE_OPTIMIZATION_ERROR", details=details)


class NoRoutesAvailableException(RouteOptimizationException):
    """Exception raised when no routes are available for a payment corridor"""

    def __init__(self, from_country: str, to_country: str):
        message = f"No routes available from {from_country} to {to_country}"
        super().__init__(message, details={"from_country": from_country, "to_country": to_country})
        self.error_code = "NO_ROUTES_AVAILABLE"


# ============================================================================
# Compliance Exceptions
# ============================================================================

class ComplianceException(CAPPException):
    """Base exception for compliance-related errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="COMPLIANCE_ERROR", details=details)


class KYCVerificationException(ComplianceException):
    """Exception raised when KYC verification fails"""

    def __init__(self, user_id: Optional[UUID] = None, reason: Optional[str] = None):
        message = "KYC verification failed"
        if reason:
            message += f": {reason}"
        details = {}
        if user_id:
            details["user_id"] = str(user_id)
        if reason:
            details["reason"] = reason
        super().__init__(message, details=details)
        self.error_code = "KYC_VERIFICATION_FAILED"


class AMLCheckException(ComplianceException):
    """Exception raised when AML checks fail"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details=details)
        self.error_code = "AML_CHECK_FAILED"


class SanctionsCheckException(ComplianceException):
    """Exception raised when sanctions screening fails"""

    def __init__(self, entity_name: str, details: Optional[Dict[str, Any]] = None):
        message = f"Sanctions check failed for entity: {entity_name}"
        details = details or {}
        details["entity_name"] = entity_name
        super().__init__(message, details=details)
        self.error_code = "SANCTIONS_CHECK_FAILED"


# ============================================================================
# Fraud Detection Exceptions
# ============================================================================

class FraudDetectionException(CAPPException):
    """Base exception for fraud detection errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="FRAUD_DETECTION_ERROR", details=details)


class SuspiciousActivityException(FraudDetectionException):
    """Exception raised when suspicious activity is detected"""

    def __init__(self, fraud_score: float, threshold: float, details: Optional[Dict[str, Any]] = None):
        message = f"Suspicious activity detected: fraud score {fraud_score} exceeds threshold {threshold}"
        details = details or {}
        details.update({"fraud_score": fraud_score, "threshold": threshold})
        super().__init__(message, details=details)
        self.error_code = "SUSPICIOUS_ACTIVITY_DETECTED"


# ============================================================================
# Settlement Exceptions
# ============================================================================

class SettlementException(CAPPException):
    """Base exception for settlement-related errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="SETTLEMENT_ERROR", details=details)


class BlockchainTransactionException(SettlementException):
    """Exception raised when blockchain transaction fails"""

    def __init__(self, message: str, tx_hash: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if tx_hash:
            details["transaction_hash"] = tx_hash
        super().__init__(message, details=details)
        self.error_code = "BLOCKCHAIN_TX_ERROR"


class LiquidityException(SettlementException):
    """Exception raised when there's insufficient liquidity"""

    def __init__(self, currency_pair: str, required: float, available: float):
        message = f"Insufficient liquidity for {currency_pair}: required {required}, available {available}"
        super().__init__(
            message,
            details={"currency_pair": currency_pair, "required": required, "available": available}
        )
        self.error_code = "INSUFFICIENT_LIQUIDITY"


# ============================================================================
# Authentication & Authorization Exceptions
# ============================================================================

class AuthenticationException(CAPPException):
    """Base exception for authentication errors"""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", details=details)


class InvalidCredentialsException(AuthenticationException):
    """Exception raised when credentials are invalid"""

    def __init__(self):
        super().__init__("Invalid email or password")
        self.error_code = "INVALID_CREDENTIALS"


class TokenExpiredException(AuthenticationException):
    """Exception raised when authentication token has expired"""

    def __init__(self):
        super().__init__("Authentication token has expired")
        self.error_code = "TOKEN_EXPIRED"


class InvalidTokenException(AuthenticationException):
    """Exception raised when authentication token is invalid"""

    def __init__(self, reason: Optional[str] = None):
        message = "Invalid authentication token"
        if reason:
            message += f": {reason}"
        super().__init__(message, details={"reason": reason} if reason else None)
        self.error_code = "INVALID_TOKEN"


class AuthorizationException(CAPPException):
    """Exception raised when user lacks required permissions"""

    def __init__(self, message: str = "Insufficient permissions", required_role: Optional[str] = None):
        details = {}
        if required_role:
            details["required_role"] = required_role
        super().__init__(message, error_code="AUTHORIZATION_ERROR", details=details)


# ============================================================================
# Validation Exceptions
# ============================================================================

class ValidationException(CAPPException):
    """Exception raised when data validation fails"""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class InvalidCurrencyException(ValidationException):
    """Exception raised when currency is not supported"""

    def __init__(self, currency: str):
        super().__init__(
            f"Unsupported currency: {currency}",
            field="currency",
            details={"currency": currency}
        )
        self.error_code = "INVALID_CURRENCY"


class InvalidCountryException(ValidationException):
    """Exception raised when country is not supported"""

    def __init__(self, country: str):
        super().__init__(
            f"Unsupported country: {country}",
            field="country",
            details={"country": country}
        )
        self.error_code = "INVALID_COUNTRY"


class InvalidAmountException(ValidationException):
    """Exception raised when payment amount is invalid"""

    def __init__(self, amount: float, reason: str):
        super().__init__(
            f"Invalid amount {amount}: {reason}",
            field="amount",
            details={"amount": amount, "reason": reason}
        )
        self.error_code = "INVALID_AMOUNT"


# ============================================================================
# External Service Exceptions
# ============================================================================

class ExternalServiceException(CAPPException):
    """Base exception for external service errors"""

    def __init__(self, service_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["service"] = service_name
        super().__init__(message, error_code="EXTERNAL_SERVICE_ERROR", details=details)


class MMOIntegrationException(ExternalServiceException):
    """Exception raised when MMO (Mobile Money Operator) integration fails"""

    def __init__(self, mmo_provider: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"MMO_{mmo_provider.upper()}", message, details)
        self.error_code = "MMO_INTEGRATION_ERROR"


class BankIntegrationException(ExternalServiceException):
    """Exception raised when bank integration fails"""

    def __init__(self, bank_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(bank_name, message, details)
        self.error_code = "BANK_INTEGRATION_ERROR"


class ExchangeRateException(ExternalServiceException):
    """Exception raised when exchange rate service fails"""

    def __init__(self, message: str, currency_pair: Optional[str] = None):
        details = {}
        if currency_pair:
            details["currency_pair"] = currency_pair
        super().__init__("EXCHANGE_RATE_SERVICE", message, details)
        self.error_code = "EXCHANGE_RATE_ERROR"


# ============================================================================
# Rate Limiting Exceptions
# ============================================================================

class RateLimitException(CAPPException):
    """Exception raised when rate limit is exceeded"""

    def __init__(self, limit: int, window: str, retry_after: Optional[int] = None):
        message = f"Rate limit exceeded: {limit} requests per {window}"
        details = {"limit": limit, "window": window}
        if retry_after:
            message += f". Retry after {retry_after} seconds"
            details["retry_after"] = retry_after
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", details=details)


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigurationException(CAPPException):
    """Exception raised when configuration is invalid"""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)


class MissingConfigurationException(ConfigurationException):
    """Exception raised when required configuration is missing"""

    def __init__(self, config_key: str):
        super().__init__(
            f"Required configuration missing: {config_key}",
            config_key=config_key
        )
        self.error_code = "MISSING_CONFIGURATION"
