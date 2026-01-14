"""
M-Pesa integration service for CAPP.
Handles STK Push, payment status checking, and webhook processing.
"""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from urllib.parse import urlencode

import aiohttp
import structlog
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .config.settings import get_settings
from .core.database import PaymentRepository, UserRepository
from capp.models.payments import PaymentStatus

logger = structlog.get_logger(__name__)
settings = get_settings()


class MpesaService:
    """M-Pesa payment service integration."""
    
    def __init__(self):
        self.base_url = settings.mpesa_base_url
        self.business_shortcode = settings.mpesa_business_shortcode
        self.passkey = settings.mpesa_passkey
        self.consumer_key = settings.mpesa_consumer_key
        self.consumer_secret = settings.mpesa_consumer_secret
        self.callback_url = settings.mpesa_callback_url
        self.timeout = 30
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
    
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
        # Combine business shortcode, passkey, and timestamp
        password_string = f"{self.business_shortcode}{self.passkey}{timestamp}"
        
        # Encode to base64
        import base64
        return base64.b64encode(password_string.encode()).decode()
    
    async def _get_access_token(self) -> str:
        """Get M-Pesa API access token."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        # Create auth header
        auth_string = f"{self.consumer_key}:{self.consumer_secret}"
        import base64
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
        """
        Initiate STK Push payment request.
        
        Args:
            phone_number: Customer phone number (254XXXXXXXXX format)
            amount: Payment amount
            reference: Payment reference ID
            description: Payment description
            
        Returns:
            Dict containing CheckoutRequestID and other response data
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            # Get access token
            access_token = await self._get_access_token()
            
            # Generate timestamp and password
            timestamp = self._generate_timestamp()
            password = self._generate_password(timestamp)
            
            # Prepare request data
            payload = {
                "BusinessShortCode": self.business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),  # M-Pesa expects integer amount
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
        """
        Check payment status using CheckoutRequestID.
        
        Args:
            checkout_request_id: The CheckoutRequestID from STK Push
            
        Returns:
            Dict containing payment status and details
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            # Get access token
            access_token = await self._get_access_token()
            
            # Generate timestamp and password
            timestamp = self._generate_timestamp()
            password = self._generate_password(timestamp)
            
            # Prepare request data
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
                        # Payment completed successfully
                        result_params = response_data.get("ResultParameters", {})
                        item_list = result_params.get("Item", [])
                        
                        # Extract payment details
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
                        # Request cancelled by user
                        return {
                            "success": False,
                            "status": "cancelled",
                            "error_code": result_code,
                            "error_message": "Payment cancelled by user"
                        }
                    elif result_code == 1037:
                        # Request timeout
                        return {
                            "success": False,
                            "status": "timeout",
                            "error_code": result_code,
                            "error_message": "Payment request timeout"
                        }
                    else:
                        # Other error
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
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process M-Pesa webhook callback.
        
        Args:
            webhook_data: Webhook payload from M-Pesa
            
        Returns:
            Dict containing processing result
        """
        try:
            # Extract webhook data
            body = webhook_data.get("Body", {})
            stk_callback = body.get("stkCallback", {})
            
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")
            
            logger.info("Processing M-Pesa webhook", 
                       checkout_request_id=checkout_request_id,
                       result_code=result_code)
            
            if result_code == 0:
                # Payment successful
                callback_metadata = stk_callback.get("CallbackMetadata", {})
                item_list = callback_metadata.get("Item", [])
                
                # Extract payment details
                payment_details = {}
                for item in item_list:
                    key = item.get("Key")
                    value = item.get("Value")
                    if key and value is not None:
                        payment_details[key] = value
                
                # Update payment in database
                # This would typically be done through a repository
                # For now, we'll return the details
                return {
                    "success": True,
                    "status": "completed",
                    "checkout_request_id": checkout_request_id,
                    "mpesa_receipt_number": payment_details.get("MpesaReceiptNumber"),
                    "transaction_date": payment_details.get("TransactionDate"),
                    "amount": payment_details.get("Amount"),
                    "phone_number": payment_details.get("PhoneNumber"),
                    "merchant_request_id": payment_details.get("MerchantRequestID")
                }
            else:
                # Payment failed
                return {
                    "success": False,
                    "status": "failed",
                    "checkout_request_id": checkout_request_id,
                    "error_code": result_code,
                    "error_message": result_desc
                }
                
        except Exception as e:
            logger.error("Error processing webhook", error=str(e))
            return {
                "success": False,
                "status": "error",
                "error_message": str(e)
            }
    
    def format_phone_number(self, phone_number: str) -> str:
        """
        Format phone number for M-Pesa (254XXXXXXXXX).
        
        Args:
            phone_number: Phone number in any format
            
        Returns:
            Formatted phone number
        """
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        # Handle different formats
        if digits_only.startswith('254'):
            return digits_only
        elif digits_only.startswith('0'):
            return '254' + digits_only[1:]
        elif digits_only.startswith('7'):
            return '254' + digits_only
        elif len(digits_only) == 9:
            return '254' + digits_only
        else:
            # Assume it's already in correct format
            return digits_only
    
    async def validate_phone_number(self, phone_number: str) -> bool:
        """
        Validate phone number format for M-Pesa.
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            True if valid, False otherwise
        """
        formatted = self.format_phone_number(phone_number)
        return len(formatted) == 12 and formatted.startswith('254')


