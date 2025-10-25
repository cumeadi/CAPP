"""
Main API router for CAPP v1
"""

from fastapi import APIRouter

from .endpoints import payments, auth

api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(auth.router)

# Include all endpoint routers
api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["payments"]
)

 