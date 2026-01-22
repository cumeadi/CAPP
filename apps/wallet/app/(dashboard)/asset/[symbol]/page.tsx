"use client";

import { use } from "react";
import { ArrowLeft, TrendingUp } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/Shared/Button";

// Since it's a server component by default in Next.js App Router but we used "use client" for interactivity in others, let's keep it consistent or use params.
// In Next.js 15/16 params is a Promise.
// "use client" needed if we want to use hooks or interactive charts.

export default function AssetDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
    const { symbol } = use(params);
    const assetSymbol = decodeURIComponent(symbol);

    return (
        <div className="space-y-8 animate-in slide-in-from-right-4 duration-500">

            {/* Header */}
            <div className="flex items-center gap-4">
                <Link href="/">
                    <div className="p-2 rounded-full border border-[var(--border-medium)] hover:bg-[var(--bg-tertiary)] text-white transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </div>
                </Link>
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center border border-[var(--border-subtle)]">
                        {assetSymbol === "ETH" ? "Ξ" : assetSymbol === "USDC" ? "$" : "C"}
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-widest">{assetSymbol}</h1>
                        <p className="text-[var(--text-secondary)] text-sm font-mono">Ethereum Network</p>
                    </div>
                </div>
            </div>

            {/* Chart Section (Mock) */}
            <div className="h-64 w-full bg-[var(--bg-card)] rounded-2xl border border-[var(--border-subtle)] p-6 relative overflow-hidden group">
                <div className="absolute top-4 right-4 flex gap-2">
                    {["1H", "1D", "1W", "1M", "1Y"].map((t) => (
                        <button key={t} className="px-2 py-1 text-xs rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-white">{t}</button>
                    ))}
                </div>

                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[var(--accent-cyan)] font-mono text-xs opacity-20">
                    [CHART VISUALIZATION PLACEHOLDER]
                </div>

                {/* Simple SVG Line */}
                <svg className="absolute bottom-0 left-0 w-full h-2/3" preserveAspectRatio="none">
                    <path d="M0,100 C150,50 300,150 450,80 S600,0 800,40 L800,200 L0,200 Z" fill="url(#grad)" opacity="0.2" />
                    <path d="M0,100 C150,50 300,150 450,80 S600,0 800,40" fill="none" stroke="var(--accent-cyan)" strokeWidth="2" />
                    <defs>
                        <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stopColor="var(--accent-cyan)" />
                            <stop offset="100%" stopColor="transparent" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                    <div className="text-xs text-[var(--text-secondary)] mb-1">Price</div>
                    <div className="text-white font-bold font-mono">$1,850.20</div>
                </div>
                <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                    <div className="text-xs text-[var(--text-secondary)] mb-1">24h Change</div>
                    <div className="text-[var(--accent-cyan)] font-bold font-mono flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" /> +2.4%
                    </div>
                </div>
                <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                    <div className="text-xs text-[var(--text-secondary)] mb-1">Your Balance</div>
                    <div className="text-white font-bold font-mono">1.5 {assetSymbol}</div>
                </div>
                <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                    <div className="text-xs text-[var(--text-secondary)] mb-1">Value</div>
                    <div className="text-white font-bold font-mono">$2,800.00</div>
                </div>
            </div>

            {/* Activity */}
            <div className="space-y-4">
                <h3 className="text-lg font-bold text-white tracking-widest">ACTIVITY</h3>
                {/* Reuse the transaction list style roughly */}
                <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-[var(--bg-tertiary)] rounded-full text-[var(--accent-secondary)]"><ArrowLeft className="w-4 h-4 rotate-45" /></div>
                        <div>
                            <div className="text-white font-bold text-sm">Sent {assetSymbol}</div>
                            <div className="text-xs text-[var(--text-secondary)]">Today, 12:00 PM</div>
                        </div>
                    </div>
                    <div className="text-right">
                        <div className="text-white font-mono font-bold">-0.5 {assetSymbol}</div>
                    </div>
                </div>
            </div>

            <div className="flex gap-4 pt-4">
                <Button variant="primary" className="flex-1">SEND</Button>
                <Button variant="secondary" className="flex-1">RECEIVE</Button>
            </div>

        </div>
    );
}
