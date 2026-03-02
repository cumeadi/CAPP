import { CAPPClient } from "../client";
import { handleApiError } from "../utils";

export interface WebhookThreshold {
    fee_pct?: number;
    usd_value?: number;
    [key: string]: any;
}

export interface WebhookSubscription {
    id: string;
    agent_id: string;
    event_type: string;
    corridor: string;
    webhook_url: string;
    threshold?: WebhookThreshold;
    is_active: boolean;
    created_at: string;
}

export class EventsModule {
    constructor(private readonly client: CAPPClient) { }

    /**
     * Subscribe a webhook URL to receive notifications when specific corridor conditions are met.
     */
    async subscribe(
        event_type: string,
        corridor: string,
        webhook_url: string,
        threshold?: WebhookThreshold
    ): Promise<WebhookSubscription> {
        const res = await this.client.fetch("/events/subscriptions", {
            method: "POST",
            body: JSON.stringify({ event_type, corridor, webhook_url, threshold })
        });
        await handleApiError(res);
        return res.json();
    }

    /**
     * List all active webhook subscriptions.
     */
    async listSubscriptions(): Promise<WebhookSubscription[]> {
        const res = await this.client.fetch("/events/subscriptions", {
            method: "GET"
        });
        await handleApiError(res);
        return res.json();
    }

    /**
     * Cancel an active webhook subscription.
     */
    async unsubscribe(subscriptionId: string): Promise<boolean> {
        const res = await this.client.fetch(`/events/subscriptions/${subscriptionId}`, {
            method: "DELETE"
        });
        await handleApiError(res);
        return true;
    }
}
