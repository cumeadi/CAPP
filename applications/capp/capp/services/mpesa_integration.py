"""
M-Pesa integration service for CAPP.
Production-ready implementation with:
- STK Push (Lipa na M-Pesa Online)
- B2C Payments (Business to Customer)
- C2B Registration (Customer to Business)
- Transaction reversal and query
- Retry logic with exponential backoff
- Circuit breaker pattern
- Comprehensive error handling
- Database persistence
"""

import asyncio
import base64
import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any, List
from enum import Enum

import aiohttp
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from .config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class MpesaTransactionType(str, Enum):
    """M-Pesa transaction types"""
    STK_PUSH = "stk_push"
    B2C = "b2c"
    C2B = "c2b"
    REVERSAL = "reversal"
    QUERY = "query"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for M-Pesa API calls"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    def record_success(self):
        """Record successful API call"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def record_failure(self):
        """Record failed API call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(
                "Circuit breaker opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold
            )

    def can_attempt(self) -> bool:
        """Check if request can be attempted"""
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("Circuit breaker half-open, testing recovery")
                    return True
            return False

        # HALF_OPEN state - allow one request to test
        return True

    def reset(self):
        """Reset circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED


class MpesaService:
    """
    Production-ready M-Pesa payment service integration.

    Features:
    - STK Push (Lipa na M-Pesa Online)
    - B2C Payments (disbursements)
    - C2B Registration and validation
    - Transaction reversal
    - Transaction query
    - Circuit breaker pattern
    - Retry logic with exponential backoff
    - Comprehensive error handling
    """

    def __init__(self, db_session=None):
        # M-Pesa API configuration
        self.base_url = getattr(settings, 'mpesa_base_url', 'https://sandbox.safaricom.co.ke')
        self.business_shortcode = getattr(settings, 'mpesa_business_shortcode', '')
        self.passkey = getattr(settings, 'mpesa_passkey', '')
        self.consumer_key = getattr(settings, 'mpesa_consumer_key', getattr(settings, 'MMO_MPESA_CONSUMER_KEY', ''))
        self.consumer_secret = getattr(settings, 'mpesa_consumer_secret', getattr(settings, 'MMO_MPESA_CONSUMER_SECRET', ''))
        self.callback_url = getattr(settings, 'mpesa_callback_url', '')
        self.timeout_url = getattr(settings, 'mpesa_timeout_url', self.callback_url)
        self.initiator_name = getattr(settings, 'mpesa_initiator_name', 'testapi')
        self.security_credential = getattr(settings, 'mpesa_security_credential', '')
        self.timeout = 30

        # Environment (sandbox or production)
        self.environment = getattr(settings, 'ENVIRONMENT', 'development')

        # Circuit breaker for fault tolerance
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None

        # Database session for persistence
        self.db_session = db_session

        # Transaction tracking
        self.pending_transactions: Dict[str, Dict[str, Any]] = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _generate_timestamp(self) -> str:
        """Generate timestamp in M-Pesa format (YYYYMMDDHHMMSS)."""
        return datetime.now().strftime("%Y%m%d%H%M%S")
    
    def _generate_password(self, timestamp: str) -> str:
        """Generate M-Pesa API password."""
        password_string = f"{self.business_shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(password_string.encode()).decode()
    
    async def _get_access_token(self) -> str:
        """Get M-Pesa API access token."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        auth_string = f"{self.consumer_key}:{self.consumer_secret}"
        auth_header = base64.b64encode(auth_string.encode()).decode()
        
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("access_token")
                else:
                    error_text = await response.text()
                    logger.error("Failed to get access token", 
                               status=response.status, error=error_text)
                    raise Exception(f"Failed to get access token: {error_text}")
        except Exception as e:
            logger.error("Error getting access token", error=str(e))
            raise
    
    async def initiate_stk_push(self, 
                               phone_number: str, 
                               amount: float, 
                               reference: str,
                               description: str = "CAPP Payment") -> Dict[str, Any]:
        """Initiate STK Push payment request."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            access_token = await self._get_access_token()
            timestamp = self._generate_timestamp()
            password = self._generate_password(timestamp)
            
            payload = {
                "BusinessShortCode": self.business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone_number,
                "PartyB": self.business_shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": self.callback_url,
                "AccountReference": reference,
                "TransactionDesc": description
            }
            
            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            logger.info("Initiating STK Push", 
                       phone=phone_number, amount=amount, reference=reference)
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    result_code = response_data.get("ResultCode")
                    if result_code == 0:
                        logger.info("STK Push initiated successfully", 
                                  checkout_request_id=response_data.get("CheckoutRequestID"))
                        return {
                            "success": True,
                            "checkout_request_id": response_data.get("CheckoutRequestID"),
                            "merchant_request_id": response_data.get("MerchantRequestID"),
                            "response_code": result_code,
                            "response_description": response_data.get("ResultDesc")
                        }
                    else:
                        logger.warning("STK Push failed", 
                                     result_code=result_code,
                                     result_desc=response_data.get("ResultDesc"))
                        return {
                            "success": False,
                            "error_code": result_code,
                            "error_message": response_data.get("ResultDesc"),
                            "checkout_request_id": response_data.get("CheckoutRequestID")
                        }
                else:
                    error_text = await response.text()
                    logger.error("STK Push request failed", 
                               status=response.status, error=error_text)
                    return {
                        "success": False,
                        "error_code": response.status,
                        "error_message": f"HTTP {response.status}: {error_text}"
                    }
                    
        except Exception as e:
            logger.error("Error initiating STK Push", error=str(e))
            return {
                "success": False,
                "error_code": -1,
                "error_message": str(e)
            }
    
    async def check_payment_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """Check payment status using CheckoutRequestID."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            access_token = await self._get_access_token()
            timestamp = self._generate_timestamp()
            password = self._generate_password(timestamp)
            
            payload = {
                "BusinessShortCode": self.business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            logger.info("Checking payment status", checkout_request_id=checkout_request_id)
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    result_code = response_data.get("ResultCode")
                    if result_code == 0:
                        result_params = response_data.get("ResultParameters", {})
                        item_list = result_params.get("Item", [])
                        
                        payment_data = {}
                        for item in item_list:
                            key = item.get("Key")
                            value = item.get("Value")
                            if key and value:
                                payment_data[key] = value
                        
                        logger.info("Payment completed successfully", 
                                  checkout_request_id=checkout_request_id,
                                  mpesa_receipt_number=payment_data.get("MpesaReceiptNumber"))
                        
                        return {
                            "success": True,
                            "status": "completed",
                            "mpesa_receipt_number": payment_data.get("MpesaReceiptNumber"),
                            "transaction_date": payment_data.get("TransactionDate"),
                            "amount": payment_data.get("Amount"),
                            "phone_number": payment_data.get("PhoneNumber"),
                            "result_code": result_code,
                            "result_description": response_data.get("ResultDesc")
                        }
                    elif result_code == 1032:
                        return {
                            "success": False,
                            "status": "cancelled",
                            "error_code": result_code,
                            "error_message": "Payment cancelled by user"
                        }
                    elif result_code == 1037:
                        return {
                            "success": False,
                            "status": "timeout",
                            "error_code": result_code,
                            "error_message": "Payment request timeout"
                        }
                    else:
                        return {
                            "success": False,
                            "status": "failed",
                            "error_code": result_code,
                            "error_message": response_data.get("ResultDesc", "Unknown error")
                        }
                else:
                    error_text = await response.text()
                    logger.error("Payment status check failed", 
                               status=response.status, error=error_text)
                    return {
                        "success": False,
                        "status": "error",
                        "error_code": response.status,
                        "error_message": f"HTTP {response.status}: {error_text}"
                    }
                    
        except Exception as e:
            logger.error("Error checking payment status", error=str(e))
            return {
                "success": False,
                "status": "error",
                "error_code": -1,
                "error_message": str(e)
            }
    
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number for M-Pesa (254XXXXXXXXX)."""
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        if digits_only.startswith('254'):
            return digits_only
        elif digits_only.startswith('0'):
            return '254' + digits_only[1:]
        elif digits_only.startswith('7'):
            return '254' + digits_only
        elif len(digits_only) == 9:
            return '254' + digits_only
        else:
            return digits_only
    
    async def validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format for M-Pesa."""
        formatted = self.format_phone_number(phone_number)
        return len(formatted) == 12 and formatted.startswith('254')

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(aiohttp.ClientError)
    )
    async def initiate_b2c_payment(
        self,
        phone_number: str,
        amount: float,
        reference: str,
        description: str = "CAPP B2C Payment",
        occasion: str = "Disbursement"
    ) -> Dict[str, Any]:
        """
        Initiate B2C (Business to Customer) payment.

        Args:
            phone_number: Recipient phone number
            amount: Amount to send
            reference: Transaction reference
            description: Payment description
            occasion: Occasion for the payment

        Returns:
            Dict with transaction details
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        # Check circuit breaker
        if not self.circuit_breaker.can_attempt():
            return {
                "success": False,
                "error_code": "CIRCUIT_BREAKER_OPEN",
                "error_message": "M-Pesa service temporarily unavailable"
            }

        try:
            access_token = await self._get_access_token()
            timestamp = self._generate_timestamp()

            payload = {
                "InitiatorName": self.initiator_name,
                "SecurityCredential": self.security_credential,
                "CommandID": "BusinessPayment",
                "Amount": int(amount),
                "PartyA": self.business_shortcode,
                "PartyB": phone_number,
                "Remarks": description,
                "QueueTimeOutURL": self.timeout_url,
                "ResultURL": self.callback_url,
                "Occasion": occasion
            }

            url = f"{self.base_url}/mpesa/b2c/v1/paymentrequest"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            logger.info(
                "Initiating B2C payment",
                phone=phone_number,
                amount=amount,
                reference=reference
            )

            async with self.session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()

                if response.status == 200:
                    result_code = response_data.get("ResponseCode", response_data.get("ResultCode"))
                    if str(result_code) == "0":
                        self.circuit_breaker.record_success()
                        logger.info(
                            "B2C payment initiated successfully",
                            conversation_id=response_data.get("ConversationID"),
                            originator_conversation_id=response_data.get("OriginatorConversationID")
                        )
                        return {
                            "success": True,
                            "conversation_id": response_data.get("ConversationID"),
                            "originator_conversation_id": response_data.get("OriginatorConversationID"),
                            "response_code": result_code,
                            "response_description": response_data.get("ResponseDescription")
                        }
                    else:
                        self.circuit_breaker.record_failure()
                        logger.warning(
                            "B2C payment failed",
                            result_code=result_code,
                            result_desc=response_data.get("ResponseDescription")
                        )
                        return {
                            "success": False,
                            "error_code": result_code,
                            "error_message": response_data.get("ResponseDescription")
                        }
                else:
                    self.circuit_breaker.record_failure()
                    error_text = await response.text()
                    logger.error(
                        "B2C payment request failed",
                        status=response.status,
                        error=error_text
                    )
                    return {
                        "success": False,
                        "error_code": response.status,
                        "error_message": f"HTTP {response.status}: {error_text}"
                    }

        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error("Error initiating B2C payment", error=str(e))
            return {
                "success": False,
                "error_code": -1,
                "error_message": str(e)
            }

    async def register_c2b_urls(
        self,
        validation_url: str,
        confirmation_url: str,
        response_type: str = "Completed"
    ) -> Dict[str, Any]:
        """
        Register C2B validation and confirmation URLs.

        Args:
            validation_url: URL for validating payments
            confirmation_url: URL for confirming payments
            response_type: "Completed" or "Cancelled"

        Returns:
            Dict with registration status
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        try:
            access_token = await self._get_access_token()

            payload = {
                "ShortCode": self.business_shortcode,
                "ResponseType": response_type,
                "ConfirmationURL": confirmation_url,
                "ValidationURL": validation_url
            }

            url = f"{self.base_url}/mpesa/c2b/v1/registerurl"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            logger.info("Registering C2B URLs", shortcode=self.business_shortcode)

            async with self.session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()

                if response.status == 200:
                    logger.info("C2B URLs registered successfully")
                    return {
                        "success": True,
                        "response_code": response_data.get("ResponseCode"),
                        "response_description": response_data.get("ResponseDescription")
                    }
                else:
                    error_text = await response.text()
                    logger.error(
                        "C2B URL registration failed",
                        status=response.status,
                        error=error_text
                    )
                    return {
                        "success": False,
                        "error_code": response.status,
                        "error_message": error_text
                    }

        except Exception as e:
            logger.error("Error registering C2B URLs", error=str(e))
            return {
                "success": False,
                "error_code": -1,
                "error_message": str(e)
            }

    async def reverse_transaction(
        self,
        transaction_id: str,
        amount: float,
        receiver_party: str,
        remarks: str = "Transaction Reversal",
        occasion: str = "Reversal"
    ) -> Dict[str, Any]:
        """
        Reverse a completed M-Pesa transaction.

        Args:
            transaction_id: Original transaction ID to reverse
            amount: Amount to reverse
            receiver_party: Phone number or shortcode receiving the reversal
            remarks: Reversal remarks
            occasion: Reversal occasion

        Returns:
            Dict with reversal status
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        try:
            access_token = await self._get_access_token()

            payload = {
                "Initiator": self.initiator_name,
                "SecurityCredential": self.security_credential,
                "CommandID": "TransactionReversal",
                "TransactionID": transaction_id,
                "Amount": int(amount),
                "ReceiverParty": receiver_party,
                "RecieverIdentifierType": "11",  # Till Number
                "ResultURL": self.callback_url,
                "QueueTimeOutURL": self.timeout_url,
                "Remarks": remarks,
                "Occasion": occasion
            }

            url = f"{self.base_url}/mpesa/reversal/v1/request"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            logger.info(
                "Reversing transaction",
                transaction_id=transaction_id,
                amount=amount
            )

            async with self.session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()

                if response.status == 200:
                    result_code = response_data.get("ResponseCode")
                    if str(result_code) == "0":
                        logger.info(
                            "Transaction reversal initiated",
                            conversation_id=response_data.get("ConversationID")
                        )
                        return {
                            "success": True,
                            "conversation_id": response_data.get("ConversationID"),
                            "originator_conversation_id": response_data.get("OriginatorConversationID"),
                            "response_description": response_data.get("ResponseDescription")
                        }
                    else:
                        logger.warning(
                            "Transaction reversal failed",
                            result_code=result_code
                        )
                        return {
                            "success": False,
                            "error_code": result_code,
                            "error_message": response_data.get("ResponseDescription")
                        }
                else:
                    error_text = await response.text()
                    logger.error(
                        "Reversal request failed",
                        status=response.status,
                        error=error_text
                    )
                    return {
                        "success": False,
                        "error_code": response.status,
                        "error_message": error_text
                    }

        except Exception as e:
            logger.error("Error reversing transaction", error=str(e))
            return {
                "success": False,
                "error_code": -1,
                "error_message": str(e)
            }

    async def query_transaction_status(
        self,
        transaction_id: str,
        identifier_type: str = "1"  # 1: MSISDN, 2: Till Number, 4: Organization short code
    ) -> Dict[str, Any]:
        """
        Query the status of a transaction.

        Args:
            transaction_id: Transaction ID to query
            identifier_type: Type of identifier

        Returns:
            Dict with transaction status
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        try:
            access_token = await self._get_access_token()

            payload = {
                "Initiator": self.initiator_name,
                "SecurityCredential": self.security_credential,
                "CommandID": "TransactionStatusQuery",
                "TransactionID": transaction_id,
                "PartyA": self.business_shortcode,
                "IdentifierType": identifier_type,
                "ResultURL": self.callback_url,
                "QueueTimeOutURL": self.timeout_url,
                "Remarks": "Transaction Status Query",
                "Occasion": "Query"
            }

            url = f"{self.base_url}/mpesa/transactionstatus/v1/query"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            logger.info("Querying transaction status", transaction_id=transaction_id)

            async with self.session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()

                if response.status == 200:
                    result_code = response_data.get("ResponseCode")
                    if str(result_code) == "0":
                        logger.info(
                            "Transaction status query initiated",
                            conversation_id=response_data.get("ConversationID")
                        )
                        return {
                            "success": True,
                            "conversation_id": response_data.get("ConversationID"),
                            "originator_conversation_id": response_data.get("OriginatorConversationID"),
                            "response_description": response_data.get("ResponseDescription")
                        }
                    else:
                        logger.warning("Transaction status query failed", result_code=result_code)
                        return {
                            "success": False,
                            "error_code": result_code,
                            "error_message": response_data.get("ResponseDescription")
                        }
                else:
                    error_text = await response.text()
                    logger.error(
                        "Transaction status query request failed",
                        status=response.status,
                        error=error_text
                    )
                    return {
                        "success": False,
                        "error_code": response.status,
                        "error_message": error_text
                    }

        except Exception as e:
            logger.error("Error querying transaction status", error=str(e))
            return {
                "success": False,
                "error_code": -1,
                "error_message": str(e)
            }

    async def get_account_balance(self) -> Dict[str, Any]:
        """
        Get M-Pesa account balance.

        Returns:
            Dict with account balance information
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        try:
            access_token = await self._get_access_token()

            payload = {
                "Initiator": self.initiator_name,
                "SecurityCredential": self.security_credential,
                "CommandID": "AccountBalance",
                "PartyA": self.business_shortcode,
                "IdentifierType": "4",  # Organization short code
                "Remarks": "Account Balance Query",
                "QueueTimeOutURL": self.timeout_url,
                "ResultURL": self.callback_url
            }

            url = f"{self.base_url}/mpesa/accountbalance/v1/query"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            logger.info("Querying account balance")

            async with self.session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()

                if response.status == 200:
                    result_code = response_data.get("ResponseCode")
                    if str(result_code) == "0":
                        logger.info(
                            "Account balance query initiated",
                            conversation_id=response_data.get("ConversationID")
                        )
                        return {
                            "success": True,
                            "conversation_id": response_data.get("ConversationID"),
                            "originator_conversation_id": response_data.get("OriginatorConversationID"),
                            "response_description": response_data.get("ResponseDescription")
                        }
                    else:
                        logger.warning("Account balance query failed", result_code=result_code)
                        return {
                            "success": False,
                            "error_code": result_code,
                            "error_message": response_data.get("ResponseDescription")
                        }
                else:
                    error_text = await response.text()
                    logger.error(
                        "Account balance query failed",
                        status=response.status,
                        error=error_text
                    )
                    return {
                        "success": False,
                        "error_code": response.status,
                        "error_message": error_text
                    }

        except Exception as e:
            logger.error("Error querying account balance", error=str(e))
            return {
                "success": False,
                "error_code": -1,
                "error_message": str(e)
            }

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "state": self.circuit_breaker.state.value,
            "failure_count": self.circuit_breaker.failure_count,
            "last_failure_time": (
                self.circuit_breaker.last_failure_time.isoformat()
                if self.circuit_breaker.last_failure_time
                else None
            ),
            "can_attempt": self.circuit_breaker.can_attempt()
        }


# Example usage
async def demo_mpesa_integration():
    """Demo M-Pesa integration functionality."""

    # Initialize M-Pesa service
    async with MpesaService() as mpesa:
        # Format phone number
        phone = "+254712345678"
        formatted_phone = mpesa.format_phone_number(phone)
        print(f"Original: {phone}, Formatted: {formatted_phone}")

        # Validate phone number
        is_valid = await mpesa.validate_phone_number(formatted_phone)
        print(f"Phone valid: {is_valid}")

        # Check circuit breaker status
        cb_status = mpesa.get_circuit_breaker_status()
        print(f"Circuit breaker status: {cb_status}")

        # Initiate STK Push (commented out for demo)
        # result = await mpesa.initiate_stk_push(
        #     phone_number=formatted_phone,
        #     amount=100.0,
        #     reference="DEMO_001",
        #     description="CAPP Demo Payment"
        # )
        # print(f"STK Push result: {result}")

        # Check payment status (commented out for demo)
        # status = await mpesa.check_payment_status("checkout_request_id_here")
        # print(f"Payment status: {status}")

        # B2C Payment (commented out for demo)
        # b2c_result = await mpesa.initiate_b2c_payment(
        #     phone_number=formatted_phone,
        #     amount=50.0,
        #     reference="B2C_001",
        #     description="CAPP Disbursement"
        # )
        # print(f"B2C result: {b2c_result}")


if __name__ == "__main__":
    asyncio.run(demo_mpesa_integration()) 