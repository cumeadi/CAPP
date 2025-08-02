"""
Aptos Blockchain Integration

Universal Aptos blockchain integration for payment settlement,
liquidity management, and smart contract operations.
"""

import asyncio
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, timezone
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from packages.integrations.data.redis_client import RedisClient


logger = structlog.get_logger(__name__)


class TransactionStatus(str, Enum):
    """Aptos transaction status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"


class TransactionType(str, Enum):
    """Aptos transaction types"""
    PAYMENT_SETTLEMENT = "payment_settlement"
    BATCH_SETTLEMENT = "batch_settlement"
    LIQUIDITY_POOL_CREATE = "liquidity_pool_create"
    LIQUIDITY_ADD = "liquidity_add"
    LIQUIDITY_REMOVE = "liquidity_remove"
    SMART_CONTRACT_CALL = "smart_contract_call"


class AptosConfig(BaseModel):
    """Configuration for Aptos integration"""
    node_url: str = "https://fullnode.mainnet.aptoslabs.com"
    private_key: str
    account_address: str
    gas_unit_price: int = 100
    max_gas_amount: int = 1000000
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Pool configuration
    default_pool_fee: Decimal = Decimal("0.001")  # 0.1%
    min_liquidity: Decimal = Decimal("100.0")
    max_liquidity: Decimal = Decimal("1000000.0")
    
    # Cache configuration
    cache_ttl: int = 300  # 5 minutes
    enable_caching: bool = True


class AptosTransaction(BaseModel):
    """Aptos transaction model"""
    transaction_id: str
    transaction_type: TransactionType
    payload: Dict[str, Any]
    status: TransactionStatus = TransactionStatus.PENDING
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    gas_used: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LiquidityPool(BaseModel):
    """Liquidity pool model"""
    pool_id: str
    currency_pair: str
    total_liquidity: Decimal
    exchange_rate: Decimal
    fees: Decimal
    created_at: datetime
    last_updated: datetime
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AptosClient:
    """
    Aptos blockchain client
    
    Provides a unified interface for interacting with the Aptos blockchain
    with support for payment settlement, liquidity management, and smart contracts.
    """
    
    def __init__(self, config: AptosConfig, redis_client: Optional[RedisClient] = None):
        self.config = config
        self.redis_client = redis_client
        self.logger = structlog.get_logger(__name__)
        
        # Initialize connection
        self._connected = False
        self._transaction_counter = 0
        
        self.logger.info("Aptos client initialized", node_url=config.node_url)
    
    async def connect(self) -> bool:
        """Connect to Aptos blockchain"""
        try:
            # This would establish actual connection to Aptos
            # For now, simulate connection
            await asyncio.sleep(0.1)
            self._connected = True
            
            self.logger.info("Connected to Aptos blockchain")
            return True
            
        except Exception as e:
            self.logger.error("Failed to connect to Aptos", error=str(e))
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Aptos blockchain"""
        try:
            self._connected = False
            self.logger.info("Disconnected from Aptos blockchain")
            
        except Exception as e:
            self.logger.error("Failed to disconnect from Aptos", error=str(e))
    
    async def submit_transaction(self, transaction: AptosTransaction) -> str:
        """
        Submit transaction to Aptos blockchain
        
        Args:
            transaction: Transaction to submit
            
        Returns:
            str: Transaction hash
        """
        try:
            if not self._connected:
                raise RuntimeError("Not connected to Aptos blockchain")
            
            # Generate transaction hash
            self._transaction_counter += 1
            tx_hash = f"0x{transaction.transaction_id}_{self._transaction_counter:08x}"
            
            # Update transaction status
            transaction.status = TransactionStatus.SUBMITTED
            transaction.submitted_at = datetime.now(timezone.utc)
            
            # Cache transaction
            if self.redis_client and self.config.enable_caching:
                await self.redis_client.set(
                    f"aptos_tx:{tx_hash}",
                    transaction.dict(),
                    ttl=self.config.cache_ttl
                )
            
            self.logger.info("Transaction submitted", tx_hash=tx_hash, type=transaction.transaction_type)
            return tx_hash
            
        except Exception as e:
            self.logger.error("Failed to submit transaction", error=str(e))
            raise
    
    async def wait_for_finality(self, tx_hash: str, timeout: int = None) -> bool:
        """
        Wait for transaction finality
        
        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds (uses config default if None)
            
        Returns:
            bool: True if transaction is finalized
        """
        try:
            timeout = timeout or self.config.timeout_seconds
            
            # Simulate blockchain confirmation
            await asyncio.sleep(1)
            
            # Update transaction status
            if self.redis_client and self.config.enable_caching:
                cached_tx = await self.redis_client.get(f"aptos_tx:{tx_hash}")
                if cached_tx:
                    transaction = AptosTransaction(**cached_tx)
                    transaction.status = TransactionStatus.CONFIRMED
                    transaction.confirmed_at = datetime.now(timezone.utc)
                    await self.redis_client.set(
                        f"aptos_tx:{tx_hash}",
                        transaction.dict(),
                        ttl=self.config.cache_ttl
                    )
            
            self.logger.info("Transaction finalized", tx_hash=tx_hash)
            return True
            
        except Exception as e:
            self.logger.error("Failed to wait for finality", tx_hash=tx_hash, error=str(e))
            return False
    
    async def get_account_balance(self, account_address: str) -> Decimal:
        """
        Get account balance
        
        Args:
            account_address: Account address
            
        Returns:
            Decimal: Account balance
        """
        try:
            cache_key = f"aptos_balance:{account_address}"
            
            # Check cache first
            if self.redis_client and self.config.enable_caching:
                cached_balance = await self.redis_client.get(cache_key)
                if cached_balance:
                    return Decimal(str(cached_balance))
            
            # Fetch from blockchain (mock for now)
            balance = Decimal("1000.0")  # Mock balance
            
            # Cache balance
            if self.redis_client and self.config.enable_caching:
                await self.redis_client.set(cache_key, str(balance), ttl=self.config.cache_ttl)
            
            self.logger.info("Account balance retrieved", account_address=account_address, balance=balance)
            return balance
            
        except Exception as e:
            self.logger.error("Failed to get account balance", account_address=account_address, error=str(e))
            return Decimal("0.0")
    
    async def get_transaction_status(self, tx_hash: str) -> Optional[TransactionStatus]:
        """
        Get transaction status
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            TransactionStatus: Current transaction status
        """
        try:
            # Check cache first
            if self.redis_client and self.config.enable_caching:
                cached_tx = await self.redis_client.get(f"aptos_tx:{tx_hash}")
                if cached_tx:
                    transaction = AptosTransaction(**cached_tx)
                    return transaction.status
            
            # Query blockchain (mock for now)
            return TransactionStatus.CONFIRMED
            
        except Exception as e:
            self.logger.error("Failed to get transaction status", tx_hash=tx_hash, error=str(e))
            return None


