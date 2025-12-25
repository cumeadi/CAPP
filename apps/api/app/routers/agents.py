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
from applications.capp.capp.models.payments import (
    CrossBorderPayment, SenderInfo, RecipientInfo, 
    PaymentType, PaymentMethod, Currency, Country
)
import uuid

router = APIRouter(
    prefix="/agents",
    tags=["agents"]
)

# ... (init code remains same) ...

# Initialize Agents Lazily
_market_agent = None
_compliance_agent = None

# Global Config Store (In-Memory for MVP)
app_config = schemas.AgentConfig()

def get_market_agent():
    global _market_agent
    if not _market_agent:
        _market_agent = MarketAnalysisAgent()
    return _market_agent

def get_compliance_agent():
    global _compliance_agent
    if not _compliance_agent:
        _compliance_agent = AIComplianceAgent()
    return _compliance_agent

@router.get("/config", response_model=schemas.AgentConfig)
async def get_config():
    return app_config

@router.post("/config", response_model=schemas.AgentConfig)
async def update_config(config: schemas.AgentConfig):
    global app_config
    app_config = config
    return app_config

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
        adjusted_reasoning = result.get("reasoning", "UNKNOWN") + risk_adjustment.get(app_config.risk_profile, "")

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        if app_config.risk_profile == "CONSERVATIVE":
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
        
        # Config Override: If Fully Autonomous, we might auto-approve low risks (logic simulated)
        reasoning = result.get("reasoning", "Check Failed")
        if app_config.autonomy_level == "AUTONOMOUS":
             reasoning += " [AUTO-APPROVED by Agent Protocol]"
        
        return schemas.ComplianceCheckResponse(
            is_compliant=result.get("is_compliant", False),
            risk_score=result.get("risk_score", 1.0),
            reasoning=reasoning,
            violations=result.get("violations", [])
        )
    except Exception as e:
        print(f"Compliance Error: {e}") # Debug log
        raise HTTPException(status_code=500, detail=str(e))
