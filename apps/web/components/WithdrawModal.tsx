'use client';

import { X, ArrowRight, Loader2, Check } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/services/api';
import Portal from './Portal';

interface WithdrawModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function WithdrawModal({ isOpen, onClose }: WithdrawModalProps) {
    const [step, setStep] = useState<'INPUT' | 'PROCESSING' | 'SUCCESS'>('INPUT');
    const [recipient, setRecipient] = useState('');
    const [amount, setAmount] = useState('');
    const [txHash, setTxHash] = useState('');

    const handleWithdraw = async () => {
        if (!recipient || !amount) return;
        setStep('PROCESSING');

        try {
            // Execute Transfer
            const result = await api.executeTransfer(recipient, parseFloat(amount));
            setTxHash(result.tx_hash);
            setStep('SUCCESS');
        } catch (e) {
            console.error(e);
            setStep('INPUT'); // Reset on failure for now
            alert("Withdrawal failed. Check console.");
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
                            <div className="w-full max-w-md bg-bg-card border border-border-medium rounded-2xl p-6 shadow-2xl pointer-events-auto">
                                <div className="flex justify-between items-center mb-6">
                                    <h3 className="font-display text-lg font-semibold uppercase tracking-wider text-text-primary">Withdraw Funds</h3>
                                    <button onClick={onClose} className="p-2 hover:bg-bg-tertiary rounded-full transition-colors">
                                        <X className="w-5 h-5 text-text-secondary" />
                                    </button>
                                </div>

                                {step === 'INPUT' && (
                                    <div className="space-y-6">
                                        <div>
                                            <label className="text-xs text-text-tertiary uppercase tracking-widest mb-2 block">Recipient Address</label>
                                            <input
                                                type="text"
                                                value={recipient}
                                                onChange={(e) => setRecipient(e.target.value)}
                                                className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 font-mono text-sm text-text-primary focus:border-accent-primary focus:outline-none transition-colors"
                                                placeholder="0x..."
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-text-tertiary uppercase tracking-widest mb-2 block">Amount (APT)</label>
                                            <input
                                                type="number"
                                                value={amount}
                                                onChange={(e) => setAmount(e.target.value)}
                                                className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 font-mono text-sm text-text-primary focus:border-accent-primary focus:outline-none transition-colors"
                                                placeholder="0.00"
                                            />
                                        </div>

                                        <button
                                            onClick={handleWithdraw}
                                            className="w-full py-4 bg-accent-primary text-bg-primary rounded-xl font-bold uppercase tracking-wide hover:bg-white transition-all shadow-lg shadow-accent-primary/20 flex items-center justify-center gap-2"
                                        >
                                            Confirm Withdrawal
                                            <ArrowRight className="w-4 h-4" />
                                        </button>
                                    </div>
                                )}

                                {step === 'PROCESSING' && (
                                    <div className="py-12 flex flex-col items-center">
                                        <Loader2 className="w-12 h-12 text-accent-primary animate-spin mb-4" />
                                        <div className="text-lg font-display font-medium text-text-primary">Processing Transaction</div>
                                        <div className="text-sm text-text-tertiary mt-2">Signing interacting with Aptos...</div>
                                    </div>
                                )}

                                {step === 'SUCCESS' && (
                                    <div className="py-8 flex flex-col items-center text-center">
                                        <div className="w-16 h-16 bg-color-success/20 rounded-full flex items-center justify-center mb-6">
                                            <Check className="w-8 h-8 text-color-success" />
                                        </div>
                                        <h4 className="text-xl font-display font-bold text-white mb-2">Withdrawal Sent!</h4>
                                        <p className="text-sm text-text-secondary mb-6 max-w-xs">
                                            Your funds have been securely transferred to the destination wallet.
                                        </p>
                                        <div className="bg-bg-tertiary p-3 rounded-lg font-mono text-xs text-text-tertiary break-all mb-6">
                                            {txHash}
                                        </div>
                                        <button onClick={onClose} className="px-8 py-3 bg-bg-tertiary hover:bg-bg-secondary text-text-primary rounded-xl font-medium transition-colors">
                                            Close
                                        </button>
                                    </div>
                                )}

                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </Portal>
    );
}
