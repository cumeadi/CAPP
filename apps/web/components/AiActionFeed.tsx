'use client';

import { motion } from 'framer-motion';
import { Activity, ShieldCheck, ArrowRightLeft, AlertTriangle } from 'lucide-react';

interface FeedItem {
    id: number;
    type: 'MARKET' | 'COMPLIANCE' | 'LIQUIDITY';
    message: string;
    detail: string;
    timestamp: string;
}

const FEED_DATA: FeedItem[] = [
    {
        id: 1,
        type: 'LIQUIDITY',
        message: 'Auto-Rebalance Executed',
        detail: 'Swapped 400 APT to 4,200 USDC to preserve capital during detected volatility spike.',
        timestamp: '2 mins ago'
    },
    {
        id: 2,
        type: 'MARKET',
        message: 'Market Analysis: High Volatility',
        detail: 'APT/USD deviation > 5%. Signal: WAIT for settlement.',
        timestamp: '15 mins ago'
    },
    {
        id: 3,
        type: 'COMPLIANCE',
        message: 'Transaction Approved',
        detail: 'Payment #8821 verified against OFAC Sanctions List. Risk Score: 0/100.',
        timestamp: '1 hr ago'
    }
];

export default function AiActionFeed() {
    return (
        <div className="lg:col-span-3 p-8 rounded-3xl glass-card">
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                    <Activity className="w-5 h-5 text-blue-400" />
                </div>
                <h2 className="text-lg font-semibold">AI Decision Feed</h2>
            </div>

            <div className="space-y-4">
                {FEED_DATA.map((item, i) => (
                    <motion.div
                        key={item.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="flex gap-4 items-start p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors group"
                    >
                        <div className={`mt-1 w-2 h-2 rounded-full shrink-0 ${item.type === 'MARKET' ? 'bg-red-500' :
                                item.type === 'COMPLIANCE' ? 'bg-green-500' : 'bg-blue-500'
                            }`} />

                        <div className="flex-1">
                            <div className="flex justify-between items-center mb-1">
                                <span className={`font-medium ${item.type === 'MARKET' ? 'text-red-200' :
                                        item.type === 'COMPLIANCE' ? 'text-green-200' : 'text-blue-200'
                                    }`}>
                                    {item.message}
                                </span>
                                <span className="text-xs text-gray-500">{item.timestamp}</span>
                            </div>
                            <p className="text-sm text-gray-400 group-hover:text-gray-300 transition-colors">
                                {item.detail}
                            </p>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}
