from fastapi import APIRouter, HTTPException
from ..schemas import ComplianceCheckRequest, ComplianceCheckResponse

router = APIRouter(
    prefix="/compliance",
    tags=["compliance"]
)

@router.post("/check", response_model=ComplianceCheckResponse)
def check_transaction_compliance(request: ComplianceCheckRequest):
    violations = []
    risk_score = 0.0
    
    # 1. Sanctions Check (Mock: Block '0xdead...')
    if request.recipient_address and request.recipient_address.lower().startswith("0xdead"):
        violations.append("RECIPIENT_WALLET_SANCTIONED")
        risk_score = 100.0
        return ComplianceCheckResponse(
            is_compliant=False,
            risk_score=risk_score,
            reasoning="Recipient address is on the OFAC Sanctions List.",
            violations=violations
        )

    # 2. Country Risk (Mock: High risk for 'KP' - North Korea)
    if request.recipient_country == "KP":
        violations.append("HIGH_RISK_JURISDICTION")
        risk_score = 100.0
        return ComplianceCheckResponse(
            is_compliant=False,
            risk_score=risk_score,
            reasoning="Transactions to this jurisdiction are prohibited.",
            violations=violations
        )

    # 3. Velocity/Value Checks
    if request.amount > 10000:
        risk_score += 40.0
        violations.append("LARGE_TRANSACTION_REVIEW")
    
    if risk_score > 50:
         return ComplianceCheckResponse(
            is_compliant=False,
            risk_score=risk_score,
            reasoning="Transaction flagged for manual review due to high value/risk.",
            violations=violations
        )

    return ComplianceCheckResponse(
        is_compliant=True,
        risk_score=risk_score,
        reasoning="Transaction passed all automated compliance checks.",
        violations=[]
    )
