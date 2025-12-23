from fastapi import APIRouter, HTTPException
import httpx
from .. import config
from pydantic import BaseModel
from datetime import datetime

class BridgeRequest(BaseModel):
    from_chain: str
    to_chain: str
    token: str
    amount: float
    recipient: str

class BridgeResponse(BaseModel):
    tx_hash: str
    status: str
    estimated_arrival: str
    bridge_fee_usd: float
router = APIRouter(
    prefix="/chain",
    tags=["chain_data"]
)

@router.get("/polygon/gas")
async def get_polygon_gas():
    """
    Fetch current gas price from Polygon via Alchemy.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_gasPrice",
        "params": [],
        "id": 1
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(config.POLYGON_RPC_URL, json=payload)
            
            if response.status_code != 200:
                print(f"Polygon RPC Error: {response.text}")
                return {"chain": "POLYGON", "gas_price_wei": 0, "gas_price_gwei": 0}

            data = response.json()
            
            if "error" in data:
                 print(f"Alchemy API Error: {data['error']}")
                 return {"chain": "POLYGON", "gas_price_wei": 0, "gas_price_gwei": 0}
            
            # Convert hex wei to Gwei
            wei_price = int(data["result"], 16)
            gwei_price = wei_price / 10**9
            
            return {
                "chain": "POLYGON",
                "gas_price_wei": wei_price,
                "gas_price_gwei": round(gwei_price, 2)
            }
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"RPC Connection Error: {str(e)}")

@router.get("/polygon/balance/{address}")
async def get_polygon_balance(address: str):
    """
    Fetch MATIC balance for an address.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [address, "latest"],
        "id": 1
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(config.POLYGON_RPC_URL, json=payload)
            data = response.json()
            
            if "error" in data:
                raise HTTPException(status_code=400, detail=f"Alchemy Error: {data['error']['message']}")
                
            wei_balance = int(data["result"], 16)
            matic_balance = wei_balance / 10**18
            
            return {
                "chain": "POLYGON",
                "address": address,
                "balance_matic": matic_balance,
                "balance_wei": str(wei_balance)
            }
    
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/bridge", response_model=BridgeResponse)
async def bridge_assets(request: BridgeRequest):
    """
    Simulate a Cross-Chain Bridge Transaction (LayerZero style).
    """
    try:
        # 1. Simulate "Locking" on Source Chain (Aptos)
        # In a real app, we would verify the burn/lock tx hash here.
        
        # 2. Simulate "Relaying" time
        # We process it immediately for the demo but return an estimated time.
        
        # 3. Simulate "Minting" on Destination (Polygon)
        # We just return a success Mock.
        
        return BridgeResponse(
            tx_hash=f"0x{request.token}_{request.to_chain}_MOCK_HASH_{int(datetime.utcnow().timestamp())}",
            status="INITIATED",
            estimated_arrival="2 mins",
            bridge_fee_usd=0.05 # Mock LayerZero Fee
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
