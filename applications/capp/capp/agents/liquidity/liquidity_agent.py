"""
Liquidity Management Agent for CAPP

Manages liquidity across payment corridors, handles liquidity reservations,
and performs automated rebalancing of liquidity pools.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field
import structlog

from .strategies import AdaptiveLiquidityStrategy
from applications.capp.capp.agents.base import BasePaymentAgent, AgentConfig
from applications.capp.capp.models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentRoute,
    Country, Currency
)
from applications.capp.capp.core.redis import get_cache
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)


class LiquidityConfig(AgentConfig):
    """Configuration for liquidity management agent"""
    agent_type: str = "liquidity_management"
    
    # Liquidity thresholds
    min_liquidity_threshold: float = 0.1  # 10% of total pool
    max_liquidity_utilization: float = 0.8  # 80% utilization
    rebalancing_threshold: float = 0.2  # 20% imbalance triggers rebalancing
    
    # Pool management
    pool_check_interval: int = 300  # 5 minutes
    rebalancing_interval: int = 3600  # 1 hour
    reservation_timeout: int = 300  # 5 minutes
    
    # Performance settings
    max_concurrent_reservations: int = 50
    batch_rebalancing_size: int = 10


class LiquidityPool(BaseModel):
    """Liquidity pool information"""
    pool_id: str
    currency_pair: str
    from_currency: Currency
    to_currency: Currency
    total_liquidity: Decimal
    available_liquidity: Decimal
    reserved_liquidity: Decimal
    utilization_rate: float
    last_updated: datetime
    status: str = "active"  # active, low_liquidity, rebalancing


class LiquidityReservation(BaseModel):
    """Liquidity reservation for payment"""
    reservation_id: str
    payment_id: str
    pool_id: str
    amount: Decimal
    currency: Currency
    reserved_at: datetime
    expires_at: datetime
    status: str = "reserved"  # reserved, used, expired, cancelled


class LiquidityResult(BaseModel):
    """Result of liquidity operation"""
    success: bool
    available_amount: Decimal
    reserved_amount: Decimal
    pool_id: str
    message: str
    reservation_id: Optional[str] = None


class LiquidityAgent(BasePaymentAgent):
    """
    Liquidity Management Agent
    
    Manages liquidity across payment corridors:
    - Monitors liquidity pools in real-time
    - Handles liquidity reservations for payments
    - Performs automated rebalancing
    - Prevents over-commitment of liquidity
    """
    
    def __init__(self, config: LiquidityConfig):
        super().__init__(config)
        self.config = config
        self.cache = get_cache()
        
        # Liquidity pools cache
        self.liquidity_pools: Dict[str, LiquidityPool] = {}
        self.active_reservations: Dict[str, LiquidityReservation] = {}
        
        # Strategy
        self.strategy = AdaptiveLiquidityStrategy(base_buffer=Decimal("50000.00")) # Lower default for testing
        
        # Initialize default pools
        self._initialize_default_pools()
    
    def _initialize_default_pools(self):
        """Initialize default liquidity pools for demo"""
        current_time = datetime.now(timezone.utc)
        
        default_pools = [
            {
                "pool_id": "pool_kes_ugx",
                "currency_pair": "KES/UGX",
                "from_currency": "KES",
                "to_currency": "UGX",
                "total_liquidity": Decimal("1000000.00"),
                "available_liquidity": Decimal("800000.00"),
                "reserved_liquidity": Decimal("200000.00")
            },
            {
                "pool_id": "pool_ngn_ghs",
                "currency_pair": "NGN/GHS",
                "from_currency": "NGN",
                "to_currency": "GHS",
                "total_liquidity": Decimal("5000000.00"),
                "available_liquidity": Decimal("4000000.00"),
                "reserved_liquidity": Decimal("1000000.00")
            },
            {
                "pool_id": "pool_zar_bwp",
                "currency_pair": "ZAR/BWP",
                "from_currency": "ZAR",
                "to_currency": "BWP",
                "total_liquidity": Decimal("2000000.00"),
                "available_liquidity": Decimal("1600000.00"),
                "reserved_liquidity": Decimal("400000.00")
            },
            {
                "pool_id": "pool_usd_ngn",
                "currency_pair": "USD/NGN",
                "from_currency": "USD",
                "to_currency": "NGN",
                "total_liquidity": Decimal("100000.00"),
                "available_liquidity": Decimal("80000.00"),
                "reserved_liquidity": Decimal("20000.00")
            },
            {
                "pool_id": "pool_usd_kes",
                "currency_pair": "USD/KES",
                "from_currency": "USD",
                "to_currency": "KES",
                "total_liquidity": Decimal("50000.00"),
                "available_liquidity": Decimal("40000.00"),
                "reserved_liquidity": Decimal("10000.00")
            }
        ]
        
        for pool_data in default_pools:
            pool = LiquidityPool(
                pool_id=pool_data["pool_id"],
                currency_pair=pool_data["currency_pair"],
                from_currency=Currency(pool_data["from_currency"]),
                to_currency=Currency(pool_data["to_currency"]),
                total_liquidity=pool_data["total_liquidity"],
                available_liquidity=pool_data["available_liquidity"],
                reserved_liquidity=pool_data["reserved_liquidity"],
                utilization_rate=float(pool_data["reserved_liquidity"] / pool_data["total_liquidity"]),
                last_updated=current_time
            )
            self.liquidity_pools[pool.pool_id] = pool
    
    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """
        Process payment by checking and reserving liquidity
        
        Args:
            payment: The payment to process
            
        Returns:
            PaymentResult: The result of liquidity processing
        """
        try:
            self.logger.info(
                "Processing liquidity for payment",
                payment_id=payment.payment_id,
                amount=payment.amount,
                from_currency=payment.from_currency,
                to_currency=payment.to_currency
            )
            
            # Check liquidity availability
            liquidity_result = await self.check_liquidity_availability(payment)
            
            if not liquidity_result.success:
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message=liquidity_result.message,
                    error_code="INSUFFICIENT_LIQUIDITY"
                )
            
            # Reserve liquidity
            reservation_result = await self.reserve_liquidity(payment)
            
            if not reservation_result.success:
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message=reservation_result.message,
                    error_code="LIQUIDITY_RESERVATION_FAILED"
                )
            
            self.logger.info(
                "Liquidity processing completed",
                payment_id=payment.payment_id,
                reservation_id=reservation_result.reservation_id
            )
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.PROCESSING,
                message="Liquidity reserved successfully"
            )
            
        except Exception as e:
            self.logger.error("Liquidity processing failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Liquidity processing failed: {str(e)}",
                error_code="LIQUIDITY_ERROR"
            )
    
    async def validate_payment(self, payment: CrossBorderPayment) -> bool:
        """Validate if payment can be processed by this agent"""
        try:
            # Check if we have a pool for this currency pair
            pool_id = self._get_pool_id(payment.from_currency, payment.to_currency)
            
            if not pool_id or pool_id not in self.liquidity_pools:
                self.logger.warning("No liquidity pool found for currency pair", 
                                  from_currency=payment.from_currency,
                                  to_currency=payment.to_currency)
                return False
            
            # Check if payment amount is reasonable
            if payment.amount <= 0:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Payment validation failed", error=str(e))
            return False
    
    async def check_liquidity_availability(self, payment: CrossBorderPayment) -> LiquidityResult:
        """
        Check if sufficient liquidity is available for payment
        
        Args:
            payment: The payment to check liquidity for
            
        Returns:
            LiquidityResult: Liquidity availability result
        """
        try:
            pool_id = self._get_pool_id(payment.from_currency, payment.to_currency)
            
            if not pool_id:
                return LiquidityResult(
                    success=False,
                    available_amount=Decimal("0"),
                    reserved_amount=Decimal("0"),
                    pool_id="",
                    message="No liquidity pool found for currency pair"
                )
            
            pool = self.liquidity_pools.get(pool_id)
            if not pool:
                return LiquidityResult(
                    success=False,
                    available_amount=Decimal("0"),
                    reserved_amount=Decimal("0"),
                    pool_id=pool_id,
                    message="Liquidity pool not found"
                )
            
            # Check if pool has sufficient available liquidity
            if pool.available_liquidity < payment.amount:
                return LiquidityResult(
                    success=False,
                    available_amount=pool.available_liquidity,
                    reserved_amount=pool.reserved_liquidity,
                    pool_id=pool_id,
                    message=f"Insufficient liquidity. Available: {pool.available_liquidity}, Required: {payment.amount}"
                )
            
            # Check utilization rate
            if pool.utilization_rate > self.config.max_liquidity_utilization:
                return LiquidityResult(
                    success=False,
                    available_amount=pool.available_liquidity,
                    reserved_amount=pool.reserved_liquidity,
                    pool_id=pool_id,
                    message=f"Pool utilization too high: {pool.utilization_rate:.2%}"
                )
            
            self.logger.info(
                "Liquidity availability check passed",
                payment_id=payment.payment_id,
                pool_id=pool_id,
                available_amount=pool.available_liquidity,
                required_amount=payment.amount
            )
            
            return LiquidityResult(
                success=True,
                available_amount=pool.available_liquidity,
                reserved_amount=pool.reserved_liquidity,
                pool_id=pool_id,
                message="Sufficient liquidity available"
            )
            
        except Exception as e:
            self.logger.error("Liquidity availability check failed", error=str(e))
            return LiquidityResult(
                success=False,
                available_amount=Decimal("0"),
                reserved_amount=Decimal("0"),
                pool_id="",
                message=f"Liquidity check failed: {str(e)}"
            )
    
    async def reserve_liquidity(self, payment: CrossBorderPayment) -> LiquidityResult:
        """
        Reserve liquidity for payment
        
        Args:
            payment: The payment to reserve liquidity for
            
        Returns:
            LiquidityResult: Reservation result
        """
        try:
            pool_id = self._get_pool_id(payment.from_currency, payment.to_currency)
            pool = self.liquidity_pools.get(pool_id)
            
            if not pool:
                return LiquidityResult(
                    success=False,
                    available_amount=Decimal("0"),
                    reserved_amount=Decimal("0"),
                    pool_id="",
                    message="Liquidity pool not found"
                )
            
            # Create reservation
            reservation_id = f"res_{payment.payment_id}_{datetime.now().timestamp()}"
            expires_at = datetime.now(timezone.utc).replace(second=0, microsecond=0) + \
                        asyncio.get_event_loop().time() + self.config.reservation_timeout
            
            reservation = LiquidityReservation(
                reservation_id=reservation_id,
                payment_id=str(payment.payment_id),
                pool_id=pool_id,
                amount=payment.amount,
                currency=payment.from_currency,
                reserved_at=datetime.now(timezone.utc),
                expires_at=expires_at
            )
            
            # Update pool
            pool.available_liquidity -= payment.amount
            pool.reserved_liquidity += payment.amount
            pool.utilization_rate = float(pool.reserved_liquidity / pool.total_liquidity)
            pool.last_updated = datetime.now(timezone.utc)
            
            # Store reservation
            self.active_reservations[reservation_id] = reservation
            
            # Cache reservation
            await self.cache.set(f"liquidity_reservation:{reservation_id}", reservation.dict(), self.config.reservation_timeout)
            
            self.logger.info(
                "Liquidity reserved successfully",
                payment_id=payment.payment_id,
                reservation_id=reservation_id,
                amount=payment.amount,
                pool_id=pool_id
            )
            
            return LiquidityResult(
                success=True,
                available_amount=pool.available_liquidity,
                reserved_amount=pool.reserved_liquidity,
                pool_id=pool_id,
                message="Liquidity reserved successfully",
                reservation_id=reservation_id
            )
            
        except Exception as e:
            self.logger.error("Liquidity reservation failed", error=str(e))
            return LiquidityResult(
                success=False,
                available_amount=Decimal("0"),
                reserved_amount=Decimal("0"),
                pool_id="",
                message=f"Liquidity reservation failed: {str(e)}"
            )
    
    async def release_liquidity(self, reservation_id: str) -> bool:
        """
        Release reserved liquidity
        
        Args:
            reservation_id: The reservation ID to release
            
        Returns:
            bool: Success status
        """
        try:
            reservation = self.active_reservations.get(reservation_id)
            if not reservation:
                self.logger.warning("Reservation not found", reservation_id=reservation_id)
                return False
            
            pool = self.liquidity_pools.get(reservation.pool_id)
            if not pool:
                self.logger.warning("Pool not found for reservation", pool_id=reservation.pool_id)
                return False
            
            # Update pool
            pool.available_liquidity += reservation.amount
            pool.reserved_liquidity -= reservation.amount
            pool.utilization_rate = float(pool.reserved_liquidity / pool.total_liquidity)
            pool.last_updated = datetime.now(timezone.utc)
            
            # Remove reservation
            del self.active_reservations[reservation_id]
            
            # Remove from cache
            await self.cache.delete(f"liquidity_reservation:{reservation_id}")
            
            self.logger.info(
                "Liquidity released",
                reservation_id=reservation_id,
                amount=reservation.amount,
                pool_id=reservation.pool_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to release liquidity", error=str(e))
            return False
    
    async def use_liquidity(self, reservation_id: str) -> bool:
        """
        Mark liquidity as used (payment completed)
        
        Args:
            reservation_id: The reservation ID to mark as used
            
        Returns:
            bool: Success status
        """
        try:
            reservation = self.active_reservations.get(reservation_id)
            if not reservation:
                self.logger.warning("Reservation not found", reservation_id=reservation_id)
                return False
            
            # Mark reservation as used
            reservation.status = "used"
            
            # Remove from active reservations
            del self.active_reservations[reservation_id]
            
            # Update cache
            await self.cache.set(f"liquidity_reservation:{reservation_id}", reservation.dict(), 3600)  # Keep for 1 hour
            
            self.logger.info(
                "Liquidity marked as used",
                reservation_id=reservation_id,
                payment_id=reservation.payment_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to mark liquidity as used", error=str(e))
            return False
    
    async def rebalance_pools(self) -> None:
        """Automated liquidity rebalancing across corridors"""
        try:
            self.logger.info("Starting liquidity pool rebalancing")
            
            # Check pools that need rebalancing
            pools_to_rebalance = []
            
            for pool in self.liquidity_pools.values():
                # Check Strategy
                action = self.strategy.evaluate(pool.pool_id, pool.available_liquidity)
                
                if action.should_rebalance:
                    pools_to_rebalance.append((pool, action.reason))
                elif pool.utilization_rate > self.config.max_liquidity_utilization:
                     # Keep old check for high utilization purely for completeness, 
                     # though strategy might cover it if we added logic there.
                     pools_to_rebalance.append((pool, "high_utilization"))
            
            # Perform rebalancing
            for pool, reason in pools_to_rebalance:
                await self._rebalance_pool(pool, reason)
            
            self.logger.info("Liquidity pool rebalancing completed", pools_rebalanced=len(pools_to_rebalance))
            
        except Exception as e:
            self.logger.error("Liquidity rebalancing failed", error=str(e))
    
    async def _rebalance_pool(self, pool: LiquidityPool, reason: str):
        """Rebalance a specific liquidity pool using Adaptive Strategy"""
        try:
            # 1. Update strategy with current usage (simulated usage since we don't have full history here yet)
            # In a real app, this would happen in process_payment specific to that pool
            self.strategy.record_usage(pool.pool_id, pool.reserved_liquidity)
            
            # 2. Evaluate Strategy
            action = self.strategy.evaluate(pool.pool_id, pool.available_liquidity)
            
            self.logger.info(
                "Evaluated rebalancing strategy",
                pool_id=pool.pool_id,
                available=pool.available_liquidity,
                should_rebalance=action.should_rebalance,
                action=action.action_type,
                reason=action.reason
            )
            
            if not action.should_rebalance:
                return

            self.logger.info(
                "Initiating Rebalancing Action",
                type=action.action_type,
                amount=action.amount_needed,
                pool=pool.pool_id
            )
            
            # Update pool status
            pool.status = "rebalancing"
            pool.last_updated = datetime.now(timezone.utc)
            
            # Simulate rebalancing execution (Swap)
            # In Phase 5, this will call SettlementAgent.execute_swap()
            await asyncio.sleep(2.0)
            
            # Apply rebalanced funds
            pool.available_liquidity += action.amount_needed
            pool.status = "active"
            pool.last_updated = datetime.now(timezone.utc)
            
            self.logger.info(
                "Pool rebalanced successfully",
                pool_id=pool.pool_id,
                new_balance=pool.available_liquidity
            )
            
        except Exception as e:
            self.logger.error("Pool rebalancing failed", pool_id=pool.pool_id, error=str(e))
            pool.status = "active" # Reset status on error
    
    async def get_pool_status(self, pool_id: str) -> Optional[LiquidityPool]:
        """Get liquidity pool status"""
        return self.liquidity_pools.get(pool_id)
    
    async def get_all_pools_status(self) -> Dict[str, LiquidityPool]:
        """Get status of all liquidity pools"""
        return self.liquidity_pools.copy()
    
    async def get_reservation_status(self, reservation_id: str) -> Optional[LiquidityReservation]:
        """Get liquidity reservation status"""
        return self.active_reservations.get(reservation_id)
    
    def _get_pool_id(self, from_currency: Currency, to_currency: Currency) -> Optional[str]:
        """Get pool ID for currency pair"""
        pool_id = f"pool_{from_currency.lower()}_{to_currency.lower()}"
        return pool_id if pool_id in self.liquidity_pools else None
    
    async def cleanup_expired_reservations(self):
        """Clean up expired liquidity reservations"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_reservations = []
            
            for reservation_id, reservation in self.active_reservations.items():
                if current_time > reservation.expires_at:
                    expired_reservations.append(reservation_id)
            
            for reservation_id in expired_reservations:
                await self.release_liquidity(reservation_id)
            
            if expired_reservations:
                self.logger.info("Cleaned up expired reservations", count=len(expired_reservations))
                
        except Exception as e:
            self.logger.error("Failed to cleanup expired reservations", error=str(e)) 