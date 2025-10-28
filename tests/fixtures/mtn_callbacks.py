"""
MTN Mobile Money Callback Test Fixtures

Provides sample MTN MoMo callback data for testing webhook endpoints
and callback processing logic.
"""

from typing import Dict, Any


class MTNMoMoCallbackFixtures:
    """Collection of MTN MoMo callback fixtures for testing"""

    @staticmethod
    def collection_success() -> Dict[str, Any]:
        """Successful Collection (Request to Pay) callback"""
        return {
            "referenceId": "d4e90f52-7e4b-4f4a-9c3a-1234567890ab",
            "externalId": "ext_ref_123456",
            "status": "SUCCESSFUL",
            "amount": "1000.00",
            "currency": "UGX",
            "financialTransactionId": "12345678",
            "reason": "",
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": "256774123456"
            },
            "payerMessage": "Payment for order #12345",
            "payeeNote": "Thank you for your payment"
        }

    @staticmethod
    def collection_pending() -> Dict[str, Any]:
        """Pending Collection callback"""
        return {
            "referenceId": "d4e90f52-7e4b-4f4a-9c3a-1234567890ab",
            "externalId": "ext_ref_123456",
            "status": "PENDING",
            "amount": "1000.00",
            "currency": "UGX",
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": "256774123456"
            }
        }

    @staticmethod
    def collection_failed() -> Dict[str, Any]:
        """Failed Collection callback"""
        return {
            "referenceId": "d4e90f52-7e4b-4f4a-9c3a-1234567890ac",
            "externalId": "ext_ref_123457",
            "status": "FAILED",
            "amount": "1000.00",
            "currency": "UGX",
            "reason": "PAYER_NOT_FOUND",
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": "256774999999"
            },
            "payerMessage": "Payment for order #12346",
            "payeeNote": "Payment failed"
        }

    @staticmethod
    def collection_insufficient_funds() -> Dict[str, Any]:
        """Collection failed - insufficient funds"""
        return {
            "referenceId": "d4e90f52-7e4b-4f4a-9c3a-1234567890ad",
            "externalId": "ext_ref_123458",
            "status": "FAILED",
            "amount": "5000.00",
            "currency": "UGX",
            "reason": "INSUFFICIENT_BALANCE",
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": "256774123456"
            }
        }

    @staticmethod
    def disbursement_success() -> Dict[str, Any]:
        """Successful Disbursement (Transfer) callback"""
        return {
            "referenceId": "e5f91f63-8e5c-5g5b-0d4b-2345678901bc",
            "externalId": "ext_ref_234567",
            "status": "SUCCESSFUL",
            "amount": "2000.00",
            "currency": "UGX",
            "financialTransactionId": "87654321",
            "reason": "",
            "payee": {
                "partyIdType": "MSISDN",
                "partyId": "256774123456"
            },
            "payerMessage": "Disbursement payment",
            "payeeNote": "Your payout has been processed"
        }

    @staticmethod
    def disbursement_pending() -> Dict[str, Any]:
        """Pending Disbursement callback"""
        return {
            "referenceId": "e5f91f63-8e5c-5g5b-0d4b-2345678901bc",
            "externalId": "ext_ref_234567",
            "status": "PENDING",
            "amount": "2000.00",
            "currency": "UGX",
            "payee": {
                "partyIdType": "MSISDN",
                "partyId": "256774123456"
            }
        }

    @staticmethod
    def disbursement_failed() -> Dict[str, Any]:
        """Failed Disbursement callback"""
        return {
            "referenceId": "e5f91f63-8e5c-5g5b-0d4b-2345678901bd",
            "externalId": "ext_ref_234568",
            "status": "FAILED",
            "amount": "2000.00",
            "currency": "UGX",
            "reason": "PAYEE_NOT_FOUND",
            "payee": {
                "partyIdType": "MSISDN",
                "partyId": "256774999999"
            }
        }

    @staticmethod
    def remittance_success() -> Dict[str, Any]:
        """Successful Remittance callback"""
        return {
            "referenceId": "f6g02g74-9f6d-6h6c-1e5c-3456789012cd",
            "externalId": "ext_ref_345678",
            "status": "SUCCESSFUL",
            "amount": "3000.00",
            "currency": "EUR",
            "financialTransactionId": "11223344",
            "reason": "",
            "payee": {
                "partyIdType": "MSISDN",
                "partyId": "256774123456"
            },
            "payerMessage": "International remittance",
            "payeeNote": "Remittance payment received"
        }

    @staticmethod
    def remittance_failed() -> Dict[str, Any]:
        """Failed Remittance callback"""
        return {
            "referenceId": "f6g02g74-9f6d-6h6c-1e5c-3456789012ce",
            "externalId": "ext_ref_345679",
            "status": "FAILED",
            "amount": "3000.00",
            "currency": "EUR",
            "reason": "NOT_ALLOWED",
            "payee": {
                "partyIdType": "MSISDN",
                "partyId": "256774123456"
            }
        }


# MTN MoMo status codes and their meanings
MTN_MOMO_STATUS_CODES = {
    "PENDING": "Transaction is pending",
    "SUCCESSFUL": "Transaction completed successfully",
    "FAILED": "Transaction failed"
}

# MTN MoMo error reasons
MTN_MOMO_ERROR_REASONS = {
    "PAYER_NOT_FOUND": "Payer account not found",
    "PAYEE_NOT_FOUND": "Payee account not found",
    "NOT_ALLOWED": "Transaction not allowed",
    "NOT_ALLOWED_TARGET_ENVIRONMENT": "Not allowed in target environment",
    "INVALID_CALLBACK_URL_HOST": "Invalid callback URL host",
    "INVALID_CURRENCY": "Invalid currency",
    "SERVICE_UNAVAILABLE": "Service temporarily unavailable",
    "INTERNAL_PROCESSING_ERROR": "Internal processing error",
    "NOT_ENOUGH_FUNDS": "Insufficient funds",
    "PAYER_LIMIT_REACHED": "Payer transaction limit reached",
    "PAYEE_NOT_ALLOWED_TO_RECEIVE": "Payee not allowed to receive payments",
    "PAYMENT_NOT_APPROVED": "Payment not approved by payer",
    "RESOURCE_NOT_FOUND": "Resource not found",
    "APPROVAL_REJECTED": "Payment approval rejected",
    "EXPIRED": "Transaction expired",
    "TRANSACTION_CANCELLED": "Transaction cancelled",
    "RESOURCE_ALREADY_EXIST": "Resource already exists"
}


def get_status_description(status_code: str) -> str:
    """Get description for MTN MoMo status code"""
    return MTN_MOMO_STATUS_CODES.get(status_code, "Unknown status")


def get_error_description(reason: str) -> str:
    """Get description for MTN MoMo error reason"""
    return MTN_MOMO_ERROR_REASONS.get(reason, "Unknown error")
