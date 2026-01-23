"use client";

import { Activity, ArrowUpRight, ArrowDownLeft, CheckCircle2, Loader2, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { api, PaymentHistoryItem } from "@/services/api";

export function RightSidebar() {
    const [transactions, setTransactions] = useState<PaymentHistoryItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadTransactions();
    }, []);

    const loadTransactions = async () => {
        try {
            const data = await api.getHistory();
            // Take recent 5
            setTransactions(data.slice(0, 10));
        } catch (e) {
            console.error("Failed to load feed", e);
        } finally {
            setLoading(false);
        }
    };

    const formatTime = (dateStr: string) => {
        return new Date(dateStr).toLocaleTimeString('en-US', {
            hour: 'numeric', minute: 'numeric', hour12: true
        });
    };

    return (
        <aside className="w-80 h-screen sticky top-0 border-l border-[var(--border-medium)] bg-[var(--bg-secondary)]/50 backdrop-blur-sm hidden xl:flex flex-col p-6 z-20">

            {/* Network Status Module */}
            <div className="mb-8">
                <h3 className="text-xs font-bold text-[var(--text-tertiary)] mb-4 tracking-widest flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-[var(--accent-cyan)] animate-pulse shadow-[0_0_8px_var(--accent-cyan)]" />
                    NETWORK STATUS
                </h3>
                <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                        <span className="text-sm font-medium">Ethereum</span>
                        <span className="text-xs text-[var(--accent-cyan)]">Operational</span>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                        <span className="text-sm font-medium">Polygon</span>
                        <span className="text-xs text-[var(--accent-cyan)]">Operational</span>
                    </div>
                </div>
            </div>

            {/* Transaction Feed */}
            <div className="flex-1 overflow-hidden flex flex-col">
                <h3 className="text-xs font-bold text-[var(--text-tertiary)] mb-4 tracking-widest flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    TRANSACTION FEED
                </h3>

                <div className="space-y-4 overflow-y-auto pr-2 custom-scrollbar flex-1">
                    {loading ? (
                        <div className="flex justify-center py-10">
                            <Loader2 className="w-6 h-6 animate-spin text-[var(--text-tertiary)]" />
                        </div>
                    ) : transactions.length === 0 ? (
                        <div className="text-center py-10 text-[var(--text-secondary)] text-xs">
                            No recent activity
                        </div>
                    ) : (
                        transactions.map((tx) => (
                            <div key={tx.payment_id} className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] transition-colors group">
                                <div className="flex items-start justify-between mb-2">
                                    <div className="p-2 rounded-lg bg-[var(--bg-tertiary)] text-[var(--accent-cyan)]">
                                        <ArrowUpRight className="w-4 h-4" />
                                    </div>
                                    <span className="text-xs text-[var(--text-tertiary)] mt-1">{formatTime(tx.created_at)}</span>
                                </div>
                                <div className="font-bold text-white mb-1 group-hover:text-[var(--accent-cyan)] transition-colors">
                                    {tx.payment_type} {tx.amount.toFixed(2)} {tx.from_currency}
                                </div>
                                <div className="text-xs text-[var(--text-secondary)] mb-2 font-mono truncate w-full">
                                    Ref: {tx.reference_id}
                                </div>
                                {tx.description && (
                                    <div className="text-[10px] text-[var(--text-tertiary)] italic mb-2 truncate">
                                        "{tx.description}"
                                    </div>
                                )}
                                <div className="flex items-center gap-1 text-[var(--accent-cyan)] text-[10px] uppercase tracking-wider">
                                    {tx.status === 'completed' ? (
                                        <><CheckCircle2 className="w-3 h-3" /> Confirmed</>
                                    ) : (
                                        <><Clock className="w-3 h-3 text-orange-400" /> <span className="text-orange-400">{tx.status}</span></>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </aside>
    );
}
