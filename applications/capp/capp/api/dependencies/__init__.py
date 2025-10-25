"""
API dependencies module

This module provides reusable dependencies for FastAPI routes,
including authentication, authorization, and validation.
"""

from .auth import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_admin,
    get_optional_user,
)

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_admin",
    "get_optional_user",
]
