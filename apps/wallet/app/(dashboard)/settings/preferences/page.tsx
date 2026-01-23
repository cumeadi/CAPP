"use client";

import { ArrowLeft, Smartphone, Bell, Moon, Sun, DollarSign } from "lucide-react";
import Link from "next/link";
import { clsx } from "clsx";
import { useSettings, Currency } from "@/components/Context/SettingsContext";

export default function PreferencesSettingsPage() {
    const {
        notificationsEnabled,
        setNotificationsEnabled,
        currency,
        setCurrency
    } = useSettings();

    return (
        <div className="max-w-2xl mx-auto animate-in slide-in-from-right-4 duration-500">

            <div className="mb-8 flex items-center gap-4">
                <Link href="/settings">
                    <div className="p-2 rounded-full border border-[var(--border-medium)] hover:bg-[var(--bg-tertiary)] text-white transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </div>
                </Link>
                <h1 className="text-2xl font-bold text-white tracking-widest">APP PREFERENCES</h1>
            </div>

            <div className="space-y-6">

                {/* Notifications */}
                <div className="p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex items-center justify-between">
                    <div className="flex gap-4">
                        <div className="p-3 bg-[var(--bg-tertiary)] rounded-xl text-[var(--accent-cyan)] h-fit">
                            <Bell className="w-6 h-6" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-white">Push Notifications</h3>
                            <p className="text-sm text-[var(--text-secondary)] mt-1">
                                Receive alerts for transactions and yield updates
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={() => setNotificationsEnabled(!notificationsEnabled)}
                        className={clsx(
                            "w-12 h-7 rounded-full transition-all duration-300 relative border",
                            notificationsEnabled ? "bg-[var(--accent-cyan)] border-[var(--accent-cyan)]" : "bg-[var(--bg-primary)] border-[var(--border-medium)]"
                        )}
                    >
                        <div className={clsx(
                            "absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform duration-300 shadow-sm",
                            notificationsEnabled ? "translate-x-5" : "translate-x-0"
                        )} />
                    </button>
                </div>

                {/* Currency */}
                <div className="p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                    <div className="flex items-center gap-4 mb-4">
                        <div className="p-3 bg-[var(--bg-tertiary)] rounded-xl text-[var(--text-secondary)] h-fit">
                            <DollarSign className="w-6 h-6" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-white">Preferred Currency</h3>
                            <p className="text-sm text-[var(--text-secondary)]">
                                Base currency for display values
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        {(["USD", "EUR", "GBP"] as Currency[]).map((curr) => (
                            <button
                                key={curr}
                                onClick={() => setCurrency(curr)}
                                className={clsx(
                                    "p-3 rounded-xl border font-bold text-sm transition-all",
                                    currency === curr
                                        ? "bg-[var(--accent-cyan)]/10 border-[var(--accent-cyan)] text-[var(--accent-cyan)]"
                                        : "bg-[var(--bg-primary)] border-[var(--border-medium)] text-[var(--text-secondary)] hover:border-[var(--text-secondary)]"
                                )}
                            >
                                {curr}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Theme (Locked) */}
                <div className="p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] opacity-60">
                    <div className="flex items-center justify-between">
                        <div className="flex gap-4">
                            <div className="p-3 bg-[var(--bg-tertiary)] rounded-xl text-[var(--text-secondary)] h-fit">
                                <Moon className="w-6 h-6" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-white">Appearance</h3>
                                <p className="text-sm text-[var(--text-secondary)] mt-1">
                                    CAPP Dark Mode (Default)
                                </p>
                            </div>
                        </div>
                        <div className="px-3 py-1 bg-[var(--bg-tertiary)] rounded-lg text-xs font-mono text-[var(--text-secondary)]">LOCKED</div>
                    </div>
                </div>

            </div>
        </div>
    );
}
