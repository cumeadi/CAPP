import { CAPPClient } from '../client';
import { RouteAnalysisResult, FXRate } from '../models';
import { handleApiError } from '../utils';

export class RoutingModule {
    constructor(private client: CAPPClient) { }

    public async analyze(params: {
        amount: number;
        fromCurrency: string;
        toCurrency: string;
        corridor: string;
    }): Promise<RouteAnalysisResult[]> {
        const res = await this.client.fetch('/routing/analyze', {
            method: 'POST',
            body: JSON.stringify({
                amount: params.amount,
                from_currency: params.fromCurrency,
                to_currency: params.toCurrency,
                corridor: params.corridor
            })
        });
        await handleApiError(res);
        const data = await res.json();
        return data.routes || [];
    }

    public async getFxRate(pair: string): Promise<FXRate> {
        const res = await this.client.fetch(`/routing/fx?pair=${encodeURIComponent(pair)}`);
        await handleApiError(res);
        return res.json();
    }
}
