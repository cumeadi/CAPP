"""
Integration Helpers Module

Integration utilities for mobile money, blockchain, configuration management,
and authentication handling. Provides simple interfaces for common integration tasks.

This module abstracts the complexity of external service integrations while
providing powerful, easy-to-use utilities for developers.
"""

from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from datetime import datetime, timezone

import structlog

from packages.integrations.mobile_money import (
    MMOBridge, MMOBridgeConfig, MMOHealthStatus,
    MpesaIntegration, MTNMoMoIntegration, AirtelMoneyIntegration
)
from packages.integrations.blockchain import (
    SettlementService, SettlementConfig, AptosClient, AptosConfig
)
from packages.integrations.data import RedisClient, RedisConfig

logger = structlog.get_logger(__name__)


class MobileMoneyBridge:
    """
    Mobile Money Integration Bridge
    
    Simple interface for mobile money operations across African countries.
    Provides unified access to M-Pesa, MTN MoMo, Airtel Money, and other MMOs.
    """
    
    def __init__(self, config: Optional[MMOBridgeConfig] = None):
        """
        Initialize Mobile Money Bridge
        
        Args:
            config: Bridge configuration
        """
        self.config = config or MMOBridgeConfig()
        self.bridge = MMOBridge(self.config)
        self.logger = structlog.get_logger(__name__)
        
        self.logger.info("Mobile Money Bridge initialized")
    
    async def initialize(self) -> bool:
        """Initialize the bridge and all integrations"""
        try:
            await self.bridge.initialize()
            self.logger.info("Mobile Money Bridge initialized successfully")
            return True
        except Exception as e:
            self.logger.error("Failed to initialize Mobile Money Bridge", error=str(e))
            return False
    
    async def send_payment(self, amount: Decimal, recipient_phone: str, 
                          provider: str = "auto", **kwargs) -> Dict[str, Any]:
        """
        Send payment via mobile money
        
        Args:
            amount: Payment amount
            recipient_phone: Recipient phone number
            provider: Mobile money provider (auto, mpesa, mtn_momo, airtel_money)
            **kwargs: Additional payment parameters
            
        Returns:
            Dict: Payment result
        """
        try:
            result = await self.bridge.send_payment(
                amount=amount,
                recipient_phone=recipient_phone,
                provider=provider,
                **kwargs
            )
            
            self.logger.info(
                "Mobile money payment sent",
                amount=amount,
                recipient=recipient_phone,
                provider=provider,
                success=result.get("success")
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Failed to send mobile money payment",
                amount=amount,
                recipient=recipient_phone,
                error=str(e)
            )
            raise
    
    async def check_balance(self, phone_number: str, provider: str = "auto") -> Dict[str, Any]:
        """
        Check mobile money balance
        
        Args:
            phone_number: Phone number to check
            provider: Mobile money provider
            
        Returns:
            Dict: Balance information
        """
        try:
            result = await self.bridge.check_balance(phone_number, provider)
            
            self.logger.info(
                "Mobile money balance checked",
                phone=phone_number,
                provider=provider,
                balance=result.get("balance")
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Failed to check mobile money balance",
                phone=phone_number,
                error=str(e)
            )
            raise
    
    async def get_provider_status(self) -> Dict[str, MMOHealthStatus]:
        """
        Get status of all mobile money providers
        
        Returns:
            Dict: Provider status information
        """
        try:
            status = await self.bridge.get_provider_status()
            
            self.logger.info(
                "Mobile money provider status retrieved",
                providers=len(status)
            )
            
            return status
            
        except Exception as e:
            self.logger.error("Failed to get provider status", error=str(e))
            raise


