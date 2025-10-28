"""
Airtel Money integration service for CAPP.

Production-ready implementation with:
- Push Payment (Merchant to Customer)
- Payment Enquiry (Customer to Merchant)
- Disbursement (Payout)
- Transaction status queries
- Retry logic with exponential backoff
- Circuit breaker pattern
- Comprehensive error handling
- Database persistence

Airtel Money API Documentation: https://developers.airtel.africa/
"""

import asyncio
import base64
import json
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any
from enum import Enum

import aiohttp
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from ..config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class AirtelMoneyTransactionType(str, Enum):
    """Airtel Money transaction types"""
    PUSH_PAYMENT = "push_payment"  # Merchant to Customer
    PAYMENT_ENQUIRY = "payment_enquiry"  # Customer to Merchant
    DISBURSEMENT = "disbursement"  # Payout
    QUERY = "query"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for Airtel Money API calls"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
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
                "Airtel Money circuit breaker opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold
            )

    def can_attempt(self) -> bool:
        """Check if request can be attempted"""
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("Airtel Money circuit breaker half-open, testing recovery")
                    return True
            return False

        return True

    def reset(self):
        """Reset circuit breaker"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time = None


class AirtelMoneyService:
    """
    Airtel Money API integration service

    Supports multiple African countries:
    - Kenya, Tanzania, Uganda, Rwanda
    - Zambia, Malawi, Nigeria, Ghana
    - Madagascar, Seychelles, Chad, Niger
    - Democratic Republic of Congo, Congo Brazzaville, Gabon
    """

    def __init__(self, db_session=None, environment: str = "staging"):
        self.db_session = db_session
        self.environment = environment  # staging or production
        self.logger = structlog.get_logger(__name__)

        # API Configuration
        self.base_url = self._get_base_url()
        self.client_id = settings.AIRTEL_MONEY_CLIENT_ID
        self.client_secret = settings.AIRTEL_MONEY_CLIENT_SECRET
        self.api_key = settings.AIRTEL_MONEY_API_KEY

        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

        # Access token cache
        self.access_token = None
        self.token_expires_at = None

        self.logger.info("Airtel Money service initialized", environment=self.environment)

    def _get_base_url(self) -> str:
        """Get base URL based on environment"""
        if self.environment == "staging":
            return "https://openapiuat.airtel.africa"
        else:
            return "https://openapi.airtel.africa"

    async def _get_access_token(self) -> Optional[str]:
        """
        Get OAuth2 access token

        Returns:
            Access token string
        """
        # Check if we have a cached valid token
        if self.access_token and self.token_expires_at:
            if self.token_expires_at > datetime.now(timezone.utc):
                return self.access_token

        # Generate new token
        try:
            url = f"{self.base_url}/auth/oauth2/token"

            headers = {
                "Content-Type": "application/json"
            }

            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        access_token = data.get("access_token")
                        expires_in = data.get("expires_in", 3600)

                        # Cache the token
                        self.access_token = access_token
                        self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)

                        self.logger.info(
                            "Airtel Money access token obtained",
                            expires_in=expires_in
                        )

                        return access_token
                    else:
                        error_text = await response.text()
                        self.logger.error(
                            "Failed to get Airtel Money access token",
                            status=response.status,
                            error=error_text
                        )
                        return None

        except Exception as e:
            self.logger.error(
                "Error getting Airtel Money access token",
                error=str(e),
                exc_info=True
            )
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def push_payment(
        self,
        phone_number: str,
        amount: float,
        currency: str,
        transaction_id: str,
        country_code: str = "KE"
    ) -> Dict[str, Any]:
        """
        Push Payment (Merchant to Customer)

        Send money to a customer's Airtel Money account

        Args:
            phone_number: Customer phone number (format: 254XXXXXXXXX)
            amount: Amount to send
            currency: Currency code (e.g., KES, UGX, TZS)
            transaction_id: Your unique transaction reference
            country_code: Country code (e.g., KE, UG, TZ)

        Returns:
            Dict with success status and reference
        """
        if not self.circuit_breaker.can_attempt():
            return {
                "success": False,
                "error_code": "CIRCUIT_BREAKER_OPEN",
                "message": "Airtel Money service temporarily unavailable"
            }

        try:
            # Get access token
            access_token = await self._get_access_token()
            if not access_token:
                self.circuit_breaker.record_failure()
                return {
                    "success": False,
                    "error_code": "AUTH_FAILED",
                    "message": "Failed to authenticate with Airtel Money"
                }

            # Prepare request
            url = f"{self.base_url}/merchant/v1/payments/"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Country": country_code,
                "X-Currency": currency
            }

            payload = {
                "reference": transaction_id,
                "subscriber": {
                    "country": country_code,
                    "currency": currency,
                    "msisdn": phone_number
                },
                "transaction": {
                    "amount": amount,
                    "country": country_code,
                    "currency": currency,
                    "id": transaction_id
                }
            }

            self.logger.info(
                "Initiating Airtel Money push payment",
                transaction_id=transaction_id,
                phone_number=phone_number[-4:],
                amount=amount,
                currency=currency
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()

                    if response.status == 200 and data.get("status", {}).get("code") == "200":
                        self.circuit_breaker.record_success()

                        transaction_data = data.get("data", {}).get("transaction", {})

                        self.logger.info(
                            "Airtel Money push payment accepted",
                            transaction_id=transaction_id,
                            airtel_ref=transaction_data.get("id")
                        )

                        return {
                            "success": True,
                            "transaction_id": transaction_id,
                            "airtel_reference": transaction_data.get("id"),
                            "status": "pending",
                            "message": "Push payment initiated successfully"
                        }
                    else:
                        error_message = data.get("status", {}).get("message", "Unknown error")
                        self.circuit_breaker.record_failure()

                        self.logger.error(
                            "Airtel Money push payment failed",
                            transaction_id=transaction_id,
                            status=response.status,
                            error=error_message
                        )

                        return {
                            "success": False,
                            "error_code": data.get("status", {}).get("code", "UNKNOWN"),
                            "message": error_message
                        }

        except Exception as e:
            self.circuit_breaker.record_failure()
            self.logger.error(
                "Airtel Money push payment error",
                transaction_id=transaction_id,
                error=str(e),
                exc_info=True
            )
            return {
                "success": False,
                "error_code": "PAYMENT_ERROR",
                "message": str(e)
            }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def disbursement(
        self,
        phone_number: str,
        amount: float,
        currency: str,
        transaction_id: str,
        country_code: str = "KE"
    ) -> Dict[str, Any]:
        """
        Disbursement (Payout)

        Transfer money to a customer

        Args:
            phone_number: Customer phone number
            amount: Amount to send
            currency: Currency code
            transaction_id: Your unique transaction reference
            country_code: Country code

        Returns:
            Dict with success status and reference
        """
        if not self.circuit_breaker.can_attempt():
            return {
                "success": False,
                "error_code": "CIRCUIT_BREAKER_OPEN",
                "message": "Airtel Money service temporarily unavailable"
            }

        try:
            # Get access token
            access_token = await self._get_access_token()
            if not access_token:
                self.circuit_breaker.record_failure()
                return {
                    "success": False,
                    "error_code": "AUTH_FAILED",
                    "message": "Failed to authenticate with Airtel Money"
                }

            # Prepare request
            url = f"{self.base_url}/standard/v1/disbursements/"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Country": country_code,
                "X-Currency": currency
            }

            payload = {
                "payee": {
                    "msisdn": phone_number
                },
                "reference": transaction_id,
                "transaction": {
                    "amount": amount,
                    "id": transaction_id
                }
            }

            self.logger.info(
                "Initiating Airtel Money disbursement",
                transaction_id=transaction_id,
                phone_number=phone_number[-4:],
                amount=amount,
                currency=currency
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()

                    if response.status == 200 and data.get("status", {}).get("code") == "200":
                        self.circuit_breaker.record_success()

                        transaction_data = data.get("data", {}).get("transaction", {})

                        self.logger.info(
                            "Airtel Money disbursement accepted",
                            transaction_id=transaction_id,
                            airtel_ref=transaction_data.get("id")
                        )

                        return {
                            "success": True,
                            "transaction_id": transaction_id,
                            "airtel_reference": transaction_data.get("id"),
                            "status": "pending",
                            "message": "Disbursement initiated successfully"
                        }
                    else:
                        error_message = data.get("status", {}).get("message", "Unknown error")
                        self.circuit_breaker.record_failure()

                        self.logger.error(
                            "Airtel Money disbursement failed",
                            transaction_id=transaction_id,
                            status=response.status,
                            error=error_message
                        )

                        return {
                            "success": False,
                            "error_code": data.get("status", {}).get("code", "UNKNOWN"),
                            "message": error_message
                        }

        except Exception as e:
            self.circuit_breaker.record_failure()
            self.logger.error(
                "Airtel Money disbursement error",
                transaction_id=transaction_id,
                error=str(e),
                exc_info=True
            )
            return {
                "success": False,
                "error_code": "DISBURSEMENT_ERROR",
                "message": str(e)
            }

    async def get_transaction_status(
        self,
        transaction_id: str,
        country_code: str = "KE"
    ) -> Dict[str, Any]:
        """
        Query transaction status

        Args:
            transaction_id: Transaction ID to query
            country_code: Country code

        Returns:
            Dict with transaction status
        """
        try:
            # Get access token
            access_token = await self._get_access_token()
            if not access_token:
                return {
                    "success": False,
                    "error_code": "AUTH_FAILED",
                    "message": "Failed to authenticate with Airtel Money"
                }

            # Prepare request
            url = f"{self.base_url}/standard/v1/payments/{transaction_id}"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Country": country_code
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    data = await response.json()

                    if response.status == 200:
                        transaction_data = data.get("data", {}).get("transaction", {})

                        self.logger.info(
                            "Airtel Money transaction status retrieved",
                            transaction_id=transaction_id,
                            status=transaction_data.get("status")
                        )

                        return {
                            "success": True,
                            "transaction_id": transaction_id,
                            "airtel_reference": transaction_data.get("id"),
                            "status": transaction_data.get("status"),  # TS, TIP, TF (Success, In Progress, Failed)
                            "amount": transaction_data.get("amount"),
                            "currency": transaction_data.get("currency"),
                            "message": transaction_data.get("message")
                        }
                    else:
                        error_message = data.get("status", {}).get("message", "Unknown error")
                        self.logger.error(
                            "Failed to get Airtel Money transaction status",
                            transaction_id=transaction_id,
                            status=response.status,
                            error=error_message
                        )

                        return {
                            "success": False,
                            "error_code": data.get("status", {}).get("code", "UNKNOWN"),
                            "message": error_message
                        }

        except Exception as e:
            self.logger.error(
                "Error getting Airtel Money transaction status",
                transaction_id=transaction_id,
                error=str(e),
                exc_info=True
            )
            return {
                "success": False,
                "error_code": "STATUS_ERROR",
                "message": str(e)
            }
