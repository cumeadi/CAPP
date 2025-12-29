from fastapi import APIRouter, HTTPException, Depends
from .. import schemas
from applications.capp.capp.core.starknet import get_starknet_client
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/starknet",
    tags=["starknet"]
)

@router.post("/address", response_model=schemas.StarknetAddressResponse)
async def compute_address(request: schemas.StarknetAddressRequest):
    """
    Compute the counterfactual address for a given public key without deploying.
    """
    try:
        client = get_starknet_client()
        # Convert hex string to int
        pub_int = int(request.public_key, 16)
        
        address = client.compute_address(pub_int)
        
        return {
            "address": address,
            "public_key": request.public_key
        }
    except Exception as e:
        logger.error("Failed to compute address", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/deploy")
async def deploy_account(request: schemas.StarknetDeployRequest):
    """
    Deploy a pre-calculated account.
    WARNING: The address MUST be funded with ETH before calling this.
    """
    try:
        client = get_starknet_client()
        pub_int = int(request.public_key, 16)
        priv_int = int(request.private_key, 16)
        
        tx_hash = await client.deploy_account(pub_int, priv_int)
        
        return {
            "status": "SUBMITTED",
            "tx_hash": tx_hash,
            "message": "Account deployment transaction submitted. Wait for acceptance."
        }
    except Exception as e:
        logger.error("Failed to deploy account", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/balance/{address}")
async def get_balance(address: str):
    """
    Get the ETH balance of a Starknet address.
    """
    try:
        client = get_starknet_client()
        
        # Use the new get_balance_of helper for arbitrary addresses
        balance_wei = await client.get_balance_of(address)
        
        return {
            "address": address,
            "balance_wei": balance_wei,
            "balance_eth": balance_wei / 1e18 # approximate
        }
    except Exception as e:
        logger.error("Failed to get balance", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transfer", response_model=schemas.TransactionResponse)
async def transfer_funds(request: schemas.StarknetTransferRequest):
    """
    Transfer funds from the SYSTEM ACCOUNT (configured in .env).
    """
    try:
        client = get_starknet_client()
        
        # Convert amount to Wei (assuming input is ETH)
        amount_wei = int(request.amount * 1e18)
        
        tx_hash = await client.transfer(request.recipient, amount_wei)
        
        return {
            "tx_hash": tx_hash,
            "status": "SUBMITTED",
            "timestamp": "2024-01-01T00:00:00" # Placeholder, schemas.TransactionResponse expects datetime object usually, let Pydantic handle if we pass current time
        }
    except Exception as e:
        logger.error("Transfer failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
