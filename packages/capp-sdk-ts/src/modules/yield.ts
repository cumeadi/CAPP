import { CAPPClient } from '../client';
import { handleApiError } from '../utils';

export class YieldModule {
    constructor(private client: CAPPClient) { }

    public async getBalance(walletAddress: string): Promise<Record<string, any>> {
        const res = await this.client.fetch(`/yield/balance/${walletAddress}`);
        await handleApiError(res);
        return res.json();
    }

    public async optimize(params: {
        walletAddress: string;
        minSweepAmount?: number;
        bufferPct?: number;
    }): Promise<Record<string, any>> {
        const res = await this.client.fetch('/yield/optimize', {
            method: 'POST',
            body: JSON.stringify({
                wallet_address: params.walletAddress,
                min_sweep_amount: params.minSweepAmount,
                buffer_pct: params.bufferPct
            })
        });
        await handleApiError(res);
        return res.json();
    }
}
