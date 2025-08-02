"""
CAPP Reference Implementation Configuration

Configuration settings that match the original CAPP system,
using SDK configuration management for easy customization.
"""

import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from decimal import Decimal

from canza_agents import Region, ComplianceLevel


@dataclass
class CAPPConfig:
    """
    CAPP Configuration
    
    Configuration settings that match the original CAPP system.
    These settings ensure the reference implementation achieves
    identical performance to the original system.
    """
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Framework settings
    region: Region = Region.AFRICA
    compliance_level: ComplianceLevel = ComplianceLevel.STANDARD
    
    # Payment optimization settings
    payment_specialization: str = "africa"
    optimization_strategy: str = "cost_first"
    enable_learning: bool = True
    preferred_providers: List[str] = field(default_factory=lambda: [
        "mpesa", "mtn_momo", "airtel_money", "orange_money", "vodafone_cash"
    ])
    
    # Compliance settings
    jurisdictions: List[str] = field(default_factory=lambda: [
        "KE", "NG", "UG", "GH", "TZ", "RW", "ZM", "MW"
    ])
    kyc_threshold: float = 1000.0
    aml_threshold: float = 3000.0
    alert_on_high_risk: bool = True
    
    # Risk settings
    risk_tolerance: str = "moderate"
    
    # Performance settings
    max_concurrent_agents: int = 10
    workflow_timeout: int = 300
    consensus_threshold: float = 0.75
    
    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_max_connections: int = 20
    
    # Mobile money settings
    mobile_money_enabled: bool = True
    mobile_money_health_check_interval: int = 300
    mobile_money_rate_limit_per_minute: int = 60
    mobile_money_cache_ttl: int = 300
    
    # Blockchain settings
    blockchain_enabled: bool = True
    aptos_node_url: str = "https://fullnode.mainnet.aptoslabs.com"
    aptos_gas_limit: int = 1000000
    aptos_gas_price: int = 100
    
    # Credentials (should be loaded from environment or secure storage)
    credentials: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    # Performance targets (matching original CAPP)
    target_cost_reduction: float = 91.0
    target_processing_time: float = 1.5
    target_success_rate: float = 95.0
    target_compliance_rate: float = 100.0
    
    # Monitoring settings
    enable_metrics: bool = True
    enable_logging: bool = True
    log_level: str = "info"
    
    # Development settings
    debug_mode: bool = False
    mock_integrations: bool = False


