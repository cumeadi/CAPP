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

from ..agents.base import BasePaymentAgent, AgentConfig
from ..models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentRoute,
    Country, Currency
)
from ..core.redis import get_cache
from ..core.database import AsyncSessionLocal
from ..repositories.liquidity import LiquidityPoolRepository, LiquidityReservationRepository
from ..config.settings import get_settings

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

        # Liquidity pools cache (for performance)
        self.liquidity_pools: Dict[str, LiquidityPool] = {}
        self.active_reservations: Dict[str, LiquidityReservation] = {}

        # Note: Pools are now loaded from database on-demand rather than pre-initialized
    
    async def _get_or_create_pool(
        self,
        from_currency: Currency,
        to_currency: Currency
    ) -> Optional[LiquidityPool]:
        """
        Get liquidity pool from database or create if doesn't exist

        Args:
            from_currency: Source currency
            to_currency: Target currency

        Returns:
            LiquidityPool model or None
        """
        try:
            async with AsyncSessionLocal() as session:
                repo = LiquidityPoolRepository(session)

                # Try to get existing pool
                pool_db = await repo.get_by_currency(to_currency)

                if not pool_db:
                    # Create new pool with default liquidity
                    self.logger.info(
                        "Creating new liquidity pool",
                        currency=to_currency,
                        initial_liquidity=100000.00
                    )
                    pool_db = await repo.create(
                        currency=to_currency,
                        country=self._get_country_for_currency(to_currency),
                        total_liquidity=Decimal("100000.00"),
                        min_balance=Decimal("10000.00"),
                        rebalance_threshold=Decimal(str(self.config.rebalancing_threshold))
                    )

                # Convert to agent model
                current_time = datetime.now(timezone.utc)
                pool = LiquidityPool(
                    pool_id=str(pool_db.id),
                    currency_pair=f"{from_currency}/{to_currency}",
                    from_currency=from_currency,
                    to_currency=to_currency,
                    total_liquidity=pool_db.total_liquidity,
                    available_liquidity=pool_db.available_liquidity,
                    reserved_liquidity=pool_db.reserved_liquidity,
                    utilization_rate=float(pool_db.reserved_liquidity / pool_db.total_liquidity) if pool_db.total_liquidity > 0 else 0.0,
                    last_updated=pool_db.updated_at,
                    status="active" if pool_db.is_active else "inactive"
                )

                # Cache the pool
                self.liquidity_pools[pool.pool_id] = pool

                return pool

        except Exception as e:
            self.logger.error(
                "Failed to get or create liquidity pool",
                error=str(e),
                from_currency=from_currency,
                to_currency=to_currency
            )
            return None

    def _get_country_for_currency(self, currency: Currency) -> str:
        """Map currency to country code"""
        currency_country_map = {
            "NGN": "NG", "KES": "KE", "UGX": "UG", "TZS": "TZ",
            "GHS": "GH", "ZAR": "ZA", "BWP": "BW", "ZMW": "ZM",
            "XOF": "SN", "RWF": "RW", "ETB": "ET"
        }
        return currency_country_map.get(str(currency), "XX")
    
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
            # Get or create pool from database
            pool = await self._get_or_create_pool(payment.from_currency, payment.to_currency)

            if not pool:
                return LiquidityResult(
                    success=False,
                    available_amount=Decimal("0"),
                    reserved_amount=Decimal("0"),
                    pool_id="",
                    message="No liquidity pool found for currency pair"
                )

            # Check if pool has sufficient available liquidity
            if pool.available_liquidity < payment.amount:
                return LiquidityResult(
                    success=False,
                    available_amount=pool.available_liquidity,
                    reserved_amount=pool.reserved_liquidity,
                    pool_id=pool.pool_id,
                    message=f"Insufficient liquidity. Available: {pool.available_liquidity}, Required: {payment.amount}"
                )

            # Check utilization rate
            if pool.utilization_rate > self.config.max_liquidity_utilization:
                return LiquidityResult(
                    success=False,
                    available_amount=pool.available_liquidity,
                    reserved_amount=pool.reserved_liquidity,
                    pool_id=pool.pool_id,
                    message=f"Pool utilization too high: {pool.utilization_rate:.2%}"
                )

            self.logger.info(
                "Liquidity availability check passed",
                payment_id=payment.payment_id,
                pool_id=pool.pool_id,
                available_amount=pool.available_liquidity,
                required_amount=payment.amount
            )

            return LiquidityResult(
                success=True,
                available_amount=pool.available_liquidity,
                reserved_amount=pool.reserved_liquidity,
                pool_id=pool.pool_id,
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
            # Get pool from database
            pool = await self._get_or_create_pool(payment.from_currency, payment.to_currency)

            if not pool:
                return LiquidityResult(
                    success=False,
                    available_amount=Decimal("0"),
                    reserved_amount=Decimal("0"),
                    pool_id="",
                    message="Liquidity pool not found"
                )

            async with AsyncSessionLocal() as session:
                pool_repo = LiquidityPoolRepository(session)
                reservation_repo = LiquidityReservationRepository(session)

                # Reserve liquidity in the pool
                success = await pool_repo.reserve_liquidity(pool.to_currency, payment.amount)

                if not success:
                    return LiquidityResult(
                        success=False,
                        available_amount=pool.available_liquidity,
                        reserved_amount=pool.reserved_liquidity,
                        pool_id=pool.pool_id,
                        message="Failed to reserve liquidity in pool"
                    )

                # Create reservation record
                from uuid import UUID, uuid4
                pool_uuid = UUID(pool.pool_id) if pool.pool_id else uuid4()
                payment_uuid = UUID(str(payment.payment_id)) if hasattr(payment.payment_id, '__str__') else uuid4()

                reservation_db = await reservation_repo.create(
                    pool_id=pool_uuid,
                    payment_id=payment_uuid,
                    amount=payment.amount,
                    currency=str(payment.to_currency),
                    expiry_minutes=self.config.reservation_timeout // 60
                )

                # Update cached pool
                pool.available_liquidity -= payment.amount
                pool.reserved_liquidity += payment.amount
                pool.utilization_rate = float(pool.reserved_liquidity / pool.total_liquidity) if pool.total_liquidity > 0 else 0.0
                pool.last_updated = datetime.now(timezone.utc)
                self.liquidity_pools[pool.pool_id] = pool

                reservation_id = str(reservation_db.id)

                self.logger.info(
                    "Liquidity reserved successfully",
                    payment_id=payment.payment_id,
                    reservation_id=reservation_id,
                    amount=payment.amount,
                    pool_id=pool.pool_id
                )

                return LiquidityResult(
                    success=True,
                    available_amount=pool.available_liquidity,
                    reserved_amount=pool.reserved_liquidity,
                    pool_id=pool.pool_id,
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
            from uuid import UUID

            async with AsyncSessionLocal() as session:
                reservation_repo = LiquidityReservationRepository(session)
                pool_repo = LiquidityPoolRepository(session)

                # Get reservation from database
                reservation_db = await reservation_repo.get_by_id(UUID(reservation_id))

                if not reservation_db:
                    self.logger.warning("Reservation not found", reservation_id=reservation_id)
                    return False

                # Release reservation in database
                success = await reservation_repo.release_reservation(UUID(reservation_id))

                if not success:
                    return False

                # Release liquidity in pool
                await pool_repo.release_liquidity(reservation_db.currency, reservation_db.amount)

                # Update cache
                if reservation_db.pool_id in [UUID(p.pool_id) for p in self.liquidity_pools.values()]:
                    # Invalidate cached pool
                    for pool_id, pool in list(self.liquidity_pools.items()):
                        if UUID(pool_id) == reservation_db.pool_id:
                            del self.liquidity_pools[pool_id]
                            break

                self.logger.info(
                    "Liquidity released",
                    reservation_id=reservation_id,
                    amount=float(reservation_db.amount),
                    pool_id=str(reservation_db.pool_id)
                )

                return True

        except Exception as e:
            self.logger.error("Failed to release liquidity", error=str(e), reservation_id=reservation_id)
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
            from uuid import UUID

            async with AsyncSessionLocal() as session:
                reservation_repo = LiquidityReservationRepository(session)
                pool_repo = LiquidityPoolRepository(session)

                # Get reservation from database
                reservation_db = await reservation_repo.get_by_id(UUID(reservation_id))

                if not reservation_db:
                    self.logger.warning("Reservation not found", reservation_id=reservation_id)
                    return False

                # Mark reservation as used in database
                success = await reservation_repo.use_reservation(UUID(reservation_id))

                if not success:
                    return False

                # Use liquidity from pool (decreases both reserved and total)
                await pool_repo.use_liquidity(reservation_db.currency, reservation_db.amount)

                # Invalidate cached pool
                for pool_id, pool in list(self.liquidity_pools.items()):
                    if UUID(pool_id) == reservation_db.pool_id:
                        del self.liquidity_pools[pool_id]
                        break

                self.logger.info(
                    "Liquidity marked as used",
                    reservation_id=reservation_id,
                    payment_id=str(reservation_db.payment_id)
                )

                return True

        except Exception as e:
            self.logger.error("Failed to mark liquidity as used", error=str(e), reservation_id=reservation_id)
            return False
    
    async def rebalance_pools(self) -> None:
        """Automated liquidity rebalancing across corridors"""
        try:
            self.logger.info("Starting liquidity pool rebalancing")
            
            # Check pools that need rebalancing
            pools_to_rebalance = []
            
            for pool in self.liquidity_pools.values():
                # Check if utilization is too high or too low
                if pool.utilization_rate > self.config.max_liquidity_utilization:
                    pools_to_rebalance.append((pool, "high_utilization"))
                elif pool.utilization_rate < self.config.min_liquidity_threshold:
                    pools_to_rebalance.append((pool, "low_utilization"))
            
            # Perform rebalancing
            for pool, reason in pools_to_rebalance:
                await self._rebalance_pool(pool, reason)
            
            self.logger.info("Liquidity pool rebalancing completed", pools_rebalanced=len(pools_to_rebalance))
            
        except Exception as e:
            self.logger.error("Liquidity rebalancing failed", error=str(e))
    
    async def _rebalance_pool(self, pool: LiquidityPool, reason: str):
        """Rebalance a specific liquidity pool"""
        try:
            self.logger.info(
                "Rebalancing pool",
                pool_id=pool.pool_id,
                reason=reason,
                current_utilization=pool.utilization_rate
            )
            
            # Mock rebalancing logic
            # In real implementation, this would:
            # 1. Calculate optimal liquidity distribution
            # 2. Execute transfers between pools
            # 3. Update pool balances
            
            # Simulate rebalancing delay
            await asyncio.sleep(1.0)
            
            # Update pool status
            pool.status = "rebalancing"
            pool.last_updated = datetime.now(timezone.utc)
            
            # Simulate rebalancing completion
            await asyncio.sleep(2.0)
            
            # Reset pool status
            pool.status = "active"
            pool.last_updated = datetime.now(timezone.utc)
            
            self.logger.info(
                "Pool rebalancing completed",
                pool_id=pool.pool_id,
                new_utilization=pool.utilization_rate
            )
            
        except Exception as e:
            self.logger.error("Pool rebalancing failed", pool_id=pool.pool_id, error=str(e))
    
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
            async with AsyncSessionLocal() as session:
                reservation_repo = LiquidityReservationRepository(session)
                pool_repo = LiquidityPoolRepository(session)

                # Get expired reservations from database
                expired_reservations = await reservation_repo.get_expired_reservations()

                for reservation in expired_reservations:
                    # Release liquidity back to pool
                    await pool_repo.release_liquidity(reservation.currency, reservation.amount)

                # Mark all as expired in database
                expired_count = await reservation_repo.cleanup_expired_reservations()

                if expired_count > 0:
                    self.logger.info("Cleaned up expired reservations", count=expired_count)

                # Clear local cache
                self.liquidity_pools.clear()

        except Exception as e:
            self.logger.error("Failed to cleanup expired reservations", error=str(e)) 