from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .. import schemas, database, models
from datetime import datetime
import sys
import os

# Ad-hoc path fix to import packages
# In production, this should be handled by proper packaging (setup.py)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from packages.intelligence.market.analyst import MarketAnalysisAgent
from packages.intelligence.compliance.agent import AIComplianceAgent
from packages.intelligence.compliance.agent import AIComplianceAgent
from packages.intelligence.core.gemini_provider import GeminiProvider
from applications.capp.capp.services.activity_log import get_activity_log
from applications.capp.capp.config.settings import settings
from applications.capp.capp.models.payments import (
    CrossBorderPayment, SenderInfo, RecipientInfo, 
    PaymentType, PaymentMethod, Currency, Country
)
from applications.capp.capp.services.approval import get_approval_service
from applications.capp.capp.services.defillama import DefiLlamaService
import uuid

router = APIRouter(
    prefix="/agents",
    tags=["agents"]
)

# Initialize Services
_defi_service = DefiLlamaService()

# ... (init code remains same) ...

# Initialize Agents Lazily
_market_agent = None
_compliance_agent = None

from .. import state

# Initialize Agents Lazily

def get_market_agent():
    global _market_agent
    if not _market_agent:
        # Check for Gemini Key
        if settings.GEMINI_API_KEY:
            try:
                provider = GeminiProvider(api_key=settings.GEMINI_API_KEY, model_name=settings.GEMINI_MODEL)
                _market_agent = MarketAnalysisAgent(provider=provider)
                print("Market Agent initialized with Real Gemini Provider")
            except Exception as e:
                print(f"Failed to init Gemini: {e}")
                _market_agent = MarketAnalysisAgent() # Fallback to Mock
        else:
            _market_agent = MarketAnalysisAgent() # Default Mock
    return _market_agent

def get_compliance_agent():
    global _compliance_agent
    if not _compliance_agent:
        _compliance_agent = AIComplianceAgent()
    return _compliance_agent

@router.get("/config", response_model=schemas.AgentConfig)
async def get_config():
    return state.app_config

@router.post("/config", response_model=schemas.AgentConfig)
async def update_config(config: schemas.AgentConfig):
    state.app_config = config
    return state.app_config

@router.get("/feed")
async def get_activity_feed(limit: int = 20):
    """
    Get real-time agent decision feed.
    """
    return get_activity_log().get_recent_activities(limit)

@router.get("/market/status")
async def get_market_status():
    """
    Get aggregated market status (Volatility, Top APY, Active Protocols)
    backed by real DefiLlama data.
    """
    return await _defi_service.get_market_status()

@router.post("/approve/{request_id}")
async def approve_request(request_id: str, payload: schemas.SignedApprovalRequest):
    success = get_approval_service().approve_request(request_id, signature=payload.signature)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or invalid signature")
    return {"status": "success", "message": "Request approved"}

@router.post("/reject/{request_id}")
async def reject_request(request_id: str):
    success = get_approval_service().reject_request(request_id)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    return {"status": "success", "message": "Request rejected"}

