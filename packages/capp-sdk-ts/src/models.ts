export interface PaymentResult {
    txId: string;
    status: string;
    settledAt?: Date;
    feeUsd: number;
}

export interface RouteAnalysisResult {
    chain: string;
    feeUsd: number;
    etaSeconds: number;
    confidenceScore: number;
}

export interface FXRate {
    mid: number;
    bid: number;
    ask: number;
    updatedAt: Date;
}

export interface Balances {
    aptos?: number;
    polygon?: number;
    starknet?: number;
    byCurrency?: Record<string, number>;
}

export interface CorridorStatus {
    liquidityUsd: number;
    health: string;
    avgFeePct: number;
}

export interface CorridorMetricRecord {
    timestamp: Date;
    liquidityDepth: number;
    avgFeePct: number;
    successRate: number;
    txVolumeUsd: number;
}

export interface CorridorFeedResponse {
    corridor: string;
    currentHealth: string;
    macroContext?: string;
    metrics: CorridorMetricRecord[];
}

export interface CorridorEvent {
    type: string;
    corridor: string;
    data: Record<string, any>;
}

export interface AgentCredential {
    agentId: string;
    organizationId?: string;
    token?: string;
    rawApiKey?: string;
    parentAgentId?: string;
    policy?: Record<string, any>;
}

export interface ApprovalRequest {
    approvalId: string;
    status: string;
    amountUsd: number;
    corridor: string;
    createdAt: Date;
}
