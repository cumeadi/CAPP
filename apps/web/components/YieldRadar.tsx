'use client';

import { motion } from 'framer-motion';
import { Radar, ArrowUpRight, TrendingUp } from 'lucide-react';

interface YieldRadarProps {
    prediction: {
        symbol: string;
        risk_level: string;
        recommendation: string;
        reasoning: string;
    };
}

export default function YieldRadar({ prediction }: YieldRadarProps) {
    const isBullish = prediction.recommendation === 'BUY' || prediction.recommendation === 'HOLD';
    const confidence = isBullish ? 85 : 45; // Mock confidence based on rec

    return (
        <div className="glass-card p-6 rounded-3xl relative overflow-hidden">
            {/* Background Animation */}
            <div className="absolute -top-10 -right-10 w-40 h-40 bg-purple-500/20 rounded-full blur-3xl animate-pulse"></div>

            <div className="relative z-10">
                <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-500/10 rounded-lg border border-purple-500/20">
                            <Radar className="w-6 h-6 text-purple-400" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-gray-100">AI Yield Radar</h3>
                            <p className="text-xs text-purple-300">24h Alpha Prediction</p>
                        </div>
                    </div>
                    <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-gray-300">
                        {prediction.symbol}
                    </div>
                </div>

                <div className="flex items-end gap-4 mb-4">
                    <div className="flex-1">
                        <div className="text-4xl font-bold text-white mb-1 flex items-center gap-2">
                            {confidence}%
                            <TrendingUp className={`w-6 h-6 ${isBullish ? 'text-green-400' : 'text-red-400'}`} />
                        </div>
                        <p className="text-sm text-gray-400">Confidence Score</p>
                    </div>
                    <div className="text-right">
                        <div className={`text-lg font-bold ${isBullish ? 'text-green-400' : 'text-red-400'}`}>
                            {prediction.recommendation}
                        </div>
                        <p className="text-xs text-gray-500 uppercase tracking-wider">Signal</p>
                    </div>
                </div>

                {/* Signal Detail */}
                <div className="p-3 bg-black/20 rounded-xl border border-white/5 text-sm text-gray-300 italic">
                    "{prediction.reasoning}"
                </div>
            </div>
        </div>
    );
}
