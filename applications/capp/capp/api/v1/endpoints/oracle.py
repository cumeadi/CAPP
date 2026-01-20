
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
from applications.capp.capp.services.oracle_service import OracleService

router = APIRouter()

class OracleStatusResponse(BaseModel):
    status: str
    updated_at: Optional[str] = None
    meta: Dict[str, Any] = {}
    message: Optional[str] = None

@router.get("/status/{tx_hash}", response_model=OracleStatusResponse)
async def get_transaction_status(tx_hash: str):
    """
    Get the cross-chain settlement status of a transaction.
    """
    oracle = OracleService.get_instance()
    result = await oracle.get_status(tx_hash)
    
    if result.get("status") == "UNKNOWN":
        # We return 404 if not found, or 200 with UNKNOWN status?
        # Usually for an Oracle, if we don't know it, it's effectively 404 or just "Not processed by us".
        # Let's return 200 with status=UNKNOWN for client ease, but include 404 semantics in message.
        return OracleStatusResponse(
            status="UNKNOWN",
            message="Transaction not found in CAPP Oracle Index."
        )
        
    return OracleStatusResponse(
        status=result["status"],
        updated_at=result.get("updated_at"),
        meta=result.get("meta", {})
    )
