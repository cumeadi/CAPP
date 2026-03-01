import { CAPPClient } from '../client';
import { PaymentResult } from '../models';
import { handleApiError } from '../utils';

export class PaymentsModule {
    constructor(private client: CAPPClient) { }

    public async send(params: {
        amount: number;
        fromCurrency: string;
        toCurrency: string;
        recipient: string;
        corridor: string;
    }): Promise<PaymentResult> {
        const res = await this.client.fetch('/payments/send', {
            method: 'POST',
            body: JSON.stringify({
                amount: params.amount,
                from_currency: params.fromCurrency,
                to_currency: params.toCurrency,
                recipient: params.recipient,
                corridor: params.corridor
            })
        });
        await handleApiError(res);
        return res.json();
    }

    public async get(txId: string): Promise<PaymentResult> {
        const res = await this.client.fetch(`/payments/${txId}`);
        await handleApiError(res);
        return res.json();
    }

    public async list(params?: { limit?: number; corridor?: string }): Promise<PaymentResult[]> {
        const query = new URLSearchParams();
        if (params?.limit) query.append('limit', params.limit.toString());
        if (params?.corridor) query.append('corridor', params.corridor);

        const qs = query.toString();
        const url = `/payments${qs ? '?' + qs : ''}`;

        const res = await this.client.fetch(url);
        await handleApiError(res);
        const data = await res.json();
        return data.items || [];
    }
}
