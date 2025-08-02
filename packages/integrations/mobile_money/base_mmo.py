"""
Base Mobile Money Operator (MMO) Integration

Universal interface for mobile money operators across Africa.
Provides a common abstraction for different mobile money providers.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from packages.integrations.data.redis_client import RedisClient, RedisConfig

logger = structlog.get_logger(__name__)


class MMOProvider(str, Enum):
    """Mobile Money Operator providers"""
    MPESA = "mpesa"
    ORANGE_MONEY = "orange_money"
    MTN_MOBILE_MONEY = "mtn_mobile_money"
    AIRTEL_MONEY = "airtel_money"
    VODAFONE_CASH = "vodafone_cash"
    ECOCASH = "ecocash"
    MPESA_UGANDA = "mpesa_uganda"


class TransactionStatus(str, Enum):
    """Transaction status"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TransactionType(str, Enum):
    """Transaction types"""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PAYMENT = "payment"
    REFUND = "refund"
    REVERSAL = "reversal"


class MMOConfig(BaseModel):
    """Base configuration for MMO integration"""
    provider: MMOProvider
    api_key: str
    api_secret: str
    environment: str = "sandbox"  # sandbox, production
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Rate limiting
    rate_limit_per_minute: int = 100
    rate_limit_per_hour: int = 1000
    
    # Cache settings
    cache_ttl: int = 300  # 5 minutes
    enable_caching: bool = True
    
    # Provider-specific settings
    provider_config: Dict[str, Any] = Field(default_factory=dict)


