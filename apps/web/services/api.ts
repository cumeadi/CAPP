const API_BASE = 'http://localhost:8000';

export interface MarketAnalysisResponse {
    symbol: string;
    risk_level: string;
    recommendation: string;
    reasoning: string;
    timestamp: string;
}

export interface ComplianceCheckResponse {
    is_compliant: boolean;
    risk_score: number;
    reasoning: string;
}

export interface AgentConfig {
    risk_profile: 'CONSERVATIVE' | 'BALANCED' | 'AGGRESSIVE';
    autonomy_level: 'HUMAN_LOOP' | 'AUTONOMOUS';
    hedge_threshold: number;
    network: string;
}

export interface BridgeResponse {
    tx_hash: string;
    status: string;
    estimated_arrival: string;
    bridge_fee_usd: number;
}

export const api = {
    // Wallet Operations
    getWalletBalance: async (address: string) => {
        const res = await fetch(`${API_BASE}/wallet/balance/${address}`);
        if (!res.ok) throw new Error('Failed to fetch balance');
        return res.json();
    },

    // Agent Operations
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

    executeTransfer: async (to: string, amount: number): Promise<{ tx_hash: string }> => {
        const res = await fetch(`${API_BASE}/wallet/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                to_address: to,
                amount: amount
            })
        });
        if (!res.ok) throw new Error('Transfer failed');
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
    }
};

export interface ChatResponse {
    response: string;
    timestamp: string;
}
