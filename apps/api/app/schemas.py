from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

# Agent Schemas
class MarketAnalysisRequest(BaseModel):
    symbol: str = "APT"

class MarketAnalysisResponse(BaseModel):
    symbol: str
    risk_level: str
    recommendation: str
    reasoning: str
    timestamp: datetime

class ComplianceCheckRequest(BaseModel):
    sender_address: str
    recipient_address: str
    amount: float

class ComplianceCheckResponse(BaseModel):
    is_compliant: bool
    risk_score: float
    reasoning: str

# Wallet Schemas
class TransactionRequest(BaseModel):
    from_address: str # In real auth, derived from token
    to_address: str
    amount: float
    asset: str = "APT"

class TransactionResponse(BaseModel):
    tx_hash: str
    status: str
    timestamp: datetime

# Liquidity Schemas
class TreasuryStatus(BaseModel):
    total_value_usd: float
    asset_allocation: dict
    active_alerts: List[str]

# Configuration Schemas
class AgentConfig(BaseModel):
    risk_profile: str = "BALANCED" # CONSERVATIVE, BALANCED, AGGRESSIVE
    autonomy_level: str = "HUMAN_LOOP" # HUMAN_LOOP, AUTONOMOUS
    hedge_threshold: int = 5
    network: str = "TESTNET"

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
    timestamp: datetime
