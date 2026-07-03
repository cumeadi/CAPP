"""
HIFI Africa Rail Integration

Unified payment rail supporting bank transfers and mobile money
across African countries. Currently in beta.
"""

from packages.integrations.hifi.config import HifiConfig
from packages.integrations.hifi.adapter import HifiAfricaRailAdapter
from packages.integrations.hifi.exceptions import (
    HifiIntegrationException,
    HifiKYCException,
    HifiCorridorNotSupportedException,
    HifiBetaLimitExceededException,
)

__all__ = [
    "HifiConfig",
    "HifiAfricaRailAdapter",
    "HifiIntegrationException",
    "HifiKYCException",
    "HifiCorridorNotSupportedException",
    "HifiBetaLimitExceededException",
]
