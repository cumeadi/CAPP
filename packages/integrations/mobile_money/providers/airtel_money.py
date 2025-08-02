"""
Airtel Money Integration

Airtel Money mobile money integration for cross-border payments
and mobile money operations across Africa.
"""

import asyncio
import hashlib
import hmac
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
import structlog

from pydantic import BaseModel, Field

from ..base_mmo import (
    BaseMMOIntegration, MMOConfig, MMOTransaction, MMOBalance,
    MMOProvider, TransactionStatus, TransactionType
)
from packages.integrations.data.redis_client import RedisClient

logger = structlog.get_logger(__name__)


class AirtelMoneyConfig(MMOConfig):
    """Airtel Money specific configuration"""
    provider: MMOProvider = MMOProvider.AIRTEL_MONEY
    
    # Airtel Money specific settings
    client_id: str
    client_secret: str
    business_short_code: str
    passkey: str
    
    # API endpoints
    base_url: str = "https://openapiuat.airtel.africa"
    sandbox_url: str = "https://openapiuat.airtel.africa"
    production_url: str = "https://openapi.airtel.africa"
    
    # Transaction limits
    min_amount: Decimal = Decimal("1.0")
    max_amount: Decimal = Decimal("10000.0")
    
    # Supported countries
    supported_countries: List[str] = [
        "KE", "UG", "NG", "GH", "RW", "BI", "ZM", "MW", "MZ", "AO", "NA", "ZW"
    ]


class AirtelMoneyTransaction(BaseModel):
    """Airtel Money transaction model"""
    reference: str
    amount: str
    currency: str = "KES"
    phone_number: str
    description: str
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AirtelMoneyResponse(BaseModel):
    """Airtel Money API response"""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None


