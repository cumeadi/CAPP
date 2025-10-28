"""
API v1 Endpoints

Exports all API endpoint routers for easy importing.
"""

from . import payments, auth, health, webhooks, mtn_webhooks, airtel_webhooks

__all__ = [
    "payments",
    "auth",
    "health",
    "webhooks",
    "mtn_webhooks",
    "airtel_webhooks",
]
