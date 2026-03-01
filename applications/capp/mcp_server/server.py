import httpx
import json
import uuid
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("CAPP Agentic Protocol")

import os

API_BASE_URL = os.environ.get("CAPP_API_URL", "http://localhost:8000/api/v1")
API_KEY = os.environ.get("CAPP_API_KEY", "REDACTED_DEV_KEY")

def _make_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
    """Helper to make HTTP requests to the CAPP FastAPI backend"""
    url = f"{API_BASE_URL}{endpoint}"
    # Basic Phase 1 integration - inject dummy auth if needed
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    
    with httpx.Client() as client:
        try:
            if method == "GET":
                response = client.get(url, headers=headers, params=params, timeout=10.0)
            elif method == "POST":
                response = client.post(url, headers=headers, json=data, timeout=10.0)
                
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": str(e), "message": getattr(e.response, "text", "")}
        except Exception as e:
            return {"error": str(e)}

@mcp.resource("capp://corridors")
def get_supported_corridors() -> str:
    """Read the list of supported payment corridors"""
    data = _make_request("GET", "/payments/corridors/supported")
    return json.dumps(data, indent=2)

@mcp.resource("capp://limits")
def get_payment_limits() -> str:
    """Read current payment limits and restrictions"""
    data = _make_request("GET", "/payments/limits")
    return json.dumps(data, indent=2)

@mcp.tool()
def analyze_routes(amount: float, recipient: str, preference: str = "CHEAP") -> str:
    """
    Get optimal corridor options for a payment.
    preference: "CHEAP" or "FAST"
    """
    payload = {
        "amount": amount,
        "currency": "USDC",
        "recipient": recipient,
        "preference": preference
    }
    data = _make_request("POST", "/routing/calculate", data=payload)
    return json.dumps(data, indent=2)

@mcp.tool()
def get_balance(address: str) -> str:
    """Check wallet balance across chains by address"""
    data = _make_request("GET", f"/wallet/balance/{address}")
    return json.dumps(data, indent=2)

@mcp.tool()
def check_liquidity() -> str:
    """Check corridor liquidity before executing payments"""
    data = _make_request("GET", "/corridors/status")
    return json.dumps(data, indent=2)

@mcp.tool()
def get_fx_rate(from_currency: str, to_currency: str) -> str:
    """Get real-time FX for a currency pair. Example: USD to KES"""
    data = _make_request("GET", f"/payments/rates/{from_currency}/{to_currency}")
    return json.dumps(data, indent=2)

@mcp.tool()
def monitor_transaction(payment_id: str) -> str:
    """Track payment status by its payment_id"""
    data = _make_request("GET", f"/payments/{payment_id}/status")
    return json.dumps(data, indent=2)

@mcp.tool()
def set_payment_policy(agent_id: str, max_per_tx_usd: float = None, daily_limit_usd: float = None) -> str:
    """Configure agent spend rules and limits"""
    payload = {
        "agent_id": agent_id,
        "max_per_tx_usd": max_per_tx_usd,
        "daily_limit_usd": daily_limit_usd,
        "corridor_allowlist": ["NG-KE", "GH-NG", "ZA-US"]
    }
    data = _make_request("POST", "/policy/set", data=payload)
    return json.dumps(data, indent=2)

@mcp.tool()
def send_payment(
    amount: float,
    recipient_name: str,
    recipient_country: str,
    from_currency: str = "USD",
    to_currency: str = "KES",
    sender_name: str = "AI Agent",
    sender_country: str = "US"
) -> str:
    """Execute a cross-border payment directly."""
    # reference id must be unique
    ref_id = f"auto-{str(uuid.uuid4())[:8]}"
    payload = {
        "reference_id": ref_id,
        "payment_type": "PERSONAL_REMITTANCE",
        "payment_method": "CRYPTO",
        "amount": amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "sender_name": sender_name,
        "sender_phone": "+10000000000",
        "sender_country": sender_country,
        "recipient_name": recipient_name,
        "recipient_phone": "+20000000000",
        "recipient_country": recipient_country,
        "priority_cost": True,
        "priority_speed": False
    }
    data = _make_request("POST", "/payments/create", data=payload)
    return json.dumps(data, indent=2)

if __name__ == "__main__":
    # Print a status to stderr so it doesn't interrupt MCP stdio
    import sys
    print("Starting CAPP MCP Server on stdio...", file=sys.stderr)
    mcp.run(transport='stdio')
