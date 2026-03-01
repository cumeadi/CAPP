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


@router.get("/credentials/principal/{principal_id}", response_model=List[AgentCredentialResponse])
async def list_agent_credentials(principal_id: uuid.UUID):
    """
    List all agent credentials issued by a specific human principal.
    """
    creds = [c for c in mock_db_agent_creds.values() if c.principal_id == principal_id]
    return [AgentCredentialResponse(**c.dict()) for c in creds]


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