class AptosSettlementService:
    """Service for handling payment settlements on Aptos"""
    
    def __init__(self, aptos_client: AptosClient):
        self.aptos_client = aptos_client
        self.logger = structlog.get_logger(__name__)
    
    async def settle_payment(
        self, 
        payment_id: str, 
        amount: Decimal, 
        from_currency: str, 
        to_currency: str,
        recipient_address: str
    ) -> str:
        """
        Settle payment on Aptos blockchain
        
        Args:
            payment_id: Payment identifier
            amount: Payment amount
            from_currency: Source currency
            to_currency: Target currency
            recipient_address: Recipient address
            
        Returns:
            str: Transaction hash
        """
        try:
            # Create settlement transaction
            transaction = AptosTransaction(
                transaction_id=payment_id,
                transaction_type=TransactionType.PAYMENT_SETTLEMENT,
                payload={
                    "amount": float(amount),
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "recipient_address": recipient_address,
                    "gas_unit_price": self.aptos_client.config.gas_unit_price,
                    "max_gas_amount": self.aptos_client.config.max_gas_amount
                }
            )
            
            # Submit transaction
            tx_hash = await self.aptos_client.submit_transaction(transaction)
            
            # Wait for finality
            finality_confirmed = await self.aptos_client.wait_for_finality(tx_hash)
            
            if not finality_confirmed:
                raise Exception("Transaction finality not confirmed")
            
            self.logger.info("Payment settled successfully", payment_id=payment_id, tx_hash=tx_hash)
            
            return tx_hash
            
        except Exception as e:
            self.logger.error("Payment settlement failed", payment_id=payment_id, error=str(e))
            raise
    
    async def batch_settle_payments(self, payments: List[Dict[str, Any]]) -> List[str]:
        """
        Batch settle multiple payments
        
        Args:
            payments: List of payment data
            
        Returns:
            List[str]: List of transaction hashes
        """
        try:
            # Create batch transaction
            transaction = AptosTransaction(
                transaction_id=f"batch_{datetime.now().timestamp()}",
                transaction_type=TransactionType.BATCH_SETTLEMENT,
                payload={
                    "payments": payments,
                    "gas_unit_price": self.aptos_client.config.gas_unit_price,
                    "max_gas_amount": self.aptos_client.config.max_gas_amount * len(payments)
                }
            )
            
            # Submit batch transaction
            tx_hash = await self.aptos_client.submit_transaction(transaction)
            
            # Wait for finality
            finality_confirmed = await self.aptos_client.wait_for_finality(tx_hash)
            
            if not finality_confirmed:
                raise Exception("Batch transaction finality not confirmed")
            
            self.logger.info("Batch settlement completed", tx_hash=tx_hash, payment_count=len(payments))
            
            return [tx_hash] * len(payments)  # Return same hash for all payments in batch
            
        except Exception as e:
            self.logger.error("Batch settlement failed", error=str(e))
            raise


