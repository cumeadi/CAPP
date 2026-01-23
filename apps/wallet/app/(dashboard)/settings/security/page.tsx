"use client";

import { useState } from "react";
import { ArrowLeft, Lock, Fingerprint, Eye, EyeOff } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/Shared/Button";
import { clsx } from "clsx";
import { useSettings } from "@/components/Context/SettingsContext";

export default function SecuritySettingsPage() {
    const { biometricsEnabled, setBiometricsEnabled } = useSettings();
    const [showSeed, setShowSeed] = useState(false);

    return (
        <div className="max-w-2xl mx-auto animate-in slide-in-from-right-4 duration-500">

            {/* Header */}
            <div className="mb-8 flex items-center gap-4">
                <Link href="/settings">
                    <div className="p-2 rounded-full border border-[var(--border-medium)] hover:bg-[var(--bg-tertiary)] text-white transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </div>
                </Link>
                <h1 className="text-2xl font-bold text-white tracking-widest">SECURITY</h1>
            </div>

            <div className="space-y-6">

                {/* Biometrics */}
                <div className="p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex items-center justify-between">
                    <div className="flex gap-4">
                        <div className="p-3 bg-[var(--bg-tertiary)] rounded-xl text-[var(--accent-cyan)] h-fit">
                            <Fingerprint className="w-6 h-6" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-white">Biometrics</h3>
                            <p className="text-sm text-[var(--text-secondary)] mt-1">
                                Use FaceID or TouchID to unlock wallet
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={() => setBiometricsEnabled(!biometricsEnabled)}
                        className={clsx(
                            "w-12 h-7 rounded-full transition-all duration-300 relative border",
                            biometricsEnabled ? "bg-[var(--accent-cyan)] border-[var(--accent-cyan)]" : "bg-[var(--bg-primary)] border-[var(--border-medium)]"
                        )}
                    >
                        <div className={clsx(
                            "absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform duration-300 shadow-sm",
                            biometricsEnabled ? "translate-x-5" : "translate-x-0"
                        )} />
                    </button>
                </div>

                {/* PIN Settings */}
                <div className="p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] transition-colors cursor-pointer group">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-[var(--bg-tertiary)] rounded-xl text-[var(--text-secondary)] group-hover:text-white transition-colors h-fit">
                            <Lock className="w-6 h-6" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-white">Change PIN</h3>
                            <p className="text-sm text-[var(--text-secondary)] mt-1">
                                Update your 6-digit access code
                            </p>
                        </div>
                    </div>
                </div>

                {/* Seed Phrase */}
                <div className="p-6 rounded-2xl bg-[rgba(255,59,48,0.05)] border border-red-500/30">
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h3 className="text-lg font-bold text-red-400">Recovery Phrase</h3>
                            <p className="text-sm text-[var(--text-secondary)] mt-1 max-w-sm">
                                Your seed phrase is the key to your funds. Never share it with anyone.
                            </p>
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            className="border-red-500/50 text-red-400 hover:bg-red-500/10"
                            onClick={() => setShowSeed(!showSeed)}
                            icon={showSeed ? EyeOff : Eye}
                        >
                            {showSeed ? "HIDE" : "REVEAL"}
                        </Button>
                    </div>

                    {showSeed ? (
                        <div className="grid grid-cols-3 gap-3">
                            {["witch", "collapse", "practice", "feed", "shame", "open", "despair", "creek", "road", "again", "ice", "least"].map((word, i) => (
                                <div key={i} className="flex items-center gap-2 p-2 bg-black/40 rounded-lg border border-red-500/20">
                                    <span className="text-xs text-red-500/50 w-4">{i + 1}</span>
                                    <span className="text-sm text-white font-mono">{word}</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="w-full h-32 bg-black/20 rounded-xl border border-red-500/10 flex items-center justify-center backdrop-blur-sm">
                            <div className="text-center">
                                <Lock className="w-8 h-8 text-red-500/30 mx-auto mb-2" />
                                <p className="text-xs text-red-500/50 mt-2">Hidden for security</p>
                            </div>
                        </div>
                    )}
                </div>

            </div>
        </div>
    );
}
