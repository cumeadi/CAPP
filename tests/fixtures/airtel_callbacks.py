"""
Airtel Money Callback Test Fixtures

Provides sample Airtel Money callback data for testing webhook endpoints
and callback processing logic.
"""

from typing import Dict, Any


class AirtelMoneyCallbackFixtures:
    """Collection of Airtel Money callback fixtures for testing"""

    @staticmethod
    def payment_success() -> Dict[str, Any]:
        """Successful payment callback"""
        return {
            "transaction": {
                "id": "airtel_txn_123456789",
                "status": "TS",  # Transaction Successful
                "message": "Transaction processed successfully"
            },
            "data": {
                "transaction": {
                    "id": "merchant_ref_123456",
                    "amount": "1000.00",
                    "currency": "KES",
                    "message": "Payment successful",
                    "status": "TS"
                }
            }
        }

    @staticmethod
    def payment_pending() -> Dict[str, Any]:
        """Pending payment callback"""
        return {
            "transaction": {
                "id": "airtel_txn_123456790",
                "status": "TIP",  # Transaction In Progress
                "message": "Transaction is being processed"
            },
            "data": {
                "transaction": {
                    "id": "merchant_ref_123457",
                    "amount": "1000.00",
                    "currency": "KES",
                    "message": "Payment processing",
                    "status": "TIP"
                }
            }
        }

    @staticmethod
    def payment_failed() -> Dict[str, Any]:
        """Failed payment callback"""
        return {
            "transaction": {
                "id": "airtel_txn_123456791",
                "status": "TF",  # Transaction Failed
                "message": "Transaction failed"
            },
            "data": {
                "transaction": {
                    "id": "merchant_ref_123458",
                    "amount": "1000.00",
                    "currency": "KES",
                    "message": "Payment failed",
                    "status": "TF"
                }
            }
        }

    @staticmethod
    def payment_insufficient_funds() -> Dict[str, Any]:
        """Payment failed - insufficient funds"""
        return {
            "transaction": {
                "id": "airtel_txn_123456792",
                "status": "TF",
                "message": "Insufficient balance in wallet"
            },
            "data": {
                "transaction": {
                    "id": "merchant_ref_123459",
                    "amount": "5000.00",
                    "currency": "KES",
                    "message": "Insufficient funds",
                    "status": "TF"
                }
            }
        }

    @staticmethod
    def disbursement_success() -> Dict[str, Any]:
        """Successful disbursement callback"""
        return {
            "transaction": {
                "id": "airtel_txn_234567890",
                "status": "TS",
                "message": "Disbursement successful"
            },
            "data": {
                "transaction": {
                    "id": "merchant_ref_234567",
                    "amount": "2000.00",
                    "currency": "UGX",
                    "message": "Disbursement processed successfully",
                    "status": "TS",
                    "airtel_money_id": "AM2023123456"
                }
            }
        }

    @staticmethod
    def disbursement_pending() -> Dict[str, Any]:
        """Pending disbursement callback"""
        return {
            "transaction": {
                "id": "airtel_txn_234567891",
                "status": "TIP",
                "message": "Disbursement being processed"
            },
            "data": {
                "transaction": {
                    "id": "merchant_ref_234568",
                    "amount": "2000.00",
                    "currency": "UGX",
                    "message": "Processing disbursement",
                    "status": "TIP"
                }
            }
        }

    @staticmethod
    def disbursement_failed() -> Dict[str, Any]:
        """Failed disbursement callback"""
        return {
            "transaction": {
                "id": "airtel_txn_234567892",
                "status": "TF",
                "message": "Disbursement failed - recipient not found"
            },
            "data": {
                "transaction": {
                    "id": "merchant_ref_234569",
                    "amount": "2000.00",
                    "currency": "UGX",
                    "message": "Disbursement failed",
                    "status": "TF"
                }
            }
        }

    @staticmethod
    def notification_balance_update() -> Dict[str, Any]:
        """Balance update notification"""
        return {
            "type": "BALANCE_UPDATE",
            "id": "notif_345678901",
            "timestamp": "2024-01-15T10:30:00Z",
            "data": {
                "account_id": "merchant_account_123",
                "available_balance": "50000.00",
                "currency": "TZS",
                "previous_balance": "48000.00"
            }
        }

    @staticmethod
    def notification_payment_confirmation() -> Dict[str, Any]:
        """Payment confirmation notification"""
        return {
            "type": "PAYMENT_CONFIRMATION",
            "id": "notif_345678902",
            "timestamp": "2024-01-15T10:35:00Z",
            "data": {
                "transaction_id": "merchant_ref_123456",
                "airtel_transaction_id": "airtel_txn_123456789",
                "amount": "1000.00",
                "currency": "KES",
                "status": "CONFIRMED"
            }
        }

    @staticmethod
    def notification_account_update() -> Dict[str, Any]:
        """Account update notification"""
        return {
            "type": "ACCOUNT_UPDATE",
            "id": "notif_345678903",
            "timestamp": "2024-01-15T10:40:00Z",
            "data": {
                "account_id": "merchant_account_123",
                "update_type": "KYC_VERIFIED",
                "message": "Account KYC verification completed"
            }
        }


# Airtel Money status codes and their meanings
AIRTEL_MONEY_STATUS_CODES = {
    "TS": "Transaction Successful",
    "TIP": "Transaction In Progress",
    "TF": "Transaction Failed"
}

# Airtel Money error codes
AIRTEL_MONEY_ERROR_CODES = {
    "DP00800001005": "Internal Error",
    "DP00800001006": "Transaction Failed",
    "DP00800001007": "Insufficient Balance",
    "DP00800001009": "Invalid MSISDN",
    "DP00800001010": "Subscriber Not Found",
    "DP00800001011": "Transaction Not Permitted",
    "DP00800001012": "Transaction Limit Exceeded",
    "DP00800001013": "Invalid Amount",
    "DP00800001014": "Duplicate Transaction",
    "DP00800001015": "Transaction Timeout",
    "DP00800001016": "Invalid PIN",
    "DP00800001017": "PIN Blocked",
    "DP00800001018": "Account Blocked",
    "DP00800001019": "Service Unavailable",
    "DP00800001020": "Invalid Request",
    "TS0001": "Success",
    "TM0001": "Invalid Signature",
    "TM0002": "Invalid Client ID",
    "TM0003": "Invalid Access Token",
    "TM0004": "Token Expired"
}


def get_status_description(status_code: str) -> str:
    """Get description for Airtel Money status code"""
    return AIRTEL_MONEY_STATUS_CODES.get(status_code, "Unknown status")


def get_error_description(error_code: str) -> str:
    """Get description for Airtel Money error code"""
    return AIRTEL_MONEY_ERROR_CODES.get(error_code, "Unknown error")
