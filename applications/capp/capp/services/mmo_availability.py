"""
MMO Availability Service for CAPP

Monitors the availability and status of Mobile Money Operators (MMOs)
across African countries.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import structlog

from applications.capp.capp.models.payments import MMOProvider
from applications.capp.capp.config.settings import get_settings
from applications.capp.capp.core.redis import get_cache

logger = structlog.get_logger(__name__)


class MMOStatus(BaseModel):
    """MMO status information"""
    provider: MMOProvider
    status: str  # online, offline, degraded, maintenance
    last_check: datetime
    response_time: float  # in seconds
    success_rate: float  # 0.0 to 1.0
    error_count: int
    maintenance_scheduled: bool
    maintenance_start: Optional[datetime] = None
    maintenance_end: Optional[datetime] = None


class MMOAvailabilityService:
    """
    MMO Availability Service
    
    Monitors and tracks the availability of Mobile Money Operators:
    - Real-time status monitoring
    - Performance metrics
    - Maintenance scheduling
    - Fallback mechanisms
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.logger = structlog.get_logger(__name__)
        
        # Cache TTL for MMO status (30 seconds)
        self.cache_ttl = 30
        
        # MMO status cache
        self.mmo_status: Dict[MMOProvider, MMOStatus] = {}
        
        # Initialize default statuses
        self._initialize_default_statuses()
    
    def _initialize_default_statuses(self):
        """Initialize default MMO statuses"""
        current_time = datetime.now(timezone.utc)
        
        default_statuses = {
            MMOProvider.MPESA: MMOStatus(
                provider=MMOProvider.MPESA,
                status="online",
                last_check=current_time,
                response_time=0.5,
                success_rate=0.98,
                error_count=0,
                maintenance_scheduled=False
            ),
            MMOProvider.ORANGE_MONEY: MMOStatus(
                provider=MMOProvider.ORANGE_MONEY,
                status="online",
                last_check=current_time,
                response_time=0.8,
                success_rate=0.95,
                error_count=0,
                maintenance_scheduled=False
            ),
            MMOProvider.MTN_MOBILE_MONEY: MMOStatus(
                provider=MMOProvider.MTN_MOBILE_MONEY,
                status="online",
                last_check=current_time,
                response_time=0.6,
                success_rate=0.97,
                error_count=0,
                maintenance_scheduled=False
            ),
            MMOProvider.AIRTEL_MONEY: MMOStatus(
                provider=MMOProvider.AIRTEL_MONEY,
                status="online",
                last_check=current_time,
                response_time=0.7,
                success_rate=0.96,
                error_count=0,
                maintenance_scheduled=False
            ),
            MMOProvider.VODAFONE_CASH: MMOStatus(
                provider=MMOProvider.VODAFONE_CASH,
                status="online",
                last_check=current_time,
                response_time=0.9,
                success_rate=0.94,
                error_count=0,
                maintenance_scheduled=False
            ),
            MMOProvider.TIGO_PESA: MMOStatus(
                provider=MMOProvider.TIGO_PESA,
                status="online",
                last_check=current_time,
                response_time=0.6,
                success_rate=0.95,
                error_count=0,
                maintenance_scheduled=False
            ),
            MMOProvider.MOOV_MONEY: MMOStatus(
                provider=MMOProvider.MOOV_MONEY,
                status="online",
                last_check=current_time,
                response_time=0.8,
                success_rate=0.93,
                error_count=0,
                maintenance_scheduled=False
            ),
            MMOProvider.ECOCASH: MMOStatus(
                provider=MMOProvider.ECOCASH,
                status="online",
                last_check=current_time,
                response_time=0.7,
                success_rate=0.96,
                error_count=0,
                maintenance_scheduled=False
            ),
            MMOProvider.MPESA_TANZANIA: MMOStatus(
                provider=MMOProvider.MPESA_TANZANIA,
                status="online",
                last_check=current_time,
                response_time=0.5,
                success_rate=0.98,
                error_count=0,
                maintenance_scheduled=False
            ),
            MMOProvider.MPESA_UGANDA: MMOStatus(
                provider=MMOProvider.MPESA_UGANDA,
                status="online",
                last_check=current_time,
                response_time=0.5,
                success_rate=0.98,
                error_count=0,
                maintenance_scheduled=False
            )
        }
        
        self.mmo_status.update(default_statuses)
    
    async def is_available(self, provider: MMOProvider) -> bool:
        """
        Check if MMO provider is available
        
        Args:
            provider: MMO provider to check
            
        Returns:
            bool: True if available, False otherwise
        """
        try:
            # Check cache first
            cache_key = f"mmo_status:{provider}"
            cached_status = await self.cache.get(cache_key)
            
            if cached_status:
                return cached_status.get("status") == "online"
            
            # Get current status
            status = await self.get_mmo_status(provider)
            
            if status:
                # Cache the status
                await self.cache.set(cache_key, {
                    "status": status.status,
                    "success_rate": status.success_rate,
                    "response_time": status.response_time
                }, self.cache_ttl)
                
                return status.status == "online"
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to check MMO availability", provider=provider, error=str(e))
            return False
    
    async def get_mmo_status(self, provider: MMOProvider) -> Optional[MMOStatus]:
        """
        Get current status of MMO provider
        
        Args:
            provider: MMO provider to check
            
        Returns:
            MMOStatus: Current status, or None if not found
        """
        try:
            # Check if we have cached status
            if provider in self.mmo_status:
                status = self.mmo_status[provider]
                
                # Check if status is recent (within last 5 minutes)
                time_diff = (datetime.now(timezone.utc) - status.last_check).total_seconds()
                if time_diff < 300:  # 5 minutes
                    return status
            
            # Perform health check
            status = await self._perform_health_check(provider)
            
            if status:
                self.mmo_status[provider] = status
            
            return status
            
        except Exception as e:
            self.logger.error("Failed to get MMO status", provider=provider, error=str(e))
            return None
    
    async def _perform_health_check(self, provider: MMOProvider) -> Optional[MMOStatus]:
        """Perform health check for MMO provider"""
        try:
            start_time = datetime.now(timezone.utc)
            
            # This would integrate with actual MMO APIs
            # For now, simulate health check
            await asyncio.sleep(0.1)  # Simulate API call
            
            end_time = datetime.now(timezone.utc)
            response_time = (end_time - start_time).total_seconds()
            
            # Simulate different statuses based on provider
            status_mapping = {
                MMOProvider.MPESA: {"status": "online", "success_rate": 0.98},
                MMOProvider.ORANGE_MONEY: {"status": "online", "success_rate": 0.95},
                MMOProvider.MTN_MOBILE_MONEY: {"status": "online", "success_rate": 0.97},
                MMOProvider.AIRTEL_MONEY: {"status": "online", "success_rate": 0.96},
                MMOProvider.VODAFONE_CASH: {"status": "online", "success_rate": 0.94},
                MMOProvider.TIGO_PESA: {"status": "online", "success_rate": 0.95},
                MMOProvider.MOOV_MONEY: {"status": "online", "success_rate": 0.93},
                MMOProvider.ECOCASH: {"status": "online", "success_rate": 0.96},
                MMOProvider.MPESA_TANZANIA: {"status": "online", "success_rate": 0.98},
                MMOProvider.MPESA_UGANDA: {"status": "online", "success_rate": 0.98}
            }
            
            provider_status = status_mapping.get(provider, {"status": "offline", "success_rate": 0.0})
            
            return MMOStatus(
                provider=provider,
                status=provider_status["status"],
                last_check=end_time,
                response_time=response_time,
                success_rate=provider_status["success_rate"],
                error_count=0,
                maintenance_scheduled=False
            )
            
        except Exception as e:
            self.logger.error("Health check failed", provider=provider, error=str(e))
            return None
    
    async def get_all_mmo_status(self) -> Dict[MMOProvider, MMOStatus]:
        """Get status of all MMO providers"""
        try:
            # Check all providers concurrently
            tasks = [self.get_mmo_status(provider) for provider in MMOProvider]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Build status dictionary
            all_status = {}
            for i, result in enumerate(results):
                if isinstance(result, MMOStatus):
                    all_status[MMOProvider[i]] = result
            
            return all_status
            
        except Exception as e:
            self.logger.error("Failed to get all MMO status", error=str(e))
            return {}
    
    async def get_available_providers(self) -> List[MMOProvider]:
        """Get list of available MMO providers"""
        try:
            all_status = await self.get_all_mmo_status()
            available_providers = [
                provider for provider, status in all_status.items()
                if status.status == "online"
            ]
            
            return available_providers
            
        except Exception as e:
            self.logger.error("Failed to get available providers", error=str(e))
            return []
    
    async def get_providers_by_country(self, country: str) -> List[MMOProvider]:
        """Get MMO providers available in a specific country"""
        try:
            # Country to provider mapping
            country_providers = {
                "KE": [MMOProvider.MPESA, MMOProvider.AIRTEL_MONEY],
                "TZ": [MMOProvider.MPESA_TANZANIA, MMOProvider.AIRTEL_MONEY, MMOProvider.TIGO_PESA],
                "UG": [MMOProvider.MPESA_UGANDA, MMOProvider.AIRTEL_MONEY, MMOProvider.MTN_MOBILE_MONEY],
                "GH": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY, MMOProvider.VODAFONE_CASH],
                "NG": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "RW": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "BI": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "ZM": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "MW": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
                "MZ": [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.VODAFONE_CASH],
                "AO": [MMOProvider.MTN_MOBILE_MONEY],
                "NA": [MMOProvider.MTN_MOBILE_MONEY],
                "ZW": [MMOProvider.ECOCASH, MMOProvider.MTN_MOBILE_MONEY],
                "SN": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "CI": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "BF": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "ML": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "NE": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "TG": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "BJ": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "GN": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "SL": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "LR": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "GM": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "GW": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY],
                "CV": [MMOProvider.ORANGE_MONEY, MMOProvider.MOOV_MONEY]
            }
            
            providers = country_providers.get(country, [])
            
            # Filter to only available providers
            available_providers = await self.get_available_providers()
            return [p for p in providers if p in available_providers]
            
        except Exception as e:
            self.logger.error("Failed to get providers by country", country=country, error=str(e))
            return []
    
    async def update_mmo_status(self, provider: MMOProvider, status: str, success_rate: float = None, response_time: float = None):
        """Update MMO status manually"""
        try:
            current_status = self.mmo_status.get(provider)
            
            if current_status:
                current_status.status = status
                current_status.last_check = datetime.now(timezone.utc)
                
                if success_rate is not None:
                    current_status.success_rate = success_rate
                
                if response_time is not None:
                    current_status.response_time = response_time
                
                self.logger.info("MMO status updated", provider=provider, status=status)
            
        except Exception as e:
            self.logger.error("Failed to update MMO status", provider=provider, error=str(e))
    
    async def schedule_maintenance(self, provider: MMOProvider, start_time: datetime, end_time: datetime):
        """Schedule maintenance for MMO provider"""
        try:
            current_status = self.mmo_status.get(provider)
            
            if current_status:
                current_status.maintenance_scheduled = True
                current_status.maintenance_start = start_time
                current_status.maintenance_end = end_time
                
                self.logger.info("Maintenance scheduled", provider=provider, start_time=start_time, end_time=end_time)
            
        except Exception as e:
            self.logger.error("Failed to schedule maintenance", provider=provider, error=str(e))
    
    async def get_performance_metrics(self) -> Dict[str, float]:
        """Get overall performance metrics for all MMOs"""
        try:
            all_status = await self.get_all_mmo_status()
            
            if not all_status:
                return {}
            
            total_providers = len(all_status)
            online_providers = sum(1 for status in all_status.values() if status.status == "online")
            avg_success_rate = sum(status.success_rate for status in all_status.values()) / total_providers
            avg_response_time = sum(status.response_time for status in all_status.values()) / total_providers
            
            return {
                "total_providers": total_providers,
                "online_providers": online_providers,
                "availability_rate": online_providers / total_providers,
                "average_success_rate": avg_success_rate,
                "average_response_time": avg_response_time
            }
            
        except Exception as e:
            self.logger.error("Failed to get performance metrics", error=str(e))
            return {} 