class AptosSettlement:
    """
    Aptos Blockchain Settlement Helper
    
    Simple interface for blockchain settlement operations on the Aptos network.
    Provides easy access to payment settlement, liquidity management, and smart contracts.
    """
    
    def __init__(self, config: Optional[AptosConfig] = None):
        """
        Initialize Aptos Settlement Helper
        
        Args:
            config: Aptos configuration
        """
        self.config = config or AptosConfig()
        self.client = AptosClient(self.config)
        self.settlement_service = SettlementService(self.config)
        self.logger = structlog.get_logger(__name__)
        
        self.logger.info("Aptos Settlement Helper initialized")
    
    async def initialize(self) -> bool:
        """Initialize the Aptos client and settlement service"""
        try:
            await self.client.initialize()
            await self.settlement_service.initialize()
            self.logger.info("Aptos Settlement Helper initialized successfully")
            return True
        except Exception as e:
            self.logger.error("Failed to initialize Aptos Settlement Helper", error=str(e))
            return False
    
    async def settle_payment(self, payment_id: str, amount: Decimal, 
                           recipient_address: str, **kwargs) -> Dict[str, Any]:
        """
        Settle payment on Aptos blockchain
        
        Args:
            payment_id: Payment identifier
            amount: Payment amount
            recipient_address: Recipient Aptos address
            **kwargs: Additional settlement parameters
            
        Returns:
            Dict: Settlement result
        """
        try:
            result = await self.settlement_service.settle_payment(
                payment_id=payment_id,
                amount=amount,
                recipient_address=recipient_address,
                **kwargs
            )
            
            self.logger.info(
                "Payment settled on Aptos",
                payment_id=payment_id,
                amount=amount,
                recipient=recipient_address,
                tx_hash=result.get("transaction_hash")
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Failed to settle payment on Aptos",
                payment_id=payment_id,
                error=str(e)
            )
            raise
    
    async def batch_settle_payments(self, payments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch settle multiple payments
        
        Args:
            payments: List of payment data
            
        Returns:
            Dict: Batch settlement result
        """
        try:
            result = await self.settlement_service.batch_settle_payments(payments)
            
            self.logger.info(
                "Batch payment settlement completed",
                payment_count=len(payments),
                success_count=result.get("successful_payments", 0)
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to batch settle payments", error=str(e))
            raise
    
    async def get_liquidity_pools(self) -> List[Dict[str, Any]]:
        """
        Get available liquidity pools
        
        Returns:
            List: Liquidity pool information
        """
        try:
            pools = await self.client.get_liquidity_pools()
            
            self.logger.info(
                "Liquidity pools retrieved",
                pool_count=len(pools)
            )
            
            return pools
            
        except Exception as e:
            self.logger.error("Failed to get liquidity pools", error=str(e))
            raise


class ConfigurationManager:
    """
    Configuration Management Helper
    
    Centralized configuration management for the Canza Agent Framework.
    Provides easy access to configuration settings with validation and defaults.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize Configuration Manager
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.logger = structlog.get_logger(__name__)
        
        self.logger.info("Configuration Manager initialized")
    
    def load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from file
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Dict: Configuration data
        """
        try:
            config_path = config_file or self.config_file
            
            if config_path:
                # Load from file (implementation would depend on file format)
                self.config = self._load_from_file(config_path)
            else:
                # Load default configuration
                self.config = self._get_default_config()
            
            self.logger.info("Configuration loaded successfully")
            return self.config
            
        except Exception as e:
            self.logger.error("Failed to load configuration", error=str(e))
            raise
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get configuration setting
        
        Args:
            key: Setting key
            default: Default value if not found
            
        Returns:
            Any: Setting value
        """
        return self.config.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """
        Set configuration setting
        
        Args:
            key: Setting key
            value: Setting value
        """
        self.config[key] = value
        self.logger.info(f"Configuration setting updated: {key}")
    
    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        redis_config = self.config.get("redis", {})
        return RedisConfig(**redis_config)
    
    def get_mobile_money_config(self) -> MMOBridgeConfig:
        """Get mobile money configuration"""
        mmo_config = self.config.get("mobile_money", {})
        return MMOBridgeConfig(**mmo_config)
    
    def get_aptos_config(self) -> AptosConfig:
        """Get Aptos configuration"""
        aptos_config = self.config.get("aptos", {})
        return AptosConfig(**aptos_config)
    
    def _load_from_file(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from file"""
        # Implementation would depend on file format (JSON, YAML, etc.)
        # For now, return default config
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": None,
                "max_connections": 20
            },
            "mobile_money": {
                "enable_health_monitoring": True,
                "health_check_interval": 300,
                "rate_limit_per_minute": 60,
                "enable_caching": True,
                "cache_ttl": 300
            },
            "aptos": {
                "node_url": "https://fullnode.mainnet.aptoslabs.com",
                "api_key": None,
                "gas_limit": 1000000,
                "gas_price": 100
            },
            "framework": {
                "region": "africa",
                "compliance_level": "standard",
                "enable_learning": True,
                "enable_consensus": True,
                "max_concurrent_agents": 10
            }
        }


class AuthenticationManager:
    """
    Authentication Management Helper
    
    Centralized authentication management for external service integrations.
    Provides secure credential management and authentication handling.
    """
    
    def __init__(self):
        """Initialize Authentication Manager"""
        self.credentials: Dict[str, Dict[str, str]] = {}
        self.logger = structlog.get_logger(__name__)
        
        self.logger.info("Authentication Manager initialized")
    
    def add_credentials(self, service: str, credentials: Dict[str, str]) -> None:
        """
        Add credentials for a service
        
        Args:
            service: Service name
            credentials: Service credentials
        """
        self.credentials[service] = credentials
        self.logger.info(f"Credentials added for service: {service}")
    
    def get_credentials(self, service: str) -> Optional[Dict[str, str]]:
        """
        Get credentials for a service
        
        Args:
            service: Service name
            
        Returns:
            Dict: Service credentials
        """
        return self.credentials.get(service)
    
    def remove_credentials(self, service: str) -> None:
        """
        Remove credentials for a service
        
        Args:
            service: Service name
        """
        if service in self.credentials:
            del self.credentials[service]
            self.logger.info(f"Credentials removed for service: {service}")
    
    def validate_credentials(self, service: str) -> bool:
        """
        Validate credentials for a service
        
        Args:
            service: Service name
            
        Returns:
            bool: True if credentials are valid
        """
        credentials = self.get_credentials(service)
        if not credentials:
            return False
        
        # Service-specific validation
        if service == "mpesa":
            return self._validate_mpesa_credentials(credentials)
        elif service == "mtn_momo":
            return self._validate_mtn_credentials(credentials)
        elif service == "airtel_money":
            return self._validate_airtel_credentials(credentials)
        elif service == "aptos":
            return self._validate_aptos_credentials(credentials)
        
        return True
    
    def _validate_mpesa_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate M-Pesa credentials"""
        required_fields = ["consumer_key", "consumer_secret", "passkey"]
        return all(field in credentials for field in required_fields)
    
    def _validate_mtn_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate MTN MoMo credentials"""
        required_fields = ["api_key", "api_secret", "subscription_key"]
        return all(field in credentials for field in required_fields)
    
    def _validate_airtel_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Airtel Money credentials"""
        required_fields = ["client_id", "client_secret", "api_key"]
        return all(field in credentials for field in required_fields)
    
    def _validate_aptos_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Aptos credentials"""
        required_fields = ["private_key"]
        return all(field in credentials for field in required_fields)


# Convenience functions for quick integration setup

def setup_mobile_money_integration(config: Optional[MMOBridgeConfig] = None) -> MobileMoneyBridge:
    """
    Quick setup for mobile money integration
    
    Args:
        config: Mobile money configuration
        
    Returns:
        MobileMoneyBridge: Configured mobile money bridge
    """
    bridge = MobileMoneyBridge(config)
    return bridge


def setup_blockchain_integration(config: Optional[AptosConfig] = None) -> AptosSettlement:
    """
    Quick setup for blockchain integration
    
    Args:
        config: Aptos configuration
        
    Returns:
        AptosSettlement: Configured blockchain settlement helper
    """
    settlement = AptosSettlement(config)
    return settlement


def setup_configuration(config_file: Optional[str] = None) -> ConfigurationManager:
    """
    Quick setup for configuration management
    
    Args:
        config_file: Configuration file path
        
    Returns:
        ConfigurationManager: Configured configuration manager
    """
    config_manager = ConfigurationManager(config_file)
    config_manager.load_config()
    return config_manager


def setup_authentication() -> AuthenticationManager:
    """
    Quick setup for authentication management
    
    Returns:
        AuthenticationManager: Configured authentication manager
    """
    auth_manager = AuthenticationManager()
    return auth_manager


# Export all integration helpers
__all__ = [
    "MobileMoneyBridge",
    "AptosSettlement", 
    "ConfigurationManager",
    "AuthenticationManager",
    "setup_mobile_money_integration",
    "setup_blockchain_integration",
    "setup_configuration",
    "setup_authentication"
]
