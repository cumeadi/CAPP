import { PaymentsModule } from './modules/payments';
import { RoutingModule } from './modules/routing';
import { WalletModule } from './modules/wallet';
import { CorridorsModule } from './modules/corridors';
import { AgentsModule } from './modules/agents';
import { ApprovalsModule } from './modules/approvals';

export interface CAPPClientOptions {
    apiKey: string;
    sandbox?: boolean;
}

export class CAPPClient {
    public apiKey: string;
    public sandbox: boolean;
    public baseUrl: string;

    public payments: PaymentsModule;
    public routing: RoutingModule;
    public wallet: WalletModule;
    public corridors: CorridorsModule;
    public agents: AgentsModule;
    public approvals: ApprovalsModule;

    constructor(options: CAPPClientOptions) {
        this.apiKey = options.apiKey;
        this.sandbox = options.sandbox ?? true;

        // For MVP sandbox testing, defaulting to a common local dev backend 
        // real SDK would point to https://api.sandbox.canza.io/v1
        this.baseUrl = this.sandbox
            ? 'http://localhost:8000/v1'
            : 'https://api.canza.io/v1';

        if (this.sandbox && !this.apiKey.startsWith('sk_test_')) {
            console.warn("Using sandbox=true with a non-test API key. This may fail.");
        }

        this.payments = new PaymentsModule(this);
        this.routing = new RoutingModule(this);
        this.wallet = new WalletModule(this);
        this.corridors = new CorridorsModule(this);
        this.agents = new AgentsModule(this);
        this.approvals = new ApprovalsModule(this);
    }

    public async fetch(path: string, options: RequestInit = {}): Promise<Response> {
        const defaultHeaders: Record<string, string> = {
            'Authorization': `Bearer ${this.apiKey}`,
            'User-Agent': '@canza/capp-sdk/0.1.0'
        };
        if (options.body && typeof options.body === 'string') {
            defaultHeaders['Content-Type'] = 'application/json';
        }

        const finalOptions: RequestInit = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers,
            }
        };

        return fetch(`${this.baseUrl}${path}`, finalOptions);
    }
}
