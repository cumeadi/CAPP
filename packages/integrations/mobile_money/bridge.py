"""
Universal Mobile Money Bridge

This module provides a unified bridge for all mobile money operators,
extracting the working MMO availability logic from CAPP and providing
a comprehensive interface for mobile money operations across Africa.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import structlog

from pydantic import BaseModel, Field

from .base_mmo import (
    BaseMMOIntegration, MMOConfig, MMOTransaction, MMOBalance,
    MMOProvider, TransactionStatus, TransactionType
)
from .providers.mpesa import MpesaIntegration
from .providers.mtn_momo import MTNMoMoIntegration
from .providers.airtel_money import AirtelMoneyIntegration
from packages.integrations.data.redis_client import RedisClient, RedisConfig

logger = structlog.get_logger(__name__)


class MMOStatus(str, Enum):
    """MMO status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class MMOHealthStatus(BaseModel):
    """MMO health status information"""
    provider: MMOProvider
    status: MMOStatus
    last_check: datetime
    response_time: float  # in seconds
    success_rate: float  # 0.0 to 1.0
    error_count: int
    maintenance_scheduled: bool
    maintenance_start: Optional[datetime] = None
    maintenance_end: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MMOBridgeConfig(BaseModel):
    """Configuration for the MMO bridge"""
    # Provider configurations
    providers: Dict[MMOProvider, MMOConfig] = Field(default_factory=dict)
    
    # Health monitoring
    health_check_interval: int = 30  # seconds
    health_check_timeout: int = 10  # seconds
    cache_ttl: int = 300  # 5 minutes
    
    # Fallback settings
    enable_fallback: bool = True
    max_fallback_attempts: int = 3
    
    # Rate limiting
    global_rate_limit_per_minute: int = 1000
    global_rate_limit_per_hour: int = 10000
    
    # Redis configuration
    redis_config: Optional[RedisConfig] = None


