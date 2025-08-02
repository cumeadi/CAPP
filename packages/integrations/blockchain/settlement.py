"""
Blockchain Settlement Service

Comprehensive settlement service for blockchain-based payment processing,
extracting the working settlement logic from CAPP and providing a unified
interface for multiple blockchain networks.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import structlog

from pydantic import BaseModel, Field

from .aptos import AptosClient, AptosConfig, AptosTransaction, TransactionStatus
from packages.integrations.data.redis_client import RedisClient, RedisConfig

logger = structlog.get_logger(__name__)


class SettlementStatus(str, Enum):
    """Settlement status enumeration"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SettlementType(str, Enum):
    """Settlement type enumeration"""
    PAYMENT_SETTLEMENT = "payment_settlement"
    BATCH_SETTLEMENT = "batch_settlement"
    LIQUIDITY_SETTLEMENT = "liquidity_settlement"
    REFUND_SETTLEMENT = "refund_settlement"
    FEE_SETTLEMENT = "fee_settlement"


class SettlementRequest(BaseModel):
    """Settlement request model"""
    settlement_id: str
    settlement_type: SettlementType
    amount: Decimal
    from_currency: str
    to_currency: str
    from_address: str
    to_address: str
    payment_id: Optional[str] = None
    batch_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SettlementResult(BaseModel):
    """Settlement result model"""
    settlement_id: str
    transaction_hash: Optional[str] = None
    status: SettlementStatus
    amount: Decimal
    from_currency: str
    to_currency: str
    from_address: str
    to_address: str
    gas_used: Optional[int] = None
    gas_price: Optional[int] = None
    total_cost: Optional[Decimal] = None
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchSettlementRequest(BaseModel):
    """Batch settlement request model"""
    batch_id: str
    settlements: List[SettlementRequest]
    priority: str = "normal"  # low, normal, high, urgent
    max_gas_price: Optional[int] = None
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchSettlementResult(BaseModel):
    """Batch settlement result model"""
    batch_id: str
    transaction_hash: Optional[str] = None
    status: SettlementStatus
    total_amount: Decimal
    settlement_count: int
    successful_settlements: int
    failed_settlements: int
    gas_used: Optional[int] = None
    gas_price: Optional[int] = None
    total_cost: Optional[Decimal] = None
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    settlement_results: List[SettlementResult] = Field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SettlementConfig(BaseModel):
    """Settlement configuration"""
    # Blockchain configuration
    blockchain_config: AptosConfig
    
    # Settlement settings
    max_settlement_amount: Decimal = Decimal("100000.0")
    min_settlement_amount: Decimal = Decimal("0.01")
    max_batch_size: int = 100
    max_gas_price: int = 1000
    gas_limit_multiplier: float = 1.2
    
    # Retry settings
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    retry_backoff_multiplier: float = 2.0
    
    # Confirmation settings
    confirmation_timeout: int = 300  # 5 minutes
    confirmation_blocks: int = 1
    enable_auto_confirmation: bool = True
    
    # Monitoring settings
    enable_monitoring: bool = True
    monitoring_interval: int = 30  # seconds
    
    # Redis configuration
    redis_config: Optional[RedisConfig] = None


