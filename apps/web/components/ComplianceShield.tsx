'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, ShieldAlert, CheckCircle, XCircle, AlertTriangle, ExternalLink } from 'lucide-react';
import { api, ComplianceCase } from '@/services/api';

export default function ComplianceShield() {
    const [cases, setCases] = useState<ComplianceCase[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedCase, setSelectedCase] = useState<string | null>(null);

    const fetchQueue = async () => {
        try {
            const data = await api.getComplianceQueue();
            setCases(data);
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchQueue();
        const interval = setInterval(fetchQueue, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    const handleDecision = async (caseId: string, decision: 'APPROVE' | 'REJECT') => {
        try {
            await api.reviewComplianceCase(caseId, decision);
            // Optimistic update
            setCases(prev => prev.filter(c => c.case_id !== caseId));
            setSelectedCase(null);
        } catch (e) {
            console.error("Decision failed", e);
            alert("Failed to submit decision");
        }
    };

    if (cases.length === 0) return null;

    return (
        <div className="fixed bottom-8 right-8 z-50">
            <motion.div
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-bg-secondary border border-accent-warning/30 rounded-xl shadow-2xl w-[400px] overflow-hidden backdrop-blur-md"
            >
                <div className="p-4 bg-accent-warning/10 border-b border-accent-warning/20 flex justify-between items-center">
                    <div className="flex items-center gap-2 text-accent-warning">
                        <ShieldAlert className="w-5 h-5 animate-pulse" />
                        <span className="font-display font-bold uppercase tracking-wider text-sm">Compliance Shield</span>
                    </div>
                    <span className="bg-accent-warning text-bg-primary text-xs font-bold px-2 py-0.5 rounded-full">
                        {cases.length} Review{cases.length > 1 ? 's' : ''}
                    </span>
                </div>

                <div className="max-h-[400px] overflow-y-auto p-4 space-y-3">
                    <AnimatePresence>
                        {cases.map((c) => (
                            <motion.div
                                key={c.case_id}
                                layout
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, x: 100 }}
                                className={`bg-bg-tertiary border ${selectedCase === c.case_id ? 'border-accent-warning' : 'border-border-subtle'} rounded-lg p-3 cursor-pointer hover:border-accent-warning/50 transition-colors`}
                                onClick={() => setSelectedCase(selectedCase === c.case_id ? null : c.case_id)}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <div>
                                        <div className="text-xs text-text-tertiary font-mono">{c.case_id}</div>
                                        <div className="font-bold text-text-primary">{c.currency} {c.amount.toLocaleString()}</div>
                                    </div>
                                    <div className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${c.risk_level === 'HIGH' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                                        }`}>
                                        {c.risk_level} Risk
                                    </div>
                                </div>

                                <div className="text-xs text-text-secondary mb-2 flex items-center gap-2">
                                    <span>{c.sender}</span>
                                    <span className="text-text-tertiary">→</span>
                                    <span>{c.recipient}</span>
                                </div>

                                <div className="flex flex-wrap gap-1 mb-3">
                                    {c.flags.map(flag => (
                                        <span key={flag} className="flex items-center gap-1 text-[10px] bg-bg-primary border border-border-medium px-1.5 py-0.5 rounded text-text-secondary">
                                            <AlertTriangle className="w-3 h-3" />
                                            {flag}
                                        </span>
                                    ))}
                                </div>

                                <AnimatePresence>
                                    {selectedCase === c.case_id && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: 'auto', opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            className="flex gap-2 pt-2 border-t border-border-subtle"
                                        >
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleDecision(c.case_id, 'REJECT'); }}
                                                className="flex-1 flex items-center justify-center gap-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 py-2 rounded text-xs font-bold uppercase transition-colors"
                                            >
                                                <XCircle className="w-4 h-4" /> Reject
                                            </button>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleDecision(c.case_id, 'APPROVE'); }}
                                                className="flex-1 flex items-center justify-center gap-1 bg-green-500/10 hover:bg-green-500/20 text-green-400 py-2 rounded text-xs font-bold uppercase transition-colors"
                                            >
                                                <CheckCircle className="w-4 h-4" /> Approve
                                            </button>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            </motion.div>
        </div>
    );
}