def load_capp_config() -> CAPPConfig:
    """
    Load CAPP configuration from environment and defaults
    
    Returns:
        CAPPConfig: Loaded configuration
    """
    config = CAPPConfig()
    
    # Load from environment variables
    config.host = os.getenv("CAPP_HOST", config.host)
    config.port = int(os.getenv("CAPP_PORT", str(config.port)))
    
    # Framework settings
    region_str = os.getenv("CAPP_REGION", "africa")
    config.region = Region(region_str)
    
    compliance_str = os.getenv("CAPP_COMPLIANCE_LEVEL", "standard")
    config.compliance_level = ComplianceLevel(compliance_str)
    
    # Payment settings
    config.payment_specialization = os.getenv("CAPP_PAYMENT_SPECIALIZATION", config.payment_specialization)
    config.optimization_strategy = os.getenv("CAPP_OPTIMIZATION_STRATEGY", config.optimization_strategy)
    config.enable_learning = os.getenv("CAPP_ENABLE_LEARNING", "true").lower() == "true"
    
    # Jurisdictions
    jurisdictions_str = os.getenv("CAPP_JURISDICTIONS", "")
    if jurisdictions_str:
        config.jurisdictions = jurisdictions_str.split(",")
    
    # Thresholds
    config.kyc_threshold = float(os.getenv("CAPP_KYC_THRESHOLD", str(config.kyc_threshold)))
    config.aml_threshold = float(os.getenv("CAPP_AML_THRESHOLD", str(config.aml_threshold)))
    config.alert_on_high_risk = os.getenv("CAPP_ALERT_ON_HIGH_RISK", "true").lower() == "true"
    
    # Risk settings
    config.risk_tolerance = os.getenv("CAPP_RISK_TOLERANCE", config.risk_tolerance)
    
    # Performance settings
    config.max_concurrent_agents = int(os.getenv("CAPP_MAX_CONCURRENT_AGENTS", str(config.max_concurrent_agents)))
    config.workflow_timeout = int(os.getenv("CAPP_WORKFLOW_TIMEOUT", str(config.workflow_timeout)))
    config.consensus_threshold = float(os.getenv("CAPP_CONSENSUS_THRESHOLD", str(config.consensus_threshold)))
    
    # Redis settings
    config.redis_host = os.getenv("CAPP_REDIS_HOST", config.redis_host)
    config.redis_port = int(os.getenv("CAPP_REDIS_PORT", str(config.redis_port)))
    config.redis_db = int(os.getenv("CAPP_REDIS_DB", str(config.redis_db)))
    config.redis_password = os.getenv("CAPP_REDIS_PASSWORD", config.redis_password)
    config.redis_max_connections = int(os.getenv("CAPP_REDIS_MAX_CONNECTIONS", str(config.redis_max_connections)))
    
    # Mobile money settings
    config.mobile_money_enabled = os.getenv("CAPP_MOBILE_MONEY_ENABLED", "true").lower() == "true"
    config.mobile_money_health_check_interval = int(os.getenv("CAPP_MOBILE_MONEY_HEALTH_CHECK_INTERVAL", str(config.mobile_money_health_check_interval)))
    config.mobile_money_rate_limit_per_minute = int(os.getenv("CAPP_MOBILE_MONEY_RATE_LIMIT", str(config.mobile_money_rate_limit_per_minute)))
    config.mobile_money_cache_ttl = int(os.getenv("CAPP_MOBILE_MONEY_CACHE_TTL", str(config.mobile_money_cache_ttl)))
    
    # Blockchain settings
    config.blockchain_enabled = os.getenv("CAPP_BLOCKCHAIN_ENABLED", "true").lower() == "true"
    config.aptos_node_url = os.getenv("CAPP_APTOS_NODE_URL", config.aptos_node_url)
    config.aptos_gas_limit = int(os.getenv("CAPP_APTOS_GAS_LIMIT", str(config.aptos_gas_limit)))
    config.aptos_gas_price = int(os.getenv("CAPP_APTOS_GAS_PRICE", str(config.aptos_gas_price)))
    
    # Development settings
    config.debug_mode = os.getenv("CAPP_DEBUG_MODE", "false").lower() == "true"
    config.mock_integrations = os.getenv("CAPP_MOCK_INTEGRATIONS", "false").lower() == "true"
    
    # Load credentials from environment
    config.credentials = load_credentials_from_env()
    
    return config


def load_credentials_from_env() -> Dict[str, Dict[str, str]]:
    """
    Load credentials from environment variables
    
    Returns:
        Dict: Credentials dictionary
    """
    credentials = {}
    
    # M-Pesa credentials
    mpesa_consumer_key = os.getenv("MPESA_CONSUMER_KEY")
    mpesa_consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
    mpesa_passkey = os.getenv("MPESA_PASSKEY")
    
    if all([mpesa_consumer_key, mpesa_consumer_secret, mpesa_passkey]):
        credentials["mpesa"] = {
            "consumer_key": mpesa_consumer_key,
            "consumer_secret": mpesa_consumer_secret,
            "passkey": mpesa_passkey
        }
    
    # MTN MoMo credentials
    mtn_api_key = os.getenv("MTN_API_KEY")
    mtn_api_secret = os.getenv("MTN_API_SECRET")
    mtn_subscription_key = os.getenv("MTN_SUBSCRIPTION_KEY")
    
    if all([mtn_api_key, mtn_api_secret, mtn_subscription_key]):
        credentials["mtn_momo"] = {
            "api_key": mtn_api_key,
            "api_secret": mtn_api_secret,
            "subscription_key": mtn_subscription_key
        }
    
    # Airtel Money credentials
    airtel_client_id = os.getenv("AIRTEL_CLIENT_ID")
    airtel_client_secret = os.getenv("AIRTEL_CLIENT_SECRET")
    airtel_api_key = os.getenv("AIRTEL_API_KEY")
    
    if all([airtel_client_id, airtel_client_secret, airtel_api_key]):
        credentials["airtel_money"] = {
            "client_id": airtel_client_id,
            "client_secret": airtel_client_secret,
            "api_key": airtel_api_key
        }
    
    # Aptos credentials
    aptos_private_key = os.getenv("APTOS_PRIVATE_KEY")
    if aptos_private_key:
        credentials["aptos"] = {
            "private_key": aptos_private_key
        }
    
    return credentials


