"""
HIFI Africa Rail Configuration
"""

from decimal import Decimal
from typing import Dict, List, Any

from pydantic import BaseModel, Field


class HifiConfig(BaseModel):
    """Configuration for HIFI Africa Rail integration"""
    api_key: str
    api_secret: str
    base_url: str = "https://sandbox.hifi.africa/v1"
    environment: str = "sandbox"  # sandbox, production
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0

    # Beta feature flags
    enabled: bool = False  # Off by default since beta
    beta_mode: bool = True
    max_transaction_amount: Decimal = Decimal("1000.00")  # Conservative limit for beta
    allowed_countries: List[str] = Field(default_factory=list)  # Explicit allow-list
    fallback_enabled: bool = True  # Fall back to existing providers on failure

    # Rate limiting
    rate_limit_per_minute: int = 100

    # Provider-specific settings
    provider_config: Dict[str, Any] = Field(default_factory=dict)
