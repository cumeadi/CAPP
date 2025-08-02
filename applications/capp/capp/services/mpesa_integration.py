"""
M-Pesa integration service for CAPP.
Core functionality for STK Push and payment status checking.
"""

import asyncio
import base64
import hashlib
import json
import time
from datetime import datetime
from typing import Dict, Optional, Any

import aiohttp
import structlog

from .config.settings import get_settings

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


if __name__ == "__main__":
    asyncio.run(demo_mpesa_integration()) 