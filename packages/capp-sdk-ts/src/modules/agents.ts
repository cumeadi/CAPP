import { CAPPClient } from '../client';
import { AgentCredential } from '../models';
import { handleApiError } from '../utils';

export class AgentsModule {
    constructor(private client: CAPPClient) { }

    public async issueCredential(params: {
        corridorAllowlist: string[];
        maxPerTxUsd: number;
        dailyLimitUsd: number;
        requireApprovalAboveUsd: number;
        expiryDays: number;
    }): Promise<AgentCredential> {
        const res = await this.client.fetch('/agents/credentials', {
            method: 'POST',
            body: JSON.stringify({
                corridor_allowlist: params.corridorAllowlist,
                max_per_tx_usd: params.maxPerTxUsd,
                daily_limit_usd: params.dailyLimitUsd,
                require_approval_above_usd: params.requireApprovalAboveUsd,
                expiry_days: params.expiryDays
            })
        });
        await handleApiError(res);
        return res.json();
    }

    public async revoke(agentId: string): Promise<void> {
        const res = await this.client.fetch(`/agents/credentials/${agentId}`, {
            method: 'DELETE'
        });
        await handleApiError(res);
    }
}
