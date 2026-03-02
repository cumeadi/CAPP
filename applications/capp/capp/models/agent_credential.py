"""
Agent credentials and authorization models for CAPP
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from applications.capp.capp.models.user import UserRole
from applications.capp.capp.models.payments import Chain


class AgentCredentialBase(BaseModel):
    """Base model for agent credentials"""
    agent_id: str = Field(description="Unique identifier for the agent instance")
    organization_id: UUID = Field(description="Organization UUID this agent belongs to")
    principal_id: Optional[UUID] = Field(None, description="Human user UUID this agent acts on behalf of (if personal)")
    parent_agent_id: Optional[str] = Field(None, description="If this is a sub-agent, the ID of the delegating agent")
    
    # Spending policies
    max_per_tx_usd: Optional[float] = Field(None, description="Maximum allowed amount per transaction in USD")
    daily_limit_usd: Optional[float] = Field(None, description="Maximum allowed cumulative spend per day in USD")
    require_approval_above_usd: Optional[float] = Field(None, description="Transactions above this amount require out-of-band principal approval")
    
    # Access policies 
    corridor_allowlist: Optional[List[str]] = Field(default_factory=list, description="List of allowed corridors e.g., 'US-KE'")
    chain_allowlist: Optional[List[Chain]] = Field(default_factory=list, description="List of allowed blockchains to interact with")
    allowed_tools: Optional[List[str]] = Field(default_factory=list, description="Specific MCP tools this agent can invoke")


class AgentCredentialCreate(AgentCredentialBase):
    """Request model for creating a new agent credential"""
    expiry_days: int = Field(default=30, ge=1, le=365, description="Number of days until the credential expires")


class AgentCredentialUpdate(BaseModel):
    """Request model for updating an existing agent credential"""
    max_per_tx_usd: Optional[float] = None
    daily_limit_usd: Optional[float] = None
    require_approval_above_usd: Optional[float] = None
    corridor_allowlist: Optional[List[str]] = None
    chain_allowlist: Optional[List[Chain]] = None
    allowed_tools: Optional[List[str]] = None
    is_active: Optional[bool] = None


class AgentCredentialInDB(AgentCredentialBase):
    """Database model for agent credentials"""
    id: UUID = Field(default_factory=uuid4)
    hashed_api_key: str = Field(description="Bcrypt hash of the agent's API key")
    
    # Status and lifecyle
    is_active: bool = True
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    last_used_at: Optional[datetime] = None
    
    # Audit tracking 
    daily_spend_accumulator: float = Field(default=0.0)
    last_spend_reset: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('expires_at', pre=True, always=True)
    def set_expires_at(cls, v):
        if v is None:
            return datetime.now(timezone.utc) + timedelta(days=30)
        return v
    
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    class Config:
        from_attributes = True


class AgentCredentialResponse(AgentCredentialBase):
    """Response model for agent credentials (never includes the raw key except on issue)"""
    id: UUID
    is_active: bool
    issued_at: datetime
    expires_at: datetime
    last_used_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AgentCredentialIssueResponse(AgentCredentialResponse):
    """Response model returned ONLY ONCE when a credential is created"""
    raw_api_key: str = Field(description="The cleartext API key. STORE THIS SECURELY, it will not be shown again.")
