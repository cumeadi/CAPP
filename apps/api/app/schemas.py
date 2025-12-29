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

# Extended Schemas for Phase 3D

class ComplianceCheckRequest(BaseModel):
    # Sender Details
    sender_name: str
    sender_country: str
    sender_address: Optional[str] = None
    
    # Recipient Details
    recipient_name: str
    recipient_country: str
    recipient_address: Optional[str] = None
    
    # Transaction Details
    amount: float
    currency: str = "USD"
    payment_method: str = "BANK_TRANSFER"

class ComplianceCheckResponse(BaseModel):
    is_compliant: bool
    risk_score: float
    reasoning: str
    violations: List[str] = []

# Wallet Schemas
class TransactionRequest(BaseModel):
    # Routing Details
    from_currency: str = "USD"
    to_currency: str = "KES"
    amount: float
    
    # Parties
    recipient_name: str = "Recipient"
    recipient_country: str = "KE"
    recipient_address: str # Wallet address or Account Number
    
    # Sender (Simulated for this demo)
    sender_id: str = "demo_user"
    
    # Optional Routing
    target_chain: Optional[str] = None

class TransactionResponse(BaseModel):
    tx_hash: str
    status: str
    timestamp: datetime

# Starknet Schemas
class StarknetAddressRequest(BaseModel):
    public_key: str # Hex string

class StarknetAddressResponse(BaseModel):
    address: str
    public_key: str

class StarknetDeployRequest(BaseModel):
    public_key: str
    private_key: str # For demo purposes, we accept private key to sign the deploy tx
    amount: Optional[float] = None # Optional initial funding?

class StarknetTransferRequest(BaseModel):
    recipient: str
    amount: float # In standard units (will be converted to Wei/Fri)
    token: Optional[str] = None # Optional token address

# Routing Schemas
class PaymentRoute(BaseModel):
    chain: str # APTOS, POLYGON, STARKNET
    fee_usd: float
    eta_seconds: int
    recommendation_score: float
    reason: str
    estimated_gas_token: float # Amount in native token (APT/MATIC/ETH)

class RoutingRequest(BaseModel):
    amount: float
    recipient: str # Ensure this can cover all chains or we use a "User ID"
    currency: str = "USD"
    preference: str = "CHEAPEST" # CHEAPEST, FASTEST, BALANCED

class RoutingResponse(BaseModel):
    routes: List[PaymentRoute]
    recommended_route: PaymentRoute


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
