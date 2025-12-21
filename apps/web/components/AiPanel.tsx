'use client';

import { motion } from 'framer-motion';
import { Bot, CheckCircle, AlertTriangle, Activity, RefreshCw, Radar, ShieldCheck } from 'lucide-react';

interface AiPanelProps {
    marketStatus: {
        sentiment: string;
        volatility: string;
        reasoning: string;
    };
}

export default function AiPanel({ marketStatus }: AiPanelProps) {
    return (
        <div className="flex flex-col gap-6">
            {/* AI Decision Feed */}
            <div className="treasury-card p-6 h-[600px] flex flex-col">
                <div className="flex items-center gap-3 mb-6 pb-4 border-b border-border-subtle">
                    <div className="w-8 h-8 flex items-center justify-center rounded-lg bg-bg-tertiary border border-border-medium text-xl">
                        🤖
                    </div>
                    <div className="font-display text-sm font-semibold uppercase tracking-widest">
                        AI Decision Feed
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto space-y-6 pr-2 custom-scrollbar">
                    {/* Item 1: Auto-Rebalance */}
                    <div className="pl-4 border-l-2 border-color-success relative">
                        <div className="flex justify-between items-start mb-1">
                            <div className="text-[10px] font-bold uppercase tracking-widest text-color-success">Auto-Rebalance Executed</div>
                            <div className="text-[10px] text-text-tertiary">2 mins ago</div>
                        </div>
                        <div className="text-xs text-text-secondary leading-relaxed mb-2">
                            Swapped 400 APT to 4,200 USDC to preserve capital during detected volatility spike.
                        </div>
                        <div className="flex gap-4 text-[10px] text-text-tertiary">
                            <div className="flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-color-success"></span>
                                Executed in 1.2s
                            </div>
                            <div className="flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" />
                                Confirmed
                            </div>
                        </div>
                    </div>

                    {/* Item 2: Market Analysis */}
                    <div className="pl-4 border-l-2 border-color-info relative">
                        <div className="flex justify-between items-start mb-1">
                            <div className="text-[10px] font-bold uppercase tracking-widest text-color-info">Market Analysis: High Volatility</div>
                            <div className="text-[10px] text-text-tertiary">15 mins ago</div>
                        </div>
                        <div className="text-xs text-text-secondary leading-relaxed mb-2">
                            APT/USD deviation {'>'} 5%. Signal: WAIT for settlement. Monitoring 5-min intervals.
                        </div>
                        <div className="flex gap-4 text-[10px] text-text-tertiary">
                            <div className="flex items-center gap-1">
                                <Activity className="w-3 h-3" />
                                Volatility: 8.2%
                            </div>
                        </div>
                    </div>

                    {/* Item 3: Approved */}
                    <div className="pl-4 border-l-2 border-accent-primary relative">
                        <div className="flex justify-between items-start mb-1">
                            <div className="text-[10px] font-bold uppercase tracking-widest text-accent-primary">Transaction Approved</div>
                            <div className="text-[10px] text-text-tertiary">1 hr ago</div>
                        </div>
                        <div className="text-xs text-text-secondary leading-relaxed mb-2">
                            Payment #8821 verified against OFAC Sanctions List. Risk Score: 0/100.
                        </div>
                        <div className="flex gap-4 text-[10px] text-text-tertiary">
                            <div className="flex items-center gap-1">
                                <ShieldCheck className="w-3 h-3" />
                                Risk: None
                            </div>
                            <div className="flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" />
                                Approved
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Yield Radar */}
            <div className="treasury-card p-6">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-2">
                        <Radar className="w-5 h-5 text-text-secondary" />
                        <span className="font-display text-xs font-semibold uppercase tracking-widest">AI Yield Radar</span>
                    </div>
                    <span className="px-2 py-1 bg-accent-warning/10 border border-accent-warning/30 rounded-full text-[10px] font-bold uppercase tracking-widest text-accent-warning flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-warning"></span>
                        Wait
                    </span>
                </div>

                <div className="text-center">
                    <div className="text-[10px] text-text-tertiary uppercase tracking-widest mb-4">24h Alpha Prediction</div>

                    {/* Radar Visual */}
                    <div className="w-32 h-32 mx-auto mb-6 relative flex items-center justify-center rounded-full bg-gradient-conic from-accent-primary via-bg-tertiary to-accent-primary animate-[spin_4s_linear_infinite]">
                        <div className="absolute inset-[2px] bg-bg-secondary rounded-full flex items-center justify-center z-10">
                            <div className="font-display text-3xl font-bold text-white">45%</div>
                        </div>
                    </div>

                    <div className="bg-bg-tertiary rounded-lg p-3 flex justify-between items-center mb-4">
                        <span className="text-[10px] text-text-tertiary uppercase tracking-widest">Confidence Score</span>
                        <span className="text-xs font-bold text-accent-primary">SIGNAL</span>
                    </div>

                    <div className="p-3 bg-color-info/5 border border-color-info/20 rounded-lg text-xs italic text-color-info">
                        "{marketStatus.reasoning || "High volatility detected. Recommended to wait for stabilization."}"
                    </div>
                </div>
            </div>
        </div>
    );
}
