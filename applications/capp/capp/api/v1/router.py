"""
Main API router for CAPP v1
"""

from fastapi import APIRouter

from .endpoints import payments, auth, health, oracle, wallet, compliance, liquidity, policy, agents, batch, analytics, admin_reconciliation

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

# Include Oracle endpoints
api_router.include_router(
    oracle.router,
    prefix="/oracle",
    tags=["oracle"]
)

# Include Wallet endpoints
api_router.include_router(
    wallet.router,
    prefix="/wallet",
    tags=["wallet"]
)

# Include Compliance endpoints
api_router.include_router(
    compliance.router,
    prefix="/compliance",
    tags=["compliance"]
)

# Include Liquidity endpoints
api_router.include_router(
    liquidity.router,
    prefix="/corridors",
    tags=["liquidity"]
)

# Include Policy endpoints
api_router.include_router(
    policy.router,
    prefix="/policy",
    tags=["policy"]
)

# Include Agent Credential endpoints
api_router.include_router(
    agents.router,
    prefix="/agents",
    tags=["agents"]
)

# Include Batch payment endpoints
api_router.include_router(
    batch.router,
    prefix="/payments",
    tags=["payments"]
)

# Include Analytics endpoints
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)

# Include Admin Reconciliation endpoints
api_router.include_router(
    admin_reconciliation.router,
    prefix="/admin/reconciliation",
    tags=["admin"]
)