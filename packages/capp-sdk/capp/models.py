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

class CorridorMetricRecord(BaseModel):
    timestamp: datetime
    liquidity_depth: float
    avg_fee_pct: float
    success_rate: float
    tx_volume_usd: float

class CorridorFeedResponse(BaseModel):
    corridor: str
    current_health: str
    macro_context: Optional[str] = None
    metrics: List[CorridorMetricRecord]

class CorridorEvent(BaseModel):
    type: str
    corridor: str
    data: Dict[str, Any]

class AgentCredential(BaseModel):
    agent_id: str
    organization_id: Optional[str] = None
    token: Optional[str] = None
    raw_api_key: Optional[str] = None
    parent_agent_id: Optional[str] = None
    policy: Optional[Dict[str, Any]] = None

class ApprovalRequest(BaseModel):
    approval_id: str
    status: str
    amount_usd: float
    corridor: str
    created_at: datetime
