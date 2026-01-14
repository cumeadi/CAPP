'use client';

import { useState, useEffect } from 'react';
import { api, YieldStatsResponse } from '@/services/api';

interface UseTreasuryResult {
    data: YieldStatsResponse | null;
    loading: boolean;
    error: Error | null;
    refetch: () => Promise<void>;
}

export function useTreasury(): UseTreasuryResult {
    const [data, setData] = useState<YieldStatsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            const stats = await api.getYieldStats();
            setData(stats);
            setError(null);
        } catch (err: any) {
            setError(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    return { data, loading, error, refetch: fetchData };
}
