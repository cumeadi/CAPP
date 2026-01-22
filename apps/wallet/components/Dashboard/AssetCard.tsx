"use client";

import { clsx } from "clsx";
import { TrendingUp, TrendingDown } from "lucide-react";

interface AssetCardProps {
    symbol: string;
    balance: string;
    value: string;
    change: number;
    color?: string;
    icon?: React.ReactNode;
}

export function AssetCard({ symbol, balance, value, change, color = "var(--accent-cyan)", icon }: AssetCardProps) {
    const isPositive = change >= 0;

    return (
        <div className="min-w-[280px] p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] transition-all duration-300 group cursor-pointer relative overflow-hidden">

            {/* Background Glow */}
            <div className="absolute -right-10 -top-10 w-32 h-32 bg-[var(--accent-primary)]/10 rounded-full blur-3xl group-hover:bg-[var(--accent-primary)]/20 transition-all" />

            <div className="flex justify-between items-start mb-6">
                <div>
                    <h3 className="text-2xl font-bold text-white tracking-tight">{symbol}</h3>
                    <p className="text-xs text-[var(--text-secondary)] font-mono mt-1">{balance}</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center border border-[var(--border-medium)] group-hover:border-[var(--accent-primary)] transition-colors">
                    {icon || <div className="w-4 h-4 bg-gray-400 rounded-full" />}
                </div>
            </div>

            <div className="space-y-2">
                <div className="text-3xl font-bold text-white tracking-widest font-mono">{value}</div>

                <div className={clsx("flex items-center gap-2 text-xs font-bold", isPositive ? "text-[var(--accent-cyan)]" : "text-[var(--accent-danger)]")}>
                    {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {isPositive ? "+" : ""}{change}% (24h)
                </div>
            </div>

            {/* Mini Chart Decoration */}
            <div className="mt-4 h-1 w-full bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-cyan)] w-[70%]" />
            </div>

        </div>
    );
}
