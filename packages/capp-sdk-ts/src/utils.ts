import {
    CAPPError, CAPPAuthError, CAPPPolicyError, CAPPLiquidityError,
    CAPPApprovalRequired, CAPPSettlementError, CAPPRateLimitError, CAPPNetworkError
} from './errors';

export async function handleApiError(response: Response): Promise<void> {
    if (response.ok) return;

    const status = response.status;
    let data: any = {};
    let text = '';
    try {
        text = await response.text();
        data = JSON.parse(text);
    } catch (e) {
        // ignore
    }

    const message = data.message || text || 'Unknown error';
    const errorCode = data.error_code || 'unknown';
    const remediation = data.remediation || 'Please check the docs or contact support.';
    const approvalId = data.approval_id;

    if (status === 401 || status === 403) {
        if (errorCode === 'policy_violation') throw new CAPPPolicyError(message, errorCode, remediation);
        throw new CAPPAuthError(message, errorCode, remediation);
    } else if (status === 402 || errorCode === 'approval_required') {
        throw new CAPPApprovalRequired(message, errorCode, remediation, approvalId || 'unknown');
    } else if (status === 429) {
        throw new CAPPRateLimitError(message, errorCode, remediation);
    } else if (status === 409 || errorCode === 'insufficient_liquidity') {
        throw new CAPPLiquidityError(message, errorCode, remediation);
    } else if (status >= 500) {
        if (errorCode === 'settlement_error') throw new CAPPSettlementError(message, errorCode, remediation);
        throw new CAPPNetworkError(message, errorCode, remediation);
    }

    throw new CAPPError(message, errorCode, remediation);
}
