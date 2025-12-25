
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowRightLeft, CheckCircle, Clock } from 'lucide-react';
import { api } from '@/services/api';
import Portal from './Portal';

interface BridgeModalProps {
    isOpen: boolean;
    onClose: () => void;
    address: string;
}

export default function BridgeModal({ isOpen, onClose, address }: BridgeModalProps) {
    const [mode, setMode] = useState<'DEPOSIT' | 'WITHDRAW'>('DEPOSIT');
    const [amount, setAmount] = useState('');
    const [status, setStatus] = useState<string | null>(null);
    const [exitId, setExitId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async () => {
        try {
            setError(null);
            setStatus('PROCESSING');

            if (mode === 'DEPOSIT') {
                const res = await api.bridgeDeposit(Number(amount), address);
                setStatus(`Deposited! L2 Mint: ${res.child_tx.slice(0, 10)}...`);
            } else {
                const res = await api.bridgeWithdraw(Number(amount), address);
                setStatus(`Exit Started! ETA: ${new Date(res.estimated_completion).toLocaleTimeString()}`);
                setExitId(res.exit_id);
            }
        } catch (e: any) {
            setError(e.message);
            setStatus(null);
        }
    };

    const handleFinalize = async () => {
        if (!exitId) return;
        try {
            setError(null);
            setStatus('FINALIZING...');
            const res = await api.finalizeExit(exitId);
            setStatus(`Finalized! Funds Released on L1.`);
            setExitId(null);
        } catch (e: any) {
            setError(e.message);
            setStatus('WAITING_CHALLENGE_PERIOD');
        }
    };

    return (
        <Portal>
            <AnimatePresence>
                {isOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={onClose}
                            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 transition-all"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none p-4"
                        >
                            <div className="bg-bg-secondary w-full max-w-md rounded-2xl border border-border-subtle shadow-2xl overflow-hidden pointer-events-auto">
                                {/* Header */}
                                <div className="p-6 border-b border-border-subtle flex justify-between items-center bg-bg-tertiary/50">
                                    <div>
                                        <h2 className="text-xl font-display font-bold">Plasma Bridge</h2>
                                        <p className="text-xs text-text-tertiary mt-1 uppercase tracking-widest">L1 (Aptos) ↔ L2 (Polygon)</p>
                                    </div>
                                    <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                                        <X className="w-5 h-5 text-text-tertiary" />
                                    </button>
                                </div>

                                {/* Tabs */}
                                <div className="flex border-b border-border-subtle">
                                    <button
                                        onClick={() => setMode('DEPOSIT')}
                                        className={`flex-1 py-4 text-sm font-medium uppercase tracking-wider transition-colors border-b-2 ${mode === 'DEPOSIT'
                                            ? 'border-accent-primary text-text-primary bg-accent-primary/5'
                                            : 'border-transparent text-text-tertiary hover:text-text-secondary'
                                            }`}
                                    >
                                        Deposit (L1 → L2)
                                    </button>
                                    <button
                                        onClick={() => setMode('WITHDRAW')}
                                        className={`flex-1 py-4 text-sm font-medium uppercase tracking-wider transition-colors border-b-2 ${mode === 'WITHDRAW'
                                            ? 'border-accent-primary text-text-primary bg-accent-primary/5'
                                            : 'border-transparent text-text-tertiary hover:text-text-secondary'
                                            }`}
                                    >
                                        Withdraw (L2 → L1)
                                    </button>
                                </div>

                                {/* Content */}
                                <div className="p-6 space-y-6">

                                    {status ? (
                                        <div className="text-center py-8">
                                            <div className="w-16 h-16 bg-accent-primary/10 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse">
                                                {status.includes('Finaliz') || status.includes('Deposit') ? <CheckCircle className="w-8 h-8 text-accent-primary" /> : <Clock className="w-8 h-8 text-accent-primary" />}
                                            </div>
                                            <h3 className="text-lg font-bold mb-2">{status}</h3>

                                            {exitId && (
                                                <div className="mt-6">
                                                    <p className="text-sm text-text-secondary mb-4">
                                                        Plasma exits require a challenge period.
                                                    </p>
                                                    <button
                                                        onClick={handleFinalize}
                                                        className="px-6 py-2 bg-bg-tertiary border border-accent-primary text-accent-primary rounded-lg text-sm font-bold uppercase hover:bg-accent-primary hover:text-bg-primary transition-all"
                                                    >
                                                        Finalize Exit
                                                    </button>
                                                </div>
                                            )}

                                            {error && (
                                                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                                                    {error}
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <>
                                            <div>
                                                <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Amount (USDC)</label>
                                                <div className="relative">
                                                    <input
                                                        type="number"
                                                        value={amount}
                                                        onChange={(e) => setAmount(e.target.value)}
                                                        placeholder="0.00"
                                                        className="w-full bg-bg-tertiary border border-border-medium rounded-xl px-4 py-3 text-lg font-mono focus:outline-none focus:border-accent-primary transition-colors"
                                                    />
                                                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm font-bold text-text-tertiary">USDC</span>
                                                </div>
                                            </div>

                                            <button
                                                onClick={handleSubmit}
                                                disabled={!amount}
                                                className="w-full py-4 bg-gradient-to-r from-accent-primary to-accent-secondary rounded-xl text-bg-primary font-bold uppercase tracking-wider shadow-lg hover:shadow-accent-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                {mode === 'DEPOSIT' ? 'Deposit to Polygon' : 'Start Plasma Exit'}
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </Portal>
    );
}
