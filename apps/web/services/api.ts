const API_BASE = 'http://localhost:8000';

export interface MarketAnalysisResponse {
    symbol: string;
    risk_level: string;
    recommendation: string;
    reasoning: string;
    timestamp: string;
}

export interface MarketStatusResponse {
    volatility: string;
    reasoning: string;
    top_apy: number;
    active_protocols: string[];
}

export interface ComplianceCheckResponse {
    is_compliant: boolean;
    risk_score: number;
    reasoning: string;
}

export interface AgentConfig {
    risk_profile: 'CONSERVATIVE' | 'BALANCED' | 'AGGRESSIVE';
    autonomy_level: 'HUMAN_LOOP' | 'AUTONOMOUS' | 'COPILOT' | 'GUARDED' | 'SOVEREIGN';
    hedge_threshold: number;
    network: string;
}

export interface BridgeResponse {
    tx_hash: string;
    status: string;
    estimated_arrival: string;
    bridge_fee_usd: number;
}

export interface ActivityItem {
    id: string;
    timestamp: string;
    agent_id: string;
    agent_type: string;
    action_type: string;
    message: string;
    metadata: any;
}

export const api = {
    getAgentFeed: async (limit: number = 20): Promise<ActivityItem[]> => {
        const res = await fetch(`${API_BASE}/agents/feed?limit=${limit}`);
        if (!res.ok) throw new Error('Failed to fetch agent feed');
        return res.json();
    },

    // Wallet Operations
    getWalletBalance: async (address: string) => {
        const res = await fetch(`${API_BASE}/wallet/balance/${address}`);
        if (!res.ok) throw new Error('Failed to fetch balance');
        return res.json();
    },

    executeTransfer: async (to: string, amount: number, targetChain?: string): Promise<{ tx_hash: string }> => {
        const res = await fetch(`${API_BASE}/wallet/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                to_address: to,
                amount: amount,
                target_chain: targetChain
            })
        });
        if (!res.ok) throw new Error('Transfer failed');
        return res.json();
    },

    // Agent Operations
    getMarketStatus: async (): Promise<MarketStatusResponse> => {
        const res = await fetch(`${API_BASE}/agents/market/status`);
        if (!res.ok) throw new Error('Failed to fetch market status');
        return res.json();
    },

    analyzeMarket: async (symbol: string = 'APT'): Promise<MarketAnalysisResponse> => {
        const res = await fetch(`${API_BASE}/agents/market/analyze/${symbol}`);
        if (!res.ok) throw new Error('Failed to fetch market analysis');
        return res.json();
    },

    checkCompliance: async (sender: string, recipient: string, amount: number): Promise<ComplianceCheckResponse> => {
        const res = await fetch(`${API_BASE}/agents/compliance/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sender_address: sender,
                recipient_address: recipient,
                amount: amount
            })
        });
        if (!res.ok) throw new Error('Compliance check failed');
        return res.json();
    },

    // Configuration
    getAgentConfig: async (): Promise<AgentConfig> => {
        const res = await fetch(`${API_BASE}/agents/config`);
        if (!res.ok) throw new Error('Failed to fetch config');
        return res.json();
    },

    updateAgentConfig: async (config: AgentConfig): Promise<AgentConfig> => {
        const res = await fetch(`${API_BASE}/agents/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        if (!res.ok) throw new Error('Failed to update config');
        return res.json();
    },

    approveRequest: async (requestId: string, signature: string): Promise<void> => {
        const res = await fetch(`${API_BASE}/agents/approve/${requestId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ signature })
        });
        if (!res.ok) throw new Error('Failed to approve request');
    },

    rejectRequest: async (requestId: string): Promise<void> => {
        const res = await fetch(`${API_BASE}/agents/reject/${requestId}`, {
            method: 'POST'
        });
        if (!res.ok) throw new Error('Failed to reject request');
    },

    // Multi-Chain Data
    getPolygonGas: async (): Promise<{ gas_price_gwei: number }> => {
        const res = await fetch(`${API_BASE}/chain/polygon/gas`);
        if (!res.ok) throw new Error('Failed to fetch gas');
        return res.json();
    },

    bridgeAssets: async (from: string, to: string, amount: number, recipient: string): Promise<BridgeResponse> => {
        const res = await fetch(`${API_BASE}/chain/bridge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                from_chain: from,
                to_chain: to,
                token: "USDC",
                amount: amount,
                recipient: recipient
            })
        });
        if (!res.ok) throw new Error('Bridge failed');
        return res.json();
    },

    chatWithAnalyst: async (query: string): Promise<ChatResponse> => {
        const res = await fetch(`${API_BASE}/agents/market/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        if (!res.ok) throw new Error('Failed to chat with analyst');
        return res.json();
    },

    scoutOpportunities: async () => {
        const res = await fetch(`${API_BASE}/agents/opportunities/scout`, {
            method: 'POST'
        });
        if (!res.ok) throw new Error('Failed to scout opportunities');
        return res.json();
    },

    // Bridge / Plasma
    bridgeDeposit: async (amount: number, userAddress: string, token: string = "USDC") => {
        const res = await fetch(`${API_BASE}/bridge/deposit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, user_address: userAddress, token })
        });
        if (!res.ok) throw new Error('Deposit failed');
        return res.json();
    },

    bridgeWithdraw: async (amount: number, userAddress: string, token: string = "USDC") => {
        const res = await fetch(`${API_BASE}/bridge/withdraw`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, user_address: userAddress, token })
        });
        if (!res.ok) throw new Error('Withdraw failed');
        return res.json();
    },

    finalizeExit: async (exitId: string) => {
        const res = await fetch(`${API_BASE}/bridge/finalize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exit_id: exitId })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Finalize failed');
        }
        return res.json();
    },

    getSystemStatus: async () => {
        const res = await fetch(`${API_BASE}/system/health`);
        if (!res.ok) throw new Error('Failed to fetch system status');
        return res.json();
    }
};



export interface ChatResponse {
    response: string;
    timestamp: string;
}