class MpesaPaymentProcessor:
    """High-level M-Pesa payment processor for CAPP."""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.payment_repo = PaymentRepository(db_session)
        self.user_repo = UserRepository(db_session)
    
    async def process_payment(self, 
                            payment_id: str, 
                            phone_number: str, 
                            amount: float,
                            description: str = "CAPP Payment") -> Dict[str, Any]:
        """
        Process a payment through M-Pesa.
        
        Args:
            payment_id: CAPP payment ID
            phone_number: Recipient phone number
            amount: Payment amount
            description: Payment description
            
        Returns:
            Dict containing processing result
        """
        try:
            # Format phone number
            formatted_phone = MpesaService().format_phone_number(phone_number)
            
            # Validate phone number
            if not await MpesaService().validate_phone_number(formatted_phone):
                return {
                    "success": False,
                    "error": "Invalid phone number format"
                }
            
            # Update payment status to processing
            await self.payment_repo.update_payment_status(
                payment_id, 
                PaymentStatus.PROCESSING,
                mmo_transaction_id=None
            )
            
            # Initiate STK Push
            async with MpesaService() as mpesa:
                stk_result = await mpesa.initiate_stk_push(
                    phone_number=formatted_phone,
                    amount=amount,
                    reference=payment_id,
                    description=description
                )
                
                if stk_result["success"]:
                    # Update payment with checkout request ID
                    await self.payment_repo.update_payment_status(
                        payment_id,
                        PaymentStatus.PENDING,
                        mmo_transaction_id=stk_result["checkout_request_id"]
                    )
                    
                    logger.info("M-Pesa payment initiated", 
                              payment_id=payment_id,
                              checkout_request_id=stk_result["checkout_request_id"])
                    
                    return {
                        "success": True,
                        "payment_id": payment_id,
                        "checkout_request_id": stk_result["checkout_request_id"],
                        "status": "pending",
                        "message": "Payment initiated successfully. Please check your phone for STK Push."
                    }
                else:
                    # Update payment status to failed
                    await self.payment_repo.update_payment_status(
                        payment_id,
                        PaymentStatus.FAILED
                    )
                    
                    logger.error("M-Pesa payment initiation failed", 
                               payment_id=payment_id,
                               error=stk_result.get("error_message"))
                    
                    return {
                        "success": False,
                        "payment_id": payment_id,
                        "error": stk_result.get("error_message"),
                        "status": "failed"
                    }
                    
        except Exception as e:
            logger.error("Error processing M-Pesa payment", 
                        payment_id=payment_id, error=str(e))
            
            # Update payment status to failed
            await self.payment_repo.update_payment_status(
                payment_id,
                PaymentStatus.FAILED
            )
            
            return {
                "success": False,
                "payment_id": payment_id,
                "error": str(e),
                "status": "failed"
            }
    
    async def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Check payment status and update database.
        
        Args:
            payment_id: CAPP payment ID
            
        Returns:
            Dict containing current status
        """
        try:
            # Get payment from database
            payment = await self.payment_repo.get_payment_by_id(payment_id)
            if not payment:
                return {
                    "success": False,
                    "error": "Payment not found"
                }
            
            if not payment.mmo_transaction_id:
                return {
                    "success": False,
                    "error": "No M-Pesa transaction ID found"
                }
            
            # Check status with M-Pesa
            async with MpesaService() as mpesa:
                status_result = await mpesa.check_payment_status(
                    payment.mmo_transaction_id
                )
                
                if status_result["success"] and status_result["status"] == "completed":
                    # Payment completed successfully
                    await self.payment_repo.update_payment_status(
                        payment_id,
                        PaymentStatus.COMPLETED,
                        settled_at=datetime.utcnow()
                    )
                    
                    logger.info("M-Pesa payment completed", 
                              payment_id=payment_id,
                              mpesa_receipt=status_result.get("mpesa_receipt_number"))
                    
                    return {
                        "success": True,
                        "payment_id": payment_id,
                        "status": "completed",
                        "mpesa_receipt_number": status_result.get("mpesa_receipt_number"),
                        "settled_at": datetime.utcnow().isoformat()
                    }
                elif status_result["status"] == "cancelled":
                    # Payment cancelled
                    await self.payment_repo.update_payment_status(
                        payment_id,
                        PaymentStatus.CANCELLED
                    )
                    
                    return {
                        "success": False,
                        "payment_id": payment_id,
                        "status": "cancelled",
                        "error": "Payment cancelled by user"
                    }
                elif status_result["status"] == "timeout":
                    # Payment timeout
                    await self.payment_repo.update_payment_status(
                        payment_id,
                        PaymentStatus.TIMEOUT
                    )
                    
                    return {
                        "success": False,
                        "payment_id": payment_id,
                        "status": "timeout",
                        "error": "Payment request timeout"
                    }
                else:
                    # Still pending or failed
                    return {
                        "success": True,
                        "payment_id": payment_id,
                        "status": status_result.get("status", "pending"),
                        "error": status_result.get("error_message")
                    }
                    
        except Exception as e:
            logger.error("Error checking M-Pesa payment status", 
                        payment_id=payment_id, error=str(e))
            
            return {
                "success": False,
                "payment_id": payment_id,
                "error": str(e)
            } 