class MMOTransaction(BaseModel):
    """Mobile money transaction model"""
    transaction_id: str
    external_id: Optional[str] = None
    transaction_type: TransactionType
    amount: Decimal
    currency: str = "USD"
    phone_number: str
    description: str
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MMOBalance(BaseModel):
    """Account balance information"""
    account_id: str
    available_balance: Decimal
    reserved_balance: Decimal
    total_balance: Decimal
    currency: str
    last_updated: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MMOAccount(BaseModel):
    """Account information"""
    account_id: str
    phone_number: str
    account_name: str
    account_type: str
    status: str
    created_at: datetime
    last_activity: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseMMOIntegration(ABC):
    """
    Base class for Mobile Money Operator integrations
    
    Provides a common interface for all mobile money providers
    with standardized methods for transactions, account management,
    and status checking.
    """
    
    def __init__(self, config: MMOConfig, redis_client: Optional[RedisClient] = None):
        self.config = config
        self.redis_client = redis_client
        self.logger = structlog.get_logger(__name__)
        
        # Rate limiting
        self._request_count = 0
        self._last_request_time = datetime.now(timezone.utc)
        
        # Initialize provider-specific client
        self._client = None
        self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize provider-specific client"""
        pass
    
    @abstractmethod
    async def _make_api_request(self, endpoint: str, method: str = "GET", 
                               data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make API request to provider"""
        pass
    
    @abstractmethod
    def _parse_transaction_response(self, response: Dict[str, Any]) -> MMOTransaction:
        """Parse transaction response from provider"""
        pass
    
    @abstractmethod
    def _parse_balance_response(self, response: Dict[str, Any]) -> MMOBalance:
        """Parse balance response from provider"""
        pass
    
    async def _check_rate_limit(self) -> bool:
        """Check rate limiting"""
        now = datetime.now(timezone.utc)
        
        # Reset counter if more than a minute has passed
        if (now - self._last_request_time).total_seconds() > 60:
            self._request_count = 0
            self._last_request_time = now
        
        if self._request_count >= self.config.rate_limit_per_minute:
            self.logger.warning("Rate limit exceeded", provider=self.config.provider)
            return False
        
        self._request_count += 1
        return True
    
    async def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data"""
        if not self.redis_client or not self.config.enable_caching:
            return None
        
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            self.logger.warning("Failed to get cached data", key=key, error=str(e))
            return None
    
    async def _set_cached_data(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached data"""
        if not self.redis_client or not self.config.enable_caching:
            return False
        
        try:
            ttl = ttl or self.config.cache_ttl
            return await self.redis_client.set(key, value, ttl=ttl)
        except Exception as e:
            self.logger.warning("Failed to set cached data", key=key, error=str(e))
            return False
    
    async def initiate_transaction(self, transaction: MMOTransaction) -> MMOTransaction:
        """
        Initiate a mobile money transaction
        
        Args:
            transaction: Transaction to initiate
            
        Returns:
            MMOTransaction: Updated transaction with status
        """
        try:
            # Check rate limiting
            if not await self._check_rate_limit():
                transaction.status = TransactionStatus.FAILED
                transaction.error_message = "Rate limit exceeded"
                return transaction
            
            # Make API request
            response = await self._make_api_request(
                endpoint="/transactions/initiate",
                method="POST",
                data=transaction.dict()
            )
            
            # Parse response
            updated_transaction = self._parse_transaction_response(response)
            
            # Cache transaction
            cache_key = f"mmo_transaction:{updated_transaction.transaction_id}"
            await self._set_cached_data(cache_key, updated_transaction.dict())
            
            self.logger.info(
                "Transaction initiated",
                transaction_id=updated_transaction.transaction_id,
                status=updated_transaction.status
            )
            
            return updated_transaction
            
        except Exception as e:
            self.logger.error(
                "Failed to initiate transaction",
                transaction_id=transaction.transaction_id,
                error=str(e)
            )
            
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = str(e)
            return transaction
    
    async def check_transaction_status(self, transaction_id: str) -> Optional[MMOTransaction]:
        """
        Check transaction status
        
        Args:
            transaction_id: Transaction ID to check
            
        Returns:
            MMOTransaction: Transaction status if found
        """
        try:
            # Check cache first
            cache_key = f"mmo_transaction:{transaction_id}"
            cached_data = await self._get_cached_data(cache_key)
            
            if cached_data:
                return MMOTransaction(**cached_data)
            
            # Check rate limiting
            if not await self._check_rate_limit():
                return None
            
            # Make API request
            response = await self._make_api_request(
                endpoint=f"/transactions/{transaction_id}/status",
                method="GET"
            )
            
            # Parse response
            transaction = self._parse_transaction_response(response)
            
            # Cache result
            await self._set_cached_data(cache_key, transaction.dict())
            
            return transaction
            
        except Exception as e:
            self.logger.error(
                "Failed to check transaction status",
                transaction_id=transaction_id,
                error=str(e)
            )
            return None
    
    async def get_account_balance(self, phone_number: str) -> Optional[MMOBalance]:
        """
        Get account balance
        
        Args:
            phone_number: Phone number to check balance for
            
        Returns:
            MMOBalance: Account balance if found
        """
        try:
            # Check cache first
            cache_key = f"mmo_balance:{phone_number}"
            cached_data = await self._get_cached_data(cache_key)
            
            if cached_data:
                return MMOBalance(**cached_data)
            
            # Check rate limiting
            if not await self._check_rate_limit():
                return None
            
            # Make API request
            response = await self._make_api_request(
                endpoint=f"/accounts/{phone_number}/balance",
                method="GET"
            )
            
            # Parse response
            balance = self._parse_balance_response(response)
            
            # Cache result (shorter TTL for balance)
            await self._set_cached_data(cache_key, balance.dict(), ttl=60)
            
            return balance
            
        except Exception as e:
            self.logger.error(
                "Failed to get account balance",
                phone_number=phone_number,
                error=str(e)
            )
            return None
    
    async def validate_phone_number(self, phone_number: str) -> bool:
        """
        Validate phone number format for this provider
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            bool: True if valid
        """
        # Base implementation - should be overridden by providers
        return len(phone_number) >= 10
    
    async def get_supported_countries(self) -> List[str]:
        """
        Get list of supported countries for this provider
        
        Returns:
            List[str]: List of country codes
        """
        # Base implementation - should be overridden by providers
        return []
    
    async def get_transaction_limits(self) -> Dict[str, Any]:
        """
        Get transaction limits for this provider
        
        Returns:
            Dict[str, Any]: Transaction limits
        """
        # Base implementation - should be overridden by providers
        return {
            "min_amount": 0.01,
            "max_amount": 10000.0,
            "daily_limit": 50000.0,
            "monthly_limit": 500000.0
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the integration
        
        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Make a simple API call to check health
            response = await self._make_api_request("/health", method="GET")
            
            return {
                "provider": self.config.provider,
                "status": "healthy",
                "response_time": response.get("response_time", 0),
                "last_check": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "provider": self.config.provider,
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.now(timezone.utc).isoformat()
            }
    
    async def close(self) -> None:
        """Close the integration"""
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                self.logger.warning("Error closing client", error=str(e))
        
        self.logger.info("MMO integration closed", provider=self.config.provider)


class MockMMOIntegration(BaseMMOIntegration):
    """
    Mock MMO integration for testing and development
    
    Provides a mock implementation that simulates mobile money operations
    without making actual API calls.
    """
    
    def __init__(self, config: MMOConfig, redis_client: Optional[RedisClient] = None):
        super().__init__(config, redis_client)
        self._mock_transactions: Dict[str, MMOTransaction] = {}
        self._mock_balances: Dict[str, MMOBalance] = {}
    
    def _initialize_client(self) -> None:
        """Initialize mock client"""
        self._client = None  # No actual client needed for mock
    
    async def _make_api_request(self, endpoint: str, method: str = "GET", 
                               data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock API request"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        if endpoint == "/transactions/initiate" and method == "POST":
            transaction_id = f"mock_tx_{len(self._mock_transactions) + 1}"
            return {
                "transaction_id": transaction_id,
                "status": "pending",
                "external_id": f"ext_{transaction_id}",
                "response_time": 0.1
            }
        
        elif "/transactions/" in endpoint and "/status" in endpoint:
            transaction_id = endpoint.split("/")[2]
            transaction = self._mock_transactions.get(transaction_id)
            if transaction:
                return transaction.dict()
            else:
                return {"error": "Transaction not found"}
        
        elif "/accounts/" in endpoint and "/balance" in endpoint:
            phone_number = endpoint.split("/")[2]
            balance = self._mock_balances.get(phone_number)
            if balance:
                return balance.dict()
            else:
                return {
                    "account_id": phone_number,
                    "available_balance": "1000.00",
                    "reserved_balance": "0.00",
                    "total_balance": "1000.00",
                    "currency": "USD"
                }
        
        elif endpoint == "/health":
            return {
                "status": "healthy",
                "response_time": 0.05
            }
        
        return {"error": "Unknown endpoint"}
    
    def _parse_transaction_response(self, response: Dict[str, Any]) -> MMOTransaction:
        """Parse mock transaction response"""
        if "error" in response:
            raise Exception(response["error"])
        
        transaction = MMOTransaction(
            transaction_id=response["transaction_id"],
            external_id=response.get("external_id"),
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("100.00"),
            phone_number="+1234567890",
            description="Mock transaction",
            status=TransactionStatus(response.get("status", "pending"))
        )
        
        # Store in mock storage
        self._mock_transactions[transaction.transaction_id] = transaction
        
        return transaction
    
    def _parse_balance_response(self, response: Dict[str, Any]) -> MMOBalance:
        """Parse mock balance response"""
        if "error" in response:
            raise Exception(response["error"])
        
        balance = MMOBalance(
            account_id=response["account_id"],
            available_balance=Decimal(response["available_balance"]),
            reserved_balance=Decimal(response["reserved_balance"]),
            total_balance=Decimal(response["total_balance"]),
            currency=response["currency"],
            last_updated=datetime.now(timezone.utc)
        )
        
        return balance
    
    async def validate_phone_number(self, phone_number: str) -> bool:
        """Mock phone number validation"""
        return phone_number.startswith("+") and len(phone_number) >= 10
    
    async def get_supported_countries(self) -> List[str]:
        """Mock supported countries"""
        return ["KE", "UG", "TZ", "RW", "BI"]
    
    async def get_transaction_limits(self) -> Dict[str, Any]:
        """Mock transaction limits"""
        return {
            "min_amount": 0.01,
            "max_amount": 10000.0,
            "daily_limit": 50000.0,
            "monthly_limit": 500000.0
        }
