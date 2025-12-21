from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .. import schemas, database, models
from datetime import datetime
import sys
import os

# Ad-hoc path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.core.aptos import get_aptos_client

router = APIRouter(
    prefix="/wallet",
    tags=["wallet"]
)

@router.get("/balance/{address}")
async def get_balance(address: str):
    try:
        client = get_aptos_client() # Will use settings from env
        balance = await client.get_account_balance(address)
        return {"address": address, "balance_apt": float(balance)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send", response_model=schemas.TransactionResponse)
async def send_transaction(request: schemas.TransactionRequest):
    """
    Execute transfer. 
    NOTE: In a real wallet, the Client signs locally and sends signed tx string.
    Here, the backend (custodial simulation) signs.
    """
    try:
        client = get_aptos_client()
        
        # In a real app, we would unlock the 'from_address' private key from DB
        # For this demo, client uses the loaded .env key (Custodial MVP)
        
        tx_hash = await client.submit_transaction(
            recipient=request.to_address,
            amount=request.amount
        )
        
        return schemas.TransactionResponse(
            tx_hash=tx_hash,
            status="SUBMITTED",
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
