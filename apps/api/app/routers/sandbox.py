from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

# Mock state for sandbox environment
sandbox_state = {
    "failures_injected": {},
    "balances": {
        "aptos": 100.0,
        "polygon": 500.0,
        "starknet": 50.0,
        "by_currency": {
            "USD": 10000.0,
            "NGN": 5000000.0,
            "KES": 200000.0,
            "GHS": 80000.0
        }
    }
}

class FailureRequest(BaseModel):
    failure_type: str
    corridor: Optional[str] = None
    duration_seconds: int

@router.post("/inject-failure")
async def inject_failure(request: FailureRequest, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer sk_test_"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Sandbox actions require a test API key starting with 'sk_test_'"
        )
        
    logger.info("sandbox_failure_injected", type=request.failure_type, duration=request.duration_seconds)
    key = request.corridor if request.corridor else "global"
    sandbox_state["failures_injected"][key] = request.failure_type
    
    return {"status": "success", "message": f"Injected {request.failure_type} into {key}"}

@router.post("/reset")
async def reset_sandbox(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer sk_test_"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Sandbox actions require a test API key starting with 'sk_test_'"
        )
        
    sandbox_state["failures_injected"].clear()
    sandbox_state["balances"] = {
        "aptos": 100.0,
        "polygon": 500.0,
        "starknet": 50.0,
        "by_currency": {
            "USD": 10000.0,
            "NGN": 5000000.0,
            "KES": 200000.0,
            "GHS": 80000.0
        }
    }
    
    logger.info("sandbox_reset")
    return {"status": "success", "message": "Sandbox values reset to defaults"}

class FaucetRequest(BaseModel):
    asset: str
    amount: float
    
@router.post("/faucet")
async def process_faucet(request: FaucetRequest, authorization: str = Header(None)):
    """
    Simulates dispensing testnet tokens to the authenticated agent's wallet.
    Only available in Sandbox mode.
    """
    if not authorization or not authorization.startswith("Bearer sk_test_"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Sandbox actions require a test API key starting with 'sk_test_'"
        )
        
    asset = request.asset.upper()
    amount = request.amount
    
    if asset not in sandbox_state["balances"]["by_currency"]:
        # Mock creating the wallet row if it doesn't exist
        sandbox_state["balances"]["by_currency"][asset] = 0.0
        
    sandbox_state["balances"]["by_currency"][asset] += amount
    
    import uuid
    tx_hash = f"mocktx_{uuid.uuid4().hex[:16]}"
    
    logger.info("sandbox_faucet_dispensed", asset=asset, amount=amount, tx_hash=tx_hash)
    
    return {
        "status": "success",
        "tx_hash": tx_hash,
        "new_balance": sandbox_state["balances"]["by_currency"][asset],
        "message": f"Dispensed {amount} {asset} to sandbox wallet."
    }

@router.get("/state")
async def get_sandbox_state():
    """For local testing and debugging"""
    return sandbox_state
