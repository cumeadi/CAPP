'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, CheckCircle, AlertTriangle, Activity, RefreshCw, Radar, ShieldCheck, Wallet, XCircle } from 'lucide-react';
import { useSignMessage } from 'wagmi';

interface AiPanelProps {
    marketStatus: {
        sentiment: string;
        volatility: string;
        reasoning: string;
        top_apy?: number;
        active_protocols?: string[];
    };
    decisionFeed: Array<{
        id: string | number;
        type: 'REBALANCE' | 'ANALYSIS' | 'APPROVAL' | 'USER' | 'PAYMENT' | 'ERROR' | 'OPPORTUNITY';
        title: string;
        description: string;
        time: string;
        meta?: {
            label: string;
            value: string;
        };
    }>;
    onChat: (query: string) => void;
    onApprove?: (id: string | number) => void;
    onReject?: (id: string | number) => void;
}

export default function AiPanel({ marketStatus, decisionFeed, onChat, onApprove, onReject }: AiPanelProps) {
    // Helper to determine radar color based on risk
    const getRadarColor = () => {
        if (marketStatus.volatility === 'HIGH') return 'text-accent-warning';
        if (marketStatus.volatility === 'LOW') return 'text-color-success';
        return 'text-accent-primary';
    };

    const getRadarScore = () => {
        if (marketStatus.top_apy) return `${marketStatus.top_apy.toFixed(1)}%`;
        if (marketStatus.volatility === 'HIGH') return '15%'; // Fallback
        return '45%';
    };

    const [signingIds, setSigningIds] = useState<Set<string | number>>(new Set());
    const { signMessageAsync } = useSignMessage();

    const handleApprove = async (id: string | number) => {
        setSigningIds(prev => new Set(prev).add(id));
        try {
            // 1. Sign off on the intent
            // In a real app, we'd sign a typed data payload (EIP-712)
            const signature = await signMessageAsync({
                message: `Approve Request: ${id}`
            });

            // 2. Send signature to backend
            await import('../services/api').then(m => m.api.approveRequest(String(id), signature));

            // 3. Optimistic Update (Backend will log activity)
            onApprove?.(id);
        } catch (e) {
            console.error("Signing failed or rejected", e);
        } finally {
            setSigningIds(prev => {
                const n = new Set(prev);
                n.delete(id);
                return n;
            });
        }
    };

    const handleYieldScan = async () => {
        try {
            await import('../services/api').then(m => m.api.scoutOpportunities());
        } catch (e) {
            console.error("Scan failed", e);
        }
    };

    return (
        <div className="flex flex-col gap-6">
            {/* AI Decision Feed */}
            <div className="treasury-card p-4 md:p-6 h-auto min-h-[500px] md:h-[600px] flex flex-col">
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
                        <div key={item.id} className={`pl-4 border-l-2 relative ${item.type === 'APPROVAL' ? 'border-accent-primary bg-accent-primary/5 p-4 rounded-r-xl border-l-4' :
                            item.type === 'OPPORTUNITY' ? 'border-color-success bg-color-success/5 p-4 rounded-r-xl border-l-4' :
                                item.type === 'REBALANCE' ? 'border-color-success' :
                                    item.type === 'ANALYSIS' ? 'border-color-info' :
                                        item.type === 'PAYMENT' ? 'border-accent-secondary' :
                                            item.type === 'ERROR' ? 'border-accent-warning' :
                                                'border-accent-primary'
                            }`}>

                            {/* Special Layout for Permission Cards & Opportunities */}
                            {item.type === 'APPROVAL' || item.type === 'OPPORTUNITY' ? (
                                <div>
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="flex items-center gap-2">
                                            {item.type === 'OPPORTUNITY' ? (
                                                <Activity className="w-4 h-4 text-color-success animate-pulse" />
                                            ) : (
                                                <ShieldCheck className="w-4 h-4 text-accent-primary animate-pulse" />
                                            )}
                                            <div className={`text-xs font-bold uppercase tracking-widest ${item.type === 'OPPORTUNITY' ? 'text-color-success' : 'text-accent-primary'}`}>
                                                {item.type === 'OPPORTUNITY' ? 'Opportunity Found' : 'Permission Required'}
                                            </div>
                                        </div>
                                        <div className="text-[10px] text-text-tertiary">{item.time}</div>
                                    </div>
                                    <div className="text-sm font-semibold text-text-primary mb-1">{item.title}</div>
                                    <div className="text-xs text-text-secondary leading-relaxed mb-4">
                                        {item.description}
                                    </div>

                                    {signingIds.has(item.id) ? (
                                        <SigningAnimation type={item.type === 'OPPORTUNITY' ? 'opportunity' : 'approval'} />
                                    ) : (
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => handleApprove(item.id)}
                                                className={`flex-1 ${item.type === 'OPPORTUNITY' ? 'bg-color-success hover:bg-color-success/90' : 'bg-accent-primary hover:bg-opacity-90'} text-bg-primary text-xs font-bold uppercase py-2 rounded transition-all`}
                                            >
                                                {item.type === 'OPPORTUNITY' ? 'Execute Strategy' : 'Approve'}
                                            </button>
                                            <button
                                                onClick={() => onReject?.(item.id)}
                                                className="flex-1 bg-bg-tertiary border border-border-medium text-text-secondary text-xs font-bold uppercase py-2 rounded hover:text-text-primary hover:border-text-tertiary transition-all"
                                            >
                                                Dismiss
                                            </button>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                /* Standard Feed Item */
                                <>
                                    <div className="flex justify-between items-start mb-1">
                                        <div className="flex items-center gap-2">
                                            {/* Icon Indicator */}
                                            {item.type === 'PAYMENT' && <Wallet className="w-3 h-3 text-accent-secondary" />}
                                            {item.type === 'ERROR' && <XCircle className="w-3 h-3 text-accent-warning" />}

                                            <div className={`text-[10px] font-bold uppercase tracking-widest ${item.type === 'REBALANCE' ? 'text-color-success' :
                                                item.type === 'ANALYSIS' ? 'text-color-info' :
                                                    item.type === 'PAYMENT' ? 'text-accent-secondary' :
                                                        item.type === 'ERROR' ? 'text-accent-warning' :
                                                            'text-accent-primary'
                                                }`}>{item.title}</div>
                                        </div>
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
                                </>
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
                            onClick={handleYieldScan}
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

            {/* Active Yield Radar */}
            <div className="treasury-card p-4 md:p-6 flex flex-col h-auto min-h-[500px] md:h-[600px]">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-2">
                        <Radar className="w-5 h-5 text-text-secondary" />
                        <span className="font-display text-xs font-semibold uppercase tracking-widest">Live Market Scanner</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-primary opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-primary"></span>
                        </span>
                        <span className="text-[10px] font-bold uppercase tracking-widest text-accent-primary">Live</span>
                    </div>
                </div>

                <div className="flex-1 flex flex-col items-center justify-center relative mb-6">
                    <RadarVisual volatility={marketStatus.volatility} />

                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <span className="text-[10px] text-text-tertiary uppercase tracking-widest mb-1">Max Projected APY</span>
                        <span className={`font-display text-4xl font-bold ${getRadarColor()} drop-shadow-lg`}>
                            {getRadarScore()}
                        </span>
                    </div>
                </div>

                <div className="space-y-4">
                    {/* Active Protocols */}
                    <div>
                        <div className="text-[10px] text-text-tertiary uppercase tracking-widest mb-3 flex justify-between">
                            <span>Scanning Protocols</span>
                            <span className="text-accent-primary animate-pulse">{marketStatus.active_protocols?.length || 0} Active</span>
                        </div>
                        <div className="space-y-2">
                            {(marketStatus.active_protocols || ['Scanning...']).map((p, i) => (
                                <div key={i} className="flex items-center justify-between p-2 rounded bg-bg-tertiary/50 border border-border-subtle">
                                    <span className="text-xs font-medium text-text-secondary">{p}</span>
                                    <Activity className="w-3 h-3 text-text-tertiary opacity-50" />
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Volatility Meter */}
                    <div className="p-4 bg-bg-tertiary rounded-xl border border-border-medium">
                        <div className="flex justify-between items-end mb-2">
                            <span className="text-[10px] text-text-tertiary uppercase tracking-widest">Market Volatility</span>
                            <span className={`text-xs font-bold ${getRadarColor()}`}>{marketStatus.volatility}</span>
                        </div>
                        <div className="flex gap-1 h-2">
                            {['LOW', 'MEDIUM', 'HIGH'].map((level, i) => {
                                const isActive =
                                    (marketStatus.volatility === 'LOW' && i === 0) ||
                                    (marketStatus.volatility === 'MEDIUM' && i <= 1) ||
                                    (marketStatus.volatility === 'HIGH');

                                const barColor = i === 0 ? 'bg-color-success' : i === 1 ? 'bg-accent-secondary' : 'bg-accent-warning';

                                return (
                                    <div key={level} className={`flex-1 rounded-full transition-all duration-500 ${isActive ? barColor : 'bg-bg-primary opacity-30'}`} />
                                );
                            })}
                        </div>
                        <div className="mt-3 text-[10px] text-text-secondary leading-relaxed border-t border-border-subtle pt-2">
                            {marketStatus.reasoning}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function SigningAnimation({ type }: { type: 'approval' | 'opportunity' }) {
    const color = type === 'opportunity' ? 'text-color-success' : 'text-accent-primary';
    const bgColor = type === 'opportunity' ? 'bg-color-success' : 'bg-accent-primary';

    return (
        <div className="h-9 relative overflow-hidden rounded bg-bg-tertiary border border-border-medium flex items-center justify-center">
            {/* Animated Scan Line */}
            <motion.div
                className={`absolute top-0 bottom-0 w-1 ${bgColor} shadow-[0_0_15px_rgba(255,255,255,0.8)] z-10`}
                animate={{ left: ['0%', '100%', '0%'] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
            />

            {/* Fingerprint / Text */}
            <div className="flex items-center gap-2 z-0 opacity-80">
                <span className={`text-xs font-bold uppercase tracking-widest ${color} animate-pulse`}>
                    Verifying Signature...
                </span>
            </div>
        </div>
    );
}

function RadarVisual({ volatility }: { volatility: string }) {
    const color = volatility === 'HIGH' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(16, 185, 129, 0.5)';
    const scanColor = volatility === 'HIGH' ? 'from-red-500/50' : 'from-emerald-500/50';

    return (
        <div className="w-48 h-48 relative flex items-center justify-center">
            {/* Grid Rings */}
            {[1, 2, 3].map(i => (
                <div key={i} className={`absolute border border-border-subtle rounded-full opacity-30`}
                    style={{ width: `${i * 33}%`, height: `${i * 33}%` }} />
            ))}

            {/* Crosshairs */}
            <div className="absolute w-full h-[1px] bg-border-subtle opacity-20" />
            <div className="absolute h-full w-[1px] bg-border-subtle opacity-20" />

            {/* Scanning Sector */}
            <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                className={`absolute w-full h-full rounded-full bg-gradient-conic ${scanColor} via-transparent to-transparent opacity-20`}
                style={{ maskImage: 'radial-gradient(circle, transparent 30%, black 100%)' }}
            />

            {/* Decorative Blips */}
            <motion.div
                className={`absolute top-1/4 left-1/4 w-2 h-2 rounded-full ${volatility === 'HIGH' ? 'bg-red-500' : 'bg-emerald-500'} shadow-lg shadow-current`}
                animate={{ opacity: [0, 1, 0] }}
                transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
            />
            <motion.div
                className={`absolute bottom-1/3 right-1/4 w-1.5 h-1.5 rounded-full ${volatility === 'HIGH' ? 'bg-red-500' : 'bg-emerald-500'} shadow-lg shadow-current`}
                animate={{ opacity: [0, 1, 0] }}
                transition={{ duration: 3, repeat: Infinity, delay: 1.5 }}
            />
        </div>
    );
}
