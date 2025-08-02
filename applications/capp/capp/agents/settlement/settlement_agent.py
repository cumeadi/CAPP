"""
Settlement Agent for CAPP

Handles blockchain settlement operations including payment batching,
transaction submission, and verification on the Aptos blockchain.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field
import structlog

from ..agents.base import BasePaymentAgent, AgentConfig
from ..models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentRoute,
    Country, Currency
)
from ..core.aptos import get_aptos_client, AptosSettlementService
from ..core.redis import get_cache
from ..config.settings import get_settings

logger = structlog.get_logger(__name__)


class SettlementConfig(AgentConfig):
    """Configuration for settlement agent"""
    agent_type: str = "settlement"
    
    # Batching settings
    max_batch_size: int = 50
    max_batch_wait_time: int = 30  # seconds
    min_batch_size: int = 5
    
    # Transaction settings
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    transaction_timeout: int = 60  # seconds
    
    # Gas optimization
    gas_limit: int = 1000000
    gas_price: int = 100  # nanoaptos
    
    # Performance settings
    max_concurrent_batches: int = 10
    batch_processing_interval: int = 10  # seconds


class SettlementBatch(BaseModel):
    """Batch of payments for settlement"""
    batch_id: str
    payments: List[CrossBorderPayment]
    total_amount: Decimal
    from_currency: Currency
    to_currency: Currency
    created_at: datetime
    status: str = "pending"  # pending, processing, completed, failed
    transaction_hash: Optional[str] = None
    gas_used: Optional[int] = None
    processing_time: Optional[float] = None


class SettlementResult(BaseModel):
    """Result of settlement operation"""
    success: bool
    batch_id: str
    transaction_hash: Optional[str] = None
    gas_used: Optional[int] = None
    processing_time: Optional[float] = None
    message: str
    failed_payments: List[str] = []


class SettlementAgent(BasePaymentAgent):
    """
    Settlement Agent
    
    Handles blockchain settlement operations:
    - Batches payments for efficient processing
    - Submits transactions to Aptos blockchain
    - Verifies transaction completion
    - Handles settlement failures and retries
    """
    
    def __init__(self, config: SettlementConfig):
        super().__init__(config)
        self.config = config
        self.cache = get_cache()
        self.aptos_client = get_aptos_client()
        self.settlement_service = AptosSettlementService()
        
        # Batch management
        self.pending_batches: Dict[str, SettlementBatch] = {}
        self.processing_batches: Dict[str, SettlementBatch] = {}
        self.completed_batches: Dict[str, SettlementBatch] = {}
        
        # Payment queue for batching
        self.payment_queue: List[CrossBorderPayment] = []
        self.last_batch_time = datetime.now(timezone.utc)
        
        # Start batch processing task
        self._start_batch_processor()
    
    def _start_batch_processor(self):
        """Start the batch processing task"""
        async def batch_processor():
            while True:
                try:
                    await self._process_pending_batches()
                    await asyncio.sleep(self.config.batch_processing_interval)
                except Exception as e:
                    self.logger.error("Batch processor error", error=str(e))
                    await asyncio.sleep(5)  # Short delay on error
        
        # Start the task
        asyncio.create_task(batch_processor())
    
    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """
        Process payment for settlement
        
        Args:
            payment: The payment to settle
            
        Returns:
            PaymentResult: The settlement result
        """
        try:
            self.logger.info(
                "Processing settlement for payment",
                payment_id=payment.payment_id,
                amount=payment.amount,
                from_currency=payment.from_currency,
                to_currency=payment.to_currency
            )
            
            # Add payment to queue for batching
            await self._add_payment_to_queue(payment)
            
            # Check if we should create a new batch
            if await self._should_create_batch():
                await self._create_and_process_batch()
            
            self.logger.info(
                "Payment queued for settlement",
                payment_id=payment.payment_id
            )
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.SETTLING,
                message="Payment queued for settlement"
            )
            
        except Exception as e:
            self.logger.error("Settlement processing failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Settlement processing failed: {str(e)}",
                error_code="SETTLEMENT_ERROR"
            )
    
    async def validate_payment(self, payment: CrossBorderPayment) -> bool:
        """Validate if payment can be settled"""
        try:
            # Check if payment has required fields
            if not payment.payment_id or not payment.amount:
                return False
            
            # Check if payment is in correct status
            if payment.status not in [PaymentStatus.PROCESSING, PaymentStatus.SETTLING]:
                return False
            
            # Check if payment has blockchain transaction hash
            if not payment.blockchain_tx_hash:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Payment validation failed", error=str(e))
            return False
    
    async def prepare_settlement(self, payments: List[CrossBorderPayment]) -> SettlementBatch:
        """
        Prepare a batch of payments for settlement
        
        Args:
            payments: List of payments to batch
            
        Returns:
            SettlementBatch: The prepared batch
        """
        try:
            if not payments:
                raise ValueError("No payments provided for settlement")
            
            # Group payments by currency pair
            currency_pairs = {}
            for payment in payments:
                pair_key = f"{payment.from_currency}-{payment.to_currency}"
                if pair_key not in currency_pairs:
                    currency_pairs[pair_key] = []
                currency_pairs[pair_key].append(payment)
            
            # Create batches for each currency pair
            batches = []
            for pair_key, pair_payments in currency_pairs.items():
                # Split into smaller batches if needed
                for i in range(0, len(pair_payments), self.config.max_batch_size):
                    batch_payments = pair_payments[i:i + self.config.max_batch_size]
                    
                    total_amount = sum(p.amount for p in batch_payments)
                    
                    batch = SettlementBatch(
                        batch_id=f"batch_{pair_key}_{datetime.now().timestamp()}_{i}",
                        payments=batch_payments,
                        total_amount=total_amount,
                        from_currency=batch_payments[0].from_currency,
                        to_currency=batch_payments[0].to_currency,
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    batches.append(batch)
            
            self.logger.info(
                "Prepared settlement batches",
                num_batches=len(batches),
                total_payments=len(payments)
            )
            
            return batches[0] if batches else None
            
        except Exception as e:
            self.logger.error("Failed to prepare settlement", error=str(e))
            raise
    
    async def execute_settlement(self, batch: SettlementBatch) -> str:
        """
        Execute settlement batch on blockchain
        
        Args:
            batch: The batch to settle
            
        Returns:
            str: Transaction hash
        """
        try:
            self.logger.info(
                "Executing settlement batch",
                batch_id=batch.batch_id,
                num_payments=len(batch.payments),
                total_amount=batch.total_amount
            )
            
            # Update batch status
            batch.status = "processing"
            self.processing_batches[batch.batch_id] = batch
            
            start_time = datetime.now(timezone.utc)
            
            # Prepare settlement data
            settlement_data = {
                "batch_id": batch.batch_id,
                "payments": [
                    {
                        "payment_id": str(p.payment_id),
                        "amount": float(p.amount),
                        "from_currency": p.from_currency,
                        "to_currency": p.to_currency,
                        "sender": p.sender,
                        "recipient": p.recipient,
                        "blockchain_tx_hash": p.blockchain_tx_hash
                    }
                    for p in batch.payments
                ],
                "total_amount": float(batch.total_amount),
                "from_currency": batch.from_currency,
                "to_currency": batch.to_currency
            }
            
            # Submit to blockchain
            tx_hash = await self.settlement_service.submit_settlement_batch(settlement_data)
            
            # Wait for transaction confirmation
            confirmed = await self.settlement_service.wait_for_confirmation(tx_hash)
            
            if not confirmed:
                raise Exception("Transaction confirmation timeout")
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Update batch
            batch.status = "completed"
            batch.transaction_hash = tx_hash
            batch.processing_time = processing_time
            batch.gas_used = 50000  # Mock gas usage
            
            # Move to completed batches
            self.completed_batches[batch.batch_id] = batch
            if batch.batch_id in self.processing_batches:
                del self.processing_batches[batch.batch_id]
            
            self.logger.info(
                "Settlement batch completed",
                batch_id=batch.batch_id,
                tx_hash=tx_hash,
                processing_time=processing_time
            )
            
            return tx_hash
            
        except Exception as e:
            self.logger.error("Settlement execution failed", error=str(e))
            
            # Update batch status
            batch.status = "failed"
            if batch.batch_id in self.processing_batches:
                del self.processing_batches[batch.batch_id]
            
            raise
    
    async def verify_settlement(self, tx_hash: str) -> bool:
        """
        Verify blockchain transaction completion
        
        Args:
            tx_hash: Transaction hash to verify
            
        Returns:
            bool: Verification result
        """
        try:
            self.logger.info("Verifying settlement transaction", tx_hash=tx_hash)
            
            # Check transaction status on blockchain
            status = await self.settlement_service.get_transaction_status(tx_hash)
            
            if status == "success":
                self.logger.info("Settlement transaction verified", tx_hash=tx_hash)
                return True
            else:
                self.logger.warning("Settlement transaction failed", tx_hash=tx_hash, status=status)
                return False
                
        except Exception as e:
            self.logger.error("Settlement verification failed", error=str(e))
            return False
    
    async def _add_payment_to_queue(self, payment: CrossBorderPayment):
        """Add payment to settlement queue"""
        self.payment_queue.append(payment)
        
        # Cache payment in queue
        await self.cache.set(
            f"settlement_queue:{payment.payment_id}",
            payment.dict(),
            3600  # 1 hour TTL
        )
    
    async def _should_create_batch(self) -> bool:
        """Check if we should create a new batch"""
        current_time = datetime.now(timezone.utc)
        time_since_last_batch = (current_time - self.last_batch_time).total_seconds()
        
        # Create batch if:
        # 1. Queue has minimum batch size, or
        # 2. Maximum wait time has elapsed
        return (len(self.payment_queue) >= self.config.min_batch_size or 
                time_since_last_batch >= self.config.max_batch_wait_time)
    
    async def _create_and_process_batch(self):
        """Create and process a new settlement batch"""
        try:
            if not self.payment_queue:
                return
            
            # Take payments from queue
            batch_payments = self.payment_queue[:self.config.max_batch_size]
            self.payment_queue = self.payment_queue[self.config.max_batch_size:]
            
            # Prepare batch
            batch = await self.prepare_settlement(batch_payments)
            
            if not batch:
                return
            
            # Execute settlement
            tx_hash = await self.execute_settlement(batch)
            
            # Update last batch time
            self.last_batch_time = datetime.now(timezone.utc)
            
            # Remove payments from cache
            for payment in batch_payments:
                await self.cache.delete(f"settlement_queue:{payment.payment_id}")
            
            self.logger.info(
                "Settlement batch created and processed",
                batch_id=batch.batch_id,
                tx_hash=tx_hash,
                num_payments=len(batch_payments)
            )
            
        except Exception as e:
            self.logger.error("Failed to create and process batch", error=str(e))
    
    async def _process_pending_batches(self):
        """Process any pending batches"""
        try:
            # Check for batches that need processing
            for batch_id, batch in list(self.pending_batches.items()):
                if batch.status == "pending":
                    try:
                        await self.execute_settlement(batch)
                    except Exception as e:
                        self.logger.error("Failed to process pending batch", batch_id=batch_id, error=str(e))
                        
        except Exception as e:
            self.logger.error("Failed to process pending batches", error=str(e))
    
    async def get_batch_status(self, batch_id: str) -> Optional[SettlementBatch]:
        """Get settlement batch status"""
        # Check in all batch collections
        for batch_collection in [self.pending_batches, self.processing_batches, self.completed_batches]:
            if batch_id in batch_collection:
                return batch_collection[batch_id]
        return None
    
    async def get_queue_status(self) -> Dict[str, any]:
        """Get settlement queue status"""
        return {
            "queue_size": len(self.payment_queue),
            "pending_batches": len(self.pending_batches),
            "processing_batches": len(self.processing_batches),
            "completed_batches": len(self.completed_batches),
            "last_batch_time": self.last_batch_time.isoformat()
        }
    
    async def retry_failed_settlement(self, batch_id: str) -> bool:
        """Retry a failed settlement batch"""
        try:
            batch = await self.get_batch_status(batch_id)
            
            if not batch or batch.status != "failed":
                return False
            
            # Reset batch status
            batch.status = "pending"
            batch.transaction_hash = None
            batch.processing_time = None
            batch.gas_used = None
            
            # Move back to pending batches
            self.pending_batches[batch_id] = batch
            
            self.logger.info("Retrying failed settlement batch", batch_id=batch_id)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to retry settlement", error=str(e))
            return False
    
    async def get_settlement_analytics(self) -> Dict[str, any]:
        """Get settlement analytics"""
        try:
            total_batches = len(self.completed_batches)
            total_payments = sum(len(batch.payments) for batch in self.completed_batches.values())
            total_amount = sum(batch.total_amount for batch in self.completed_batches.values())
            
            # Calculate average processing time
            processing_times = [batch.processing_time for batch in self.completed_batches.values() if batch.processing_time]
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            # Calculate success rate
            failed_batches = [batch for batch in self.completed_batches.values() if batch.status == "failed"]
            success_rate = (total_batches - len(failed_batches)) / total_batches if total_batches > 0 else 0
            
            return {
                "total_batches": total_batches,
                "total_payments": total_payments,
                "total_amount": float(total_amount),
                "average_processing_time": avg_processing_time,
                "success_rate": success_rate,
                "queue_size": len(self.payment_queue),
                "pending_batches": len(self.pending_batches),
                "processing_batches": len(self.processing_batches)
            }
            
        except Exception as e:
            self.logger.error("Failed to get settlement analytics", error=str(e))
            return {} 