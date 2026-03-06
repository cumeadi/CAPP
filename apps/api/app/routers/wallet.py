from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .. import schemas, database, models
from ..database import SessionLocal
from datetime import datetime
import sys
import os
import uuid
from decimal import Decimal

# Ad-hoc path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.core.aptos import get_aptos_client
from applications.capp.capp.core.starknet import get_starknet_client
from applications.capp.capp.core.polygon import PolygonSettlementService
from applications.capp.capp.core.solana import get_solana_client
from applications.capp.capp.core.stellar import get_stellar_client
from applications.capp.capp.agents.settlement.settlement_agent import SettlementAgent, SettlementConfig
from applications.capp.capp.models.payments import (
    PaymentBatch, CrossBorderPayment, PaymentStatus, Currency,
    PaymentType, PaymentMethod, SenderInfo, RecipientInfo, Country, SettlementBatch
)
from .. import state
from applications.capp.capp.services.approval import get_approval_service
from applications.capp.capp.config.settings import settings
from applications.capp.capp.services.anomaly_detection import anomaly_detector
from ..services.price_oracle import get_oracle

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
        # Determine EVM address to check
        # We try to use the derived address from the private key if available (via settings).
        # Since we don't have that easily accessible here without a utility, we will default to 0x0
        # unless a specific EVM address was passed in the request or settings configured.
        
        # NOTE: Reduced to real-data only. If address length is 42 (EVM), use it. 
        # Else check if env has EVM_ACCOUNT_ADDRESS (future).
        # Otherwise, no fallback to 'demo whale'.
        evm_address = address if len(address) == 42 else "0x0"
        
        balance_matic = await poly_service.get_account_balance(evm_address)
        
        # USDC (Polygon PoS USDC)
        USDC_ADDRESS = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359" # USDC.e on Polygon
        balance_usdc = await poly_service.get_token_balance(USDC_ADDRESS, evm_address)

        # Starknet Balance
        # We need a valid Starknet address. For demo, we might use a default if the input doesn't look like one.
        # Starknet addresses are typically 66 chars hex (like Aptos). 
        # For simplicity in this demo hack, we'll just check a default env/system address if provided wasn't explicit.
        stark_client = get_starknet_client()
        stark_balance = 0.0
        try:
             # We can't easily guess the Starknet address from an Aptos/EVM one without a mapping service.
             # We'll rely on the default account in the client for this dashboard view
             if stark_client.account:
                 # Check ETH balance on Starknet
                 # ETH Contract on Starknet Mainnet: 0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
                 stark_balance = await stark_client.get_balance("0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7")
        except Exception as e:
             print(f"Starknet Balance Check Failed: {e}")
             stark_balance = 0.0

        return {
            "address": address, 
            "balance_apt": float(balance_apt),
            "balance_eth": balance_matic,  # Showing MATIC as ETH/L2 native for now in UI slot
            "balance_usdc": balance_usdc,
            "balance_starknet": float(stark_balance)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send", response_model=schemas.TransactionResponse)
async def send_transaction(request: schemas.TransactionRequest):
    """
    Execute transfer using Settlement Agent (Multi-Chain).
    """
    try:
        # Idempotency Check (Must be first)
        from applications.capp.capp.services.idempotency import IdempotencyService
        idempotency_svc = IdempotencyService()
        
        # NOTE: Schema update required to accept idempotency_key. 
        idempotency_key = getattr(request, "idempotency_key", None)
        import structlog
        evt_logger = structlog.get_logger(__name__)
        evt_logger.info("received_idempotency_request", key=idempotency_key)
        
        if idempotency_key:
            locked = await idempotency_svc.check_lock(idempotency_key)
            evt_logger.info("idempotency_check_result", key=idempotency_key, locked=locked)
            if not locked:
                raise HTTPException(status_code=409, detail=f"Idempotency conflict: Key {idempotency_key} already processed")

        agent = get_settlement_agent()
        
        # Autonomy Checks
        requires_approval = False
        approval_reason = ""
        
        if state.app_config.autonomy_level == "COPILOT":
            requires_approval = True
            approval_reason = "Copilot Mode Active: All transactions require approval."
        elif state.app_config.autonomy_level == "GUARDED":
            # Example threshold: $1000
            if request.amount > 1000:
                requires_approval = True
                approval_reason = f"Guarded Mode: Amount {request.amount} exceeds auto-limit of 1000."

        # Security Hook: Plumb through Anomaly Detection
        # Usually from the authenticated agent ID. For demo, we use sender_id.
        active_agent_id = request.sender_id
        anomaly_detector.analyze_transaction(agent_id=active_agent_id, tx_req=request)

        if requires_approval:
            req_id = get_approval_service().request_approval(
                agent_id="settlement_agent",
                action_type="PAYMENT", # Special type that triggers Payment Card in UI
                description=approval_reason + f" Send {request.amount} to {request.recipient_name}",
                payload=request.dict()
            )
            return schemas.TransactionResponse(
                tx_hash="WAITING_FOR_APPROVAL",
                status="PENDING_APPROVAL",
                timestamp=datetime.utcnow()
            )
        
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
        
        # If successfully locked, we proceed. 
        # ideally we update the lock with the result later, but for now just locking initiates is enough for "Phase 2".
        
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

        # 2. Execute settlement — this is what produces the on-chain tx_hash.
        #    SettlementAgent.execute_settlement() returns the transaction hash string.
        tx_hash = await agent.execute_settlement(batch)

        # 3. Write to Payment Memory Layer
        db = SessionLocal()
        try:
            memory_record = models.PaymentMemoryRecord(
                tx_hash=tx_hash,
                corridor=f"{request.from_currency}-{request.to_currency}",
                target_chain=request.target_chain or "UNKNOWN",
                amount_usd=float(request.amount),
                execution_time_ms=1200, # Mock execution time
                success=True
            )
            db.add(memory_record)
            db.commit()
        except Exception as e:
            evt_logger.error("failed_to_write_payment_memory", error=str(e))
        finally:
            db.close()
        
        return schemas.TransactionResponse(
            tx_hash=tx_hash,
            status="SUBMITTED",
            timestamp=datetime.utcnow()
        )
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_wallet_stats():
    """
    Aggregate total value from all configured chains.
    Asset prices are fetched from the PriceOracle (Redis-cached, upstream feed,
    then hardcoded fallback). No prices are hardcoded in this function.
    """
    try:
        oracle = get_oracle()
        prices = await oracle.get_prices(["APT", "MATIC", "USDC", "ETH", "SOL", "XLM"])

        total_usd = 0.0
        hot_wallet = 0.0
        bal_sol = 0.0
        bal_xlm = 0.0

        # 1. Aptos
        try:
            apt_client = get_aptos_client()
            apt_addr = settings.APTOS_ACCOUNT_ADDRESS
            if apt_addr and apt_addr != "demo-account-address":
                bal_apt = await apt_client.get_account_balance(apt_addr)
                apt_usd = float(bal_apt) * prices["APT"]
                total_usd += apt_usd
                hot_wallet += apt_usd
        except Exception as e:
            print(f"Stats Aptos Error: {e}")

        # 2. Polygon (EVM)
        try:
            poly_service = PolygonSettlementService()
            # Using a known address for demo or 0x0
            evm_address = "0x0"
            if settings.POLYGON_PRIVATE_KEY:
                 # In a real app we'd derive this. For now we assume the user funds the generated address
                 # We will use a hardcoded 0x0 unless we pass it in env.
                 # Actually, let's use the one we just generated if we can...
                 # Ideally we add EVM_ACCOUNT_ADDRESS to settings.
                 pass

            # MATIC
            bal_matic = await poly_service.get_account_balance(evm_address)
            matic_usd = bal_matic * prices["MATIC"]
            total_usd += matic_usd
            hot_wallet += matic_usd

            # USDC (price is ~1.0 but fetched from oracle for consistency)
            USDC_ADDR = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
            bal_usdc = await poly_service.get_token_balance(USDC_ADDR, evm_address)
            usdc_usd = bal_usdc * prices["USDC"]
            total_usd += usdc_usd
            hot_wallet += usdc_usd

        except Exception as e:
            print(f"Stats EVM Error: {e}")

        # 3. Starknet
        try:
            stark_client = get_starknet_client()
            if settings.STARKNET_ACCOUNT_ADDRESS != "0x0":
                ETH_CONTRACT = "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7"
                bal_eth = await stark_client.get_balance(ETH_CONTRACT)
                eth_usd = float(bal_eth) * prices["ETH"]
                total_usd += eth_usd
                hot_wallet += eth_usd
        except Exception as e:
             print(f"Stats Starknet Error: {e}")

        # 4. Solana
        try:
            sol_client = get_solana_client()
            bal_sol = await sol_client.get_balance("default")
            sol_usd = float(bal_sol) * prices["SOL"]
            total_usd += sol_usd
            hot_wallet += sol_usd
        except Exception as e:
             print(f"Stats Solana Error: {e}")

        # 5. Stellar
        try:
            xlm_client = get_stellar_client()
            bal_xlm = await xlm_client.get_balance("default")
            xlm_usd = float(bal_xlm) * prices["XLM"]
            total_usd += xlm_usd
            hot_wallet += xlm_usd
        except Exception as e:
             print(f"Stats Stellar Error: {e}")

        return {
            "total_value_usd": total_usd,
            "hot_wallet_balance": hot_wallet,
            "yield_balance": 0.0, # Placeholder for Defi positions
            "apy": 6.8, # Placeholder
            "is_sweeping": True,
            "solana_balance": float(bal_sol),
            "stellar_balance": float(bal_xlm)
        }
    except Exception as e:
        print(f"Stats Error: {e}")
        # Fallback to 0 instead of erroring out UI
        return {
            "total_value_usd": 0.0,
            "hot_wallet_balance": 0.0,
            "yield_balance": 0.0,
            "apy": 0.0,
            "is_sweeping": False,
            "solana_balance": 0.0,
            "stellar_balance": 0.0
        }
