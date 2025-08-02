"""
Base Banking Integration

Universal interface for banking integrations including traditional banks,
SWIFT, and other banking protocols.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from packages.integrations.data.redis_client import RedisClient

logger = structlog.get_logger(__name__)


class BankingProvider(str, Enum):
    """Banking providers"""
    SWIFT = "swift"
    ACH = "ach"
    SEPA = "sepa"
    FEDWIRE = "fedwire"
    CHAPS = "chaps"
    BACS = "bacs"
    CUSTOM = "custom"


class TransactionType(str, Enum):
    """Banking transaction types"""
    TRANSFER = "transfer"
    PAYMENT = "payment"
    WIRE = "wire"
    ACH_DEBIT = "ach_debit"
    ACH_CREDIT = "ach_credit"
    SEPA_CREDIT = "sepa_credit"
    SEPA_DEBIT = "sepa_debit"
    REFUND = "refund"
    REVERSAL = "reversal"


class TransactionStatus(str, Enum):
    """Transaction status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    RETURNED = "returned"


class AccountType(str, Enum):
    """Account types"""
    CHECKING = "checking"
    SAVINGS = "savings"
    BUSINESS = "business"
    MONEY_MARKET = "money_market"
    CERTIFICATE_OF_DEPOSIT = "certificate_of_deposit"


class BankingConfig(BaseModel):
    """Base configuration for banking integration"""
    provider: BankingProvider
    api_key: str
    api_secret: str
    environment: str = "sandbox"  # sandbox, production
    timeout: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Rate limiting
    rate_limit_per_minute: int = 50
    rate_limit_per_hour: int = 500
    
    # Cache settings
    cache_ttl: int = 300  # 5 minutes
    enable_caching: bool = True
    
    # Provider-specific settings
    provider_config: Dict[str, Any] = Field(default_factory=dict)


