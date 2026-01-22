export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface PaymentRoute {
    chain: string;
    fee_usd: number;
    eta_seconds: number;
    recommendation_score: number;
    reason: string;
    estimated_gas_token: number;
}

export interface RoutingResponse {
    routes: PaymentRoute[];
    recommended_route: PaymentRoute;
}

export interface YieldStatsResponse {
    total_value_usd: number;
    hot_wallet_balance: number;
    yield_balance: number;
    apy: number;
    is_sweeping: boolean;
}

export const api = {
    // Routing Engine
    calculateRoute: async (amount: number, currency: string, recipient: string, preference: string = "CHEAPEST"): Promise<RoutingResponse> => {
        const res = await fetch(`${API_BASE}/routing/calculate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount,
                currency,
                recipient,
                preference
            })
        });
        if (!res.ok) {
            const err = await res.text();
            console.error("Route calc failed", err);
            throw new Error('Route calculation failed');
        }
        return res.json();
    },

    // Wallet Stats (Yield)
    getYieldStats: async (): Promise<YieldStatsResponse> => {
        const res = await fetch(`${API_BASE}/wallet/stats`);
        if (!res.ok) {
            console.warn('Failed to fetch stats, falling back to 0');
            return {
                total_value_usd: 0,
                hot_wallet_balance: 0,
                yield_balance: 0,
                apy: 0,
                is_sweeping: false
            };
        }
        return res.json();
    }
};

export interface AgentConfig {
    risk_profile: 'CONSERVATIVE' | 'BALANCED' | 'AGGRESSIVE';
    autonomy_level: 'HUMAN_LOOP' | 'AUTONOMOUS' | 'COPILOT' | 'GUARDED' | 'SOVEREIGN';
    min_yield_apy: number;
    notifications_enabled: boolean;
}

export const agentApi = {
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
    }
};
