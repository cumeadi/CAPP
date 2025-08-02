"""
Exchange Rate Agent for CAPP

Handles exchange rate optimization, rate aggregation from multiple sources,
rate locking, and arbitrage opportunities for cross-border payments.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pydantic import BaseModel, Field
import structlog

from ..agents.base import BasePaymentAgent, AgentConfig
from ..models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentRoute,
    Country, Currency
)
from ..services.exchange_rates import ExchangeRateService
from ..core.redis import get_cache
from ..config.settings import get_settings

logger = structlog.get_logger(__name__)


class ExchangeRateConfig(AgentConfig):
    """Configuration for exchange rate agent"""
    agent_type: str = "exchange_rate"
    
    # Rate aggregation settings
    min_rate_sources: int = 3
    max_rate_age_minutes: int = 5
    rate_aggregation_method: str = "weighted_average"  # weighted_average, median, best_rate
    
    # Rate locking settings
    rate_lock_duration_minutes: int = 5
    rate_lock_buffer_percentage: float = 0.001  # 0.1% buffer
    
    # Arbitrage settings
    arbitrage_threshold_percentage: float = 0.005  # 0.5% minimum spread
    max_arbitrage_amount: float = 10000.0  # USD equivalent
    
    # Performance settings
    rate_update_interval: int = 60  # seconds
    max_concurrent_requests: int = 10
    request_timeout: int = 10  # seconds
    
    # Rate source weights
    source_weights: Dict[str, float] = {
        "central_bank": 0.4,
        "commercial_bank": 0.3,
        "forex_market": 0.2,
        "mobile_money": 0.1
    }


class RateSource(BaseModel):
    """Exchange rate source information"""
    source_id: str
    source_name: str
    source_type: str  # central_bank, commercial_bank, forex_market, mobile_money
    rate: Decimal
    bid_rate: Optional[Decimal] = None
    ask_rate: Optional[Decimal] = None
    last_updated: datetime
    reliability_score: float
    latency_ms: int
    is_available: bool = True


class RateLock(BaseModel):
    """Exchange rate lock for payment"""
    lock_id: str
    payment_id: str
    from_currency: Currency
    to_currency: Currency
    rate: Decimal
    amount: Decimal
    converted_amount: Decimal
    locked_at: datetime
    expires_at: datetime
    source_id: str
    status: str = "locked"  # locked, used, expired, cancelled


class ArbitrageOpportunity(BaseModel):
    """Arbitrage opportunity between rate sources"""
    opportunity_id: str
    from_currency: Currency
    to_currency: Currency
    buy_source: str
    sell_source: str
    buy_rate: Decimal
    sell_rate: Decimal
    spread_percentage: float
    potential_profit: Decimal
    max_amount: Decimal
    created_at: datetime
    status: str = "open"  # open, executed, expired


class ExchangeRateResult(BaseModel):
    """Exchange rate operation result"""
    success: bool
    rate: Optional[Decimal] = None
    converted_amount: Optional[Decimal] = None
    rate_lock_id: Optional[str] = None
    sources_used: List[str]
    arbitrage_opportunity: Optional[ArbitrageOpportunity] = None
    message: str


class ExchangeRateAgent(BasePaymentAgent):
    """
    Exchange Rate Agent
    
    Handles exchange rate optimization for cross-border payments:
    - Aggregates rates from multiple sources
    - Locks optimal rates for payments
    - Identifies arbitrage opportunities
    - Manages rate volatility and spreads
    """
    
    def __init__(self, config: ExchangeRateConfig):
        super().__init__(config)
        self.config = config
        self.cache = get_cache()
        self.exchange_rate_service = ExchangeRateService()
        
        # Rate management
        self.rate_sources: Dict[str, RateSource] = {}
        self.active_rate_locks: Dict[str, RateLock] = {}
        self.arbitrage_opportunities: List[ArbitrageOpportunity] = []
        
        # Rate history for volatility tracking
        self.rate_history: Dict[str, List[Tuple[datetime, Decimal]]] = {}
        
        # Initialize rate sources
        self._initialize_rate_sources()
        
        # Start rate monitoring task
        self._start_rate_monitoring()
    
    def _initialize_rate_sources(self):
        """Initialize exchange rate sources"""
        current_time = datetime.now(timezone.utc)
        
        # Initialize mock rate sources for demo
        default_sources = [
            {
                "source_id": "cb_ngn",
                "source_name": "Central Bank of Nigeria",
                "source_type": "central_bank",
                "rate": Decimal("1.0"),  # USD/NGN
                "reliability_score": 0.95,
                "latency_ms": 50
            },
            {
                "source_id": "cb_kes",
                "source_name": "Central Bank of Kenya",
                "source_type": "central_bank",
                "rate": Decimal("150.0"),  # USD/KES
                "reliability_score": 0.95,
                "latency_ms": 45
            },
            {
                "source_id": "cb_ghs",
                "source_name": "Bank of Ghana",
                "source_type": "central_bank",
                "rate": Decimal("12.0"),  # USD/GHS
                "reliability_score": 0.90,
                "latency_ms": 60
            },
            {
                "source_id": "forex_ngn",
                "source_name": "Forex Market NGN",
                "source_type": "forex_market",
                "rate": Decimal("1.02"),  # USD/NGN
                "bid_rate": Decimal("1.01"),
                "ask_rate": Decimal("1.03"),
                "reliability_score": 0.85,
                "latency_ms": 30
            },
            {
                "source_id": "forex_kes",
                "source_name": "Forex Market KES",
                "source_type": "forex_market",
                "rate": Decimal("151.0"),  # USD/KES
                "bid_rate": Decimal("150.5"),
                "ask_rate": Decimal("151.5"),
                "reliability_score": 0.85,
                "latency_ms": 25
            },
            {
                "source_id": "mmo_mpesa",
                "source_name": "M-Pesa Exchange",
                "source_type": "mobile_money",
                "rate": Decimal("152.0"),  # USD/KES
                "reliability_score": 0.80,
                "latency_ms": 100
            }
        ]
        
        for source_data in default_sources:
            source = RateSource(
                source_id=source_data["source_id"],
                source_name=source_data["source_name"],
                source_type=source_data["source_type"],
                rate=source_data["rate"],
                bid_rate=source_data.get("bid_rate"),
                ask_rate=source_data.get("ask_rate"),
                last_updated=current_time,
                reliability_score=source_data["reliability_score"],
                latency_ms=source_data["latency_ms"]
            )
            self.rate_sources[source.source_id] = source
    
    def _start_rate_monitoring(self):
        """Start the rate monitoring task"""
        async def rate_monitor():
            while True:
                try:
                    await self._update_exchange_rates()
                    await self._check_arbitrage_opportunities()
                    await self._cleanup_expired_locks()
                    await asyncio.sleep(self.config.rate_update_interval)
                except Exception as e:
                    self.logger.error("Rate monitoring error", error=str(e))
                    await asyncio.sleep(30)  # 30 seconds delay on error
        
        # Start the task
        asyncio.create_task(rate_monitor())
    
    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """
        Process payment for exchange rate optimization
        
        Args:
            payment: The payment to process
            
        Returns:
            PaymentResult: The exchange rate processing result
        """
        try:
            self.logger.info(
                "Processing exchange rate for payment",
                payment_id=payment.payment_id,
                amount=payment.amount,
                from_currency=payment.from_currency,
                to_currency=payment.to_currency
            )
            
            # Get optimal exchange rate
            rate_result = await self.get_optimal_rate(payment.from_currency, payment.to_currency)
            
            if not rate_result.success:
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message=rate_result.message,
                    error_code="EXCHANGE_RATE_ERROR"
                )
            
            # Lock the rate for payment
            lock_result = await self.lock_exchange_rate(payment, rate_result.rate)
            
            if not lock_result.success:
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message=lock_result.message,
                    error_code="RATE_LOCK_ERROR"
                )
            
            # Update payment with locked rate
            payment.exchange_rate = rate_result.rate
            payment.converted_amount = lock_result.converted_amount
            
            self.logger.info(
                "Exchange rate processing completed",
                payment_id=payment.payment_id,
                rate=rate_result.rate,
                converted_amount=lock_result.converted_amount
            )
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.PROCESSING,
                message="Exchange rate locked successfully",
                exchange_rate_used=rate_result.rate
            )
            
        except Exception as e:
            self.logger.error("Exchange rate processing failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Exchange rate processing failed: {str(e)}",
                error_code="EXCHANGE_RATE_ERROR"
            )
    
    async def validate_payment(self, payment: CrossBorderPayment) -> bool:
        """Validate if payment can be processed by this agent"""
        try:
            # Check if payment has required currency information
            if not payment.from_currency or not payment.to_currency:
                return False
            
            # Check if currencies are different
            if payment.from_currency == payment.to_currency:
                return False
            
            # Check if payment amount is positive
            if payment.amount <= 0:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Payment validation failed", error=str(e))
            return False
    
    async def get_optimal_rate(self, from_currency: Currency, to_currency: Currency) -> ExchangeRateResult:
        """
        Get optimal exchange rate for currency pair
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            ExchangeRateResult: Optimal rate result
        """
        try:
            self.logger.info("Getting optimal exchange rate", from_currency=from_currency, to_currency=to_currency)
            
            # Get rates from all available sources
            available_rates = await self._get_available_rates(from_currency, to_currency)
            
            if not available_rates:
                return ExchangeRateResult(
                    success=False,
                    sources_used=[],
                    message="No exchange rates available for currency pair"
                )
            
            # Aggregate rates based on configuration
            if self.config.rate_aggregation_method == "weighted_average":
                optimal_rate = self._calculate_weighted_average_rate(available_rates)
            elif self.config.rate_aggregation_method == "median":
                optimal_rate = self._calculate_median_rate(available_rates)
            elif self.config.rate_aggregation_method == "best_rate":
                optimal_rate = self._get_best_rate(available_rates)
            else:
                optimal_rate = self._calculate_weighted_average_rate(available_rates)
            
            # Check for arbitrage opportunities
            arbitrage_opportunity = await self._check_arbitrage_opportunity(from_currency, to_currency, available_rates)
            
            sources_used = [rate.source_id for rate in available_rates]
            
            self.logger.info(
                "Optimal rate calculated",
                from_currency=from_currency,
                to_currency=to_currency,
                rate=optimal_rate,
                sources_count=len(sources_used),
                arbitrage_available=arbitrage_opportunity is not None
            )
            
            return ExchangeRateResult(
                success=True,
                rate=optimal_rate,
                sources_used=sources_used,
                arbitrage_opportunity=arbitrage_opportunity,
                message="Optimal rate calculated successfully"
            )
            
        except Exception as e:
            self.logger.error("Failed to get optimal rate", error=str(e))
            return ExchangeRateResult(
                success=False,
                sources_used=[],
                message=f"Failed to get optimal rate: {str(e)}"
            )
    
    async def lock_exchange_rate(self, payment: CrossBorderPayment, rate: Decimal) -> ExchangeRateResult:
        """
        Lock exchange rate for payment
        
        Args:
            payment: The payment to lock rate for
            rate: The exchange rate to lock
            
        Returns:
            ExchangeRateResult: Rate lock result
        """
        try:
            # Calculate converted amount
            converted_amount = payment.amount * rate
            
            # Create rate lock
            lock_id = f"lock_{payment.payment_id}_{datetime.now().timestamp()}"
            locked_at = datetime.now(timezone.utc)
            expires_at = locked_at + timedelta(minutes=self.config.rate_lock_duration_minutes)
            
            rate_lock = RateLock(
                lock_id=lock_id,
                payment_id=str(payment.payment_id),
                from_currency=payment.from_currency,
                to_currency=payment.to_currency,
                rate=rate,
                amount=payment.amount,
                converted_amount=converted_amount,
                locked_at=locked_at,
                expires_at=expires_at,
                source_id="aggregated"
            )
            
            # Store rate lock
            self.active_rate_locks[lock_id] = rate_lock
            
            # Cache rate lock
            await self.cache.set(
                f"rate_lock:{lock_id}",
                rate_lock.dict(),
                self.config.rate_lock_duration_minutes * 60
            )
            
            self.logger.info(
                "Exchange rate locked",
                payment_id=payment.payment_id,
                lock_id=lock_id,
                rate=rate,
                converted_amount=converted_amount,
                expires_at=expires_at
            )
            
            return ExchangeRateResult(
                success=True,
                rate=rate,
                converted_amount=converted_amount,
                rate_lock_id=lock_id,
                sources_used=["aggregated"],
                message="Exchange rate locked successfully"
            )
            
        except Exception as e:
            self.logger.error("Failed to lock exchange rate", error=str(e))
            return ExchangeRateResult(
                success=False,
                sources_used=[],
                message=f"Failed to lock exchange rate: {str(e)}"
            )
    
    async def use_rate_lock(self, lock_id: str) -> bool:
        """
        Mark rate lock as used (payment completed)
        
        Args:
            lock_id: The rate lock ID to mark as used
            
        Returns:
            bool: Success status
        """
        try:
            rate_lock = self.active_rate_locks.get(lock_id)
            if not rate_lock:
                self.logger.warning("Rate lock not found", lock_id=lock_id)
                return False
            
            # Mark as used
            rate_lock.status = "used"
            
            # Remove from active locks
            del self.active_rate_locks[lock_id]
            
            # Update cache
            await self.cache.set(f"rate_lock:{lock_id}", rate_lock.dict(), 3600)  # Keep for 1 hour
            
            self.logger.info("Rate lock marked as used", lock_id=lock_id)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to use rate lock", error=str(e))
            return False
    
    async def _get_available_rates(self, from_currency: Currency, to_currency: Currency) -> List[RateSource]:
        """Get available rates for currency pair"""
        available_rates = []
        current_time = datetime.now(timezone.utc)
        
        for source in self.rate_sources.values():
            # Check if source is available and rate is recent
            if (source.is_available and 
                (current_time - source.last_updated).total_seconds() < self.config.max_rate_age_minutes * 60):
                
                # Check if source has rate for this currency pair
                # For demo, we'll use a simple mapping
                if self._source_has_rate_for_pair(source, from_currency, to_currency):
                    available_rates.append(source)
        
        return available_rates
    
    def _source_has_rate_for_pair(self, source: RateSource, from_currency: Currency, to_currency: Currency) -> bool:
        """Check if source has rate for currency pair"""
        # Mock implementation - in real system, this would check actual rate availability
        currency_pairs = {
            ("USD", "NGN"): ["cb_ngn", "forex_ngn"],
            ("USD", "KES"): ["cb_kes", "forex_kes", "mmo_mpesa"],
            ("USD", "GHS"): ["cb_ghs"],
            ("NGN", "USD"): ["cb_ngn", "forex_ngn"],
            ("KES", "USD"): ["cb_kes", "forex_kes", "mmo_mpesa"],
            ("GHS", "USD"): ["cb_ghs"]
        }
        
        pair = (from_currency, to_currency)
        return source.source_id in currency_pairs.get(pair, [])
    
    def _calculate_weighted_average_rate(self, rates: List[RateSource]) -> Decimal:
        """Calculate weighted average rate based on source reliability"""
        if not rates:
            return Decimal("0")
        
        total_weight = 0
        weighted_sum = Decimal("0")
        
        for rate in rates:
            weight = self.config.source_weights.get(rate.source_type, 0.1)
            weighted_sum += rate.rate * Decimal(str(weight))
            total_weight += weight
        
        return weighted_sum / Decimal(str(total_weight)) if total_weight > 0 else Decimal("0")
    
    def _calculate_median_rate(self, rates: List[RateSource]) -> Decimal:
        """Calculate median rate"""
        if not rates:
            return Decimal("0")
        
        sorted_rates = sorted(rates, key=lambda x: x.rate)
        n = len(sorted_rates)
        
        if n % 2 == 0:
            # Even number of rates
            mid1 = sorted_rates[n // 2 - 1].rate
            mid2 = sorted_rates[n // 2].rate
            return (mid1 + mid2) / Decimal("2")
        else:
            # Odd number of rates
            return sorted_rates[n // 2].rate
    
    def _get_best_rate(self, rates: List[RateSource]) -> Decimal:
        """Get the best (lowest) rate"""
        if not rates:
            return Decimal("0")
        
        return min(rate.rate for rate in rates)
    
    async def _check_arbitrage_opportunity(self, from_currency: Currency, to_currency: Currency, rates: List[RateSource]) -> Optional[ArbitrageOpportunity]:
        """Check for arbitrage opportunities"""
        try:
            if len(rates) < 2:
                return None
            
            # Find best buy and sell rates
            best_buy_rate = min(rates, key=lambda x: x.rate)
            best_sell_rate = max(rates, key=lambda x: x.rate)
            
            if best_buy_rate.source_id == best_sell_rate.source_id:
                return None
            
            # Calculate spread
            spread = best_sell_rate.rate - best_buy_rate.rate
            spread_percentage = float(spread / best_buy_rate.rate)
            
            # Check if spread is above threshold
            if spread_percentage < self.config.arbitrage_threshold_percentage:
                return None
            
            # Calculate potential profit (simplified)
            max_amount = Decimal(str(self.config.max_arbitrage_amount))
            potential_profit = max_amount * spread_percentage
            
            opportunity = ArbitrageOpportunity(
                opportunity_id=f"arb_{datetime.now().timestamp()}",
                from_currency=from_currency,
                to_currency=to_currency,
                buy_source=best_buy_rate.source_id,
                sell_source=best_sell_rate.source_id,
                buy_rate=best_buy_rate.rate,
                sell_rate=best_sell_rate.rate,
                spread_percentage=spread_percentage,
                potential_profit=potential_profit,
                max_amount=max_amount,
                created_at=datetime.now(timezone.utc)
            )
            
            self.arbitrage_opportunities.append(opportunity)
            
            self.logger.info(
                "Arbitrage opportunity detected",
                opportunity_id=opportunity.opportunity_id,
                spread_percentage=spread_percentage,
                potential_profit=potential_profit
            )
            
            return opportunity
            
        except Exception as e:
            self.logger.error("Failed to check arbitrage opportunity", error=str(e))
            return None
    
    async def _update_exchange_rates(self):
        """Update exchange rates from sources"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Mock rate updates - in real implementation, this would call external APIs
            for source in self.rate_sources.values():
                # Simulate rate volatility
                volatility = Decimal("0.01")  # 1% volatility
                random_change = (Decimal(str(hash(str(current_time) + source.source_id)) % 100) / 1000) - Decimal("0.05")
                
                new_rate = source.rate * (Decimal("1") + random_change * volatility)
                source.rate = max(new_rate, Decimal("0.1"))  # Ensure positive rate
                source.last_updated = current_time
                
                # Update rate history
                currency_pair = f"{source.source_id}"
                if currency_pair not in self.rate_history:
                    self.rate_history[currency_pair] = []
                
                self.rate_history[currency_pair].append((current_time, source.rate))
                
                # Keep only last 1000 rate points
                if len(self.rate_history[currency_pair]) > 1000:
                    self.rate_history[currency_pair] = self.rate_history[currency_pair][-1000:]
            
            self.logger.debug("Exchange rates updated", sources_count=len(self.rate_sources))
            
        except Exception as e:
            self.logger.error("Failed to update exchange rates", error=str(e))
    
    async def _check_arbitrage_opportunities(self):
        """Check for arbitrage opportunities across all currency pairs"""
        try:
            # Check for arbitrage opportunities
            currency_pairs = [("USD", "NGN"), ("USD", "KES"), ("USD", "GHS")]
            
            for from_curr, to_curr in currency_pairs:
                available_rates = await self._get_available_rates(Currency(from_curr), Currency(to_curr))
                if available_rates:
                    await self._check_arbitrage_opportunity(Currency(from_curr), Currency(to_curr), available_rates)
            
        except Exception as e:
            self.logger.error("Failed to check arbitrage opportunities", error=str(e))
    
    async def _cleanup_expired_locks(self):
        """Clean up expired rate locks"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_locks = []
            
            for lock_id, rate_lock in self.active_rate_locks.items():
                if current_time > rate_lock.expires_at:
                    expired_locks.append(lock_id)
            
            for lock_id in expired_locks:
                rate_lock = self.active_rate_locks[lock_id]
                rate_lock.status = "expired"
                
                # Remove from active locks
                del self.active_rate_locks[lock_id]
                
                # Update cache
                await self.cache.set(f"rate_lock:{lock_id}", rate_lock.dict(), 3600)
            
            if expired_locks:
                self.logger.info("Cleaned up expired rate locks", count=len(expired_locks))
                
        except Exception as e:
            self.logger.error("Failed to cleanup expired locks", error=str(e))
    
    async def get_rate_analytics(self) -> Dict[str, any]:
        """Get exchange rate analytics"""
        try:
            total_locks = len(self.active_rate_locks)
            total_opportunities = len(self.arbitrage_opportunities)
            
            # Calculate average rate volatility
            total_volatility = 0.0
            volatility_count = 0
            
            for currency_pair, history in self.rate_history.items():
                if len(history) >= 2:
                    rates = [rate for _, rate in history[-10:]]  # Last 10 rates
                    if rates:
                        avg_rate = sum(rates) / len(rates)
                        volatility = sum(abs(rate - avg_rate) / avg_rate for rate in rates) / len(rates)
                        total_volatility += volatility
                        volatility_count += 1
            
            avg_volatility = total_volatility / volatility_count if volatility_count > 0 else 0.0
            
            return {
                "total_active_locks": total_locks,
                "total_arbitrage_opportunities": total_opportunities,
                "average_volatility": avg_volatility,
                "rate_sources_count": len(self.rate_sources),
                "available_sources": sum(1 for s in self.rate_sources.values() if s.is_available)
            }
            
        except Exception as e:
            self.logger.error("Failed to get rate analytics", error=str(e))
            return {} 