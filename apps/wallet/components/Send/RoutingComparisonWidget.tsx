"use client";

import { clsx } from "clsx";
import { Clock, Fuel, Zap } from "lucide-react";
import { useState, useEffect } from "react";
import { api, RoutingResponse, PaymentRoute } from "@/services/api"; // Ensure you export these types

interface RoutingComparisonWidgetProps {
    amount: number;
    recipient: string;
}

export function RoutingComparisonWidget({ amount, recipient }: RoutingComparisonWidgetProps) {
    const [selectedRoute, setSelectedRoute] = useState<"standard" | "capp">("capp");
    const [data, setData] = useState<RoutingResponse | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        async function fetchRoutes() {
            if (!amount || !recipient) return;
            setLoading(true);
            try {
                // MockStandard only for comparison visualization if API returns only CAPP
                const res = await api.calculateRoute(amount, "USDC", recipient);
                setData(res);
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        }

        // Debounce
        const timer = setTimeout(fetchRoutes, 800);
        return () => clearTimeout(timer);
    }, [amount, recipient]);

    // Fallback / Initial State
    const standardFee = 5.20;
    const standardTime = 120; // seconds

    const cappRoute = data?.recommended_route;
    const standardRoute = data?.routes.find(r => r.chain !== "POLYGON" && r.chain !== "APTOS") || null; // Just heuristic

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative">

            {/* Connector Label - visible on desktop */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 hidden md:flex flex-col items-center">
                <span className="text-[10px] text-[var(--text-secondary)] bg-[var(--bg-primary)] px-2 py-1 rounded-full border border-[var(--border-subtle)]">VS</span>
            </div>

            {/* Standard Route Card */}
            <div
                onClick={() => setSelectedRoute("standard")}
                className={clsx(
                    "relative p-6 rounded-2xl border transition-all duration-300 cursor-pointer overflow-hidden",
                    selectedRoute === "standard"
                        ? "bg-[var(--bg-card)] border-white/50 shadow-[0_0_20px_rgba(255,255,255,0.1)]"
                        : "bg-[var(--bg-primary)] border-[var(--border-medium)] opacity-60 hover:opacity-80"
                )}
            >
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h3 className="text-sm font-bold text-white uppercase tracking-wider">Standard Route</h3>
                        <p className="text-xs text-[var(--text-secondary)] mt-1">Ethereum Direct</p>
                    </div>
                    <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center">
                        <div className="text-xs">Ξ</div>
                    </div>
                </div>

                <div className="space-y-3 mb-6">
                    <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2 text-[var(--text-secondary)]"><Fuel className="w-4 h-4" /> Gas Fee</span>
                        <span className="font-mono text-white">${standardFee.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2 text-[var(--text-secondary)]"><Clock className="w-4 h-4" /> Est. Time</span>
                        <span className="font-mono text-white">~2 mins</span>
                    </div>
                </div>

                {/* Visual Route Line - Simple */}
                <div className="h-1 bg-gray-700 rounded-full w-full relative">
                    <div className="absolute left-0 top-0 h-full w-full bg-white/20" />
                    <div className="absolute left-0 -top-1 w-3 h-3 bg-gray-500 rounded-full" />
                    <div className="absolute right-0 -top-1 w-3 h-3 bg-gray-500 rounded-full" />
                </div>

            </div>

            {/* CAPP Smart Route Card */}
            <div
                onClick={() => setSelectedRoute("capp")}
                className={clsx(
                    "relative p-6 rounded-2xl border transition-all duration-300 cursor-pointer overflow-hidden group",
                    selectedRoute === "capp"
                        ? "bg-[rgba(0,255,179,0.05)] border-[var(--accent-cyan)] shadow-[0_0_30px_rgba(0,255,179,0.15)]"
                        : "bg-[var(--bg-primary)] border-[var(--border-medium)] opacity-60 hover:opacity-100"
                )}
            >
                {/* Recommended Badge */}
                <div className="absolute top-0 right-0 bg-[var(--accent-cyan)] text-black text-[10px] font-bold px-3 py-1 rounded-bl-xl uppercase flex items-center gap-1">
                    <Zap className="w-3 h-3 fill-black" /> Recommended
                </div>

                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h3 className="text-sm font-bold text-[var(--accent-cyan)] uppercase tracking-wider flex items-center gap-2">
                            CAPP Smart Route
                        </h3>
                        <p className="text-xs text-[var(--text-tertiary)] mt-1">Poly-Bridge Optimization</p>
                    </div>
                    {loading && <div className="text-[var(--accent-cyan)] animate-spin">C</div>}
                </div>

                <div className="space-y-3 mb-6">
                    <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2 text-[var(--text-secondary)]"><Fuel className="w-4 h-4" /> Gas Fee</span>
                        <span className="font-mono text-[var(--accent-cyan)] font-bold">
                            {cappRoute ? `$${cappRoute.fee_usd.toFixed(2)}` : (loading ? "..." : "$0.80")}
                        </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2 text-[var(--text-secondary)]"><Clock className="w-4 h-4" /> Est. Time</span>
                        <span className="font-mono text-[var(--accent-cyan)] font-bold">
                            {cappRoute ? `~${cappRoute.eta_seconds}s` : (loading ? "..." : "~30s")}
                        </span>
                    </div>
                </div>

                {/* Animated Map Route Visualization */}
                <div className="relative h-12 w-full mt-2">
                    <div className="absolute inset-0 flex items-center justify-between px-2">
                        {[1, 2, 3, 4].map((i) => (
                            <div key={i} className={clsx("w-2 h-2 rounded-full z-10", i === 4 ? "bg-[var(--accent-cyan)] shadow-[0_0_10px_var(--accent-cyan)]" : "bg-[var(--bg-tertiary)] border border-[var(--accent-cyan)]")} />
                        ))}
                    </div>
                    {/* Connecting Lines */}
                    <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
                        <path d="M 10,24 Q 50,5 100,24 T 200,24" fill="none" stroke="url(#gradient)" strokeWidth="2" strokeDasharray="4 4" className="animate-[dash_20s_linear_infinite]" />
                        <defs>
                            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stopColor="transparent" />
                                <stop offset="50%" stopColor="var(--accent-cyan)" />
                                <stop offset="100%" stopColor="var(--accent-cyan)" />
                            </linearGradient>
                        </defs>
                    </svg>
                    <div className="absolute bottom-0 w-full flex justify-between text-[8px] text-[var(--text-secondary)] uppercase px-1">
                        <span>Start</span>
                        <span>Bridge</span>
                        <span>Swap</span>
                        <span>Dest</span>
                    </div>
                </div>

                {/* Savings Tag */}
                <div className="absolute bottom-4 right-4 translate-y-[150%] group-hover:translate-y-0 transition-transform duration-300">
                    <div className="bg-[var(--accent-cyan)] text-black font-bold font-mono px-3 py-1 rounded-lg text-sm shadow-[0_0_15px_var(--accent-cyan)]">
                        SAVINGS: ${cappRoute ? (standardFee - cappRoute.fee_usd).toFixed(2) : "4.40"}
                    </div>
                </div>

            </div>

        </div>
    );
}