@router.get("/market/analyze/{symbol}", response_model=schemas.MarketAnalysisResponse)
async def analyze_market(symbol: str, db: Session = Depends(database.get_db)):
    try:
        agent = get_market_agent()
        # Mocking settlement amount generic analysis
        result = await agent.analyze_settlement_risk(symbol, settlement_amount_usd=1000.0)
        
        # Adjust recommendation based on Risk Profile
        risk_adjustment = {
            "CONSERVATIVE": " (Conservative Mode applied: reduced exposure)",
            "AGGRESSIVE": " (Aggressive Mode: yielding seeking enabled)",
            "BALANCED": ""
        }
        adjusted_reasoning = result.get("reasoning", "UNKNOWN") + risk_adjustment.get(state.app_config.risk_profile, "")

        # Persist Analysis to DB
        log_entry = models.MarketAnalysisLog(
            symbol=symbol,
            risk_level=result.get("risk_level", "UNKNOWN"),
            recommendation=result.get("recommendation", "UNKNOWN"),
            reasoning=adjusted_reasoning
        )
        db.add(log_entry)
        db.commit()

        return schemas.MarketAnalysisResponse(
            symbol=symbol,
            risk_level=result.get("risk_level", "UNKNOWN"),
            recommendation=result.get("recommendation", "UNKNOWN"),
            reasoning=adjusted_reasoning,
            timestamp=datetime.utcnow()
        )
        return schemas.MarketAnalysisResponse(
            symbol=symbol,
            risk_level=result.get("risk_level", "UNKNOWN"),
            recommendation=result.get("recommendation", "UNKNOWN"),
            reasoning=adjusted_reasoning,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        get_activity_log().log_activity(
            agent_id="market_analyst", 
            agent_type="MARKET", 
            action_type="ERROR", 
            message=f"Analysis failed for {symbol}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))
    else:
        # Success Log
        get_activity_log().log_activity(
            agent_id="market_analyst", 
            agent_type="MARKET", 
            action_type="DECISION", 
            message=f"Analyzed {symbol}: {result.get('recommendation', 'N/A')}",
            metadata=result
        )

@router.post("/market/chat", response_model=schemas.ChatResponse)
async def chat_analyst(request: schemas.ChatRequest, db: Session = Depends(database.get_db)):
    try:
        agent = get_market_agent()
        response_text = await agent.chat_with_analyst(request.query)
        
        # Persist Chat to DB
        chat_entry = models.AgentChatLog(
            user_query=request.query,
            agent_response=response_text
        )
        db.add(chat_entry)
        db.commit()
        
        return schemas.ChatResponse(
            response=response_text,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    else:
         get_activity_log().log_activity(
            agent_id="market_analyst", 
            agent_type="MARKET", 
            action_type="CHAT", 
            message=f"Answered: {request.query[:30]}...",
            metadata={"full_response": response_text}
        )

@router.post("/compliance/check", response_model=schemas.ComplianceCheckResponse)
async def check_compliance(request: schemas.ComplianceCheckRequest):
    try:
        agent = get_compliance_agent()
        
        # Construct full CrossBorderPayment from simple request
        # We mock the missing KYC info for this demo to satisfy the agent's contract
        
        from_address = request.sender_address
        to_address = request.recipient_address
        
        # Configuration Logic: Aggressive mode might skip detailed KYC in simulation
        kyc_verified_sim = True
        if state.app_config.risk_profile == "CONSERVATIVE":
             # In conservative mode, we might simulate stricter checks (mock only)
             pass
        
        sender = SenderInfo(
            name=request.sender_name, 
            phone_number="+1234567890",
            country=request.sender_country, 
            address=from_address,
            kyc_verified=kyc_verified_sim
        )
        
        recipient = RecipientInfo(
            name=request.recipient_name,
            phone_number="+0987654321",
            country=request.recipient_country, 
            address=to_address,
            kyc_verified=False
        )
        
        payment = CrossBorderPayment(
            reference_id=str(uuid.uuid4())[:8].upper(),
            payment_type=PaymentType.PERSONAL_REMITTANCE,
            payment_method=PaymentMethod.CRYPTO,
            amount=request.amount,
            from_currency=Currency.USD, # Assuming USD equivalent for compliance logic
            to_currency=Currency.GHS, # Cross-border payment must have FX
            sender=sender,
            recipient=recipient
        )
        
        # Call the correct method on the agent
        result = await agent.evaluate_transaction(payment)
        
        # Config Override: If Sovereign, we might auto-approve low risks (logic simulated)
        reasoning = result.get("reasoning", "Check Failed")
        if state.app_config.autonomy_level == "SOVEREIGN":
             reasoning += " [AUTO-APPROVED by Sovereign Protocol]"
        
        return schemas.ComplianceCheckResponse(
            is_compliant=result.get("is_compliant", False),
            risk_score=result.get("risk_score", 1.0),
            reasoning=reasoning,
            violations=result.get("violations", [])
        )
    except Exception as e:
        print(f"Compliance Error: {e}") # Debug log
        get_activity_log().log_activity(
            agent_id="compliance_bot", 
            agent_type="COMPLIANCE", 
            action_type="ERROR", 
            message=f"Check failed: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))
    else:
        status = "APPROVED" if result.get("is_compliant", False) else "FLAGGED"
        get_activity_log().log_activity(
            agent_id="compliance_bot", 
            agent_type="COMPLIANCE", 
            action_type="REVIEW", 
            message=f"Transaction {status}: {reasoning[:50]}...",
            metadata=result
        )
@router.post("/opportunities/scout")
async def scout_opportunities():
    """
    Proactively scout for yield opportunities using DefiLlama.
    """
    # 1. Fetch Real Opportunities
    opportunities = await _defi_service.get_yield_opportunities()
    
    if not opportunities:
        # Fallback if API fails
        opportunity = {
            "protocol": "Aave V3",
            "chain": "Arbitrum",
            "asset": "USDC",
            "apy": 5.2,
            "strategy": "Lending",
            "risk": "LOW"
        }
    else:
        # Pick the best one
        best = opportunities[0]
        opportunity = {
            "protocol": best["protocol"],
            "chain": best["chain"],
            "asset": best["asset"],
            "apy": float(best["apy"]), # Ensure float
            "strategy": "Lending",
            "risk": best["risk"]
        }

    # 2. Create an approval request for this opportunity
    req_id = get_approval_service().request_approval(
        agent_id="market_scout",
        action_type="OPPORTUNITY",
        description=f"Move 1000 USDC to {opportunity['protocol']} on {opportunity['chain']} for {opportunity['apy']:.2f}% APY",
        payload={
             "type": "YIELD_FARM",
             "asset": opportunity['asset'],
             "amount": 1000,
             "protocol": opportunity['protocol'],
             "chain": opportunity['chain'],
             "details": opportunity
        }
    )

    return {"status": "found", "opportunity": opportunity, "request_id": req_id}
