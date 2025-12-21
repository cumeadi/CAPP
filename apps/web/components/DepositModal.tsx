'use client';

import { X, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DepositModalProps {
    isOpen: boolean;
    onClose: () => void;
    address: string;
}

export default function DepositModal({ isOpen, onClose, address }: DepositModalProps) {
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(address);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-bg-primary/80 backdrop-blur-sm" onClick={onClose} />
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="relative w-full max-w-md bg-bg-card border border-border-medium rounded-2xl p-6 shadow-2xl overflow-hidden"
            >
                {/* Background Glow */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-accent-primary/10 rounded-full blur-3xl -z-10" />

                <div className="flex justify-between items-center mb-6">
                    <h3 className="font-display text-lg font-semibold uppercase tracking-wider text-text-primary">Deposit Assets</h3>
                    <button onClick={onClose} className="p-2 hover:bg-bg-tertiary rounded-full transition-colors">
                        <X className="w-5 h-5 text-text-secondary" />
                    </button>
                </div>

                <div className="flex flex-col items-center gap-6">
                    <div className="p-4 bg-white rounded-xl">
                        {/* Placeholder for QR Code */}
                        <div className="w-48 h-48 bg-gray-900 flex items-center justify-center text-xs text-gray-500 font-mono">
                            [QR CODE PLACEHOLDER]
                        </div>
                    </div>

                    <div className="w-full">
                        <label className="text-xs text-text-tertiary uppercase tracking-widest mb-2 block">
                            Treasury Address (Aptos Testnet)
                        </label>
                        <div className="flex gap-2">
                            <div className="flex-1 bg-bg-tertiary border border-border-medium rounded-xl p-3 font-mono text-sm text-text-secondary truncate">
                                {address}
                            </div>
                            <button
                                onClick={handleCopy}
                                className="p-3 bg-accent-primary/10 border border-accent-primary/30 rounded-xl hover:bg-accent-primary hover:text-bg-primary transition-all group"
                            >
                                {copied ? <Check className="w-5 h-5 text-color-success" /> : <Copy className="w-5 h-5 text-accent-primary group-hover:text-bg-primary" />}
                            </button>
                        </div>
                    </div>

                    <div className="p-3 bg-accent-warning/10 border border-accent-warning/20 rounded-xl text-center">
                        <p className="text-xs text-accent-warning">
                            Only send Aptos (APT) or supported assets on the Aptos Testnet network.
                        </p>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
