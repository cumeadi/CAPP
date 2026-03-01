export class CAPPError extends Error {
    public errorCode: string;
    public remediation: string;

    constructor(message: string, errorCode: string, remediation: string) {
        super(message);
        this.name = this.constructor.name;
        this.errorCode = errorCode;
        this.remediation = remediation;
    }
}

export class CAPPAuthError extends CAPPError { }
export class CAPPPolicyError extends CAPPError { }
export class CAPPLiquidityError extends CAPPError { }

export class CAPPApprovalRequired extends CAPPError {
    public approvalId: string;

    constructor(message: string, errorCode: string, remediation: string, approvalId: string) {
        super(message, errorCode, remediation);
        this.approvalId = approvalId;
    }
}

export class CAPPSettlementError extends CAPPError { }
export class CAPPRateLimitError extends CAPPError { }
export class CAPPNetworkError extends CAPPError { }
