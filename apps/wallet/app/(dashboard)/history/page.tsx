"use client";
import { useState, useEffect } from "react";
import { ArrowUpRight, ArrowDownLeft, Filter, Search, Download, RefreshCw } from "lucide-react";
import { Button } from "@/components/Shared/Button";
import { clsx } from "clsx";
import { api, PaymentHistoryItem } from "@/services/api";

export default function HistoryPage() {
    const [filter, setFilter] = useState("all");
    const [history, setHistory] = useState<PaymentHistoryItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadHistory();
    }, []);

    const loadHistory = async () => {
        setLoading(true);
        try {
            const data = await api.getHistory();
            setHistory(data);
        } catch (e) {
            console.error("Failed to load history", e);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
            hour: 'numeric', minute: 'numeric', hour12: true
        });
    };

    const getStatusColor = (status: string) => {
        switch (status.toLowerCase()) {
            case 'completed': return 'text-[var(--accent-cyan)]';
            case 'pending':
            case 'processing': return 'text-orange-400';
            case 'failed': return 'text-red-500';
            default: return 'text-[var(--text-secondary)]';
        }
    };

    const filteredHistory = history.filter(item => {
        if (filter === "all") return true;
        // Simple mapping for now, ideally we check sender_id vs current_user_id
        // But for this MVP assume all created payments are 'sent' unless type specifies otherwise
        if (filter === "sent") return true;
        return false;
    });

    return (
        <div className="space-y-8 animate-in fade-in duration-500">

            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold text-white tracking-widest mb-2">TRANSACTIONS</h1>
                    <p className="text-[var(--text-secondary)] text-sm font-mono">View your past activity.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={loadHistory} icon={RefreshCw}>REFRESH</Button>
                    <Button variant="outline" size="sm" icon={Download}>EXPORT CSV</Button>
                </div>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4 bg-[var(--bg-card)] p-2 rounded-xl border border-[var(--border-subtle)]">
                <div className="pl-2 pr-4 border-r border-[var(--border-subtle)]">
                    <Filter className="w-5 h-5 text-[var(--accent-cyan)]" />
                </div>
                <div className="flex gap-2">
                    {["All", "Sent", "Received", "Swaps"].map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f.toLowerCase())}
                            className={clsx(
                                "px-4 py-1.5 rounded-lg text-sm font-bold transition-colors",
                                filter === f.toLowerCase()
                                    ? "bg-[var(--accent-cyan)] text-black"
                                    : "text-[var(--text-secondary)] hover:text-white"
                            )}
                        >
                            {f}
                        </button>
                    ))}
                </div>
                <div className="ml-auto relative">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]" />
                    <input
                        type="text"
                        placeholder="Search hash or address"
                        className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg pl-9 pr-4 py-1.5 text-sm text-white focus:outline-none focus:border-[var(--accent-cyan)]"
                    />
                </div>
            </div>

            {/* List */}
            <div className="space-y-4">
                {loading ? (
                    <div className="text-center py-10 text-[var(--text-secondary)]">Loading history...</div>
                ) : filteredHistory.length === 0 ? (
                    <div className="text-center py-10 text-[var(--text-secondary)]">No transactions found.</div>
                ) : (
                    filteredHistory.map((tx) => (
                        <div key={tx.payment_id} className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] transition-all group flex items-center justify-between">

                            {/* Left: Icon & Type */}
                            <div className="flex items-center gap-4">
                                <div className={clsx(
                                    "w-10 h-10 rounded-full flex items-center justify-center",
                                    "bg-[var(--bg-tertiary)] text-[var(--accent-secondary)]"
                                    // defaulting to 'send' style for now as we mostly demonstrate sending
                                )}>
                                    <ArrowUpRight className="w-5 h-5" />
                                </div>
                                <div>
                                    <h4 className="text-white font-bold text-sm uppercase flex items-center gap-2">
                                        SEND {tx.from_currency}
                                        {/* Optional pill if we had route info, omitting for now or calculating */}
                                    </h4>
                                    <p className="text-xs text-[var(--text-secondary)] font-mono mt-0.5">{formatDate(tx.created_at)}</p>
                                    <p className="text-[10px] text-[var(--text-secondary)]">To: {tx.recipient_name || tx.reference_id}</p>
                                    {tx.description && (
                                        <p className="text-[10px] text-[var(--text-tertiary)] italic mt-0.5 max-w-[200px] truncate">"{tx.description}"</p>
                                    )}
                                </div>
                            </div>

                            {/* Middle: Details */}
                            <div className="hidden md:block text-right">
                                <div className="text-xs text-[var(--text-secondary)]">Amount</div>
                                <div className="text-white font-mono font-bold">{tx.amount.toFixed(2)} {tx.from_currency}</div>
                            </div>

                            {/* Right: Value & Status */}
                            <div className="text-right">
                                <div className="text-white font-bold">{tx.amount.toFixed(2)} {tx.from_currency}</div>
                                <div className={clsx("text-xs font-bold uppercase", getStatusColor(tx.status))}>
                                    {tx.status}
                                </div>
                            </div>

                        </div>
                    ))
                )}
            </div>

        </div>
    );
}

