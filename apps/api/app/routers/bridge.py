
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional
from applications.capp.capp.core.bridge import PlasmaBridgeService

router = APIRouter(
    prefix="/bridge",
    tags=["bridge"]
)

# Service Instance
bridge_service = PlasmaBridgeService()

class BridgeRequest(BaseModel):
    amount: float
    user_address: str
    token: str = "USDC"

class FinalizeRequest(BaseModel):
    exit_id: str

@router.post("/deposit")
async def deposit_assets(request: BridgeRequest):
    """Bridge assets from Root (L1) to Child (L2)"""
    try:
        result = await bridge_service.deposit(request.amount, request.user_address, request.token)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/withdraw")
async def withdraw_assets(request: BridgeRequest):
    """Initiate Plasma Exit from Child (L2) to Root (L1)"""
    try:
        result = await bridge_service.initiate_withdraw(request.amount, request.user_address, request.token)
        return result
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/exit/{exit_id}")
async def check_exit(exit_id: str):
    """Check status of a Plasma Exit"""
    try:
        result = await bridge_service.check_exit_status(exit_id)
        if result.get("status") == "NOT_FOUND":
            raise HTTPException(status_code=404, detail="Exit not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/finalize")
async def finalize_exit(request: FinalizeRequest):
    """Finalize Exit and Release Funds on Root"""
    try:
        result = await bridge_service.finalize_exit(request.exit_id)
        if "error" in result:
             raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