class BankAccount(BaseModel):
    """Bank account information"""
    account_id: str
    account_number: str
    routing_number: str
    account_type: AccountType
    currency: str
    bank_name: str
    bank_code: str
    account_holder_name: str
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BankTransaction(BaseModel):
    """Banking transaction model"""
    transaction_id: str
    external_id: Optional[str] = None
    transaction_type: TransactionType
    amount: Decimal
    currency: str
    from_account: str
    to_account: str
    description: str
    reference: str
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    fees: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BankBalance(BaseModel):
    """Account balance information"""
    account_id: str
    available_balance: Decimal
    current_balance: Decimal
    pending_balance: Decimal
    currency: str
    last_updated: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseBankingIntegration(ABC):
    """
    Base class for banking integrations
    
    Provides a common interface for all banking providers
    with standardized methods for transactions, account management,
    and status checking.
    """
    
    def __init__(self, config: BankingConfig, redis_client: Optional[RedisClient] = None):
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
    def _parse_transaction_response(self, response: Dict[str, Any]) -> BankTransaction:
        """Parse transaction response from provider"""
        pass
    
    @abstractmethod
    def _parse_balance_response(self, response: Dict[str, Any]) -> BankBalance:
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
    
    async def initiate_transfer(self, transaction: BankTransaction) -> BankTransaction:
        """
        Initiate a bank transfer
        
        Args:
            transaction: Transaction to initiate
            
        Returns:
            BankTransaction: Updated transaction with status
        """
        try:
            # Check rate limiting
            if not await self._check_rate_limit():
                transaction.status = TransactionStatus.FAILED
                transaction.error_message = "Rate limit exceeded"
                return transaction
            
            # Make API request
            response = await self._make_api_request(
                endpoint="/transfers/initiate",
                method="POST",
                data=transaction.dict()
            )
            
            # Parse response
            updated_transaction = self._parse_transaction_response(response)
            
            # Cache transaction
            cache_key = f"bank_transaction:{updated_transaction.transaction_id}"
            await self._set_cached_data(cache_key, updated_transaction.dict())
            
            self.logger.info(
                "Bank transfer initiated",
                transaction_id=updated_transaction.transaction_id,
                status=updated_transaction.status
            )
            
            return updated_transaction
            
        except Exception as e:
            self.logger.error(
                "Failed to initiate bank transfer",
                transaction_id=transaction.transaction_id,
                error=str(e)
            )
            
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = str(e)
            return transaction
    
    async def check_transaction_status(self, transaction_id: str) -> Optional[BankTransaction]:
        """
        Check transaction status
        
        Args:
            transaction_id: Transaction ID to check
            
        Returns:
            BankTransaction: Transaction status if found
        """
        try:
            # Check cache first
            cache_key = f"bank_transaction:{transaction_id}"
            cached_data = await self._get_cached_data(cache_key)
            
            if cached_data:
                return BankTransaction(**cached_data)
            
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
    
    async def get_account_balance(self, account_id: str) -> Optional[BankBalance]:
        """
        Get account balance
        
        Args:
            account_id: Account ID to check balance for
            
        Returns:
            BankBalance: Account balance if found
        """
        try:
            # Check cache first
            cache_key = f"bank_balance:{account_id}"
            cached_data = await self._get_cached_data(cache_key)
            
            if cached_data:
                return BankBalance(**cached_data)
            
            # Check rate limiting
            if not await self._check_rate_limit():
                return None
            
            # Make API request
            response = await self._make_api_request(
                endpoint=f"/accounts/{account_id}/balance",
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
                account_id=account_id,
                error=str(e)
            )
            return None
    
    async def get_account_info(self, account_id: str) -> Optional[BankAccount]:
        """
        Get account information
        
        Args:
            account_id: Account ID to get info for
            
        Returns:
            BankAccount: Account information if found
        """
        try:
            # Check cache first
            cache_key = f"bank_account:{account_id}"
            cached_data = await self._get_cached_data(cache_key)
            
            if cached_data:
                return BankAccount(**cached_data)
            
            # Check rate limiting
            if not await self._check_rate_limit():
                return None
            
            # Make API request
            response = await self._make_api_request(
                endpoint=f"/accounts/{account_id}",
                method="GET"
            )
            
            # Parse response (this would be implemented by subclasses)
            account = self._parse_account_response(response)
            
            # Cache result
            await self._set_cached_data(cache_key, account.dict(), ttl=3600)  # 1 hour
            
            return account
            
        except Exception as e:
            self.logger.error(
                "Failed to get account info",
                account_id=account_id,
                error=str(e)
            )
            return None
    
    def _parse_account_response(self, response: Dict[str, Any]) -> BankAccount:
        """Parse account response from provider"""
        # Base implementation - should be overridden by providers
        return BankAccount(
            account_id=response.get("account_id", "unknown"),
            account_number=response.get("account_number", ""),
            routing_number=response.get("routing_number", ""),
            account_type=AccountType.CHECKING,
            currency=response.get("currency", "USD"),
            bank_name=response.get("bank_name", ""),
            bank_code=response.get("bank_code", ""),
            account_holder_name=response.get("account_holder_name", ""),
            status=response.get("status", "active")
        )
    
    async def validate_account(self, account_number: str, routing_number: str) -> bool:
        """
        Validate account number and routing number
        
        Args:
            account_number: Account number to validate
            routing_number: Routing number to validate
            
        Returns:
            bool: True if valid
        """
        # Base implementation - should be overridden by providers
        return len(account_number) >= 8 and len(routing_number) >= 8
    
    async def get_supported_currencies(self) -> List[str]:
        """
        Get list of supported currencies for this provider
        
        Returns:
            List[str]: List of currency codes
        """
        # Base implementation - should be overridden by providers
        return ["USD", "EUR", "GBP"]
    
    async def get_transaction_limits(self) -> Dict[str, Any]:
        """
        Get transaction limits for this provider
        
        Returns:
            Dict[str, Any]: Transaction limits
        """
        # Base implementation - should be overridden by providers
        return {
            "min_amount": 0.01,
            "max_amount": 100000.0,
            "daily_limit": 1000000.0,
            "monthly_limit": 10000000.0
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
        
        self.logger.info("Banking integration closed", provider=self.config.provider)


class MockBankingIntegration(BaseBankingIntegration):
    """
    Mock banking integration for testing and development
    
    Provides a mock implementation that simulates banking operations
    without making actual API calls.
    """
    
    def __init__(self, config: BankingConfig, redis_client: Optional[RedisClient] = None):
        super().__init__(config, redis_client)
        self._mock_transactions: Dict[str, BankTransaction] = {}
        self._mock_balances: Dict[str, BankBalance] = {}
        self._mock_accounts: Dict[str, BankAccount] = {}
    
    def _initialize_client(self) -> None:
        """Initialize mock client"""
        self._client = None  # No actual client needed for mock
    
    async def _make_api_request(self, endpoint: str, method: str = "GET", 
                               data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock API request"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        if endpoint == "/transfers/initiate" and method == "POST":
            transaction_id = f"mock_bank_tx_{len(self._mock_transactions) + 1}"
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
            account_id = endpoint.split("/")[2]
            balance = self._mock_balances.get(account_id)
            if balance:
                return balance.dict()
            else:
                return {
                    "account_id": account_id,
                    "available_balance": "10000.00",
                    "current_balance": "10000.00",
                    "pending_balance": "0.00",
                    "currency": "USD"
                }
        
        elif "/accounts/" in endpoint and not "/balance" in endpoint:
            account_id = endpoint.split("/")[2]
            account = self._mock_accounts.get(account_id)
            if account:
                return account.dict()
            else:
                return {
                    "account_id": account_id,
                    "account_number": "1234567890",
                    "routing_number": "021000021",
                    "account_type": "checking",
                    "currency": "USD",
                    "bank_name": "Mock Bank",
                    "bank_code": "MOCK",
                    "account_holder_name": "John Doe",
                    "status": "active"
                }
        
        elif endpoint == "/health":
            return {
                "status": "healthy",
                "response_time": 0.05
            }
        
        return {"error": "Unknown endpoint"}
    
    def _parse_transaction_response(self, response: Dict[str, Any]) -> BankTransaction:
        """Parse mock transaction response"""
        if "error" in response:
            raise Exception(response["error"])
        
        transaction = BankTransaction(
            transaction_id=response["transaction_id"],
            external_id=response.get("external_id"),
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("1000.00"),
            currency="USD",
            from_account="1234567890",
            to_account="0987654321",
            description="Mock bank transfer",
            reference="MOCK_REF",
            status=TransactionStatus(response.get("status", "pending"))
        )
        
        # Store in mock storage
        self._mock_transactions[transaction.transaction_id] = transaction
        
        return transaction
    
    def _parse_balance_response(self, response: Dict[str, Any]) -> BankBalance:
        """Parse mock balance response"""
        if "error" in response:
            raise Exception(response["error"])
        
        balance = BankBalance(
            account_id=response["account_id"],
            available_balance=Decimal(response["available_balance"]),
            current_balance=Decimal(response["current_balance"]),
            pending_balance=Decimal(response["pending_balance"]),
            currency=response["currency"],
            last_updated=datetime.now(timezone.utc)
        )
        
        return balance
    
    async def validate_account(self, account_number: str, routing_number: str) -> bool:
        """Mock account validation"""
        return len(account_number) >= 8 and len(routing_number) >= 8
    
    async def get_supported_currencies(self) -> List[str]:
        """Mock supported currencies"""
        return ["USD", "EUR", "GBP", "CAD", "AUD"]
    
    async def get_transaction_limits(self) -> Dict[str, Any]:
        """Mock transaction limits"""
        return {
            "min_amount": 0.01,
            "max_amount": 100000.0,
            "daily_limit": 1000000.0,
            "monthly_limit": 10000000.0
        }