class SettlementService:
    """
    Blockchain Settlement Service
    
    Provides comprehensive settlement functionality for blockchain-based payments:
    - Individual payment settlements
    - Batch settlements for efficiency
    - Liquidity pool settlements
    - Settlement monitoring and tracking
    - Error handling and retry logic
    """
    
    def __init__(self, config: SettlementConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        # Initialize blockchain client
        self.blockchain_client = AptosClient(config.blockchain_config)
        
        # Initialize Redis client for caching
        self.redis_client = None
        if config.redis_config:
            self.redis_client = RedisClient(config.redis_config)
        
        # Settlement tracking
        self.pending_settlements: Dict[str, SettlementRequest] = {}
        self.settlement_results: Dict[str, SettlementResult] = {}
        self.batch_settlements: Dict[str, BatchSettlementRequest] = {}
        
        # Monitoring task
        self.monitoring_task = None
        
        self.logger.info("Settlement service initialized")
    
    async def initialize(self) -> bool:
        """Initialize the settlement service"""
        try:
            # Connect to blockchain
            connected = await self.blockchain_client.connect()
            if not connected:
                raise Exception("Failed to connect to blockchain")
            
            # Connect to Redis if configured
            if self.redis_client:
                await self.redis_client.connect()
            
            # Start monitoring if enabled
            if self.config.enable_monitoring:
                self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            self.logger.info("Settlement service initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize settlement service", error=str(e))
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the settlement service"""
        try:
            # Stop monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect from blockchain
            await self.blockchain_client.disconnect()
            
            # Disconnect from Redis
            if self.redis_client:
                await self.redis_client.disconnect()
            
            self.logger.info("Settlement service shutdown completed")
            
        except Exception as e:
            self.logger.error("Error during settlement service shutdown", error=str(e))
    
    async def settle_payment(self, request: SettlementRequest) -> SettlementResult:
        """
        Settle a single payment
        
        Args:
            request: Settlement request
            
        Returns:
            SettlementResult: Settlement result
        """
        try:
            # Validate request
            if not await self._validate_settlement_request(request):
                return SettlementResult(
                    settlement_id=request.settlement_id,
                    status=SettlementStatus.FAILED,
                    amount=request.amount,
                    from_currency=request.from_currency,
                    to_currency=request.to_currency,
                    from_address=request.from_address,
                    to_address=request.to_address,
                    error_message="Invalid settlement request"
                )
            
            # Check if already processed
            cached_result = await self._get_cached_settlement_result(request.settlement_id)
            if cached_result:
                return cached_result
            
            # Create blockchain transaction
            transaction = await self._create_settlement_transaction(request)
            
            # Submit transaction
            tx_hash = await self.blockchain_client.submit_transaction(transaction)
            
            # Create initial result
            result = SettlementResult(
                settlement_id=request.settlement_id,
                transaction_hash=tx_hash,
                status=SettlementStatus.SUBMITTED,
                amount=request.amount,
                from_currency=request.from_currency,
                to_currency=request.to_currency,
                from_address=request.from_address,
                to_address=request.to_address,
                submitted_at=datetime.now(timezone.utc),
                metadata=request.metadata
            )
            
            # Store result
            self.settlement_results[request.settlement_id] = result
            
            # Cache result
            await self._cache_settlement_result(result)
            
            # Wait for confirmation if auto-confirmation is enabled
            if self.config.enable_auto_confirmation:
                confirmed_result = await self._wait_for_confirmation(tx_hash, request.settlement_id)
                if confirmed_result:
                    return confirmed_result
            
            self.logger.info(
                "Payment settlement submitted",
                settlement_id=request.settlement_id,
                transaction_hash=tx_hash,
                amount=request.amount
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Failed to settle payment",
                settlement_id=request.settlement_id,
                error=str(e)
            )
            
            return SettlementResult(
                settlement_id=request.settlement_id,
                status=SettlementStatus.FAILED,
                amount=request.amount,
                from_currency=request.from_currency,
                to_currency=request.to_currency,
                from_address=request.from_address,
                to_address=request.to_address,
                error_message=str(e)
            )
    
    async def batch_settle_payments(self, request: BatchSettlementRequest) -> BatchSettlementResult:
        """
        Settle multiple payments in a batch
        
        Args:
            request: Batch settlement request
            
        Returns:
            BatchSettlementResult: Batch settlement result
        """
        try:
            # Validate batch request
            if not await self._validate_batch_settlement_request(request):
                return BatchSettlementResult(
                    batch_id=request.batch_id,
                    status=SettlementStatus.FAILED,
                    total_amount=sum(s.amount for s in request.settlements),
                    settlement_count=len(request.settlements),
                    successful_settlements=0,
                    failed_settlements=len(request.settlements),
                    error_message="Invalid batch settlement request"
                )
            
            # Check if already processed
            cached_result = await self._get_cached_batch_result(request.batch_id)
            if cached_result:
                return cached_result
            
            # Create batch transaction
            batch_transaction = await self._create_batch_settlement_transaction(request)
            
            # Submit batch transaction
            tx_hash = await self.blockchain_client.submit_transaction(batch_transaction)
            
            # Create initial batch result
            total_amount = sum(s.amount for s in request.settlements)
            batch_result = BatchSettlementResult(
                batch_id=request.batch_id,
                transaction_hash=tx_hash,
                status=SettlementStatus.SUBMITTED,
                total_amount=total_amount,
                settlement_count=len(request.settlements),
                successful_settlements=0,
                failed_settlements=0,
                submitted_at=datetime.now(timezone.utc),
                metadata=request.metadata
            )
            
            # Create individual settlement results
            for settlement_request in request.settlements:
                settlement_result = SettlementResult(
                    settlement_id=settlement_request.settlement_id,
                    transaction_hash=tx_hash,
                    status=SettlementStatus.SUBMITTED,
                    amount=settlement_request.amount,
                    from_currency=settlement_request.from_currency,
                    to_currency=settlement_request.to_currency,
                    from_address=settlement_request.from_address,
                    to_address=settlement_request.to_address,
                    submitted_at=datetime.now(timezone.utc),
                    metadata=settlement_request.metadata
                )
                
                batch_result.settlement_results.append(settlement_result)
                self.settlement_results[settlement_request.settlement_id] = settlement_result
            
            # Store batch result
            self.batch_settlements[request.batch_id] = request
            
            # Cache batch result
            await self._cache_batch_result(batch_result)
            
            # Wait for confirmation if auto-confirmation is enabled
            if self.config.enable_auto_confirmation:
                confirmed_result = await self._wait_for_batch_confirmation(tx_hash, request.batch_id)
                if confirmed_result:
                    return confirmed_result
            
            self.logger.info(
                "Batch settlement submitted",
                batch_id=request.batch_id,
                transaction_hash=tx_hash,
                settlement_count=len(request.settlements),
                total_amount=total_amount
            )
            
            return batch_result
            
        except Exception as e:
            self.logger.error(
                "Failed to batch settle payments",
                batch_id=request.batch_id,
                error=str(e)
            )
            
            return BatchSettlementResult(
                batch_id=request.batch_id,
                status=SettlementStatus.FAILED,
                total_amount=sum(s.amount for s in request.settlements),
                settlement_count=len(request.settlements),
                successful_settlements=0,
                failed_settlements=len(request.settlements),
                error_message=str(e)
            )
    
    async def get_settlement_status(self, settlement_id: str) -> Optional[SettlementResult]:
        """Get settlement status by ID"""
        try:
            # Check cache first
            cached_result = await self._get_cached_settlement_result(settlement_id)
            if cached_result:
                return cached_result
            
            # Check in-memory results
            if settlement_id in self.settlement_results:
                result = self.settlement_results[settlement_id]
                
                # Update status if still pending
                if result.status == SettlementStatus.SUBMITTED and result.transaction_hash:
                    updated_result = await self._check_transaction_status(result.transaction_hash, settlement_id)
                    if updated_result:
                        return updated_result
                
                return result
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get settlement status", settlement_id=settlement_id, error=str(e))
            return None
    
    async def get_batch_status(self, batch_id: str) -> Optional[BatchSettlementResult]:
        """Get batch settlement status by ID"""
        try:
            # Check cache first
            cached_result = await self._get_cached_batch_result(batch_id)
            if cached_result:
                return cached_result
            
            # Check in-memory batch results
            if batch_id in self.batch_settlements:
                # This would need to be implemented to track batch results
                pass
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get batch status", batch_id=batch_id, error=str(e))
            return None
    
    async def cancel_settlement(self, settlement_id: str) -> bool:
        """Cancel a pending settlement"""
        try:
            # Check if settlement exists and is cancellable
            if settlement_id in self.settlement_results:
                result = self.settlement_results[settlement_id]
                
                if result.status in [SettlementStatus.PENDING, SettlementStatus.SUBMITTED]:
                    # Update status to cancelled
                    result.status = SettlementStatus.CANCELLED
                    
                    # Update cache
                    await self._cache_settlement_result(result)
                    
                    self.logger.info("Settlement cancelled", settlement_id=settlement_id)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to cancel settlement", settlement_id=settlement_id, error=str(e))
            return False
    
    async def _validate_settlement_request(self, request: SettlementRequest) -> bool:
        """Validate settlement request"""
        try:
            # Check amount limits
            if request.amount < self.config.min_settlement_amount:
                self.logger.warning(
                    "Settlement amount below minimum",
                    amount=request.amount,
                    min_amount=self.config.min_settlement_amount
                )
                return False
            
            if request.amount > self.config.max_settlement_amount:
                self.logger.warning(
                    "Settlement amount above maximum",
                    amount=request.amount,
                    max_amount=self.config.max_settlement_amount
                )
                return False
            
            # Validate addresses
            if not request.from_address or not request.to_address:
                self.logger.warning("Invalid addresses", from_address=request.from_address, to_address=request.to_address)
                return False
            
            # Validate currencies
            if not request.from_currency or not request.to_currency:
                self.logger.warning("Invalid currencies", from_currency=request.from_currency, to_currency=request.to_currency)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Settlement request validation failed", error=str(e))
            return False
    
    async def _validate_batch_settlement_request(self, request: BatchSettlementRequest) -> bool:
        """Validate batch settlement request"""
        try:
            # Check batch size
            if len(request.settlements) > self.config.max_batch_size:
                self.logger.warning(
                    "Batch size exceeds maximum",
                    batch_size=len(request.settlements),
                    max_size=self.config.max_batch_size
                )
                return False
            
            # Validate individual settlements
            for settlement in request.settlements:
                if not await self._validate_settlement_request(settlement):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error("Batch settlement request validation failed", error=str(e))
            return False
    
    async def _create_settlement_transaction(self, request: SettlementRequest) -> AptosTransaction:
        """Create blockchain transaction for settlement"""
        try:
            payload = {
                "type": "payment_settlement",
                "settlement_id": request.settlement_id,
                "amount": float(request.amount),
                "from_currency": request.from_currency,
                "to_currency": request.to_currency,
                "from_address": request.from_address,
                "to_address": request.to_address,
                "payment_id": request.payment_id,
                "metadata": request.metadata
            }
            
            return AptosTransaction(
                transaction_id=request.settlement_id,
                transaction_type="payment_settlement",
                payload=payload,
                status=TransactionStatus.PENDING
            )
            
        except Exception as e:
            self.logger.error("Failed to create settlement transaction", error=str(e))
            raise
    
    async def _create_batch_settlement_transaction(self, request: BatchSettlementRequest) -> AptosTransaction:
        """Create blockchain transaction for batch settlement"""
        try:
            settlements_data = []
            for settlement in request.settlements:
                settlements_data.append({
                    "settlement_id": settlement.settlement_id,
                    "amount": float(settlement.amount),
                    "from_currency": settlement.from_currency,
                    "to_currency": settlement.to_currency,
                    "from_address": settlement.from_address,
                    "to_address": settlement.to_address,
                    "payment_id": settlement.payment_id
                })
            
            payload = {
                "type": "batch_settlement",
                "batch_id": request.batch_id,
                "settlements": settlements_data,
                "priority": request.priority,
                "deadline": request.deadline.isoformat() if request.deadline else None,
                "metadata": request.metadata
            }
            
            return AptosTransaction(
                transaction_id=request.batch_id,
                transaction_type="batch_settlement",
                payload=payload,
                status=TransactionStatus.PENDING
            )
            
        except Exception as e:
            self.logger.error("Failed to create batch settlement transaction", error=str(e))
            raise
    
    async def _wait_for_confirmation(self, tx_hash: str, settlement_id: str) -> Optional[SettlementResult]:
        """Wait for transaction confirmation"""
        try:
            confirmed = await self.blockchain_client.wait_for_finality(tx_hash, self.config.confirmation_timeout)
            
            if confirmed:
                # Update settlement result
                result = self.settlement_results.get(settlement_id)
                if result:
                    result.status = SettlementStatus.CONFIRMED
                    result.confirmed_at = datetime.now(timezone.utc)
                    
                    # Update cache
                    await self._cache_settlement_result(result)
                    
                    self.logger.info("Settlement confirmed", settlement_id=settlement_id, tx_hash=tx_hash)
                    return result
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to wait for confirmation", error=str(e))
            return None
    
    async def _wait_for_batch_confirmation(self, tx_hash: str, batch_id: str) -> Optional[BatchSettlementResult]:
        """Wait for batch transaction confirmation"""
        try:
            confirmed = await self.blockchain_client.wait_for_finality(tx_hash, self.config.confirmation_timeout)
            
            if confirmed:
                # Update batch result
                # This would need to be implemented to track batch results
                self.logger.info("Batch settlement confirmed", batch_id=batch_id, tx_hash=tx_hash)
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to wait for batch confirmation", error=str(e))
            return None
    
    async def _check_transaction_status(self, tx_hash: str, settlement_id: str) -> Optional[SettlementResult]:
        """Check transaction status and update settlement result"""
        try:
            status = await self.blockchain_client.get_transaction_status(tx_hash)
            
            if status:
                result = self.settlement_results.get(settlement_id)
                if result:
                    if status == TransactionStatus.CONFIRMED:
                        result.status = SettlementStatus.CONFIRMED
                        result.confirmed_at = datetime.now(timezone.utc)
                    elif status == TransactionStatus.FAILED:
                        result.status = SettlementStatus.FAILED
                        result.error_message = "Transaction failed on blockchain"
                    
                    # Update cache
                    await self._cache_settlement_result(result)
                    
                    return result
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to check transaction status", error=str(e))
            return None
    
    async def _get_cached_settlement_result(self, settlement_id: str) -> Optional[SettlementResult]:
        """Get cached settlement result from Redis"""
        try:
            if self.redis_client:
                cached_data = await self.redis_client.get(f"settlement:{settlement_id}")
                if cached_data:
                    return SettlementResult(**cached_data)
            return None
            
        except Exception as e:
            self.logger.error("Failed to get cached settlement result", error=str(e))
            return None
    
    async def _cache_settlement_result(self, result: SettlementResult) -> None:
        """Cache settlement result in Redis"""
        try:
            if self.redis_client:
                await self.redis_client.set(
                    f"settlement:{result.settlement_id}",
                    result.dict(),
                    ttl=3600  # 1 hour
                )
                
        except Exception as e:
            self.logger.error("Failed to cache settlement result", error=str(e))
    
    async def _get_cached_batch_result(self, batch_id: str) -> Optional[BatchSettlementResult]:
        """Get cached batch result from Redis"""
        try:
            if self.redis_client:
                cached_data = await self.redis_client.get(f"batch:{batch_id}")
                if cached_data:
                    return BatchSettlementResult(**cached_data)
            return None
            
        except Exception as e:
            self.logger.error("Failed to get cached batch result", error=str(e))
            return None
    
    async def _cache_batch_result(self, result: BatchSettlementResult) -> None:
        """Cache batch result in Redis"""
        try:
            if self.redis_client:
                await self.redis_client.set(
                    f"batch:{result.batch_id}",
                    result.dict(),
                    ttl=3600  # 1 hour
                )
                
        except Exception as e:
            self.logger.error("Failed to cache batch result", error=str(e))
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for pending settlements"""
        try:
            while True:
                await self._check_pending_settlements()
                await asyncio.sleep(self.config.monitoring_interval)
                
        except asyncio.CancelledError:
            self.logger.info("Settlement monitoring loop cancelled")
        except Exception as e:
            self.logger.error("Settlement monitoring loop error", error=str(e))
    
    async def _check_pending_settlements(self) -> None:
        """Check and update pending settlements"""
        try:
            for settlement_id, result in self.settlement_results.items():
                if result.status == SettlementStatus.SUBMITTED and result.transaction_hash:
                    await self._check_transaction_status(result.transaction_hash, settlement_id)
                    
        except Exception as e:
            self.logger.error("Failed to check pending settlements", error=str(e))
    
    async def get_settlement_metrics(self) -> Dict[str, Any]:
        """Get settlement service metrics"""
        try:
            metrics = {
                "total_settlements": len(self.settlement_results),
                "pending_settlements": 0,
                "confirmed_settlements": 0,
                "failed_settlements": 0,
                "total_amount_settled": Decimal("0"),
                "average_settlement_time": 0.0,
                "success_rate": 0.0
            }
            
            total_time = 0.0
            successful_count = 0
            
            for result in self.settlement_results.values():
                if result.status == SettlementStatus.PENDING:
                    metrics["pending_settlements"] += 1
                elif result.status == SettlementStatus.CONFIRMED:
                    metrics["confirmed_settlements"] += 1
                    successful_count += 1
                    metrics["total_amount_settled"] += result.amount
                    
                    if result.submitted_at and result.confirmed_at:
                        settlement_time = (result.confirmed_at - result.submitted_at).total_seconds()
                        total_time += settlement_time
                elif result.status == SettlementStatus.FAILED:
                    metrics["failed_settlements"] += 1
            
            # Calculate averages
            if successful_count > 0:
                metrics["average_settlement_time"] = total_time / successful_count
                metrics["success_rate"] = successful_count / len(self.settlement_results)
            
            return metrics
            
        except Exception as e:
            self.logger.error("Failed to get settlement metrics", error=str(e))
            return {} 