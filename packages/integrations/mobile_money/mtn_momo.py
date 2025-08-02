"""
MTN Mobile Money Integration

Complete MTN Mobile Money integration for multiple African countries.
Based on the working CAPP system implementation.
"""

import asyncio
import hashlib
import hmac
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
import json

import structlog
from pydantic import BaseModel, Field

from .base_mmo import (
    BaseMMOIntegration, MMOConfig, MMOTransaction, MMOBalance,
    TransactionStatus, TransactionType, MMOProvider
)

logger = structlog.get_logger(__name__)


class MTNMoMoConfig(MMOConfig):
    """MTN Mobile Money specific configuration"""
    provider: MMOProvider = MMOProvider.MTN_MOBILE_MONEY
    
    # MTN MoMo API endpoints
    base_url: str = "https://sandbox.momodeveloper.mtn.com"
    production_url: str = "https://proxy.momoapi.mtn.com"
    
    # MTN MoMo specific settings
    subscription_key: str
    target_environment: str = "sandbox"  # sandbox, production
    currency: str = "EUR"
    country: str = "UG"  # UG, GH, NG, RW, BI, ZM, MW, MZ, AO, NA, ZW
    
    # API versions
    api_version: str = "v1"
    
    # Callback URLs
    callback_url: str
    timeout_url: str
    
    # Collection settings
    collection_subscription_key: str
    disbursement_subscription_key: str
    
    # Remittance settings
    remittance_subscription_key: str


