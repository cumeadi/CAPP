
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from applications.capp.capp.services.yield_service import YieldService
from applications.capp.capp.api.dependencies.auth import get_current_active_user
from applications.capp.capp.models.user import User

router = APIRouter()

@router.get("/stats")
async def get_wallet_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get wallet statistics including yield and hot wallet balances.
    """
    try:
        service = YieldService()
        # For MVP/Demo, we use a fixed wallet address or the user's mapped address if available
        # In a real system, we'd map current_user.id to their on-chain address(es) managed by CAPP
        # passing "external_client" to simulate a user wallet
        stats = await service.get_total_treasury_balance(wallet_address="external_client")
        
        # Map response to what frontend expects
        # Frontend API expects:
        # total_value_usd: number;
        # hot_wallet_balance: number;
        # yield_balance: number;
        # apy: number;
        # is_sweeping: boolean;
        
        breakdown = stats.get("breakdown", {})
        usdc_stats = breakdown.get("USDC", {})
        apt_stats = breakdown.get("APT", {})
        
        return {
            "total_value_usd": stats.get("total_usd_value", 0),
            "hot_wallet_balance": usdc_stats.get("hot", 0),
            "yield_balance": usdc_stats.get("yielding", 0),
            "aptos_balance": apt_stats.get("total", 0),
            "apy": 4.5, # Mock APY
            "is_sweeping": usdc_stats.get("yielding", 0) > 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
