class CAPPError(Exception):
    """Base class for all CAPP exceptions."""
    def __init__(self, message: str, error_code: str, remediation: str):
        super().__init__(message)
        self.error_code = error_code
        self.remediation = remediation

class CAPPAuthError(CAPPError):
    """Invalid / expired credential."""
    pass

class CAPPPolicyError(CAPPError):
    """Action violates spend policy."""
    pass

class CAPPLiquidityError(CAPPError):
    """Corridor has insufficient liquidity."""
    pass

class CAPPApprovalRequired(CAPPError):
    """Transaction exceeds approval threshold."""
    def __init__(self, message: str, error_code: str, remediation: str, approval_id: str):
        super().__init__(message, error_code, remediation)
        self.approval_id = approval_id

class CAPPSettlementError(CAPPError):
    """Blockchain settlement failed."""
    pass

class CAPPRateLimitError(CAPPError):
    """Rate limit exceeded."""
    pass

class CAPPNetworkError(CAPPError):
    """Connectivity or timeout issue."""
    pass
