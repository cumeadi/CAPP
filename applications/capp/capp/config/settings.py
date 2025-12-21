"""
Configuration settings for CAPP application
"""

import os
from typing import List, Optional
from functools import lru_cache

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "CAPP"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Security
    SECRET_KEY: str = Field(default="demo-secret-key-change-in-production", env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        env="ALLOWED_HOSTS"
    )
    
    # Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://demo:demo@localhost:5432/capp_demo", env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    REDIS_POOL_SIZE: int = Field(default=10, env="REDIS_POOL_SIZE")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9092",
        env="KAFKA_BOOTSTRAP_SERVERS"
    )
    KAFKA_TOPIC_PAYMENTS: str = Field(
        default="capp.payments",
        env="KAFKA_TOPIC_PAYMENTS"
    )
    KAFKA_TOPIC_SETTLEMENTS: str = Field(
        default="capp.settlements",
        env="KAFKA_TOPIC_SETTLEMENTS"
    )
    
    # Aptos Blockchain
    APTOS_NODE_URL: str = Field(
        default="https://fullnode.testnet.aptoslabs.com/v1",
        env="APTOS_NODE_URL"
    )
    APTOS_FAUCET_URL: str = Field(
        default="https://faucet.testnet.aptoslabs.com",
        env="APTOS_FAUCET_URL"
    )
    APTOS_PRIVATE_KEY: str = Field(default="demo-private-key", env="APTOS_PRIVATE_KEY")
    APTOS_ACCOUNT_ADDRESS: str = Field(default="demo-account-address", env="APTOS_ACCOUNT_ADDRESS")
    
    # Smart Contract Address (Placeholder until deployment)
    APTOS_CONTRACT_ADDRESS: str = Field(
        default="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef", 
        env="APTOS_CONTRACT_ADDRESS"
    )
    
    # LiquidSwap (Pontem) DEX Address
    LIQUIDSWAP_ADDRESS: str = Field(
        default="0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12",
        env="LIQUIDSWAP_ADDRESS"
    )
    
    # Mobile Money Operators (MMO)
    MMO_MPESA_CONSUMER_KEY: str = Field(default="", env="MMO_MPESA_CONSUMER_KEY")
    MMO_MPESA_CONSUMER_SECRET: str = Field(default="", env="MMO_MPESA_CONSUMER_SECRET")
    MMO_MPESA_BUSINESS_SHORT_CODE: str = Field(default="", env="MMO_MPESA_BUSINESS_SHORT_CODE")
    MMO_MPESA_PASSKEY: str = Field(default="", env="MMO_MPESA_PASSKEY")
    
    MMO_ORANGE_API_KEY: str = Field(default="", env="MMO_ORANGE_API_KEY")
    MMO_ORANGE_API_SECRET: str = Field(default="", env="MMO_ORANGE_API_SECRET")
    
    MMO_MTN_API_KEY: str = Field(default="", env="MMO_MTN_API_KEY")
    MMO_MTN_API_SECRET: str = Field(default="", env="MMO_MTN_API_SECRET")
    
    MMO_AIRTEL_API_KEY: str = Field(default="", env="MMO_AIRTEL_API_KEY")
    MMO_AIRTEL_API_SECRET: str = Field(default="", env="MMO_AIRTEL_API_SECRET")
    
    # Exchange Rate APIs
    EXCHANGE_RATE_API_KEY: str = Field(default="", env="EXCHANGE_RATE_API_KEY")
    EXCHANGE_RATE_BASE_URL: str = Field(
        default="https://api.exchangerate-api.com/v4/latest",
        env="EXCHANGE_RATE_BASE_URL"
    )
    
    # Temporal Workflow
    TEMPORAL_HOST: str = Field(default="localhost:7233", env="TEMPORAL_HOST")
    TEMPORAL_NAMESPACE: str = Field(default="capp", env="TEMPORAL_NAMESPACE")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    
    # Payment Configuration
    MAX_PAYMENT_AMOUNT: float = Field(default=10000.0, env="MAX_PAYMENT_AMOUNT")
    MIN_PAYMENT_AMOUNT: float = Field(default=1.0, env="MIN_PAYMENT_AMOUNT")
    DEFAULT_TRANSACTION_TIMEOUT: int = Field(default=300, env="DEFAULT_TRANSACTION_TIMEOUT")  # 5 minutes
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # Fraud Detection
    FRAUD_DETECTION_ENABLED: bool = Field(default=True, env="FRAUD_DETECTION_ENABLED")
    FRAUD_THRESHOLD_SCORE: float = Field(default=0.8, env="FRAUD_THRESHOLD_SCORE")
    
    # Compliance
    COMPLIANCE_ENABLED: bool = Field(default=True, env="COMPLIANCE_ENABLED")
    SANCTIONS_CHECK_ENABLED: bool = Field(default=True, env="SANCTIONS_CHECK_ENABLED")
    
    # Offline Support
    OFFLINE_MODE_ENABLED: bool = Field(default=True, env="OFFLINE_MODE_ENABLED")
    OFFLINE_SYNC_INTERVAL: int = Field(default=300, env="OFFLINE_SYNC_INTERVAL")  # 5 minutes
    
    # Performance
    MAX_CONCURRENT_PAYMENTS: int = Field(default=10000, env="MAX_CONCURRENT_PAYMENTS")
    PAYMENT_BATCH_SIZE: int = Field(default=100, env="PAYMENT_BATCH_SIZE")
    
    # SMS/USSD Configuration
    SMS_PROVIDER: str = Field(default="twilio", env="SMS_PROVIDER")
    SMS_API_KEY: str = Field(default="", env="SMS_API_KEY")
    SMS_API_SECRET: str = Field(default="", env="SMS_API_SECRET")
    SMS_FROM_NUMBER: str = Field(default="", env="SMS_FROM_NUMBER")
    
    USSD_PROVIDER: str = Field(default="africastalking", env="USSD_PROVIDER")
    USSD_API_KEY: str = Field(default="", env="USSD_API_KEY")
    USSD_API_SECRET: str = Field(default="", env="USSD_API_SECRET")

    # Market Intelligence (CoinMarketCap)
    COINMARKETCAP_API_KEY: str = Field(default="", env="COINMARKETCAP_API_KEY")
    MARKET_ANALYSIS_ENABLED: bool = Field(default=True, env="MARKET_ANALYSIS_ENABLED")
    CMC_BASE_URL: str = Field(default="https://pro-api.coinmarketcap.com/v1", env="CMC_BASE_URL")
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    # Removed KAFKA_BOOTSTRAP_SERVERS validator since field is now a string
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings() 