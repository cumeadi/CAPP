"""
Secrets management for CAPP

This module provides utilities for managing secrets securely,
including validation, rotation helpers, and secure storage recommendations.
"""

import os
import secrets
import string
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import structlog

from ..config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


# Default insecure values that should never be used in production
INSECURE_DEFAULTS = [
    "demo-secret-key-change-in-production",
    "your-super-secret-key-change-this-in-production",
    "demo-private-key",
    "demo-account-address",
    "changeme",
    "password",
    "secret",
]


class SecretsManager:
    """
    Secrets manager for validating and managing application secrets
    """

    def __init__(self):
        self.settings = get_settings()
        self._warnings: list[str] = []

    def validate_secrets(self) -> Dict[str, Any]:
        """
        Validate all application secrets

        Returns:
            Dictionary with validation results and warnings
        """
        warnings = []
        errors = []

        # Check SECRET_KEY
        if self.settings.SECRET_KEY in INSECURE_DEFAULTS:
            warnings.append(
                "SECRET_KEY is using an insecure default value. "
                "Change it immediately for production!"
            )

        if len(self.settings.SECRET_KEY) < 32:
            warnings.append(
                "SECRET_KEY should be at least 32 characters long"
            )

        # Check APTOS credentials
        if self.settings.APTOS_PRIVATE_KEY in INSECURE_DEFAULTS:
            warnings.append(
                "APTOS_PRIVATE_KEY is using default value. "
                "Set a real private key for production."
            )

        if self.settings.APTOS_ACCOUNT_ADDRESS in INSECURE_DEFAULTS:
            warnings.append(
                "APTOS_ACCOUNT_ADDRESS is using default value. "
                "Set a real account address for production."
            )

        # Check MMO credentials
        if not self.settings.MMO_MPESA_CONSUMER_KEY and settings.ENVIRONMENT == "production":
            errors.append("M-Pesa consumer key not configured")

        if not self.settings.MMO_MPESA_CONSUMER_SECRET and settings.ENVIRONMENT == "production":
            errors.append("M-Pesa consumer secret not configured")

        # Check environment
        if settings.ENVIRONMENT == "production":
            if settings.DEBUG:
                errors.append("DEBUG mode is enabled in production!")

            if "*" in settings.ALLOWED_ORIGINS:
                errors.append("CORS allows all origins in production!")

        # Log warnings and errors
        for warning in warnings:
            logger.warning("Security warning", message=warning)
            self._warnings.append(warning)

        for error in errors:
            logger.error("Security error", message=error)

        return {
            "is_secure": len(errors) == 0,
            "warnings": warnings,
            "errors": errors,
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_warnings(self) -> list[str]:
        """Get all security warnings"""
        return self._warnings


def generate_secret_key(length: int = 64) -> str:
    """
    Generate a cryptographically secure secret key

    Args:
        length: Length of the secret key (default: 64)

    Returns:
        Secure random secret key
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def validate_secret_strength(secret: str, min_length: int = 32) -> bool:
    """
    Validate the strength of a secret

    Args:
        secret: Secret to validate
        min_length: Minimum required length

    Returns:
        True if secret is strong enough
    """
    if len(secret) < min_length:
        return False

    if secret in INSECURE_DEFAULTS:
        return False

    # Check for character diversity
    has_lower = any(c.islower() for c in secret)
    has_upper = any(c.isupper() for c in secret)
    has_digit = any(c.isdigit() for c in secret)
    has_special = any(c in string.punctuation for c in secret)

    # Should have at least 3 of the 4 character types
    char_types = sum([has_lower, has_upper, has_digit, has_special])

    return char_types >= 3


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """
    Mask a secret for safe logging

    Args:
        secret: Secret to mask
        visible_chars: Number of characters to show at the end

    Returns:
        Masked secret string
    """
    if len(secret) <= visible_chars:
        return "*" * len(secret)

    return "*" * (len(secret) - visible_chars) + secret[-visible_chars:]


def check_secret_rotation_needed(
    last_rotation: datetime,
    rotation_days: int = 90
) -> bool:
    """
    Check if a secret needs rotation

    Args:
        last_rotation: Date of last rotation
        rotation_days: Days between rotations (default: 90)

    Returns:
        True if rotation is needed
    """
    rotation_threshold = last_rotation + timedelta(days=rotation_days)
    return datetime.utcnow() > rotation_threshold


def get_secret_from_env_or_file(
    env_var: str,
    file_path: Optional[str] = None,
    default: Optional[str] = None
) -> Optional[str]:
    """
    Get a secret from environment variable or file

    Supports Docker secrets pattern where secrets are stored in files.

    Args:
        env_var: Environment variable name
        file_path: Optional path to file containing the secret
        default: Default value if secret not found

    Returns:
        Secret value or None
    """
    # First try environment variable
    value = os.getenv(env_var)
    if value:
        return value

    # Then try file (for Docker secrets)
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(
                "Failed to read secret from file",
                file_path=file_path,
                error=str(e)
            )

    # Finally return default
    return default


# Initialize secrets manager
secrets_manager = SecretsManager()


def validate_all_secrets_on_startup() -> None:
    """
    Validate all secrets on application startup

    Logs warnings and errors for any security issues found.
    """
    logger.info("Validating application secrets...")

    validation_result = secrets_manager.validate_secrets()

    if not validation_result["is_secure"]:
        logger.error(
            "Security validation failed",
            errors=validation_result["errors"],
            warnings=validation_result["warnings"]
        )

        if settings.ENVIRONMENT == "production":
            raise RuntimeError(
                "Cannot start application with security errors in production. "
                f"Errors: {validation_result['errors']}"
            )
    elif validation_result["warnings"]:
        logger.warning(
            "Security warnings detected",
            warnings=validation_result["warnings"]
        )
    else:
        logger.info("All secrets validated successfully")