class MTNMoMoTransaction(BaseModel):
    """MTN Mobile Money transaction model"""
    amount: str
    currency: str
    external_id: str
    payer: Dict[str, str]
    payer_message: str
    payee_note: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MTNMoMoResponse(BaseModel):
    """MTN Mobile Money API response"""
    status: bool
    reference_id: str
    external_id: str
    amount: str
    currency: str
    financial_transaction_id: str
    payer_message: str
    payee_note: str
    status_message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MTNMoMoCallback(BaseModel):
    """MTN Mobile Money callback data"""
    amount: str
    currency: str
    external_id: str
    financial_transaction_id: str
    payer_message: str
    payee_note: str
    status: str
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MTNMoMoIntegration(BaseMMOIntegration):
    """
    MTN Mobile Money integration
    
    Provides complete integration with MTN Mobile Money APIs including:
    - Collection (C2B)
    - Disbursement (B2C)
    - Remittance
    - Transaction status checking
    - Account balance queries
    """
    
    def __init__(self, config: MTNMoMoConfig, redis_client=None):
        super().__init__(config, redis_client)
        self.mtn_config = config
        
        # Set base URL based on environment
        if config.target_environment == "production":
            self.base_url = config.production_url
        else:
            self.base_url = config.base_url
        
        # Initialize session for API calls
        self._session = None
        self._access_token = None
    
    def _initialize_client(self) -> None:
        """Initialize MTN MoMo client"""
        import aiohttp
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
    
    async def _get_access_token(self) -> str:
        """Get MTN MoMo access token"""
        # Check cache first
        cache_key = f"mtn_momo_access_token_{self.mtn_config.country}"
        cached_token = await self._get_cached_data(cache_key)
        
        if cached_token:
            return cached_token
        
        # Generate new token
        url = f"{self.base_url}/collection/token/"
        headers = {
            "X-Reference-Id": self._generate_reference_id(),
            "X-Target-Environment": self.mtn_config.target_environment,
            "Ocp-Apim-Subscription-Key": self.mtn_config.collection_subscription_key
        }
        
        try:
            async with self._session.post(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    access_token = result.get("access_token")
                    
                    if access_token:
                        # Cache token for 55 minutes
                        await self._set_cached_data(cache_key, access_token, ttl=3300)
                        return access_token
                    else:
                        raise Exception("Failed to get access token")
                else:
                    raise Exception(f"Failed to get access token: {response.status}")
                    
        except Exception as e:
            self.logger.error("Failed to get MTN MoMo access token", error=str(e))
            raise
    
    def _generate_reference_id(self) -> str:
        """Generate unique reference ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _generate_external_id(self) -> str:
        """Generate external ID for transactions"""
        import uuid
        return f"ext_{uuid.uuid4().hex[:16]}"
    
    async def _make_api_request(self, endpoint: str, method: str = "GET", 
                               data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make API request to MTN MoMo"""
        if not self._session:
            raise RuntimeError("MTN MoMo client not initialized")
        
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {await self._get_access_token()}",
            "X-Reference-Id": self._generate_reference_id(),
            "X-Target-Environment": self.mtn_config.target_environment,
            "Ocp-Apim-Subscription-Key": self.mtn_config.collection_subscription_key,
            "Content-Type": "application/json"
        }
        
        try:
            if method.upper() == "GET":
                async with self._session.get(url, headers=headers) as response:
                    return await response.json()
            elif method.upper() == "POST":
                async with self._session.post(url, headers=headers, json=data) as response:
                    return await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
        except Exception as e:
            self.logger.error("MTN MoMo API request failed", endpoint=endpoint, error=str(e))
            raise
    
    async def initiate_collection(self, phone_number: str, amount: Decimal,
                                 reference: str, description: str) -> MTNMoMoResponse:
        """
        Initiate collection (C2B) transaction
        
        Args:
            phone_number: Customer phone number
            amount: Transaction amount
            reference: Transaction reference
            description: Transaction description
            
        Returns:
            MTNMoMoResponse: MTN MoMo response
        """
        try:
            external_id = self._generate_external_id()
            
            # Prepare request data
            request_data = {
                "amount": str(int(amount)),
                "currency": self.mtn_config.currency,
                "externalId": external_id,
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": phone_number
                },
                "payerMessage": description,
                "payeeNote": reference
            }
            
            # Make API request
            response = await self._make_api_request(
                endpoint="/collection/v1_0/requesttopay",
                method="POST",
                data=request_data
            )
            
            # Parse response
            mtn_response = MTNMoMoResponse(
                status=True,
                reference_id=response.get("referenceId", ""),
                external_id=external_id,
                amount=str(int(amount)),
                currency=self.mtn_config.currency,
                financial_transaction_id=response.get("financialTransactionId", ""),
                payer_message=description,
                payee_note=reference,
                status_message="Request to pay initiated"
            )
            
            self.logger.info(
                "Collection initiated",
                reference_id=mtn_response.reference_id,
                phone_number=phone_number,
                amount=amount
            )
            
            return mtn_response
            
        except Exception as e:
            self.logger.error("Failed to initiate collection", error=str(e))
            raise
    
    async def initiate_disbursement(self, phone_number: str, amount: Decimal,
                                   reference: str, description: str) -> MTNMoMoResponse:
        """
        Initiate disbursement (B2C) transaction
        
        Args:
            phone_number: Recipient phone number
            amount: Transaction amount
            reference: Transaction reference
            description: Transaction description
            
        Returns:
            MTNMoMoResponse: MTN MoMo response
        """
        try:
            external_id = self._generate_external_id()
            
            # Prepare request data
            request_data = {
                "amount": str(int(amount)),
                "currency": self.mtn_config.currency,
                "externalId": external_id,
                "payee": {
                    "partyIdType": "MSISDN",
                    "partyId": phone_number
                },
                "payerMessage": description,
                "payeeNote": reference
            }
            
            # Use disbursement subscription key
            url = f"{self.base_url}/disbursement/v1_0/transfer"
            headers = {
                "Authorization": f"Bearer {await self._get_access_token()}",
                "X-Reference-Id": self._generate_reference_id(),
                "X-Target-Environment": self.mtn_config.target_environment,
                "Ocp-Apim-Subscription-Key": self.mtn_config.disbursement_subscription_key,
                "Content-Type": "application/json"
            }
            
            async with self._session.post(url, headers=headers, json=request_data) as response:
                result = await response.json()
            
            # Parse response
            mtn_response = MTNMoMoResponse(
                status=True,
                reference_id=result.get("referenceId", ""),
                external_id=external_id,
                amount=str(int(amount)),
                currency=self.mtn_config.currency,
                financial_transaction_id=result.get("financialTransactionId", ""),
                payer_message=description,
                payee_note=reference,
                status_message="Transfer initiated"
            )
            
            self.logger.info(
                "Disbursement initiated",
                reference_id=mtn_response.reference_id,
                phone_number=phone_number,
                amount=amount
            )
            
            return mtn_response
            
        except Exception as e:
            self.logger.error("Failed to initiate disbursement", error=str(e))
            raise
    
    async def check_transaction_status(self, reference_id: str) -> Optional[Dict[str, Any]]:
        """
        Check transaction status
        
        Args:
            reference_id: Reference ID to check
            
        Returns:
            Dict[str, Any]: Transaction status
        """
        try:
            # Make API request
            response = await self._make_api_request(
                endpoint=f"/collection/v1_0/requesttopay/{reference_id}",
                method="GET"
            )
            
            return response
            
        except Exception as e:
            self.logger.error("Failed to check transaction status", error=str(e))
            return None
    
    async def get_account_balance(self) -> Optional[MMOBalance]:
        """
        Get account balance
        
        Returns:
            MMOBalance: Account balance
        """
        try:
            # Make API request
            response = await self._make_api_request(
                endpoint="/collection/v1_0/account/balance",
                method="GET"
            )
            
            # Parse response
            balance = MMOBalance(
                account_id=f"mtn_momo_{self.mtn_config.country}",
                available_balance=Decimal(response.get("availableBalance", "0")),
                reserved_balance=Decimal(response.get("reservedBalance", "0")),
                total_balance=Decimal(response.get("totalBalance", "0")),
                currency=response.get("currency", self.mtn_config.currency),
                last_updated=datetime.now(timezone.utc)
            )
            
            return balance
            
        except Exception as e:
            self.logger.error("Failed to get account balance", error=str(e))
            return None
    
    def _parse_transaction_response(self, response: Dict[str, Any]) -> MMOTransaction:
        """Parse MTN MoMo transaction response"""
        transaction = MMOTransaction(
            transaction_id=response.get("referenceId", "unknown"),
            external_id=response.get("externalId"),
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal(response.get("amount", "0")),
            phone_number=response.get("payer", {}).get("partyId", ""),
            description=response.get("payerMessage", "MTN MoMo transaction"),
            status=TransactionStatus.PENDING
        )
        
        return transaction
    
    def _parse_balance_response(self, response: Dict[str, Any]) -> MMOBalance:
        """Parse MTN MoMo balance response"""
        balance = MMOBalance(
            account_id=f"mtn_momo_{self.mtn_config.country}",
            available_balance=Decimal(response.get("availableBalance", "0")),
            reserved_balance=Decimal(response.get("reservedBalance", "0")),
            total_balance=Decimal(response.get("totalBalance", "0")),
            currency=response.get("currency", self.mtn_config.currency),
            last_updated=datetime.now(timezone.utc)
        )
        
        return balance
    
    async def validate_phone_number(self, phone_number: str) -> bool:
        """Validate MTN MoMo phone number format"""
        # MTN MoMo phone numbers vary by country
        country_formats = {
            "UG": lambda p: p.startswith("256") and len(p) == 12,
            "GH": lambda p: p.startswith("233") and len(p) == 12,
            "NG": lambda p: p.startswith("234") and len(p) == 13,
            "RW": lambda p: p.startswith("250") and len(p) == 12,
            "BI": lambda p: p.startswith("257") and len(p) == 12,
            "ZM": lambda p: p.startswith("260") and len(p) == 12,
            "MW": lambda p: p.startswith("265") and len(p) == 12,
            "MZ": lambda p: p.startswith("258") and len(p) == 12,
            "AO": lambda p: p.startswith("244") and len(p) == 12,
            "NA": lambda p: p.startswith("264") and len(p) == 12,
            "ZW": lambda p: p.startswith("263") and len(p) == 12
        }
        
        validator = country_formats.get(self.mtn_config.country)
        if validator:
            return validator(phone_number)
        
        # Default validation
        return len(phone_number) >= 10
    
    async def get_supported_countries(self) -> List[str]:
        """Get MTN MoMo supported countries"""
        return ["UG", "GH", "NG", "RW", "BI", "ZM", "MW", "MZ", "AO", "NA", "ZW"]
    
    async def get_transaction_limits(self) -> Dict[str, Any]:
        """Get MTN MoMo transaction limits"""
        # Limits vary by country
        country_limits = {
            "UG": {"min_amount": 100, "max_amount": 3000000, "daily_limit": 10000000},
            "GH": {"min_amount": 1, "max_amount": 5000, "daily_limit": 20000},
            "NG": {"min_amount": 10, "max_amount": 100000, "daily_limit": 500000},
            "RW": {"min_amount": 100, "max_amount": 1000000, "daily_limit": 5000000},
            "BI": {"min_amount": 100, "max_amount": 500000, "daily_limit": 2000000},
            "ZM": {"min_amount": 1, "max_amount": 5000, "daily_limit": 20000},
            "MW": {"min_amount": 1, "max_amount": 5000, "daily_limit": 20000},
            "MZ": {"min_amount": 1, "max_amount": 5000, "daily_limit": 20000},
            "AO": {"min_amount": 100, "max_amount": 500000, "daily_limit": 2000000},
            "NA": {"min_amount": 1, "max_amount": 5000, "daily_limit": 20000},
            "ZW": {"min_amount": 1, "max_amount": 5000, "daily_limit": 20000}
        }
        
        limits = country_limits.get(self.mtn_config.country, {
            "min_amount": 1,
            "max_amount": 10000,
            "daily_limit": 50000
        })
        
        return {
            "min_amount": limits["min_amount"],
            "max_amount": limits["max_amount"],
            "daily_limit": limits["daily_limit"],
            "monthly_limit": limits["daily_limit"] * 30
        }
    
    async def process_callback(self, callback_data: Dict[str, Any]) -> MTNMoMoCallback:
        """
        Process MTN MoMo callback
        
        Args:
            callback_data: Callback data from MTN MoMo
            
        Returns:
            MTNMoMoCallback: Parsed callback data
        """
        try:
            callback = MTNMoMoCallback(
                amount=callback_data.get("amount", ""),
                currency=callback_data.get("currency", ""),
                external_id=callback_data.get("externalId", ""),
                financial_transaction_id=callback_data.get("financialTransactionId", ""),
                payer_message=callback_data.get("payerMessage", ""),
                payee_note=callback_data.get("payeeNote", ""),
                status=callback_data.get("status", ""),
                reason=callback_data.get("reason")
            )
            
            self.logger.info(
                "MTN MoMo callback processed",
                external_id=callback.external_id,
                status=callback.status,
                amount=callback.amount
            )
            
            return callback
            
        except Exception as e:
            self.logger.error("Failed to process MTN MoMo callback", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close MTN MoMo integration"""
        if self._session:
            await self._session.close()
        
        await super().close()


class MTNMoMoBridge:
    """
    MTN Mobile Money Bridge for universal mobile money operations
    
    Provides a simplified interface for MTN MoMo operations
    that can be used across different applications.
    """
    
    def __init__(self, config: MTNMoMoConfig, redis_client=None):
        self.mtn_momo = MTNMoMoIntegration(config, redis_client)
        self.logger = structlog.get_logger(__name__)
    
    async def send_money(self, phone_number: str, amount: Decimal, 
                        reference: str, description: str) -> Dict[str, Any]:
        """
        Send money via MTN Mobile Money
        
        Args:
            phone_number: Recipient phone number
            amount: Amount to send
            reference: Transaction reference
            description: Transaction description
            
        Returns:
            Dict[str, Any]: Transaction result
        """
        try:
            # Validate phone number
            if not await self.mtn_momo.validate_phone_number(phone_number):
                raise ValueError("Invalid phone number format")
            
            # Check transaction limits
            limits = await self.mtn_momo.get_transaction_limits()
            if amount < limits["min_amount"] or amount > limits["max_amount"]:
                raise ValueError(f"Amount must be between {limits['min_amount']} and {limits['max_amount']}")
            
            # Initiate disbursement
            response = await self.mtn_momo.initiate_disbursement(
                phone_number=phone_number,
                amount=amount,
                reference=reference,
                description=description
            )
            
            return {
                "success": True,
                "transaction_id": response.reference_id,
                "external_id": response.external_id,
                "message": response.status_message,
                "status": "pending"
            }
            
        except Exception as e:
            self.logger.error("Failed to send money", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    async def collect_money(self, phone_number: str, amount: Decimal,
                           reference: str, description: str) -> Dict[str, Any]:
        """
        Collect money via MTN Mobile Money
        
        Args:
            phone_number: Customer phone number
            amount: Amount to collect
            reference: Transaction reference
            description: Transaction description
            
        Returns:
            Dict[str, Any]: Transaction result
        """
        try:
            # Validate phone number
            if not await self.mtn_momo.validate_phone_number(phone_number):
                raise ValueError("Invalid phone number format")
            
            # Check transaction limits
            limits = await self.mtn_momo.get_transaction_limits()
            if amount < limits["min_amount"] or amount > limits["max_amount"]:
                raise ValueError(f"Amount must be between {limits['min_amount']} and {limits['max_amount']}")
            
            # Initiate collection
            response = await self.mtn_momo.initiate_collection(
                phone_number=phone_number,
                amount=amount,
                reference=reference,
                description=description
            )
            
            return {
                "success": True,
                "transaction_id": response.reference_id,
                "external_id": response.external_id,
                "message": response.status_message,
                "status": "pending"
            }
            
        except Exception as e:
            self.logger.error("Failed to collect money", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    async def check_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check transaction status
        
        Args:
            transaction_id: Transaction ID to check
            
        Returns:
            Dict[str, Any]: Transaction status
        """
        try:
            status = await self.mtn_momo.check_transaction_status(transaction_id)
            
            if status:
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "status": status.get("status", "unknown"),
                    "amount": status.get("amount"),
                    "currency": status.get("currency"),
                    "external_id": status.get("externalId")
                }
            else:
                return {
                    "success": False,
                    "transaction_id": transaction_id,
                    "status": "not_found"
                }
                
        except Exception as e:
            self.logger.error("Failed to check transaction", error=str(e))
            return {
                "success": False,
                "transaction_id": transaction_id,
                "error": str(e),
                "status": "error"
            }
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance
        
        Returns:
            Dict[str, Any]: Account balance
        """
        try:
            balance = await self.mtn_momo.get_account_balance()
            
            if balance:
                return {
                    "success": True,
                    "available_balance": float(balance.available_balance),
                    "reserved_balance": float(balance.reserved_balance),
                    "total_balance": float(balance.total_balance),
                    "currency": balance.currency
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to get balance"
                }
                
        except Exception as e:
            self.logger.error("Failed to get balance", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get MTN MoMo integration health status"""
        return await self.mtn_momo.get_health_status()
    
    async def close(self) -> None:
        """Close MTN MoMo bridge"""
        await self.mtn_momo.close() 