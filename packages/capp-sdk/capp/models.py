from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class PaymentResult(BaseModel):
    tx_id: str
    status: str
    settled_at: Optional[datetime] = None
    fee_usd: float

class RouteAnalysisResult(BaseModel):
    chain: str
    fee_usd: float
    eta_seconds: int
    confidence_score: float

class FXRate(BaseModel):
    mid: float
    bid: float
    ask: float
    updated_at: datetime

class Balances(BaseModel):
    aptos: Optional[float] = None
    polygon: Optional[float] = None
    starknet: Optional[float] = None
    by_currency: Dict[str, float] = Field(default_factory=dict)

class CorridorStatus(BaseModel):
    liquidity_usd: float
    health: str
    avg_fee_pct: float

class CorridorEvent(BaseModel):
    type: str
    corridor: str
    data: Dict[str, Any]

class AgentCredential(BaseModel):
    agent_id: str
    token: str
    policy: Dict[str, Any]

class ApprovalRequest(BaseModel):
    approval_id: str
    status: str
    amount_usd: float
    corridor: str
    created_at: datetime
