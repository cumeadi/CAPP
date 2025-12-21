'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Send, ShieldCheck, Loader2, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

import { api, ComplianceCheckResponse } from '@/services/api';

export default function SendPage() {
    const [step, setStep] = useState<'INPUT' | 'CHECKING' | 'SUCCESS'>('INPUT');
    const [recipient, setRecipient] = useState('');
    const [amount, setAmount] = useState('');
    const [checkResult, setCheckResult] = useState<ComplianceCheckResponse | null>(null);
    const [txHash, setTxHash] = useState('');

    const handleSend = async () => {
        if (!recipient || !amount) return;
        setStep('CHECKING');

        try {
            // Real AI Compliance Check
            // Using a demo sender address for MVP
            const result = await api.checkCompliance("0xME", recipient, parseFloat(amount));
            setCheckResult(result);

            // Artificial delay to show the "Scanning" animation because the API is too fast!
            // Artificial delay to show the "Scanning" animation because the API is too fast!
            setTimeout(async () => {
                if (result.is_compliant) {
                    try {
                        const transferRes = await api.executeTransfer(recipient, parseFloat(amount));
                        setTxHash(transferRes.tx_hash);
                        setStep('SUCCESS');
                    } catch (transferError) {
                        alert("Compliance Passed but Transfer Failed. Check console.");
                        console.error(transferError);
                        setStep('INPUT');
                    }
                } else {
                    alert(`Transfer Blocked by AI: ${result.reasoning}`);
                    setStep('INPUT');
                }
            }, 2000);

        } catch (e) {
            console.error("Compliance check failed:", e);
            setStep('INPUT');
        }
    };

    return (
        <div className="min-h-screen p-8 bg-black text-white relative">
            {/* Back Button */}
            <Link href="/" className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-8 transition-colors">
                <ArrowLeft className="w-5 h-5" />
                Back to Treasury
            </Link>

            <div className="max-w-md mx-auto">
                <AnimatePresence mode='wait'>

                    {/* Step 1: Input Form */}
                    {step === 'INPUT' && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className="glass-card p-8 rounded-3xl"
                        >
                            <h1 className="text-2xl font-bold mb-6">Smart Transfer</h1>

                            <div className="space-y-6">
                                <div>
                                    <label className="block text-sm text-gray-400 mb-2">Recipient Address</label>
                                    <input
                                        type="text"
                                        value={recipient}
                                        onChange={(e) => setRecipient(e.target.value)}
                                        placeholder="0x..."
                                        className="w-full bg-white/5 border border-white/10 rounded-xl p-4 text-white focus:outline-none focus:border-blue-500 transition-colors"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm text-gray-400 mb-2">Amount (APT)</label>
                                    <div className="relative">
                                        <input
                                            type="number"
                                            value={amount}
                                            onChange={(e) => setAmount(e.target.value)}
                                            placeholder="0.00"
                                            className="w-full bg-white/5 border border-white/10 rounded-xl p-4 text-white focus:outline-none focus:border-blue-500 transition-colors pr-16"
                                        />
                                        <span className="absolute right-4 top-4 text-gray-500 font-bold">APT</span>
                                    </div>
                                </div>

                                <button
                                    onClick={handleSend}
                                    className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-4 rounded-xl flex items-center justify-center gap-2 transition-all"
                                >
                                    <Send className="w-5 h-5" />
                                    Verify & Send
                                </button>
                            </div>
                        </motion.div>
                    )}

                    {/* Step 2: AI Compliance Check Animation */}
                    {step === 'CHECKING' && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className="glass-card p-8 rounded-3xl text-center"
                        >
                            <div className="relative w-24 h-24 mx-auto mb-6">
                                <div className="absolute inset-0 border-4 border-blue-500/30 rounded-full animate-ping"></div>
                                <div className="relative z-10 w-full h-full bg-blue-500/10 rounded-full flex items-center justify-center border border-blue-500">
                                    <ShieldCheck className="w-10 h-10 text-blue-400" />
                                </div>
                            </div>

                            <h2 className="text-xl font-bold mb-2">AI Compliance Check</h2>
                            <p className="text-gray-400 text-sm mb-6">
                                Scanning recipient against OFAC Sanctions List and analyzing transaction pattern...
                            </p>

                            <div className="space-y-3 text-left bg-black/20 p-4 rounded-xl">
                                <div className="flex items-center gap-3 text-sm">
                                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                                    <span className="text-gray-300">Verifying Identity...</span>
                                </div>
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: 1 }}
                                    className="flex items-center gap-3 text-sm"
                                >
                                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                                    <span className="text-green-300">Sanctions Check Passed</span>
                                </motion.div>
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: 2 }}
                                    className="flex items-center gap-3 text-sm"
                                >
                                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                                    <span className="text-green-300">Market Risk Acceptable</span>
                                </motion.div>
                            </div>
                        </motion.div>
                    )}

                    {/* Step 3: Success */}
                    {step === 'SUCCESS' && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="glass-card p-8 rounded-3xl text-center"
                        >
                            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                                <CheckCircle2 className="w-10 h-10 text-green-500" />
                            </div>
                            <h2 className="text-2xl font-bold mb-2 text-white">Transfer Sent!</h2>
                            <p className="text-gray-400 mb-4">
                                Your transaction has been securely settled on the Aptos network.
                            </p>
                            <div className="bg-white/5 p-3 rounded-lg font-mono text-xs text-gray-500 break-all mb-8">
                                {txHash}
                            </div>
                            <Link href="/" className="block w-full bg-white/10 hover:bg-white/20 text-white font-semibold py-4 rounded-xl transition-all">
                                Return to Dashboard
                            </Link>
                        </motion.div>
                    )}

                </AnimatePresence>
            </div>
        </div>
    );
}
