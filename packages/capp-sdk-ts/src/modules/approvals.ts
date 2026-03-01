import { CAPPClient } from '../client';
import { ApprovalRequest } from '../models';
import { handleApiError } from '../utils';

export class ApprovalsModule {
    constructor(private client: CAPPClient) { }

    public async list(status: string = 'pending'): Promise<ApprovalRequest[]> {
        const res = await this.client.fetch(`/approvals?status=${encodeURIComponent(status)}`);
        await handleApiError(res);
        const data = await res.json();
        return data.items || [];
    }

    public async resolve(
        approvalId: string,
        decision: string,
        note?: string
    ): Promise<void> {
        const body: Record<string, string> = { decision };
        if (note) body.note = note;

        const res = await this.client.fetch(`/approvals/${approvalId}/resolve`, {
            method: 'POST',
            body: JSON.stringify(body)
        });
        await handleApiError(res);
    }
}
