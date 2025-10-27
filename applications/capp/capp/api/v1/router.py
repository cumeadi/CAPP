"""
Main API router for CAPP v1
"""

from fastapi import APIRouter

from .endpoints import payments, auth, health, webhooks

api_router = APIRouter()

# Include health check endpoints (no prefix for standard health paths)
api_router.include_router(health.router)

# Include authentication endpoints
api_router.include_router(auth.router)

# Include all endpoint routers
api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["payments"]
)

# Include webhook endpoints (M-Pesa, MTN, Airtel, Orange Money)
api_router.include_router(
    webhooks.router,
    tags=["webhooks"]
)

 