"use client";

import { useState } from "react";
import { ArrowLeft, Copy, Share2, AlertCircle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/Shared/Button";
import { clsx } from "clsx";

export default function ReceivePage() {
    const [copied, setCopied] = useState(false);
    const address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e";

    const handleCopy = () => {
        navigator.clipboard.writeText(address);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="max-w-xl mx-auto animate-in fade-in duration-500">

            {/* Header */}
            <div className="mb-8 flex items-center gap-4">
                <Link href="/">
                    <div className="p-2 rounded-full border border-[var(--border-medium)] hover:bg-[var(--bg-tertiary)] text-white transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </div>
                </Link>
                <h1 className="text-2xl font-bold text-white tracking-widest">RECEIVE ASSETS</h1>
            </div>

            <div className="bg-[var(--bg-card)] border border-[var(--border-medium)] rounded-2xl p-8 flex flex-col items-center relative overflow-hidden">

                {/* Glow Effect */}
                <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-transparent via-[var(--accent-cyan)] to-transparent opacity-50" />

                <div className="mb-6 p-4 bg-white rounded-xl">
                    {/* Mock QR Code */}
                    <div className="w-48 h-48 bg-black pattern-grid-lg"
                        style={{
                            backgroundImage: `radial-gradient(var(--bg-primary) 2px, transparent 2px)`,
                            backgroundSize: '10px 10px',
                            display: 'grid',
                            placeItems: 'center'
                        }}>
                        <div className="w-10 h-10 bg-[var(--accent-cyan)] rounded-lg flex items-center justify-center font-bold text-black text-xl">C</div>
                    </div>
                </div>

                <p className="text-[var(--text-secondary)] text-sm font-mono mb-2">Scan to deposit funds</p>

                <div className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] p-4 rounded-xl flex items-center justify-between gap-4 mb-6 group hover:border-[var(--accent-cyan)] transition-colors cursor-pointer" onClick={handleCopy}>
                    <div className="font-mono text-xs md:text-sm text-white truncate px-2">
                        {address}
                    </div>
                    <Button variant="ghost" size="sm" icon={Copy} className={clsx("text-[var(--accent-cyan)]", copied && "text-green-400")}>
                        {copied ? "COPIED" : "COPY"}
                    </Button>
                </div>

                <div className="flex gap-4 w-full">
                    <Button variant="outline" className="flex-1">SHARE ADDRESS</Button>
                </div>

            </div>

            {/* CAPP Network Detect Callout */}
            <div className="mt-6 flex items-start gap-4 p-4 rounded-xl bg-[rgba(0,255,179,0.05)] border border-[rgba(0,255,179,0.2)]">
                <div className="p-2 bg-[var(--bg-tertiary)] rounded-full text-[var(--accent-cyan)]">
                    <AlertCircle className="w-4 h-4" />
                </div>
                <div>
                    <h4 className="text-white font-bold text-sm mb-1 uppercase tracking-wide">Universal Address</h4>
                    <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                        This address works for all supported networks (Ethereum, Polygon, Arbitrum, Optimism).
                        <span className="text-[var(--accent-cyan)] font-bold"> CAPP auto-detects incoming chains.</span>
                    </p>
                </div>
            </div>

        </div>
    );
}
