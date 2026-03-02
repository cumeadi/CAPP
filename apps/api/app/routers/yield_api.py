from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from applications.capp.capp.services.yield_service import YieldService

router = APIRouter(
    prefix="/yield",
    tags=["yield"]
)

_yield_service = YieldService()

class OptimizeRequest(BaseModel):
    wallet_address: str
    min_sweep_amount: Optional[float] = None
    buffer_pct: Optional[float] = None

@router.get("/balance/{address}")
async def get_yield_balance(address: str):
    """
    Get aggregated treasury balance (Hot + Yield) for a specific wallet.
    """
    try:
        data = await _yield_service.get_total_treasury_balance(wallet_address=address)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize")
async def optimize_wallet(req: OptimizeRequest):
    """
    Trigger the Smart Sweep Agent to analyze and optimize a specific wallet's idle funds.
    """
    try:
        config = {}
        if req.min_sweep_amount is not None:
            config["min_sweep_amount"] = str(req.min_sweep_amount)
        if req.buffer_pct is not None:
            config["buffer_pct"] = str(req.buffer_pct)
            
        await _yield_service.optimize_wallet(req.wallet_address, config)
        
        # Return the new updated balance
        return await _yield_service.get_total_treasury_balance(wallet_address=req.wallet_address)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
