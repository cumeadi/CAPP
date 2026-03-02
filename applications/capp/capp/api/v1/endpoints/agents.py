from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext

from applications.capp.capp.models.agent_credential import (
    AgentCredentialCreate,
    AgentCredentialUpdate,
    AgentCredentialResponse,
    AgentCredentialIssueResponse,
    AgentCredentialInDB
)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory store for Phase 2 demonstration purposes
# In a real deployment, this interfaces with SQLAlchemy
mock_db_agent_creds = {}

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/credentials", response_model=AgentCredentialIssueResponse, status_code=status.HTTP_201_CREATED)
async def issue_agent_credential(cred_in: AgentCredentialCreate):
    """
    Issue a new API credential for an autonomous agent.
    This links an agent to a human principal and establishes its spending limits.
    """
    # Generate a secure random API key
    raw_api_key = f"capp_agent_{secrets.token_urlsafe(32)}"
    hashed_key = get_password_hash(raw_api_key)
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=cred_in.expiry_days)
    
    db_cred = AgentCredentialInDB(
        **cred_in.dict(exclude={"expiry_days"}),
        hashed_api_key=hashed_key,
        expires_at=expires_at
    )
    
    # Store in mock DB
    mock_db_agent_creds[db_cred.id] = db_cred
    
    # Return response including the raw key (only time it is shown)
    response_data = db_cred.dict()
    response_data["raw_api_key"] = raw_api_key
    
    return AgentCredentialIssueResponse(**response_data)


@router.get("/credentials/organization/{organization_id}", response_model=List[AgentCredentialResponse])
async def list_agent_credentials(organization_id: uuid.UUID):
    """
    List all agent credentials belonging to a specific organization.
    """
    creds = [c for c in mock_db_agent_creds.values() if c.organization_id == organization_id]
    return [AgentCredentialResponse(**c.dict()) for c in creds]

@router.post("/credentials/{parent_agent_id}/delegate", response_model=AgentCredentialIssueResponse, status_code=status.HTTP_201_CREATED)
async def delegate_credential(parent_agent_id: str, cred_in: AgentCredentialCreate):
    """
    Delegate a sub-credential from an existing agent credential.
    Enforces depth limits (max depth 2) and permission narrowing.
    """
    # 1. Find parent
    parent_creds = [c for c in mock_db_agent_creds.values() if c.agent_id == parent_agent_id]
    if not parent_creds:
        raise HTTPException(status_code=404, detail="Parent agent credential not found")
    parent_cred = parent_creds[0]

    # 2. Check depth constraint
    if parent_cred.parent_agent_id is not None:
        raise HTTPException(status_code=400, detail="Delegation depth exceeded. Sub-agents cannot delegate further.")

    # 3. Enforce permission narrowing
    if parent_cred.max_per_tx_usd is not None:
        if cred_in.max_per_tx_usd is None or cred_in.max_per_tx_usd > parent_cred.max_per_tx_usd:
             raise HTTPException(status_code=400, detail="Sub-agent max_per_tx_usd cannot exceed parent's limit.")
             
    if parent_cred.daily_limit_usd is not None:
         if cred_in.daily_limit_usd is None or cred_in.daily_limit_usd > parent_cred.daily_limit_usd:
              raise HTTPException(status_code=400, detail="Sub-agent daily_limit_usd cannot exceed parent's limit.")
              
    if parent_cred.corridor_allowlist:
         if not cred_in.corridor_allowlist or not set(cred_in.corridor_allowlist).issubset(set(parent_cred.corridor_allowlist)):
              raise HTTPException(status_code=400, detail="Sub-agent corridors must be a subset of parent's allowed corridors.")

    # 4. Issue credential
    raw_api_key = f"capp_subagent_{secrets.token_urlsafe(32)}"
    hashed_key = get_password_hash(raw_api_key)
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=cred_in.expiry_days)
    
    # Ensure parent_agent_id is set
    cred_data = cred_in.dict(exclude={"expiry_days"})
    cred_data["parent_agent_id"] = parent_agent_id
    cred_data["organization_id"] = parent_cred.organization_id # Inherit organization
    cred_data["principal_id"] = parent_cred.principal_id # Inherit principal (if exists)
    
    db_cred = AgentCredentialInDB(
        **cred_data,
        hashed_api_key=hashed_key,
        expires_at=expires_at
    )
    
    mock_db_agent_creds[db_cred.id] = db_cred
    
    response_data = db_cred.dict()
    response_data["raw_api_key"] = raw_api_key
    
    return AgentCredentialIssueResponse(**response_data)


@router.patch("/credentials/{credential_id}", response_model=AgentCredentialResponse)
async def update_agent_credential(credential_id: uuid.UUID, update_data: AgentCredentialUpdate):
    """
    Update the policies or status of an existing agent credential.
    Can be used to quickly adjust limits or revoke an agent's access by setting is_active=False.
    """
    if credential_id not in mock_db_agent_creds:
        raise HTTPException(status_code=404, detail="Agent credential not found")
        
    db_cred = mock_db_agent_creds[credential_id]
    
    update_dict = update_data.dict(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(db_cred, k, v)
        
    return AgentCredentialResponse(**db_cred.dict())


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_agent_credential(credential_id: uuid.UUID):
    """
    Permanently delete/revoke an agent credential.
    """
    if credential_id not in mock_db_agent_creds:
        raise HTTPException(status_code=404, detail="Agent credential not found")
        
    del mock_db_agent_creds[credential_id]
    return None