class AptosLiquidityService:
    """Service for managing liquidity pools on Aptos"""
    
    def __init__(self, aptos_client: AptosClient):
        self.aptos_client = aptos_client
        self.logger = structlog.get_logger(__name__)
    
    async def create_liquidity_pool(
        self, 
        currency_pair: str, 
        initial_liquidity: Decimal,
        fees: Optional[Decimal] = None
    ) -> str:
        """
        Create liquidity pool for currency pair
        
        Args:
            currency_pair: Currency pair (e.g., "KES/UGX")
            initial_liquidity: Initial liquidity amount
            fees: Pool fees (uses default if None)
            
        Returns:
            str: Pool ID
        """
        try:
            if initial_liquidity < self.aptos_client.config.min_liquidity:
                raise ValueError(f"Initial liquidity below minimum: {self.aptos_client.config.min_liquidity}")
            
            if initial_liquidity > self.aptos_client.config.max_liquidity:
                raise ValueError(f"Initial liquidity above maximum: {self.aptos_client.config.max_liquidity}")
            
            pool_fees = fees or self.aptos_client.config.default_pool_fee
            
            # Create pool transaction
            transaction = AptosTransaction(
                transaction_id=f"pool_create_{currency_pair}_{datetime.now().timestamp()}",
                transaction_type=TransactionType.LIQUIDITY_POOL_CREATE,
                payload={
                    "currency_pair": currency_pair,
                    "initial_liquidity": float(initial_liquidity),
                    "fees": float(pool_fees),
                    "gas_unit_price": self.aptos_client.config.gas_unit_price,
                    "max_gas_amount": self.aptos_client.config.max_gas_amount
                }
            )
            
            # Submit transaction
            tx_hash = await self.aptos_client.submit_transaction(transaction)
            
            # Wait for finality
            finality_confirmed = await self.aptos_client.wait_for_finality(tx_hash)
            
            if not finality_confirmed:
                raise Exception("Pool creation finality not confirmed")
            
            pool_id = f"pool_{currency_pair}_{tx_hash[:8]}"
            
            self.logger.info("Liquidity pool created", pool_id=pool_id, currency_pair=currency_pair)
            
            return pool_id
            
        except Exception as e:
            self.logger.error("Failed to create liquidity pool", error=str(e))
            raise
    
    async def add_liquidity(self, pool_id: str, amount: Decimal) -> bool:
        """
        Add liquidity to pool
        
        Args:
            pool_id: Pool identifier
            amount: Amount to add
            
        Returns:
            bool: Success status
        """
        try:
            # Create add liquidity transaction
            transaction = AptosTransaction(
                transaction_id=f"add_liquidity_{pool_id}_{datetime.now().timestamp()}",
                transaction_type=TransactionType.LIQUIDITY_ADD,
                payload={
                    "pool_id": pool_id,
                    "amount": float(amount),
                    "gas_unit_price": self.aptos_client.config.gas_unit_price,
                    "max_gas_amount": self.aptos_client.config.max_gas_amount
                }
            )
            
            # Submit transaction
            tx_hash = await self.aptos_client.submit_transaction(transaction)
            
            # Wait for finality
            finality_confirmed = await self.aptos_client.wait_for_finality(tx_hash)
            
            if finality_confirmed:
                self.logger.info("Liquidity added", pool_id=pool_id, amount=amount, tx_hash=tx_hash)
                return True
            else:
                self.logger.error("Liquidity addition failed", pool_id=pool_id, amount=amount)
                return False
                
        except Exception as e:
            self.logger.error("Failed to add liquidity", error=str(e))
            return False
    
    async def remove_liquidity(self, pool_id: str, amount: Decimal) -> bool:
        """
        Remove liquidity from pool
        
        Args:
            pool_id: Pool identifier
            amount: Amount to remove
            
        Returns:
            bool: Success status
        """
        try:
            # Create remove liquidity transaction
            transaction = AptosTransaction(
                transaction_id=f"remove_liquidity_{pool_id}_{datetime.now().timestamp()}",
                transaction_type=TransactionType.LIQUIDITY_REMOVE,
                payload={
                    "pool_id": pool_id,
                    "amount": float(amount),
                    "gas_unit_price": self.aptos_client.config.gas_unit_price,
                    "max_gas_amount": self.aptos_client.config.max_gas_amount
                }
            )
            
            # Submit transaction
            tx_hash = await self.aptos_client.submit_transaction(transaction)
            
            # Wait for finality
            finality_confirmed = await self.aptos_client.wait_for_finality(tx_hash)
            
            if finality_confirmed:
                self.logger.info("Liquidity removed", pool_id=pool_id, amount=amount, tx_hash=tx_hash)
                return True
            else:
                self.logger.error("Liquidity removal failed", pool_id=pool_id, amount=amount)
                return False
                
        except Exception as e:
            self.logger.error("Failed to remove liquidity", error=str(e))
            return False
    
    async def get_pool_info(self, pool_id: str) -> Optional[LiquidityPool]:
        """
        Get liquidity pool information
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            LiquidityPool: Pool information
        """
        try:
            # Check cache first
            if self.aptos_client.redis_client and self.aptos_client.config.enable_caching:
                cached_pool = await self.aptos_client.redis_client.get(f"aptos_pool:{pool_id}")
                if cached_pool:
                    return LiquidityPool(**cached_pool)
            
            # Query blockchain (mock for now)
            pool_info = LiquidityPool(
                pool_id=pool_id,
                currency_pair="KES/UGX",
                total_liquidity=Decimal("10000.0"),
                exchange_rate=Decimal("0.025"),
                fees=Decimal("0.001"),
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )
            
            # Cache pool info
            if self.aptos_client.redis_client and self.aptos_client.config.enable_caching:
                await self.aptos_client.redis_client.set(
                    f"aptos_pool:{pool_id}",
                    pool_info.dict(),
                    ttl=self.aptos_client.config.cache_ttl
                )
            
            return pool_info
            
        except Exception as e:
            self.logger.error("Failed to get pool info", pool_id=pool_id, error=str(e))
            return None


