"use client";

import { useState } from "react";
import { ArrowLeft, ScanLine, Info } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/Shared/Button";
import { RoutingComparisonWidget } from "@/components/Send/RoutingComparisonWidget";

export default function SendPage() {
    const [amount, setAmount] = useState("");
    const [recipient, setRecipient] = useState("");

    return (
        <div className="max-w-2xl mx-auto animate-in slide-in-from-right-4 duration-500">

            {/* Header */}
            <div className="mb-8 flex items-center gap-4">
                <Link href="/">
                    <div className="p-2 rounded-full border border-[var(--border-medium)] hover:bg-[var(--bg-tertiary)] text-white transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </div>
                </Link>
                <h1 className="text-2xl font-bold text-white tracking-widest">SEND CRYPTO</h1>
            </div>

            <div className="space-y-6">

                {/* Asset Selection */}
                <div className="space-y-2">
                    <label className="text-xs text-[var(--text-secondary)] uppercase tracking-wider font-bold ml-1">Select Asset</label>
                    <div className="relative">
                        <select className="w-full p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-medium)] text-white appearance-none focus:outline-none focus:border-[var(--accent-cyan)]">
                            <option>USDC (USD Coin)</option>
                            <option>ETH (Ethereum)</option>
                            <option>CAPP (CAPP Token)</option>
                        </select>
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-[var(--text-secondary)]">▼</div>
                    </div>
                    <div className="flex justify-between px-1 text-xs text-[var(--text-secondary)]">
                        <span>Balance: 5,000.00 USDC</span>
                    </div>
                </div>

                {/* Recipient */}
                <div className="space-y-2">
                    <label className="text-xs text-[var(--text-secondary)] uppercase tracking-wider font-bold ml-1">Recipient Address</label>
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="0x..."
                            value={recipient}
                            onChange={(e) => setRecipient(e.target.value)}
                            className="w-full p-4 pr-12 rounded-xl bg-[var(--bg-card)] border border-[var(--border-medium)] text-white focus:outline-none focus:border-[var(--accent-cyan)] font-mono placeholder:text-gray-600"
                        />
                        <button className="absolute right-3 top-1/2 -translate-y-1/2 p-2 text-[var(--accent-cyan)] hover:bg-[var(--accent-cyan)]/10 rounded-lg transition-colors">
                            <ScanLine className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Amount */}
                <div className="space-y-2">
                    <label className="text-xs text-[var(--text-secondary)] uppercase tracking-wider font-bold ml-1">Amount</label>
                    <div className="relative">
                        <input
                            type="number"
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                            placeholder="0.00"
                            className="w-full p-4 pr-20 rounded-xl bg-[var(--bg-card)] border border-[var(--border-medium)] text-white focus:outline-none focus:border-[var(--accent-cyan)] font-mono text-2xl font-bold placeholder:text-gray-700"
                        />
                        <button className="absolute right-3 top-1/2 -translate-y-1/2 px-3 py-1 bg-[var(--bg-tertiary)] text-[var(--accent-cyan)] text-xs font-bold rounded hover:bg-[var(--accent-cyan)] hover:text-black transition-colors">
                            MAX
                        </button>
                    </div>
                </div>

                <div className="h-[1px] bg-[var(--border-medium)] w-full my-8" />

                {/* CAPP Routing Widget */}
                <div className="space-y-4">
                    <div className="flex items-center gap-2">
                        <label className="text-xs text-[var(--accent-cyan)] uppercase tracking-wider font-bold">Smart Routing Optimization</label>
                        <Info className="w-3 h-3 text-[var(--text-secondary)]" />
                    </div>
                    <RoutingComparisonWidget amount={parseFloat(amount) || 0} recipient={recipient} />
                </div>

                <div className="pt-4">
                    <Button variant="primary" size="lg" className="w-full shadow-[0_0_30px_rgba(0,255,179,0.3)] hover:shadow-[0_0_50px_rgba(0,255,179,0.5)]">
                        SEND WITH CAPP
                    </Button>
                    <div className="text-center mt-4">
                        <button className="text-xs text-[var(--text-secondary)] underline decoration-dotted hover:text-white">Send using standard route (Slower)</button>
                    </div>
                </div>

            </div>
        </div>
    );
}
