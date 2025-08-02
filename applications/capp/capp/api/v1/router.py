"""
Main API router for CAPP v1
"""

from fastapi import APIRouter

from ..api.v1.endpoints import payments

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["payments"]
)

 