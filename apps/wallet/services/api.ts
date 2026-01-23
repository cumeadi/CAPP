export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

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
    aptos_balance?: number;
    apy: number;
    is_sweeping: boolean;
}

export interface CreatePaymentRequest {
    amount: number;
    currency: string;
    description?: string;
    recipient_id?: string;
    wallet_address?: string;
    metadata?: Record<string, any>;
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
        const res = await fetch(`${API_BASE}/api/v1/wallet/stats`);
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
    },

    // Payment History
    getHistory: async (): Promise<PaymentHistoryItem[]> => {
        const token = localStorage.getItem('token'); // Simplistic auth for now
        const res = await fetch(`${API_BASE}/api/v1/payments/history`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (!res.ok) {
            console.warn('Failed to fetch history');
            return [];
        }
        return res.json();
    },

    // Create Payment
    createPayment: async (data: CreatePaymentRequest): Promise<PaymentHistoryItem> => {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_BASE}/api/v1/payments/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { 'Authorization': `Bearer ${token}` } : {})
            },
            body: JSON.stringify(data)
        });

        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Payment creation failed');
        }
        return res.json();
    },

    // Compliance Reports
    downloadComplianceReport: async (year: number, format: 'PDF' | 'CSV'): Promise<void> => {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_BASE}/api/v1/compliance/reports/download?year=${year}&report_type=${format}`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });

        if (!res.ok) {
            throw new Error('Failed to generate report');
        }

        // Handle File Download
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `capp_compliance_${year}.${format.toLowerCase()}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
};

export interface PaymentHistoryItem {
    payment_id: string;
    reference_id: string;
    amount: number;
    from_currency: string;
    to_currency: string;
    status: string;
    payment_type: string;
    created_at: string;
    transaction_hash?: string;
    sender_name?: string;
    recipient_name?: string;
    description?: string;
}



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
