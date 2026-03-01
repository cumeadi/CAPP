import { CAPPClient } from '../client';
import { Balances } from '../models';
import { handleApiError } from '../utils';

export class WalletModule {
    constructor(private client: CAPPClient) { }

    public async getBalance(params?: { chain?: string; currency?: string }): Promise<Balances> {
        const query = new URLSearchParams();
        if (params?.chain) query.append('chain', params.chain);
        if (params?.currency) query.append('currency', params.currency);

        const qs = query.toString();
        const url = `/wallet/balances${qs ? '?' + qs : ''}`;

        const res = await this.client.fetch(url);
        await handleApiError(res);
        return res.json();
    }
}
