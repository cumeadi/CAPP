"use client";

import Link from "next/link";
import { Wallet, ArrowRight, ShieldCheck, Zap } from "lucide-react";
import { Button } from "@/components/Shared/Button";

export default function OnboardingPage() {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-6 relative overflow-hidden">

            {/* Background Decor */}
            <div className="absolute top-0 left-0 w-full h-full pointer-events-none -z-10">
                <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-[var(--accent-primary)]/20 blur-[120px] rounded-full mix-blend-screen" />
                <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-[var(--accent-cyan)]/10 blur-[100px] rounded-full mix-blend-screen" />
            </div>

            <div className="max-w-md w-full text-center space-y-8 animate-in zoom-in duration-500">

                <div className="flex justify-center mb-6">
                    <div className="w-20 h-20 bg-gradient-to-br from-[var(--bg-tertiary)] to-[var(--bg-card)] rounded-2xl border border-[var(--border-medium)] flex items-center justify-center shadow-[0_0_40px_rgba(168,85,247,0.3)]">
                        <Wallet className="w-10 h-10 text-[var(--accent-cyan)]" />
                    </div>
                </div>

                <div>
                    <h1 className="text-4xl font-bold text-white mb-4 tracking-tight">CAPP WALLET</h1>
                    <p className="text-[var(--text-secondary)] text-lg">
                        The intelligent multi-chain wallet that optimizes your routes and yields automatically.
                    </p>
                </div>

                <div className="grid grid-cols-2 gap-4 text-left">
                    <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                        <Zap className="w-6 h-6 text-[var(--accent-cyan)] mb-2" />
                        <h3 className="font-bold text-white text-sm">Smart Routing</h3>
                        <p className="text-xs text-[var(--text-secondary)]">Save up to 40% on gas</p>
                    </div>
                    <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                        <ShieldCheck className="w-6 h-6 text-[var(--accent-primary)] mb-2" />
                        <h3 className="font-bold text-white text-sm">Audited Security</h3>
                        <p className="text-xs text-[var(--text-secondary)]">Non-custodial core</p>
                    </div>
                </div>

                <div className="space-y-4 pt-4">
                    <Link href="/">
                        <Button variant="primary" size="lg" className="w-full text-lg shadow-[0_0_20px_rgba(0,255,179,0.4)] group">
                            CREATE NEW WALLET
                            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </Button>
                    </Link>
                    <Button variant="ghost" className="w-full">
                        I already have a wallet
                    </Button>
                </div>

            </div>

            <div className="absolute bottom-8 text-xs text-[var(--text-tertiary)] font-mono">
                Powered by CAPP Protocol v2.0
            </div>

        </div>
    );
}
