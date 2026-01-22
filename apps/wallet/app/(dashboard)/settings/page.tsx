"use client";

import { useState } from "react";
import { ArrowLeft, Shield, Smartphone, Globe, Briefcase, ChevronRight, Zap } from "lucide-react";
import Link from "next/link";
import { clsx } from "clsx";

export default function SettingsPage() {
    const [smartSweepEnabled, setSmartSweepEnabled] = useState(false);
    const [loading, setLoading] = useState(false);

    // Load initial config
    /* 
    useEffect(() => {
        agentApi.getAgentConfig().then(config => {
            setSmartSweepEnabled(config.yield_preferences.includes("SMART_SWEEP"));
        }).catch(err => console.error(err));
    }, []);
    */

    const handleToggle = async () => {
        setLoading(true);
        const newState = !smartSweepEnabled;
        setSmartSweepEnabled(newState); // Optimistic

        try {
            // await agentApi.updateAgentConfig({ ...currentConfig, notifications_enabled: newState });
            // Mocking the API delay for now since backend might not have the full schema yet
            await new Promise(r => setTimeout(r, 800));

        } catch (error) {
            console.error("Failed to update settings", error);
            setSmartSweepEnabled(!newState); // Revert
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-3xl mx-auto animate-in slide-in-from-bottom-4 duration-500">

            {/* Header */}
            <div className="mb-8 flex items-center gap-4">
                <Link href="/">
                    <div className="p-2 rounded-full border border-[var(--border-medium)] hover:bg-[var(--bg-tertiary)] text-white transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </div>
                </Link>
                <h1 className="text-2xl font-bold text-white tracking-widest">SETTINGS</h1>
            </div>

            <div className="space-y-6">

                {/* Smart Sweep Section (Highlighted) */}
                <div className="p-6 rounded-2xl bg-gradient-to-br from-[var(--bg-card)] to-[rgba(0,255,179,0.05)] border border-[var(--accent-cyan)] relative overflow-hidden">
                    <div className="absolute right-0 top-0 w-32 h-32 bg-[var(--accent-cyan)]/10 rounded-bl-[100px] -z-0" />

                    <div className="relative z-10 flex items-start justify-between">
                        <div className="flex gap-4">
                            <div className="p-3 bg-[var(--accent-cyan)]/10 rounded-xl text-[var(--accent-cyan)] h-fit">
                                <Zap className="w-6 h-6" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                    SMART SWEEP™
                                    <span className="text-[10px] bg-[var(--accent-cyan)] text-black px-2 py-0.5 rounded font-bold">PRO</span>
                                </h3>
                                <p className="text-sm text-[var(--text-secondary)] mt-1 max-w-md">
                                    Automatically routes idle assets to high-yield strategies when gas costs are low. Funds are instantly available when you need to send.
                                </p>
                                {smartSweepEnabled && (
                                    <div className="mt-4 flex items-center gap-2 text-xs text-[var(--accent-cyan)]">
                                        <span className="w-2 h-2 rounded-full bg-[var(--accent-cyan)] animate-pulse" />
                                        Currently earning 4.5% APY on idle liquidity
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Toggle Switch */}
                        <button
                            onClick={handleToggle}
                            disabled={loading}
                            className={clsx(
                                "w-14 h-8 rounded-full transition-all duration-300 relative border",
                                smartSweepEnabled ? "bg-[var(--accent-cyan)] border-[var(--accent-cyan)]" : "bg-[var(--bg-primary)] border-[var(--border-medium)]",
                                loading && "opacity-50 cursor-wait"
                            )}
                        >
                            <div className={clsx(
                                "absolute top-1 left-1 w-5 h-5 rounded-full bg-white transition-transform duration-300 shadow-sm",
                                smartSweepEnabled ? "translate-x-6" : "translate-x-0"
                            )} />
                        </button>
                    </div>
                </div>

                {/* General Settings */}
                <div className="space-y-3">
                    <h3 className="text-xs font-bold text-[var(--text-tertiary)] uppercase tracking-widest ml-1 mb-2">General</h3>

                    {[
                        { icon: Shield, label: "Security", desc: "Biometrics, PIN, Seed Phrase" },
                        { icon: Globe, label: "Networks", desc: "Manage operational chains" },
                        { icon: Smartphone, label: "App Preferences", desc: "Notifications, Currency" },
                        { icon: Briefcase, label: "Compliance Mode", desc: "Tax reports, Audit logs" },
                    ].map((item) => (
                        <div key={item.label} className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] transition-all flex items-center justify-between group cursor-pointer">
                            <div className="flex items-center gap-4">
                                <div className="p-2 rounded-lg bg-[var(--bg-tertiary)] text-[var(--text-secondary)] group-hover:text-white transition-colors">
                                    <item.icon className="w-5 h-5" />
                                </div>
                                <div>
                                    <h4 className="text-white font-bold text-sm">{item.label}</h4>
                                    <p className="text-xs text-[var(--text-secondary)]">{item.desc}</p>
                                </div>
                            </div>
                            <ChevronRight className="w-5 h-5 text-[var(--text-tertiary)] group-hover:text-white transition-colors" />
                        </div>
                    ))}
                </div>

                <div className="mt-8 text-center">
                    <p className="text-xs text-[var(--text-tertiary)] font-mono">CAPP Wallet v0.1.0-alpha</p>
                </div>

            </div>
        </div>
    );
}
