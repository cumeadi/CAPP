"use client";

import { useState } from "react";
import { ArrowUpRight, ArrowDownLeft, Filter, Search, Download } from "lucide-react";
import { Button } from "@/components/Shared/Button";
import { clsx } from "clsx";

const MOCK_HISTORY = [
    { id: 1, type: "send", asset: "ETH", amount: "0.1", value: "$280.00", to: "0xAB...CDEF", date: "Today, 10:45 AM", status: "Confirmed", route: "CAPP Optimized" },
    { id: 2, type: "receive", asset: "USDC", amount: "1,000", value: "$1,000.00", from: "0x12...3456", date: "Today, 09:30 AM", status: "Confirmed", route: "Standard" },
    { id: 3, type: "swap", asset: "USDC -> CAPP", amount: "500", value: "$500.00", date: "Yesterday", status: "Confirmed", route: "Uniswap" },
    { id: 4, type: "send", asset: "ETH", amount: "1.5", value: "$4,200.00", to: "0xTreasury", date: "Jan 12, 2026", status: "Confirmed", route: "Standard" },
    { id: 5, type: "receive", asset: "CAPP", amount: "5,000", value: "$500.00", from: "Staking", date: "Jan 10, 2026", status: "Confirmed", route: "Reward" },
];

export default function HistoryPage() {
    const [filter, setFilter] = useState("all");

    return (
        <div className="space-y-8 animate-in fade-in duration-500">

            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold text-white tracking-widest mb-2">TRANSACTIONS</h1>
                    <p className="text-[var(--text-secondary)] text-sm font-mono">View your past activity.</p>
                </div>
                <Button variant="outline" size="sm" icon={Download}>EXPORT CSV</Button>
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
                {MOCK_HISTORY.map((tx) => (
                    <div key={tx.id} className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] transition-all group flex items-center justify-between">

                        {/* Left: Icon & Type */}
                        <div className="flex items-center gap-4">
                            <div className={clsx(
                                "w-10 h-10 rounded-full flex items-center justify-center",
                                tx.type === "send" ? "bg-[var(--bg-tertiary)] text-[var(--accent-secondary)]" :
                                    tx.type === "receive" ? "bg-[rgba(0,255,179,0.1)] text-[var(--accent-cyan)]" :
                                        "bg-orange-500/10 text-orange-500"
                            )}>
                                {tx.type === "send" ? <ArrowUpRight className="w-5 h-5" /> :
                                    tx.type === "receive" ? <ArrowDownLeft className="w-5 h-5" /> :
                                        <div className="font-bold text-xs">SWAP</div>}
                            </div>
                            <div>
                                <h4 className="text-white font-bold text-sm uppercase flex items-center gap-2">
                                    {tx.type} {tx.asset}
                                    {tx.route.includes("CAPP") && (
                                        <span className="text-[10px] bg-[var(--accent-cyan)] text-black px-1.5 rounded font-bold">CAPP ROUTED</span>
                                    )}
                                </h4>
                                <p className="text-xs text-[var(--text-secondary)] font-mono mt-0.5">{tx.date}</p>
                            </div>
                        </div>

                        {/* Middle: Details */}
                        <div className="hidden md:block text-right">
                            <div className="text-xs text-[var(--text-secondary)]">Amount</div>
                            <div className="text-white font-mono font-bold">{tx.amount} {tx.asset.split(" ")[0]}</div>
                        </div>

                        {/* Right: Value & Status */}
                        <div className="text-right">
                            <div className="text-white font-bold">{tx.value}</div>
                            <div className="text-xs text-[var(--accent-cyan)]">{tx.status}</div>
                        </div>

                    </div>
                ))}
            </div>

        </div>
    );
}
