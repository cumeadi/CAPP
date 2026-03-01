import { CAPPClient } from '../client';
import { CorridorStatus, CorridorEvent } from '../models';
import { handleApiError } from '../utils';

export class CorridorsModule {
    constructor(private client: CAPPClient) { }

    public async status(corridor: string): Promise<CorridorStatus> {
        const res = await this.client.fetch(`/corridors/${corridor}/status`);
        await handleApiError(res);
        return res.json();
    }

    public async list(): Promise<string[]> {
        const res = await this.client.fetch('/corridors');
        await handleApiError(res);
        const data = await res.json();
        return data.corridors || [];
    }

    public async *subscribe(corridor: string): AsyncGenerator<CorridorEvent, void, unknown> {
        const res = await this.client.fetch(`/corridors/${corridor}/events`);
        await handleApiError(res);

        if (!res.body) return;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        yield JSON.parse(line.slice(6));
                    } catch (e) {
                        // Ignore parse errors on stream data
                    }
                }
            }
        }
    }
}