class AirtelMoneyIntegration(BaseMMOIntegration):
    """
    Airtel Money Integration
    
    Provides integration with Airtel Money for mobile money operations
    across multiple African countries.
    """
    
    def __init__(self, config: AirtelMoneyConfig, redis_client: Optional[RedisClient] = None):
        super().__init__(config, redis_client)
        self.airtel_config = config
        self.access_token = None
        self.token_expiry = None
        
        # API endpoints
        self.base_url = (
            config.sandbox_url if config.environment == "sandbox" 
            else config.production_url
        )
        
        # Endpoints
        self.auth_endpoint = "/auth/oauth2/token"
        self.collection_endpoint = "/merchant/v1/payments/"
        self.disbursement_endpoint = "/merchant/v1/payments/"
        self.status_endpoint = "/merchant/v1/payments/"
        self.balance_endpoint = "/merchant/v1/payments/"
        
        self.logger = structlog.get_logger(__name__)
    
    def _initialize_client(self) -> None:
        """Initialize Airtel Money client"""
        # No specific client initialization needed for HTTP-based API
        pass
    
    async def initialize(self) -> bool:
        """Initialize the Airtel Money integration"""
        try:
            # Get access token
            await self._get_access_token()
            
            self.logger.info("Airtel Money integration initialized")
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize Airtel Money integration", error=str(e))
            return False
    
    async def _get_access_token(self) -> str:
        """Get Airtel Money access token"""
        try:
            # Check if we have a valid cached token
            if self.access_token and self.token_expiry and datetime.now(timezone.utc) < self.token_expiry:
                return self.access_token
            
            # Get cached token from Redis
            if self.redis_client:
                cached_token = await self.redis_client.get("airtel_access_token")
                if cached_token:
                    token_data = json.loads(cached_token)
                    if datetime.fromisoformat(token_data["expiry"]) > datetime.now(timezone.utc):
                        self.access_token = token_data["token"]
                        self.token_expiry = datetime.fromisoformat(token_data["expiry"])
                        return self.access_token
            
            # Request new token
            auth_data = {
                "client_id": self.airtel_config.client_id,
                "client_secret": self.airtel_config.client_secret,
                "grant_type": "client_credentials"
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            response = await self._make_api_request(
                self.auth_endpoint,
                method="POST",
                data=auth_data,
                headers=headers,
                auth_required=False
            )
            
            if response.get("status") == "success":
                token_data = response.get("data", {})
                self.access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                
                # Set expiry time
                self.token_expiry = datetime.now(timezone.utc) + asyncio.get_event_loop().time() + expires_in
                
                # Cache token in Redis
                if self.redis_client:
                    cache_data = {
                        "token": self.access_token,
                        "expiry": self.token_expiry.isoformat()
                    }
                    await self.redis_client.set(
                        "airtel_access_token",
                        json.dumps(cache_data),
                        ttl=expires_in - 300  # Cache for 5 minutes less than expiry
                    )
                
                self.logger.info("Airtel Money access token obtained")
                return self.access_token
            else:
                raise Exception(f"Failed to get access token: {response.get('message')}")
                
        except Exception as e:
            self.logger.error("Failed to get Airtel Money access token", error=str(e))
            raise
    
    async def _make_api_request(
        self, 
        endpoint: str, 
        method: str = "GET", 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth_required: bool = True
    ) -> Dict[str, Any]:
        """Make API request to Airtel Money"""
        try:
            import aiohttp
            
            # Prepare headers
            request_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            if headers:
                request_headers.update(headers)
            
            # Add authorization header if required
            if auth_required:
                access_token = await self._get_access_token()
                request_headers["Authorization"] = f"Bearer {access_token}"
            
            # Prepare request data
            request_data = None
            if data:
                request_data = json.dumps(data)
            
            # Make request
            url = f"{self.base_url}{endpoint}"
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    data=request_data,
                    timeout=aiohttp.ClientTimeout(total=self.airtel_config.timeout)
                ) as response:
                    
                    response_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            return json.loads(response_text)
                        except json.JSONDecodeError:
                            return {
                                "status": "success",
                                "data": response_text
                            }
                    else:
                        error_data = {
                            "status": "error",
                            "message": f"HTTP {response.status}: {response_text}",
                            "error_code": str(response.status)
                        }
                        
                        try:
                            error_json = json.loads(response_text)
                            error_data.update(error_json)
                        except json.JSONDecodeError:
                            pass
                        
                        return error_data
                        
        except Exception as e:
            self.logger.error("Airtel Money API request failed", error=str(e))
            return {
                "status": "error",
                "message": str(e),
                "error_code": "API_REQUEST_FAILED"
            }
    
    def _parse_transaction_response(self, response: Dict[str, Any]) -> MMOTransaction:
        """Parse Airtel Money transaction response"""
        try:
            if response.get("status") == "success":
                data = response.get("data", {})
                
                return MMOTransaction(
                    transaction_id=data.get("transaction_id", ""),
                    external_id=data.get("reference", ""),
                    transaction_type=TransactionType.TRANSFER,
                    amount=Decimal(str(data.get("amount", 0))),
                    currency=data.get("currency", "KES"),
                    phone_number=data.get("phone_number", ""),
                    description=data.get("description", ""),
                    status=TransactionStatus.SUCCESSFUL,
                    completed_at=datetime.now(timezone.utc),
                    metadata={
                        "airtel_response": data,
                        "provider": "airtel_money"
                    }
                )
            else:
                return MMOTransaction(
                    transaction_id="",
                    transaction_type=TransactionType.TRANSFER,
                    amount=Decimal("0"),
                    currency="KES",
                    phone_number="",
                    description="",
                    status=TransactionStatus.FAILED,
                    error_code=response.get("error_code"),
                    error_message=response.get("message"),
                    metadata={
                        "airtel_response": response,
                        "provider": "airtel_money"
                    }
                )
                
        except Exception as e:
            self.logger.error("Failed to parse Airtel Money transaction response", error=str(e))
            
            return MMOTransaction(
                transaction_id="",
                transaction_type=TransactionType.TRANSFER,
                amount=Decimal("0"),
                currency="KES",
                phone_number="",
                description="",
                status=TransactionStatus.FAILED,
                error_code="PARSE_ERROR",
                error_message=str(e),
                metadata={
                    "provider": "airtel_money",
                    "parse_error": True
                }
            )
    
    def _parse_balance_response(self, response: Dict[str, Any]) -> MMOBalance:
        """Parse Airtel Money balance response"""
        try:
            if response.get("status") == "success":
                data = response.get("data", {})
                
                return MMOBalance(
                    account_id=data.get("account_id", ""),
                    available_balance=Decimal(str(data.get("available_balance", 0))),
                    reserved_balance=Decimal(str(data.get("reserved_balance", 0))),
                    total_balance=Decimal(str(data.get("total_balance", 0))),
                    currency=data.get("currency", "KES"),
                    metadata={
                        "airtel_response": data,
                        "provider": "airtel_money"
                    }
                )
            else:
                return MMOBalance(
                    account_id="",
                    available_balance=Decimal("0"),
                    reserved_balance=Decimal("0"),
                    total_balance=Decimal("0"),
                    currency="KES",
                    metadata={
                        "airtel_response": response,
                        "provider": "airtel_money"
                    }
                )
                
        except Exception as e:
            self.logger.error("Failed to parse Airtel Money balance response", error=str(e))
            
            return MMOBalance(
                account_id="",
                available_balance=Decimal("0"),
                reserved_balance=Decimal("0"),
                total_balance=Decimal("0"),
                currency="KES",
                metadata={
                    "provider": "airtel_money",
                    "parse_error": True
                }
            )
    
    async def initiate_transaction(self, transaction: MMOTransaction) -> MMOTransaction:
        """Initiate Airtel Money transaction"""
        try:
            # Validate transaction
            if not await self._validate_transaction(transaction):
                transaction.status = TransactionStatus.FAILED
                transaction.error_message = "Transaction validation failed"
                return transaction
            
            # Prepare Airtel Money transaction data
            airtel_transaction = AirtelMoneyTransaction(
                reference=transaction.transaction_id,
                amount=str(transaction.amount),
                currency=transaction.currency,
                phone_number=transaction.phone_number,
                description=transaction.description,
                callback_url=self.airtel_config.provider_config.get("callback_url")
            )
            
            # Make API request
            response = await self._make_api_request(
                self.collection_endpoint,
                method="POST",
                data=airtel_transaction.dict()
            )
            
            # Parse response
            result = self._parse_transaction_response(response)
            
            # Update original transaction
            transaction.status = result.status
            transaction.external_id = result.external_id
            transaction.completed_at = result.completed_at
            transaction.error_code = result.error_code
            transaction.error_message = result.error_message
            transaction.metadata.update(result.metadata)
            
            self.logger.info(
                "Airtel Money transaction initiated",
                transaction_id=transaction.transaction_id,
                status=transaction.status
            )
            
            return transaction
            
        except Exception as e:
            self.logger.error(
                "Failed to initiate Airtel Money transaction",
                transaction_id=transaction.transaction_id,
                error=str(e)
            )
            
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = str(e)
            return transaction
    
    async def check_transaction_status(self, transaction_id: str) -> Optional[MMOTransaction]:
        """Check Airtel Money transaction status"""
        try:
            # Make API request
            response = await self._make_api_request(
                f"{self.status_endpoint}{transaction_id}",
                method="GET"
            )
            
            # Parse response
            result = self._parse_transaction_response(response)
            
            if result.transaction_id:
                self.logger.info(
                    "Airtel Money transaction status checked",
                    transaction_id=transaction_id,
                    status=result.status
                )
                return result
            else:
                return None
                
        except Exception as e:
            self.logger.error(
                "Failed to check Airtel Money transaction status",
                transaction_id=transaction_id,
                error=str(e)
            )
            return None
    
    async def get_account_balance(self, phone_number: str) -> Optional[MMOBalance]:
        """Get Airtel Money account balance"""
        try:
            # Make API request
            response = await self._make_api_request(
                f"{self.balance_endpoint}balance?phone_number={phone_number}",
                method="GET"
            )
            
            # Parse response
            result = self._parse_balance_response(response)
            
            if result.account_id:
                self.logger.info(
                    "Airtel Money account balance retrieved",
                    phone_number=phone_number,
                    balance=result.total_balance
                )
                return result
            else:
                return None
                
        except Exception as e:
            self.logger.error(
                "Failed to get Airtel Money account balance",
                phone_number=phone_number,
                error=str(e)
            )
            return None
    
    async def validate_phone_number(self, phone_number: str) -> bool:
        """Validate Airtel Money phone number"""
        try:
            # Airtel Money phone number validation logic
            # Remove any non-digit characters
            clean_number = ''.join(filter(str.isdigit, phone_number))
            
            # Check if it's a valid Airtel number format
            # This is a simplified validation - in production, you'd want more robust validation
            
            # Check length (should be 9-12 digits)
            if len(clean_number) < 9 or len(clean_number) > 12:
                return False
            
            # Check if it starts with valid Airtel prefixes
            airtel_prefixes = [
                "254", "255", "256", "257", "258", "260", "261", "263", "264", "265", "266", "267"
            ]
            
            for prefix in airtel_prefixes:
                if clean_number.startswith(prefix):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to validate Airtel Money phone number", error=str(e))
            return False
    
    async def get_supported_countries(self) -> List[str]:
        """Get list of supported countries"""
        return self.airtel_config.supported_countries.copy()
    
    async def get_transaction_limits(self) -> Dict[str, Any]:
        """Get transaction limits"""
        return {
            "min_amount": float(self.airtel_config.min_amount),
            "max_amount": float(self.airtel_config.max_amount),
            "currency": "KES",
            "daily_limit": 50000.0,
            "monthly_limit": 500000.0,
            "provider": "airtel_money"
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get Airtel Money health status"""
        try:
            # Simple health check - try to get access token
            await self._get_access_token()
            
            return {
                "status": "healthy",
                "provider": "airtel_money",
                "access_token_valid": bool(self.access_token),
                "last_check": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "airtel_money",
                "error": str(e),
                "last_check": datetime.now(timezone.utc).isoformat()
            }
    
    async def _validate_transaction(self, transaction: MMOTransaction) -> bool:
        """Validate transaction before processing"""
        try:
            # Check amount limits
            if transaction.amount < self.airtel_config.min_amount:
                self.logger.warning(
                    "Transaction amount below minimum",
                    amount=transaction.amount,
                    min_amount=self.airtel_config.min_amount
                )
                return False
            
            if transaction.amount > self.airtel_config.max_amount:
                self.logger.warning(
                    "Transaction amount above maximum",
                    amount=transaction.amount,
                    max_amount=self.airtel_config.max_amount
                )
                return False
            
            # Validate phone number
            if not await self.validate_phone_number(transaction.phone_number):
                self.logger.warning(
                    "Invalid phone number",
                    phone_number=transaction.phone_number
                )
                return False
            
            # Check currency support
            if transaction.currency not in ["KES", "UGX", "NGN", "GHS", "RWF", "BIF", "ZMW", "MWK", "MZN", "AOA", "NAD", "ZWL"]:
                self.logger.warning(
                    "Unsupported currency",
                    currency=transaction.currency
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Transaction validation failed", error=str(e))
            return False
    
    async def close(self) -> None:
        """Close Airtel Money integration"""
        try:
            # Clear access token
            self.access_token = None
            self.token_expiry = None
            
            self.logger.info("Airtel Money integration closed")
            
        except Exception as e:
            self.logger.error("Error closing Airtel Money integration", error=str(e)) 