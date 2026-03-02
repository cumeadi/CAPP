import { CAPPClient } from '../client';
import { handleApiError } from '../utils';

export class ComplianceModule {
    constructor(private client: CAPPClient) { }

    public async getCsvReport(organizationId: string): Promise<string> {
        /**
         * Downloads the full transaction history for the organization as CSV.
         * Returns the CSV file content as a string.
         */
        const res = await this.client.fetch(`/compliance/reports/csv?organizationId=${organizationId}`);
        await handleApiError(res);
        return res.text();
    }
}
