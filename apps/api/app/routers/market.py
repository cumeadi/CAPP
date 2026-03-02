from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from applications.capp.capp.core.limiter import limiter
from fastapi import Request

from ..services.market_context import market_context

router = APIRouter(
    prefix="/market",
    tags=["market-intelligence"]
)

@router.get("/stress", response_model=Dict[str, Any])
@limiter.limit("20/minute")
async def get_market_stress(request: Request):
    """
    Get the current global AI-driven market stress indicator.
    """
    return await market_context.get_market_stress_indicator()

@router.get("/protocol/{protocol_id}/health", response_model=Dict[str, Any])
@limiter.limit("20/minute")
async def get_protocol_health(protocol_id: str, request: Request):
    """
    Get AI-driven health and sentiment metrics for a specific DeFi protocol.
    Used by Smart Sweep agents to evaluate risk before allocating idle treasury.
    """
    return await market_context.get_protocol_health(protocol_id)

@router.get("/corridor/{corridor}/context", response_model=Dict[str, Any])
@limiter.limit("20/minute")
async def get_corridor_context(corridor: str, request: Request):
    """
    Get macro market context and AI insights for a specific corridor.
    """
    return await market_context.get_corridor_macro_context(corridor)
