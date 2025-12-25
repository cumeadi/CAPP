'use client';

import { motion } from 'framer-motion';
import { Bot, CheckCircle, AlertTriangle, Activity, RefreshCw, Radar, ShieldCheck } from 'lucide-react';

interface AiPanelProps {
    marketStatus: {
        sentiment: string;
        volatility: string;
        reasoning: string;
    };
    decisionFeed: Array<{
        id: number;
        type: 'REBALANCE' | 'ANALYSIS' | 'APPROVAL' | 'USER';
        title: string;
        description: string;
        time: string;
        meta?: {
            label: string;
            value: string;
        };
    }>;
    onChat: (query: string) => void;
}

export default function AiPanel({ marketStatus, decisionFeed, onChat }: AiPanelProps) {
    // Helper to determine radar color based on risk
    const getRadarColor = () => {
        if (marketStatus.volatility === 'HIGH') return 'text-accent-warning';
        if (marketStatus.volatility === 'LOW') return 'text-color-success';
        return 'text-accent-primary';
    };

    const getRadarScore = () => {
        if (marketStatus.volatility === 'HIGH') return '15%'; // Low confidence/safe mode
        if (marketStatus.volatility === 'LOW') return '85%'; // High confidence
        return '45%';
    };

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

                <div className="flex-1 overflow-y-auto space-y-6 pr-2 custom-scrollbar relative">
                    {decisionFeed.map((item) => (
                        <div key={item.id} className={`pl-4 border-l-2 relative ${item.type === 'REBALANCE' ? 'border-color-success' :
                            item.type === 'ANALYSIS' ? 'border-color-info' : 'border-accent-primary'
                            }`}>
                            <div className="flex justify-between items-start mb-1">
                                <div className={`text-[10px] font-bold uppercase tracking-widest ${item.type === 'REBALANCE' ? 'text-color-success' :
                                    item.type === 'ANALYSIS' ? 'text-color-info' : 'text-accent-primary'
                                    }`}>{item.title}</div>
                                <div className="text-[10px] text-text-tertiary">{item.time}</div>
                            </div>
                            <div className="text-xs text-text-secondary leading-relaxed mb-2">
                                {item.description}
                            </div>
                            {item.meta && (
                                <div className="flex gap-4 text-[10px] text-text-tertiary">
                                    <div className="flex items-center gap-1">
                                        <Activity className="w-3 h-3" />
                                        {item.meta.label}: {item.meta.value}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}

                </div>

                {/* AI Actions Footer */}
                <div className="mt-auto pt-4 border-t border-border-subtle bg-bg-secondary z-10">
                    <div className="grid grid-cols-2 gap-2">
                        <button
                            onClick={() => onChat("Analyze current portfolio risks and suggest hedging actions")}
                            className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-bg-tertiary hover:bg-bg-card border border-border-medium hover:border-accent-primary transition-all text-xs font-medium text-text-secondary hover:text-text-primary group"
                        >
                            <ShieldCheck className="w-3.5 h-3.5 text-accent-warning group-hover:scale-110 transition-transform" />
                            Risk Check
                        </button>

                        <button
                            onClick={() => onChat("Forecast yield opportunities for the next 24 hours")}
                            className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-bg-tertiary hover:bg-bg-card border border-border-medium hover:border-accent-primary transition-all text-xs font-medium text-text-secondary hover:text-text-primary group"
                        >
                            <Radar className="w-3.5 h-3.5 text-color-info group-hover:scale-110 transition-transform" />
                            Yield Scan
                        </button>

                        <button
                            onClick={() => onChat("Optimize current holdings for maximum stability")}
                            className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-bg-tertiary hover:bg-bg-card border border-border-medium hover:border-accent-primary transition-all text-xs font-medium text-text-secondary hover:text-text-primary group col-span-2"
                        >
                            <Bot className="w-3.5 h-3.5 text-accent-primary group-hover:scale-110 transition-transform" />
                            Optimize Holdings
                        </button>
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
                            <div className={`font-display text-3xl font-bold ${getRadarColor()}`}>{getRadarScore()}</div>
                        </div>
                    </div>

                    <div className="bg-bg-tertiary rounded-lg p-3 flex justify-between items-center mb-4">
                        <span className="text-[10px] text-text-tertiary uppercase tracking-widest">Confidence Score</span>
                        <span className={`text-xs font-bold ${getRadarColor()}`}>{marketStatus.volatility === 'HIGH' ? 'LOW' : 'HIGH'}</span>
                    </div>

                    <div className="p-3 bg-color-info/5 border border-color-info/20 rounded-lg text-xs italic text-color-info">
                        "{marketStatus.reasoning || "High volatility detected. Recommended to wait for stabilization."}"
                    </div>
                </div>
            </div>
        </div>
    );
}
