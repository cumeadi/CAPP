import httpx
from .errors import (
    CAPPError, CAPPAuthError, CAPPPolicyError, CAPPLiquidityError,
    CAPPApprovalRequired, CAPPSettlementError, CAPPRateLimitError, CAPPNetworkError
)

def handle_api_error(response: httpx.Response):
    if response.is_success:
        return
        
    status = response.status_code
    try:
        data = response.json()
        message = data.get("message", "Unknown error")
        error_code = data.get("error_code", "unknown")
        remediation = data.get("remediation", "Please check the docs or contact support.")
        approval_id = data.get("approval_id")
    except Exception:
        message = response.text
        error_code = "network_error" if status >= 500 else "client_error"
        remediation = "Check the request status."
        approval_id = None

    if status == 401 or status == 403:
        if error_code == "policy_violation":
            raise CAPPPolicyError(message, error_code, remediation)
        raise CAPPAuthError(message, error_code, remediation)
    elif status == 402 or error_code == "approval_required":
        raise CAPPApprovalRequired(message, error_code, remediation, approval_id or "unknown")
    elif status == 429:
        raise CAPPRateLimitError(message, error_code, remediation)
    elif status == 409 or error_code == "insufficient_liquidity":
        raise CAPPLiquidityError(message, error_code, remediation)
    elif status >= 500:
        if error_code == "settlement_error":
            raise CAPPSettlementError(message, error_code, remediation)
        raise CAPPNetworkError(message, error_code, remediation)
        
    raise CAPPError(message, error_code, remediation)