def get_default_config() -> CAPPConfig:
    """
    Get default CAPP configuration
    
    Returns:
        CAPPConfig: Default configuration
    """
    return CAPPConfig()


def get_development_config() -> CAPPConfig:
    """
    Get development configuration with mock integrations
    
    Returns:
        CAPPConfig: Development configuration
    """
    config = CAPPConfig()
    config.debug_mode = True
    config.mock_integrations = True
    config.log_level = "debug"
    return config


def get_production_config() -> CAPPConfig:
    """
    Get production configuration with strict settings
    
    Returns:
        CAPPConfig: Production configuration
    """
    config = CAPPConfig()
    config.debug_mode = False
    config.mock_integrations = False
    config.log_level = "info"
    config.enable_metrics = True
    config.enable_logging = True
    return config


def validate_config(config: CAPPConfig) -> bool:
    """
    Validate CAPP configuration
    
    Args:
        config: Configuration to validate
        
    Returns:
        bool: True if configuration is valid
    """
    try:
        # Validate required settings
        if not config.host:
            raise ValueError("Host is required")
        
        if config.port < 1 or config.port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        
        if config.kyc_threshold < 0:
            raise ValueError("KYC threshold must be positive")
        
        if config.aml_threshold < 0:
            raise ValueError("AML threshold must be positive")
        
        if config.consensus_threshold < 0 or config.consensus_threshold > 1:
            raise ValueError("Consensus threshold must be between 0 and 1")
        
        if config.target_cost_reduction < 0 or config.target_cost_reduction > 100:
            raise ValueError("Target cost reduction must be between 0 and 100")
        
        if config.target_processing_time < 0:
            raise ValueError("Target processing time must be positive")
        
        if config.target_success_rate < 0 or config.target_success_rate > 100:
            raise ValueError("Target success rate must be between 0 and 100")
        
        if config.target_compliance_rate < 0 or config.target_compliance_rate > 100:
            raise ValueError("Target compliance rate must be between 0 and 100")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False


def print_config_summary(config: CAPPConfig):
    """
    Print configuration summary
    
    Args:
        config: Configuration to summarize
    """
    print("📋 CAPP Configuration Summary")
    print("=" * 40)
    print(f"Server: {config.host}:{config.port}")
    print(f"Region: {config.region.value}")
    print(f"Compliance Level: {config.compliance_level.value}")
    print(f"Payment Specialization: {config.payment_specialization}")
    print(f"Optimization Strategy: {config.optimization_strategy}")
    print(f"Jurisdictions: {', '.join(config.jurisdictions)}")
    print(f"Risk Tolerance: {config.risk_tolerance}")
    print(f"Target Cost Reduction: {config.target_cost_reduction}%")
    print(f"Target Processing Time: {config.target_processing_time}s")
    print(f"Target Success Rate: {config.target_success_rate}%")
    print(f"Target Compliance Rate: {config.target_compliance_rate}%")
    print(f"Debug Mode: {config.debug_mode}")
    print(f"Mock Integrations: {config.mock_integrations}")
    print("=" * 40) 