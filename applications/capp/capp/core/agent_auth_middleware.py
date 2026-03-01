"""
Middleware for intercepting and authenticating Agent calls in CAPP
"""

import httpx
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi.responses import Response

from datetime import datetime, timezone

from applications.capp.capp.models.agent_credential import AgentCredentialInDB
from applications.capp.capp.api.v1.endpoints.agents import mock_db_agent_creds, verify_password

def _get_agent_cred_from_key(raw_api_key: str) -> AgentCredentialInDB:
    """Finds an agent credential by verifying the raw key against hashed keys in the DB."""
    # In a real setup, we'd lookup by an ID prefix first, then verify the hash.
    for cred in mock_db_agent_creds.values():
        if verify_password(raw_api_key, cred.hashed_api_key):
            return cred
    return None

class AgentAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts requests with Agent API Keys and validates policies.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        
        # Check if this is an Agent request
        api_key = request.headers.get("X-API-Key")
        if not api_key or not api_key.startswith("capp_agent_"):
            # Not an agent request, pass through to normal auth/routes
            return await call_next(request)
            
        # 1. Authenticate the Agent
        agent_cred = _get_agent_cred_from_key(api_key)
        
        if not agent_cred:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or unknown Agent API Key"}
            )
            
        if not agent_cred.is_active:
            return JSONResponse(
                status_code=403,
                content={"detail": "Agent credential has been revoked or deactivated"}
            )
            
        if agent_cred.is_expired():
            return JSONResponse(
                status_code=403,
                content={"detail": "Agent credential has expired"}
            )
            
        # 2. Inject context into request state for downstream handlers
        request.state.is_agent = True
        request.state.agent_cred = agent_cred
        request.state.principal_id = agent_cred.principal_id
        
        # 3. Policy checks (Pre-execution bounds)
        path = request.url.path
        
        # E.g. Restricted Tool usage filtering
        # Assuming the path dictates the tool, or some known mapping
        if agent_cred.allowed_tools:
            # Simple allowlist enforcement for paths (Phase 2 Demo)
            tool_name = path.strip("/").split("/")[-1] 
            # In a real system, you'd map FastAPI endpoints back to the specific conceptual tools
            pass
            
        # 4. Proceed with Execution
        response = await call_next(request)
        
        # 5. Post-Execution accounting (Tracking limit accumulation)
        # Assuming only 200/201 creation requests count toward spend limits
        if request.method == "POST" and "payments/create" in path and response.status_code in (200, 201):
            # In a real setup, we'd intercept the req body to inspect the 'amount' field
            # and accumulate it onto the db_cred.daily_spend_accumulator
            pass
            
        # Update last used timestamp
        agent_cred.last_used_at = datetime.now(timezone.utc)
        
        return response
