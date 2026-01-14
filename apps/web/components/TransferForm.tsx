'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface TransferFormProps {
    onCancel: () => void;
    onSuccess: () => void;
}

export default function TransferForm({ onCancel, onSuccess }: TransferFormProps) {
    const [step, setStep] = useState<'DETAILS' | 'COMPLIANCE' | 'ROUTING' | 'REVIEW' | 'PROCESSING'>('DETAILS');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [logs, setLogs] = useState<string[]>([]);
    const [routes, setRoutes] = useState<any[]>([]);
    const [selectedRoute, setSelectedRoute] = useState<any>(null);

    const [formData, setFormData] = useState({
        recipientName: "John Doe",
        recipientCountry: "KE",
        amount: "100",
        currency: "KES",
        senderName: "Demo Treasury",
        senderCountry: "US"
    });

    const addLog = (msg: string) => setLogs(prev => [...prev, `${new Date().toLocaleTimeString()} > ${msg}`]);

    const handleComplianceCheck = async () => {
        setLoading(true);
        setError("");
        addLog("Initiating Compliance Check...");

        try {
            // Call Backend Compliance Agent
            const res = await fetch('http://localhost:8000/agents/compliance/check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sender_name: formData.senderName,
                    sender_country: formData.senderCountry,
                    recipient_name: formData.recipientName,
                    recipient_country: formData.recipientCountry,
                    amount: parseFloat(formData.amount),
                    currency: "USD", // Example base
                    payment_method: "BANK_TRANSFER"
                })
            });

            const data = await res.json();

            if (!data.is_compliant) {
                setError(`Compliance Blocked: ${data.violations?.join(", ") || data.reasoning}`);
                addLog(`[BLOCKED] Risk Score: ${data.risk_score}`);
                setLoading(false);
                return;
            }

            addLog(`[PASSED] Risk Score: ${data.risk_score}`);
            addLog("Compliance Approved. Calculating Routes...");
            handleRouting();
        } catch (e: any) {
            setError(e.message);
            setLoading(false);
        }
    };

    const handleRouting = async () => {
        try {
            const res = await fetch('http://localhost:8000/routing/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    amount: parseFloat(formData.amount),
                    recipient: "0xMock",
                    preference: "CHEAPEST"
                })
            });
            const data = await res.json();
            setRoutes(data.routes);
            setSelectedRoute(data.recommended_route);
            setStep('ROUTING');
        } catch (e: any) {
            setError("Routing Failed: " + e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleTransfer = async () => {
        setStep('PROCESSING');
        addLog("Submitting to Settlement Agent...");

        try {
            // Call Backend Wallet Send (Settlement Agent)
            const res = await fetch('http://localhost:8000/wallet/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    from_currency: "USD",
                    to_currency: formData.currency, // e.g. KES or APT or MATIC
                    amount: parseFloat(formData.amount),
                    recipient_name: formData.recipientName,
                    recipient_country: formData.recipientCountry,
                    recipient_address: "0xMockRecipient",
                    sender_id: "treasury_us"
                })
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Transfer failed");
            }

            const data = await res.json();
            addLog(`[SUCCESS] TX Hash: ${data.tx_hash}`);
            setTimeout(onSuccess, 2000);

        } catch (e: any) {
            setError(e.message);
            addLog(`[ERROR] ${e.message}`);
            setStep('DETAILS'); // Reset to allow retry
        }
    };

    return (
        <div className="bg-bg-card border border-border-subtle rounded-xl p-6 w-full max-w-lg mx-auto shadow-2xl relative overflow-hidden">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <h3 className="font-display font-bold text-xl text-text-primary">Initiate Transfer</h3>
                <button onClick={onCancel} className="text-text-tertiary hover:text-text-primary text-sm">Cancel</button>
            </div>

            {/* Content */}
            <AnimatePresence mode='wait'>
                {step === 'DETAILS' && (
                    <motion.div key="details" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs uppercase text-text-tertiary mb-1">Pass-Through Recipient</label>
                                <input
                                    className="w-full bg-bg-tertiary border border-border-medium rounded px-3 py-2 text-text-primary"
                                    value={formData.recipientName}
                                    onChange={e => setFormData({ ...formData, recipientName: e.target.value })}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs uppercase text-text-tertiary mb-1">Country (ISO)</label>
                                    <input
                                        className="w-full bg-bg-tertiary border border-border-medium rounded px-3 py-2 text-text-primary"
                                        value={formData.recipientCountry}
                                        onChange={e => setFormData({ ...formData, recipientCountry: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs uppercase text-text-tertiary mb-1">Currency</label>
                                    <select
                                        className="w-full bg-bg-tertiary border border-border-medium rounded px-3 py-2 text-text-primary"
                                        value={formData.currency}
                                        onChange={e => setFormData({ ...formData, currency: e.target.value })}
                                    >
                                        <option value="KES">KES (MPesa)</option>
                                        <option value="GHS">GHS (Momo)</option>
                                        <option value="APT">APT (Aptos)</option>
                                        <option value="MATIC">MATIC (Polygon)</option>
                                        <option value="USDC">USDC (Polygon)</option>
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs uppercase text-text-tertiary mb-1">Amount</label>
                                <input
                                    className="w-full bg-bg-tertiary border border-border-medium rounded px-3 py-2 text-text-primary"
                                    type="number"
                                    value={formData.amount}
                                    onChange={e => setFormData({ ...formData, amount: e.target.value })}
                                />
                            </div>

                            {error && <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded">{error}</div>}

                            <button
                                onClick={handleComplianceCheck}
                                disabled={loading}
                                className="w-full bg-accent-primary hover:bg-accent-primary/90 text-bg-primary font-bold py-3 rounded mt-4"
                            >
                                {loading ? 'Checking Compliance...' : 'Review Transfer'}
                            </button>
                        </div>
                    </motion.div>
                )}

                {(step === 'ROUTING') && (
                    <motion.div key="routing" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
                        <h4 className="text-sm uppercase text-text-tertiary mb-3">Select Payment Route</h4>
                        <div className="space-y-3 mb-6">
                            {routes.map((route, idx) => (
                                <div
                                    key={idx}
                                    onClick={() => setSelectedRoute(route)}
                                    className={`p-3 rounded-lg border cursor-pointer transition-all ${selectedRoute?.chain === route.chain
                                            ? 'bg-accent-primary/10 border-accent-primary'
                                            : 'bg-bg-tertiary border-border-medium hover:border-text-secondary'
                                        }`}
                                >
                                    <div className="flex justify-between items-center mb-1">
                                        <div className="font-bold text-sm text-text-primary flex items-center gap-2">
                                            {route.chain}
                                            {idx === 0 && <span className="text-[10px] bg-green-500/20 text-green-400 px-1.5 rounded uppercase">Best</span>}
                                        </div>
                                        <div className="text-sm font-mono">${route.fee_usd.toFixed(4)}</div>
                                    </div>
                                    <div className="flex justify-between text-xs text-text-tertiary">
                                        <div>{route.reason}</div>
                                        <div>~{route.eta_seconds}s</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                        <button
                            onClick={() => setStep('REVIEW')}
                            className="w-full bg-accent-primary hover:bg-accent-primary/90 text-bg-primary font-bold py-3 rounded"
                        >
                            Continue with {selectedRoute?.chain}
                        </button>
                    </motion.div>
                )}

                {(step === 'REVIEW' || step === 'PROCESSING') && (
                    <motion.div key="review" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
                        <div className="bg-bg-tertiary rounded p-4 mb-4 text-sm font-mono space-y-2">
                            <div className="flex justify-between"><span>Recipient:</span> <span className="text-text-primary">{formData.recipientName} ({formData.recipientCountry})</span></div>
                            <div className="flex justify-between"><span>Amount:</span> <span className="text-accent-secondary">{formData.amount} {formData.currency}</span></div>
                            <div className="flex justify-between"><span>Route:</span> <span className="text-text-primary">Optimized (Agent)</span></div>
                        </div>

                        <div className="h-32 bg-black/50 rounded p-2 mb-4 overflow-y-auto font-mono text-xs text-green-400 border border-border-subtle">
                            {logs.map((log, i) => <div key={i}>{log}</div>)}
                        </div>

                        {step !== 'PROCESSING' && (
                            <button
                                onClick={handleTransfer}
                                className="w-full bg-accent-secondary hover:bg-accent-secondary/90 text-bg-primary font-bold py-3 rounded"
                            >
                                Confirm & Send
                            </button>
                        )}
                        {step === 'PROCESSING' && (
                            <div className="text-center text-accent-secondary animate-pulse">Processing Settlement...</div>
                        )}
                        {error && <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded">{error}</div>}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
