from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .. import schemas, database, models
from datetime import datetime
import sys
import os
import uuid
from decimal import Decimal

# Ad-hoc path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.core.aptos import get_aptos_client
from applications.capp.capp.core.polygon import PolygonSettlementService
from applications.capp.capp.agents.settlement.settlement_agent import SettlementAgent, SettlementConfig
from applications.capp.capp.models.payments import (
    PaymentBatch, CrossBorderPayment, PaymentStatus, Currency,
    PaymentType, PaymentMethod, SenderInfo, RecipientInfo, Country, SettlementBatch
)

router = APIRouter(
    prefix="/wallet",
    tags=["wallet"]
)

# Global Settlement Agent (Lazily initialized)
_settlement_agent = None

def get_settlement_agent():
    global _settlement_agent
    if not _settlement_agent:
        config = SettlementConfig(agent_type="SETTLEMENT")
        _settlement_agent = SettlementAgent(config)
    return _settlement_agent

@router.get("/balance/{address}")
async def get_balance(address: str):
    try:
        # Aptos Balance
        client = get_aptos_client() 
        balance_apt = await client.get_account_balance(address)

        # Polygon Balances (MATIC & USDC)
        # Note: We use the same address for EVM since we assume user has same derived key or just reusing the string for demo
        # In reality, Aptos and EVM addresses differ. For this demo, we'll try to use the configured "Polygon Account" 
        # or if the user passed an EVM-like address (starts with 0x).
        
        poly_service = PolygonSettlementService()
        
        # Determine EVM address to check
        # If address passed is 66 chars (Aptos), we can't check it on Polygon.
        # We'll use the hardcoded/configured settings.POLYGON_ACCOUNT_ADDRESS if available or just return 0
        # for the specific user check unless they enabled "Linked Wallets".
        # For this specific "Debug" request, the user likely wants to see the *system* or *demo* wallet balance.
        
        # Let's check the address format.
        evm_address = address if len(address) == 42 else "0x742d35Cc6634C0532925a3b844Bc454e4438f44e" # Default/Demo EVM
        
        balance_matic = await poly_service.get_account_balance(evm_address)
        
        # USDC (Polygon PoS USDC)
        USDC_ADDRESS = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359" # USDC.e on Polygon
        balance_usdc = await poly_service.get_token_balance(USDC_ADDRESS, evm_address)

        return {
            "address": address, 
            "balance_apt": float(balance_apt),
            "balance_eth": balance_matic,  # Showing MATIC as ETH/L2 native for now in UI slot
            "balance_usdc": balance_usdc
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send", response_model=schemas.TransactionResponse)
async def send_transaction(request: schemas.TransactionRequest):
    """
    Execute transfer using Settlement Agent (Multi-Chain).
    """
    try:
        agent = get_settlement_agent()
        
        # Determine Enums safely
        try:
            from_curr = Currency(request.from_currency)
            to_curr = Currency(request.to_currency)
            sender_country = Country(request.sender_country) if hasattr(request, 'sender_country') and request.sender_country else Country.UNITED_STATES
            recipient_country = Country(request.recipient_country) if hasattr(request, 'recipient_country') and request.recipient_country else Country.KENYA
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")

        # Construct full payment object
        payment_id = uuid.uuid4()
        
        # Create Sender Info Model
        sender = SenderInfo(
            sender_id=uuid.uuid4(), # Generate valid UUID for sender
            name=request.sender_id, # Using sender_id as name for now if name missing
            phone_number="+15550000000",
            country=sender_country,
            kyc_verified=True
        )
        
        # Create Recipient Info Model
        recipient = RecipientInfo(
            name=request.recipient_name,
            phone_number="+254700000000", # Default for KE
            country=recipient_country,
            address=request.recipient_address
        )

        payment = CrossBorderPayment(
            payment_id=payment_id,
            reference_id=f"TX-{str(payment_id)[:8]}".upper(),
            amount=Decimal(str(request.amount)),
            from_currency=from_curr,
            to_currency=to_curr,
            payment_type=PaymentType.PERSONAL_REMITTANCE,
            payment_method=PaymentMethod.CRYPTO,
            status=PaymentStatus.SETTLING,
            sender=sender,
            recipient=recipient,
            metadata={"target_chain": request.target_chain} if request.target_chain else {}
        )
        
        batch = SettlementBatch(
            batch_id=str(uuid.uuid4()),
            payments=[payment],
            total_amount=Decimal(str(request.amount)),
            total_fees=Decimal("0"),
            currency=to_curr,
            from_currency=from_curr,
            to_currency=to_curr
        )
        
        # 2. Execute Settlement
        # The agent returns a tx_hash string
        tx_hash = await agent.execute_settlement(batch)
        
        return schemas.TransactionResponse(
            tx_hash=tx_hash,
            status="SUBMITTED",
            timestamp=datetime.utcnow()
        )
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