class MMOBridge:
    """
    Universal Mobile Money Bridge
    
    Provides a unified interface for all mobile money operators with:
    - Automatic provider selection and fallback
    - Health monitoring and status tracking
    - Rate limiting and caching
    - Transaction routing and optimization
    """
    
    def __init__(self, config: MMOBridgeConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        # Initialize Redis client
        self.redis_client = None
        if config.redis_config:
            self.redis_client = RedisClient(config.redis_config)
        
        # Provider integrations
        self.providers: Dict[MMOProvider, BaseMMOIntegration] = {}
        
        # Health status tracking
        self.health_status: Dict[MMOProvider, MMOHealthStatus] = {}
        
        # Rate limiting
        self.rate_limit_counters: Dict[str, int] = {}
        self.last_rate_limit_reset = datetime.now(timezone.utc)
        
        # Initialize providers
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize all configured MMO providers"""
        try:
            for provider, config in self.config.providers.items():
                integration = self._create_provider_integration(provider, config)
                if integration:
                    self.providers[provider] = integration
                    self.logger.info(f"Initialized {provider} integration")
            
            self.logger.info(f"MMO Bridge initialized with {len(self.providers)} providers")
            
        except Exception as e:
            self.logger.error("Failed to initialize MMO providers", error=str(e))
            raise
    
    def _create_provider_integration(
        self, 
        provider: MMOProvider, 
        config: MMOConfig
    ) -> Optional[BaseMMOIntegration]:
        """Create provider-specific integration"""
        try:
            if provider == MMOProvider.MPESA:
                return MpesaIntegration(config, self.redis_client)
            elif provider == MMOProvider.MTN_MOBILE_MONEY:
                return MTNMoMoIntegration(config, self.redis_client)
            elif provider == MMOProvider.AIRTEL_MONEY:
                return AirtelMoneyIntegration(config, self.redis_client)
            else:
                self.logger.warning(f"Unsupported provider: {provider}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create {provider} integration", error=str(e))
            return None
    
    async def initialize(self) -> bool:
        """Initialize the MMO bridge"""
        try:
            # Initialize Redis connection
            if self.redis_client:
                await self.redis_client.connect()
            
            # Initialize all providers
            for provider, integration in self.providers.items():
                await integration.initialize()
            
            # Start health monitoring
            asyncio.create_task(self._health_monitoring_loop())
            
            self.logger.info("MMO Bridge initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize MMO Bridge", error=str(e))
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the MMO bridge"""
        try:
            # Stop health monitoring
            # (The task will be cancelled when the event loop stops)
            
            # Close all provider connections
            for provider, integration in self.providers.items():
                await integration.close()
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.disconnect()
            
            self.logger.info("MMO Bridge shutdown completed")
            
        except Exception as e:
            self.logger.error("Error during MMO Bridge shutdown", error=str(e))
    
    async def initiate_transaction(
        self, 
        transaction: MMOTransaction,
        preferred_provider: Optional[MMOProvider] = None,
        fallback_providers: Optional[List[MMOProvider]] = None
    ) -> MMOTransaction:
        """
        Initiate a mobile money transaction with automatic provider selection
        
        Args:
            transaction: Transaction to initiate
            preferred_provider: Preferred provider to use
            fallback_providers: List of fallback providers
            
        Returns:
            MMOTransaction: Updated transaction with result
        """
        try:
            # Check rate limiting
            if not await self._check_rate_limit():
                raise Exception("Rate limit exceeded")
            
            # Select provider
            selected_provider = await self._select_provider(
                transaction, preferred_provider, fallback_providers
            )
            
            if not selected_provider:
                raise Exception("No available providers")
            
            # Get provider integration
            integration = self.providers.get(selected_provider)
            if not integration:
                raise Exception(f"Provider {selected_provider} not available")
            
            # Check provider health
            if not await self._is_provider_healthy(selected_provider):
                raise Exception(f"Provider {selected_provider} is not healthy")
            
            # Initiate transaction
            result = await integration.initiate_transaction(transaction)
            
            # Update health metrics
            await self._update_health_metrics(selected_provider, True)
            
            self.logger.info(
                "Transaction initiated successfully",
                transaction_id=result.transaction_id,
                provider=selected_provider,
                status=result.status
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Failed to initiate transaction",
                transaction_id=transaction.transaction_id,
                error=str(e)
            )
            
            # Update health metrics on failure
            if selected_provider:
                await self._update_health_metrics(selected_provider, False)
            
            # Set transaction as failed
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = str(e)
            return transaction
    
    async def check_transaction_status(
        self, 
        transaction_id: str,
        provider: Optional[MMOProvider] = None
    ) -> Optional[MMOTransaction]:
        """
        Check transaction status
        
        Args:
            transaction_id: Transaction ID to check
            provider: Provider to check (if known)
            
        Returns:
            MMOTransaction: Transaction status
        """
        try:
            # If provider is specified, use it directly
            if provider and provider in self.providers:
                integration = self.providers[provider]
                return await integration.check_transaction_status(transaction_id)
            
            # Otherwise, check all providers
            for provider, integration in self.providers.items():
                if await self._is_provider_healthy(provider):
                    result = await integration.check_transaction_status(transaction_id)
                    if result:
                        return result
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to check transaction status",
                transaction_id=transaction_id,
                error=str(e)
            )
            return None
    
    async def get_account_balance(
        self, 
        phone_number: str,
        provider: Optional[MMOProvider] = None
    ) -> Optional[MMOBalance]:
        """
        Get account balance
        
        Args:
            phone_number: Phone number to check
            provider: Provider to check (if known)
            
        Returns:
            MMOBalance: Account balance information
        """
        try:
            # If provider is specified, use it directly
            if provider and provider in self.providers:
                integration = self.providers[provider]
                return await integration.get_account_balance(phone_number)
            
            # Otherwise, try all providers
            for provider, integration in self.providers.items():
                if await self._is_provider_healthy(provider):
                    result = await integration.get_account_balance(phone_number)
                    if result:
                        return result
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to get account balance",
                phone_number=phone_number,
                error=str(e)
            )
            return None
    
    async def get_available_providers(self) -> List[MMOProvider]:
        """Get list of available and healthy providers"""
        try:
            available_providers = []
            
            for provider in self.providers.keys():
                if await self._is_provider_healthy(provider):
                    available_providers.append(provider)
            
            return available_providers
            
        except Exception as e:
            self.logger.error("Failed to get available providers", error=str(e))
            return []
    
    async def get_provider_health_status(self, provider: MMOProvider) -> Optional[MMOHealthStatus]:
        """Get health status for a specific provider"""
        return self.health_status.get(provider)
    
    async def get_all_health_status(self) -> Dict[MMOProvider, MMOHealthStatus]:
        """Get health status for all providers"""
        return self.health_status.copy()
    
    async def get_providers_by_country(self, country_code: str) -> List[MMOProvider]:
        """
        Get available providers for a specific country
        
        Args:
            country_code: ISO country code (e.g., "KE", "NG", "UG")
            
        Returns:
            List of available providers for the country
        """
        try:
            # Country to provider mapping
            country_providers = {
                "KE": [MMOProvider.MPESA, MMOProvider.AIRTEL_MONEY],
                "NG": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "UG": [MMOProvider.MPESA, MMOProvider.AIRTEL_MONEY, MMOProvider.MTN_MOBILE_MONEY],
                "GH": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "RW": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "BI": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "ZM": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "MW": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "MZ": [MMOProvider.MTN_MOBILE_MONEY],
                "AO": [MMOProvider.MTN_MOBILE_MONEY],
                "NA": [MMOProvider.MTN_MOBILE_MONEY],
                "ZW": [MMOProvider.MTN_MOBILE_MONEY]
            }
            
            providers = country_providers.get(country_code, [])
            
            # Filter to only available and healthy providers
            available_providers = []
            for provider in providers:
                if provider in self.providers and await self._is_provider_healthy(provider):
                    available_providers.append(provider)
            
            return available_providers
            
        except Exception as e:
            self.logger.error(
                "Failed to get providers for country",
                country_code=country_code,
                error=str(e)
            )
            return []
    
    async def _select_provider(
        self,
        transaction: MMOTransaction,
        preferred_provider: Optional[MMOProvider] = None,
        fallback_providers: Optional[List[MMOProvider]] = None
    ) -> Optional[MMOProvider]:
        """Select the best provider for the transaction"""
        try:
            # Start with preferred provider
            if preferred_provider and await self._is_provider_healthy(preferred_provider):
                return preferred_provider
            
            # Try fallback providers
            if fallback_providers:
                for provider in fallback_providers:
                    if await self._is_provider_healthy(provider):
                        return provider
            
            # Auto-select based on transaction characteristics
            return await self._auto_select_provider(transaction)
            
        except Exception as e:
            self.logger.error("Failed to select provider", error=str(e))
            return None
    
    async def _auto_select_provider(self, transaction: MMOTransaction) -> Optional[MMOProvider]:
        """Automatically select provider based on transaction characteristics"""
        try:
            # Get available providers
            available_providers = await self.get_available_providers()
            
            if not available_providers:
                return None
            
            # Simple selection logic - can be enhanced with ML
            # For now, select the provider with the best success rate
            best_provider = None
            best_success_rate = 0.0
            
            for provider in available_providers:
                health_status = self.health_status.get(provider)
                if health_status and health_status.success_rate > best_success_rate:
                    best_success_rate = health_status.success_rate
                    best_provider = provider
            
            return best_provider
            
        except Exception as e:
            self.logger.error("Failed to auto-select provider", error=str(e))
            return None
    
    async def _is_provider_healthy(self, provider: MMOProvider) -> bool:
        """Check if provider is healthy"""
        try:
            health_status = self.health_status.get(provider)
            if not health_status:
                return False
            
            # Check if provider is online and not in maintenance
            if health_status.status != MMOStatus.ONLINE:
                return False
            
            # Check if in maintenance window
            if health_status.maintenance_scheduled:
                now = datetime.now(timezone.utc)
                if (health_status.maintenance_start and 
                    health_status.maintenance_end and
                    health_status.maintenance_start <= now <= health_status.maintenance_end):
                    return False
            
            # Check success rate threshold
            if health_status.success_rate < 0.8:  # 80% success rate threshold
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to check health for {provider}", error=str(e))
            return False
    
    async def _check_rate_limit(self) -> bool:
        """Check global rate limiting"""
        try:
            now = datetime.now(timezone.utc)
            
            # Reset counters if needed
            if (now - self.last_rate_limit_reset).total_seconds() >= 60:
                self.rate_limit_counters.clear()
                self.last_rate_limit_reset = now
            
            # Check minute limit
            minute_key = f"minute_{now.minute}"
            minute_count = self.rate_limit_counters.get(minute_key, 0)
            if minute_count >= self.config.global_rate_limit_per_minute:
                return False
            
            # Check hour limit
            hour_key = f"hour_{now.hour}"
            hour_count = self.rate_limit_counters.get(hour_key, 0)
            if hour_count >= self.config.global_rate_limit_per_hour:
                return False
            
            # Increment counters
            self.rate_limit_counters[minute_key] = minute_count + 1
            self.rate_limit_counters[hour_key] = hour_count + 1
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to check rate limit", error=str(e))
            return False
    
    async def _update_health_metrics(self, provider: MMOProvider, success: bool) -> None:
        """Update health metrics for a provider"""
        try:
            health_status = self.health_status.get(provider)
            if not health_status:
                health_status = MMOHealthStatus(
                    provider=provider,
                    status=MMOStatus.ONLINE,
                    last_check=datetime.now(timezone.utc),
                    response_time=0.0,
                    success_rate=1.0,
                    error_count=0,
                    maintenance_scheduled=False
                )
                self.health_status[provider] = health_status
            
            # Update metrics
            health_status.last_check = datetime.now(timezone.utc)
            
            if success:
                health_status.error_count = max(0, health_status.error_count - 1)
            else:
                health_status.error_count += 1
            
            # Update success rate (simple moving average)
            alpha = 0.1  # Smoothing factor
            current_success = 1.0 if success else 0.0
            health_status.success_rate = (
                alpha * current_success + 
                (1 - alpha) * health_status.success_rate
            )
            
            # Update status based on error count
            if health_status.error_count > 10:
                health_status.status = MMOStatus.OFFLINE
            elif health_status.error_count > 5:
                health_status.status = MMOStatus.DEGRADED
            else:
                health_status.status = MMOStatus.ONLINE
            
        except Exception as e:
            self.logger.error(f"Failed to update health metrics for {provider}", error=str(e))
    
    async def _health_monitoring_loop(self) -> None:
        """Background health monitoring loop"""
        try:
            while True:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
                
        except asyncio.CancelledError:
            self.logger.info("Health monitoring loop cancelled")
        except Exception as e:
            self.logger.error("Health monitoring loop error", error=str(e))
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks for all providers"""
        try:
            for provider, integration in self.providers.items():
                try:
                    # Perform health check
                    start_time = datetime.now(timezone.utc)
                    
                    # Simple health check - get supported countries
                    countries = await integration.get_supported_countries()
                    
                    response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                    
                    # Update health status
                    await self._update_health_metrics(provider, len(countries) > 0)
                    
                    # Update response time
                    health_status = self.health_status.get(provider)
                    if health_status:
                        health_status.response_time = response_time
                    
                except Exception as e:
                    self.logger.warning(f"Health check failed for {provider}", error=str(e))
                    await self._update_health_metrics(provider, False)
                    
        except Exception as e:
            self.logger.error("Failed to perform health checks", error=str(e))
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all providers"""
        try:
            metrics = {
                "total_providers": len(self.providers),
                "healthy_providers": 0,
                "degraded_providers": 0,
                "offline_providers": 0,
                "average_success_rate": 0.0,
                "average_response_time": 0.0,
                "provider_details": {}
            }
            
            total_success_rate = 0.0
            total_response_time = 0.0
            healthy_count = 0
            
            for provider, health_status in self.health_status.items():
                provider_metrics = {
                    "status": health_status.status.value,
                    "success_rate": health_status.success_rate,
                    "response_time": health_status.response_time,
                    "error_count": health_status.error_count,
                    "last_check": health_status.last_check.isoformat(),
                    "maintenance_scheduled": health_status.maintenance_scheduled
                }
                
                metrics["provider_details"][provider.value] = provider_metrics
                
                # Update counters
                if health_status.status == MMOStatus.ONLINE:
                    metrics["healthy_providers"] += 1
                    healthy_count += 1
                elif health_status.status == MMOStatus.DEGRADED:
                    metrics["degraded_providers"] += 1
                elif health_status.status == MMOStatus.OFFLINE:
                    metrics["offline_providers"] += 1
                
                total_success_rate += health_status.success_rate
                total_response_time += health_status.response_time
            
            # Calculate averages
            if self.health_status:
                metrics["average_success_rate"] = total_success_rate / len(self.health_status)
                metrics["average_response_time"] = total_response_time / len(self.health_status)
            
            return metrics
            
        except Exception as e:
            self.logger.error("Failed to get performance metrics", error=str(e))
            return {} 