from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class SpenderPolicyUpdate(BaseModel):
    agent_id: str
    max_per_tx_usd: Optional[float] = None
    daily_limit_usd: Optional[float] = None
    corridor_allowlist: Optional[List[str]] = None
    require_approval_above_usd: Optional[float] = None
    allowed_tools: Optional[List[str]] = None

@router.post("/set")
async def set_payment_policy(policy: SpenderPolicyUpdate):
    """
    Update or set payment policy for a specific agent.
    This manages agent credentials and spending constraints for Phase 1.
    """
    # Exposing the endpoint logic to configure an agent's policy.
    # In a full implementation, this stores the policy in the database.
    return {
        "status": "success",
        "message": f"Policy updated successfully for agent {policy.agent_id}",
        "policy_applied": policy.dict(exclude_none=True)
    }