class AptosIntegration:
    """
    Main Aptos integration class
    
    Provides a unified interface for all Aptos blockchain operations
    including settlement, liquidity management, and smart contracts.
    """
    
    def __init__(self, config: AptosConfig, redis_client: Optional[RedisClient] = None):
        self.config = config
        self.aptos_client = AptosClient(config, redis_client)
        self.settlement_service = AptosSettlementService(self.aptos_client)
        self.liquidity_service = AptosLiquidityService(self.aptos_client)
        self.logger = structlog.get_logger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize Aptos integration"""
        try:
            success = await self.aptos_client.connect()
            if success:
                self.logger.info("Aptos integration initialized successfully")
            return success
            
        except Exception as e:
            self.logger.error("Failed to initialize Aptos integration", error=str(e))
            return False
    
    async def shutdown(self) -> None:
        """Shutdown Aptos integration"""
        try:
            await self.aptos_client.disconnect()
            self.logger.info("Aptos integration shutdown")
            
        except Exception as e:
            self.logger.error("Failed to shutdown Aptos integration", error=str(e))
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get Aptos integration health status"""
        try:
            return {
                "connected": self.aptos_client._connected,
                "node_url": self.config.node_url,
                "account_address": self.config.account_address,
                "cache_enabled": self.config.enable_caching,
                "last_check": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get health status", error=str(e))
            return {"error": str(e)}
