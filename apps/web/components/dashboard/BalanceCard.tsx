'use client';
import { useEffect, useState } from 'react';
import { api } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Wallet, RefreshCw } from 'lucide-react';

interface BalanceData {
    address: string;
    balances: {
        [token: string]: number;
    };
    total_usd: number;
}

export function BalanceCard() {
    const [data, setData] = useState<BalanceData | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchBalance = async () => {
        setLoading(true);
        try {
            // Hardcoded agent/user ID for demo
            const res = await api.getWalletBalance("0x123");
            setData(res);
        } catch (e) {
            console.error("Failed to fetch balance", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchBalance();
    }, []);

    return (
        <Card className="glass-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Balance</CardTitle>
                <div className="flex gap-2">
                    <button onClick={fetchBalance} className={`p-1 hover:bg-white/10 rounded ${loading ? 'animate-spin' : ''}`}>
                        <RefreshCw size={16} />
                    </button>
                    <Wallet className="h-4 w-4 text-muted-foreground" />
                </div>
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold">
                    {loading ? "..." : `$${data?.total_usd?.toFixed(2) || '0.00'}`}
                </div>
                <div className="mt-4 space-y-2">
                    {data?.balances && Object.entries(data.balances).map(([token, amount]) => (
                        <div key={token} className="flex justify-between text-sm">
                            <span className="text-muted-foreground">{token}</span>
                            <span className="font-mono">{typeof amount === 'number' ? amount.toFixed(4) : amount}</span>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
