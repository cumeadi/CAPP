"""
M-Pesa Callback Test Fixtures

Provides sample M-Pesa callback data for testing webhook endpoints
and callback processing logic.
"""

from datetime import datetime
from typing import Dict, Any


class MpesaCallbackFixtures:
    """Collection of M-Pesa callback fixtures for testing"""

    @staticmethod
    def stk_push_success() -> Dict[str, Any]:
        """Successful STK Push callback"""
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": "ws_CO_191220191020363925",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 1000.00},
                            {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
                            {"Name": "TransactionDate", "Value": 20191219102115},
                            {"Name": "PhoneNumber", "Value": 254708374149}
                        ]
                    }
                }
            }
        }

    @staticmethod
    def stk_push_user_cancelled() -> Dict[str, Any]:
        """STK Push cancelled by user"""
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-2",
                    "CheckoutRequestID": "ws_CO_191220191020363926",
                    "ResultCode": 1032,
                    "ResultDesc": "Request cancelled by user"
                }
            }
        }

    @staticmethod
    def stk_push_insufficient_funds() -> Dict[str, Any]:
        """STK Push failed - insufficient funds"""
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-3",
                    "CheckoutRequestID": "ws_CO_191220191020363927",
                    "ResultCode": 1,
                    "ResultDesc": "The balance is insufficient for the transaction"
                }
            }
        }

    @staticmethod
    def stk_push_invalid_phone() -> Dict[str, Any]:
        """STK Push failed - invalid phone number"""
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-4",
                    "CheckoutRequestID": "ws_CO_191220191020363928",
                    "ResultCode": 1019,
                    "ResultDesc": "Invalid phone number"
                }
            }
        }

    @staticmethod
    def stk_push_timeout() -> Dict[str, Any]:
        """STK Push timeout"""
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-5",
                    "CheckoutRequestID": "ws_CO_191220191020363929",
                    "ResultCode": 1,
                    "ResultDesc": "Request timeout"
                }
            }
        }

    @staticmethod
    def b2c_success() -> Dict[str, Any]:
        """Successful B2C transaction"""
        return {
            "Result": {
                "ResultType": 0,
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "OriginatorConversationID": "10571-7910404-1",
                "ConversationID": "AG_20191219_00004e48cf7e3533f581",
                "TransactionID": "NLJ41HAY6Q",
                "ResultParameters": {
                    "ResultParameter": [
                        {"Key": "TransactionAmount", "Value": "5000.00"},
                        {"Key": "TransactionReceipt", "Value": "NLJ41HAY6Q"},
                        {"Key": "ReceiverPartyPublicName", "Value": "254708374149 - John Doe"},
                        {"Key": "TransactionCompletedDateTime", "Value": "19.12.2019 11:45:50"},
                        {"Key": "B2CUtilityAccountAvailableFunds", "Value": "10000.00"},
                        {"Key": "B2CWorkingAccountAvailableFunds", "Value": "900000.00"},
                        {"Key": "B2CRecipientIsRegisteredCustomer", "Value": "Y"}
                    ]
                },
                "ReferenceData": {
                    "ReferenceItem": {
                        "Key": "QueueTimeoutURL",
                        "Value": "https://internalsandbox.safaricom.co.ke/mpesa/b2cresults/v1/submit"
                    }
                }
            }
        }

    @staticmethod
    def b2c_failed_insufficient_funds() -> Dict[str, Any]:
        """B2C failed - insufficient funds"""
        return {
            "Result": {
                "ResultType": 0,
                "ResultCode": 1,
                "ResultDesc": "Insufficient funds in B2C account",
                "OriginatorConversationID": "10571-7910404-2",
                "ConversationID": "AG_20191219_00004e48cf7e3533f582",
                "TransactionID": ""
            }
        }

    @staticmethod
    def b2c_invalid_receiver() -> Dict[str, Any]:
        """B2C failed - invalid receiver"""
        return {
            "Result": {
                "ResultType": 0,
                "ResultCode": 1019,
                "ResultDesc": "Invalid receiver phone number",
                "OriginatorConversationID": "10571-7910404-3",
                "ConversationID": "AG_20191219_00004e48cf7e3533f583",
                "TransactionID": ""
            }
        }

    @staticmethod
    def c2b_confirmation() -> Dict[str, Any]:
        """C2B confirmation callback"""
        return {
            "TransactionType": "Pay Bill",
            "TransID": "NLJ41HAY6Q",
            "TransTime": "20191219104905",
            "TransAmount": "1500.00",
            "BusinessShortCode": "600000",
            "BillRefNumber": "account123",
            "InvoiceNumber": "",
            "OrgAccountBalance": "49001.00",
            "ThirdPartyTransID": "",
            "MSISDN": "254708374149",
            "FirstName": "John",
            "MiddleName": "",
            "LastName": "Doe"
        }

    @staticmethod
    def c2b_validation() -> Dict[str, Any]:
        """C2B validation request"""
        return {
            "TransactionType": "Pay Bill",
            "TransID": "NLJ51HAY7R",
            "TransTime": "20191219105015",
            "TransAmount": "2000.00",
            "BusinessShortCode": "600000",
            "BillRefNumber": "account456",
            "InvoiceNumber": "",
            "OrgAccountBalance": "51001.00",
            "ThirdPartyTransID": "",
            "MSISDN": "254708374150",
            "FirstName": "Jane",
            "MiddleName": "",
            "LastName": "Smith"
        }

    @staticmethod
    def account_balance_success() -> Dict[str, Any]:
        """Successful account balance query"""
        return {
            "Result": {
                "ResultType": 0,
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "OriginatorConversationID": "10571-7910404-4",
                "ConversationID": "AG_20191219_00004e48cf7e3533f584",
                "TransactionID": "NLJ61HAY8S",
                "ResultParameters": {
                    "ResultParameter": [
                        {
                            "Key": "AccountBalance",
                            "Value": "Working Account|KES|500000.00|500000.00|0.00|0.00&Utility Account|KES|50000.00|50000.00|0.00|0.00"
                        },
                        {"Key": "BOCompletedTime", "Value": "20191219115045"}
                    ]
                }
            }
        }

    @staticmethod
    def transaction_status_success() -> Dict[str, Any]:
        """Successful transaction status query"""
        return {
            "Result": {
                "ResultType": 0,
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "OriginatorConversationID": "10571-7910404-5",
                "ConversationID": "AG_20191219_00004e48cf7e3533f585",
                "TransactionID": "NLJ41HAY6Q",
                "ResultParameters": {
                    "ResultParameter": [
                        {"Key": "ReceiptNo", "Value": "NLJ41HAY6Q"},
                        {"Key": "Conversation ID", "Value": "AG_20191219_00004e48cf7e3533f581"},
                        {"Key": "FinalisedTime", "Value": 20191219115045},
                        {"Key": "Amount", "Value": 5000.00},
                        {"Key": "TransactionStatus", "Value": "Completed"},
                        {"Key": "ReasonType", "Value": "Salary Payment"},
                        {"Key": "TransactionReason", "Value": "Monthly salary"},
                        {"Key": "DebitPartyCharges", "Value": ""},
                        {"Key": "DebitAccountType", "Value": "Utility Account"},
                        {"Key": "InitiatedTime", "Value": 20191219114530},
                        {"Key": "OriginatorConversationID", "Value": "10571-7910404-1"},
                        {"Key": "CreditPartyName", "Value": "254708374149 - John Doe"},
                        {"Key": "DebitPartyName", "Value": "600000 - TestOrg"}
                    ]
                }
            }
        }

    @staticmethod
    def transaction_status_not_found() -> Dict[str, Any]:
        """Transaction not found"""
        return {
            "Result": {
                "ResultType": 0,
                "ResultCode": 1,
                "ResultDesc": "Transaction not found",
                "OriginatorConversationID": "10571-7910404-6",
                "ConversationID": "AG_20191219_00004e48cf7e3533f586",
                "TransactionID": ""
            }
        }

    @staticmethod
    def reversal_success() -> Dict[str, Any]:
        """Successful transaction reversal"""
        return {
            "Result": {
                "ResultType": 0,
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "OriginatorConversationID": "10571-7910404-7",
                "ConversationID": "AG_20191219_00004e48cf7e3533f587",
                "TransactionID": "NLJ71HAY9T"
            }
        }

    @staticmethod
    def reversal_failed() -> Dict[str, Any]:
        """Failed transaction reversal"""
        return {
            "Result": {
                "ResultType": 0,
                "ResultCode": 1,
                "ResultDesc": "Transaction cannot be reversed",
                "OriginatorConversationID": "10571-7910404-8",
                "ConversationID": "AG_20191219_00004e48cf7e3533f588",
                "TransactionID": ""
            }
        }


# Result codes and their meanings
MPESA_RESULT_CODES = {
    0: "Success",
    1: "Insufficient Funds",
    2: "Less Than Minimum Transaction Value",
    3: "More Than Maximum Transaction Value",
    4: "Would Exceed Daily Transfer Limit",
    5: "Would Exceed Minimum Balance",
    6: "Unresolved Primary Party",
    7: "Unresolved Receiver Party",
    8: "Would Exceed Maxiumum Balance",
    11: "Debit Account Invalid",
    12: "Credit Account Invalid",
    13: "Unresolved Debit Account",
    14: "Unresolved Credit Account",
    15: "Duplicate Detected",
    17: "Internal Failure",
    20: "Unresolved Initiator",
    26: "Traffic blocking condition in place",
    1001: "Invalid Amount",
    1019: "Invalid Phone Number",
    1032: "Cancelled by User",
    1037: "Request Timeout",
    2001: "Invalid API Credentials"
}


def get_result_description(result_code: int) -> str:
    """Get description for M-Pesa result code"""
    return MPESA_RESULT_CODES.get(result_code, "Unknown Error")
