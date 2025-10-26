"""
Route Optimization Agent for CAPP

This agent is responsible for finding the optimal payment routes across African countries
using multi-objective optimization considering cost, speed, reliability, and compliance.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import numpy as np
from sklearn.preprocessing import MinMaxScaler

import structlog
from pydantic import BaseModel, Field

from ..agents.base import BasePaymentAgent, AgentConfig
from ..models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentRoute,
    Country, Currency, MMOProvider, PaymentPreferences
)
from ..services.exchange_rates import ExchangeRateService
from ..services.compliance import ComplianceService
from ..services.mmo_availability import MMOAvailabilityService
from ..core.redis import get_redis_client
from ..core.database import AsyncSessionLocal
from ..repositories.agent_activity import AgentActivityRepository


logger = structlog.get_logger(__name__)


class RouteOptimizationConfig(AgentConfig):
    """Configuration for route optimization agent"""
    agent_type: str = "route_optimization"
    
    # Optimization parameters
    max_routes_to_evaluate: int = 50
    optimization_timeout: float = 10.0  # seconds
    cache_ttl: int = 300  # 5 minutes
    
    # Scoring weights
    cost_weight: float = 0.4
    speed_weight: float = 0.3
    reliability_weight: float = 0.2
    compliance_weight: float = 0.1
    
    # Route discovery
    enable_direct_routes: bool = True
    enable_hub_routes: bool = True
    enable_multi_hop_routes: bool = False
    max_hops: int = 2
    
    # Performance thresholds
    min_success_rate: float = 0.95
    max_delivery_time: int = 1440  # 24 hours in minutes
    max_cost_percentage: float = 0.05  # 5% of payment amount


class RouteScore(BaseModel):
    """Route scoring model"""
    route: PaymentRoute
    cost_score: float
    speed_score: float
    reliability_score: float
    compliance_score: float
    total_score: float
    ranking: int


class RouteOptimizationAgent(BasePaymentAgent):
    """
    Route Optimization Agent
    
    This agent uses multi-objective optimization to find the best payment routes
    across African countries, considering:
    - Cost optimization (fees + exchange rate spread)
    - Speed optimization (delivery time)
    - Reliability optimization (success rate)
    - Compliance optimization (regulatory requirements)
    """
    
    def __init__(self, config: RouteOptimizationConfig):
        super().__init__(config)
        self.config = config
        
        # Services
        self.exchange_rate_service = ExchangeRateService()
        self.compliance_service = ComplianceService()
        self.mmo_availability_service = MMOAvailabilityService()
        self.redis_client = get_redis_client()
        
        # Optimization components
        self.scaler = MinMaxScaler()
        self.route_cache: Dict[str, List[PaymentRoute]] = {}
        
        self.logger.info("Route optimization agent initialized")
    
    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """
        Process payment by finding optimal route and updating payment
        
        Args:
            payment: The payment to process
            
        Returns:
            PaymentResult: The result with optimal route selected
        """
        try:
            self.logger.info(
                "Finding optimal route for payment",
                payment_id=payment.payment_id,
                from_country=payment.sender.country,
                to_country=payment.recipient.country,
                amount=payment.amount,
                currency=payment.from_currency
            )
            
            # Find optimal route
            optimal_route = await self.find_optimal_route(payment)
            
            if not optimal_route:
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message="No suitable payment route found",
                    error_code="NO_ROUTE_AVAILABLE"
                )
            
            # Update payment with selected route
            payment.selected_route = optimal_route
            payment.available_routes = await self.get_available_routes(payment)
            payment.exchange_rate = optimal_route.exchange_rate
            payment.converted_amount = payment.amount * optimal_route.exchange_rate
            payment.fees = optimal_route.fees
            payment.total_cost = payment.calculate_total_cost()
            
            # Update payment status
            payment.update_status(PaymentStatus.ROUTING)

            # Log route selection to database
            await self._log_route_selection(payment, optimal_route)

            self.logger.info(
                "Optimal route selected",
                payment_id=payment.payment_id,
                route_id=optimal_route.route_id,
                total_cost=payment.total_cost,
                delivery_time=optimal_route.estimated_delivery_time
            )

            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.ROUTING,
                message="Optimal route found and selected",
                estimated_delivery_time=optimal_route.estimated_delivery_time,
                fees_charged=optimal_route.fees,
                exchange_rate_used=optimal_route.exchange_rate
            )
            
        except Exception as e:
            self.logger.error(
                "Error in route optimization",
                payment_id=payment.payment_id,
                error=str(e),
                exc_info=True
            )
            
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Route optimization failed: {str(e)}",
                error_code="ROUTE_OPTIMIZATION_ERROR"
            )
    
    async def validate_payment(self, payment: CrossBorderPayment) -> bool:
        """Validate if payment can be routed"""
        # Check if corridor is supported
        if not await self.validate_corridor(payment.sender.country, payment.recipient.country):
            return False
        
        # Check amount limits
        if payment.amount < self.settings.MIN_PAYMENT_AMOUNT:
            return False
        
        if payment.amount > self.settings.MAX_PAYMENT_AMOUNT:
            return False
        
        # Check if currencies are supported
        if not await self._validate_currencies(payment.from_currency, payment.to_currency):
            return False
        
        return True
    
    async def find_optimal_route(self, payment: CrossBorderPayment) -> Optional[PaymentRoute]:
        """
        Find the optimal payment route using multi-objective optimization
        
        Args:
            payment: The payment to route
            
        Returns:
            PaymentRoute: The optimal route, or None if no route found
        """
        # Check cache first
        cache_key = self._get_route_cache_key(payment)
        cached_routes = await self._get_cached_routes(cache_key)
        
        if cached_routes:
            self.logger.info("Using cached routes", cache_key=cache_key)
            routes = cached_routes
        else:
            # Discover available routes
            routes = await self.discover_routes(payment)
            
            # Cache the routes
            await self._cache_routes(cache_key, routes)
        
        if not routes:
            self.logger.warning("No routes found for payment", payment_id=payment.payment_id)
            return None
        
        # Score and rank routes
        scored_routes = await self.score_routes(routes, payment)
        
        if not scored_routes:
            return None
        
        # Select optimal route based on preferences
        optimal_route = self._select_optimal_route(scored_routes, payment.preferences)
        
        return optimal_route.route if optimal_route else None
    
    async def discover_routes(self, payment: CrossBorderPayment) -> List[PaymentRoute]:
        """
        Discover all available payment routes for the given payment
        
        Args:
            payment: The payment to find routes for
            
        Returns:
            List[PaymentRoute]: Available routes
        """
        routes = []
        
        # Direct routes (single hop)
        if self.config.enable_direct_routes:
            direct_routes = await self._discover_direct_routes(payment)
            routes.extend(direct_routes)
        
        # Hub routes (via major financial hubs)
        if self.config.enable_hub_routes:
            hub_routes = await self._discover_hub_routes(payment)
            routes.extend(hub_routes)
        
        # Multi-hop routes
        if self.config.enable_multi_hop_routes:
            multi_hop_routes = await self._discover_multi_hop_routes(payment)
            routes.extend(multi_hop_routes)
        
        # Filter routes based on basic criteria
        filtered_routes = await self._filter_routes(routes, payment)
        
        self.logger.info(
            "Routes discovered",
            payment_id=payment.payment_id,
            total_routes=len(routes),
            filtered_routes=len(filtered_routes)
        )
        
        return filtered_routes
    
    async def _discover_direct_routes(self, payment: CrossBorderPayment) -> List[PaymentRoute]:
        """Discover direct routes between countries"""
        routes = []
        
        # Check MMO direct connections
        mmo_routes = await self._get_mmo_direct_routes(payment)
        routes.extend(mmo_routes)
        
        # Check bank direct connections
        bank_routes = await self._get_bank_direct_routes(payment)
        routes.extend(bank_routes)
        
        return routes
    
    async def _discover_hub_routes(self, payment: CrossBorderPayment) -> List[PaymentRoute]:
        """Discover routes via major financial hubs"""
        routes = []
        
        # Major financial hubs in Africa
        hubs = [
            Country.SOUTH_AFRICA,  # Johannesburg
            Country.NIGERIA,       # Lagos
            Country.KENYA,         # Nairobi
            Country.UGANDA,        # Kampala
            Country.GHANA,         # Accra
            Country.SENEGAL,       # Dakar
            Country.MOROCCO,       # Casablanca
            Country.EGYPT          # Cairo
        ]
        
        for hub in hubs:
            if hub not in [payment.sender.country, payment.recipient.country]:
                hub_routes = await self._get_hub_routes(payment, hub)
                routes.extend(hub_routes)
        
        return routes
    
    async def _discover_multi_hop_routes(self, payment: CrossBorderPayment) -> List[PaymentRoute]:
        """Discover multi-hop routes (limited to max_hops)"""
        # This is a simplified implementation
        # In a real system, this would use graph algorithms to find paths
        return []
    
    async def score_routes(self, routes: List[PaymentRoute], payment: CrossBorderPayment) -> List[RouteScore]:
        """
        Score routes using multi-objective optimization
        
        Args:
            routes: List of routes to score
            payment: The payment being routed
            
        Returns:
            List[RouteScore]: Scored and ranked routes
        """
        if not routes:
            return []
        
        scored_routes = []
        
        for route in routes:
            # Calculate individual scores
            cost_score = await self._calculate_cost_score(route, payment)
            speed_score = await self._calculate_speed_score(route)
            reliability_score = await self._calculate_reliability_score(route)
            compliance_score = await self._calculate_compliance_score(route, payment)
            
            # Calculate weighted total score
            total_score = (
                cost_score * self.config.cost_weight +
                speed_score * self.config.speed_weight +
                reliability_score * self.config.reliability_weight +
                compliance_score * self.config.compliance_weight
            )
            
            scored_route = RouteScore(
                route=route,
                cost_score=cost_score,
                speed_score=speed_score,
                reliability_score=reliability_score,
                compliance_score=compliance_score,
                total_score=total_score,
                ranking=0  # Will be set after sorting
            )
            
            scored_routes.append(scored_route)
        
        # Sort by total score (descending)
        scored_routes.sort(key=lambda x: x.total_score, reverse=True)
        
        # Assign rankings
        for i, scored_route in enumerate(scored_routes):
            scored_route.ranking = i + 1
        
        self.logger.info(
            "Routes scored",
            payment_id=payment.payment_id,
            total_routes=len(scored_routes),
            top_score=scored_routes[0].total_score if scored_routes else 0
        )
        
        return scored_routes
    
    async def _calculate_cost_score(self, route: PaymentRoute, payment: CrossBorderPayment) -> float:
        """Calculate cost score (lower is better)"""
        # Calculate total cost as percentage of payment amount
        total_cost = route.fees + (payment.amount * (1 - route.exchange_rate))
        cost_percentage = float(total_cost / payment.amount)
        
        # Normalize to 0-1 scale (lower cost = higher score)
        max_acceptable_cost = self.config.max_cost_percentage
        if cost_percentage <= max_acceptable_cost:
            score = 1.0 - (cost_percentage / max_acceptable_cost)
        else:
            score = 0.0
        
        return max(0.0, min(1.0, score))
    
    async def _calculate_speed_score(self, route: PaymentRoute) -> float:
        """Calculate speed score (faster is better)"""
        # Normalize delivery time to 0-1 scale
        max_time = self.config.max_delivery_time
        if route.estimated_delivery_time <= max_time:
            score = 1.0 - (route.estimated_delivery_time / max_time)
        else:
            score = 0.0
        
        return max(0.0, min(1.0, score))
    
    async def _calculate_reliability_score(self, route: PaymentRoute) -> float:
        """Calculate reliability score based on success rate"""
        return route.reliability_score
    
    async def _calculate_compliance_score(self, route: PaymentRoute, payment: CrossBorderPayment) -> float:
        """Calculate compliance score"""
        # Check compliance for the route
        compliance_result = await self.compliance_service.check_route_compliance(
            route, payment.sender.country, payment.recipient.country
        )
        
        if compliance_result.is_compliant:
            return 1.0
        else:
            return 0.0
    
    def _select_optimal_route(self, scored_routes: List[RouteScore], preferences: PaymentPreferences) -> Optional[RouteScore]:
        """Select optimal route based on user preferences"""
        if not scored_routes:
            return None
        
        # Apply preference-based filtering
        filtered_routes = scored_routes
        
        # Filter by delivery time preference
        if preferences.max_delivery_time:
            filtered_routes = [
                r for r in filtered_routes 
                if r.route.estimated_delivery_time <= preferences.max_delivery_time
            ]
        
        # Filter by max fees preference
        if preferences.max_fees:
            filtered_routes = [
                r for r in filtered_routes 
                if r.route.fees <= preferences.max_fees
            ]
        
        # Filter by preferred MMO
        if preferences.preferred_mmo:
            filtered_routes = [
                r for r in filtered_routes 
                if r.route.to_mmo == preferences.preferred_mmo or r.route.from_mmo == preferences.preferred_mmo
            ]
        
        # Return the highest scoring route after filtering
        return filtered_routes[0] if filtered_routes else scored_routes[0]
    
    async def _filter_routes(self, routes: List[PaymentRoute], payment: CrossBorderPayment) -> List[PaymentRoute]:
        """Filter routes based on basic criteria"""
        filtered_routes = []
        
        for route in routes:
            # Check success rate threshold
            if route.success_rate < self.config.min_success_rate:
                continue
            
            # Check delivery time threshold
            if route.estimated_delivery_time > self.config.max_delivery_time:
                continue
            
            # Check MMO availability
            if route.to_mmo and not await self.mmo_availability_service.is_available(route.to_mmo):
                continue
            
            if route.from_mmo and not await self.mmo_availability_service.is_available(route.from_mmo):
                continue
            
            filtered_routes.append(route)
        
        return filtered_routes
    
    async def _get_mmo_direct_routes(self, payment: CrossBorderPayment) -> List[PaymentRoute]:
        """Get direct MMO routes with real exchange rates from database"""
        routes = []

        # Get real exchange rate from database-backed service
        try:
            exchange_rate = await self.exchange_rate_service.get_exchange_rate(
                payment.from_currency,
                payment.to_currency
            )

            if not exchange_rate:
                self.logger.warning(
                    "No exchange rate available for currency pair",
                    from_currency=payment.from_currency,
                    to_currency=payment.to_currency
                )
                return routes

        except Exception as e:
            self.logger.error("Failed to get exchange rate", error=str(e))
            return routes

        # Create routes with real exchange rates
        # This would integrate with actual MMO APIs for availability
        if payment.sender.country == Country.KENYA and payment.recipient.country == Country.UGANDA:
            routes.append(PaymentRoute(
                from_country=payment.sender.country,
                to_country=payment.recipient.country,
                from_currency=payment.from_currency,
                to_currency=payment.to_currency,
                from_mmo=MMOProvider.MPESA,
                to_mmo=MMOProvider.MPESA_UGANDA,
                exchange_rate=exchange_rate,
                fees=Decimal('2.50'),
                estimated_delivery_time=5,  # 5 minutes
                success_rate=0.98,
                cost_score=0.9,
                speed_score=0.95,
                reliability_score=0.98,
                total_score=0.94
            ))
        elif payment.sender.country == Country.NIGERIA and payment.recipient.country == Country.KENYA:
            routes.append(PaymentRoute(
                from_country=payment.sender.country,
                to_country=payment.recipient.country,
                from_currency=payment.from_currency,
                to_currency=payment.to_currency,
                from_mmo=MMOProvider.MTN_MOBILE_MONEY,
                to_mmo=MMOProvider.MPESA,
                exchange_rate=exchange_rate,  # Real rate from database
                fees=Decimal('0.80'),  # 0.8% of amount
                estimated_delivery_time=5,  # 5 minutes
                success_rate=0.99,
                cost_score=0.95,
                speed_score=0.98,
                reliability_score=0.99,
                total_score=0.97
            ))

        return routes
    
    async def _get_bank_direct_routes(self, payment: CrossBorderPayment) -> List[PaymentRoute]:
        """Get direct bank routes"""
        # Implementation would integrate with banking APIs
        return []
    
    async def _get_hub_routes(self, payment: CrossBorderPayment, hub: Country) -> List[PaymentRoute]:
        """Get routes via a specific hub"""
        # Implementation would find routes through the hub
        return []
    
    async def _validate_currencies(self, from_currency: Currency, to_currency: Currency) -> bool:
        """Validate currency pair is supported"""
        # Check if exchange rate is available
        try:
            rate = await self.exchange_rate_service.get_exchange_rate(from_currency, to_currency)
            return rate is not None
        except Exception:
            return False
    
    def _get_route_cache_key(self, payment: CrossBorderPayment) -> str:
        """Generate cache key for routes"""
        return f"routes:{payment.sender.country}:{payment.recipient.country}:{payment.from_currency}:{payment.to_currency}"
    
    async def _get_cached_routes(self, cache_key: str) -> Optional[List[PaymentRoute]]:
        """Get cached routes from Redis"""
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                # Deserialize cached routes
                # Implementation would depend on serialization format
                return []
        except Exception as e:
            self.logger.warning("Failed to get cached routes", error=str(e))
        
        return None
    
    async def _cache_routes(self, cache_key: str, routes: List[PaymentRoute]) -> None:
        """Cache routes in Redis"""
        try:
            # Serialize routes
            # Implementation would depend on serialization format
            await self.redis_client.setex(cache_key, self.config.cache_ttl, "cached_routes")
        except Exception as e:
            self.logger.warning("Failed to cache routes", error=str(e))
    
    async def get_available_routes(self, payment: CrossBorderPayment) -> List[PaymentRoute]:
        """Get all available routes for a payment"""
        return await self.discover_routes(payment)

    async def _log_route_selection(self, payment: CrossBorderPayment, route: PaymentRoute):
        """Log route selection to database for analytics"""
        try:
            from uuid import UUID
            import json

            async with AsyncSessionLocal() as session:
                activity_repo = AgentActivityRepository(session)

                payment_uuid = UUID(str(payment.payment_id))

                # Create detailed route information
                route_details = {
                    "route_id": route.route_id,
                    "from_country": str(route.from_country),
                    "to_country": str(route.to_country),
                    "from_currency": str(route.from_currency),
                    "to_currency": str(route.to_currency),
                    "exchange_rate": float(route.exchange_rate),
                    "fees": float(route.fees),
                    "total_score": route.total_score,
                    "cost_score": route.cost_score,
                    "speed_score": route.speed_score,
                    "reliability_score": route.reliability_score,
                    "estimated_delivery_time": route.estimated_delivery_time,
                    "from_mmo": str(route.from_mmo) if route.from_mmo else None,
                    "to_mmo": str(route.to_mmo) if route.to_mmo else None
                }

                await activity_repo.create(
                    payment_id=payment_uuid,
                    agent_type="routing",
                    agent_id=route.route_id,
                    action="select_route",
                    status="success",
                    details=json.dumps(route_details)
                )

                self.logger.debug(
                    "Route selection logged to database",
                    payment_id=payment.payment_id,
                    route_id=route.route_id
                )

        except Exception as e:
            # Log but don't fail route selection if database save fails
            self.logger.warning(
                "Failed to log route selection to database",
                error=str(e),
                payment_id=payment.payment_id
            ) 