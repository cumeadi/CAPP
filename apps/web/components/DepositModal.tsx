'use client';

import { X, Copy, Check, Building2, Smartphone, ArrowRight, Loader2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Portal from './Portal';
import { api, HifiCorridor } from '../services/api';

interface DepositModalProps {
    isOpen: boolean;
    onClose: () => void;
    address: string;
}

type DepositTab = 'crypto' | 'local';
type DepositStep = 'SELECT_COUNTRY' | 'FORM' | 'PROCESSING' | 'SUCCESS';

export default function DepositModal({ isOpen, onClose, address }: DepositModalProps) {
    const [copied, setCopied] = useState(false);
    const [tab, setTab] = useState<DepositTab>('crypto');

    // HIFI state
    const [corridors, setCorridors] = useState<HifiCorridor[]>([]);
    const [loadingCorridors, setLoadingCorridors] = useState(false);
    const [selectedCorridor, setSelectedCorridor] = useState<HifiCorridor | null>(null);
    const [step, setStep] = useState<DepositStep>('SELECT_COUNTRY');
    const [paymentMethod, setPaymentMethod] = useState<'bank_transfer' | 'mobile_money'>('mobile_money');
    const [amount, setAmount] = useState('');
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [additionalIdType, setAdditionalIdType] = useState('');
    const [additionalIdNumber, setAdditionalIdNumber] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [txResult, setTxResult] = useState<{ transaction_id: string; estimated_delivery?: string } | null>(null);

    useEffect(() => {
        if (isOpen && tab === 'local' && corridors.length === 0) {
            loadCorridors();
        }
    }, [isOpen, tab]);

    const loadCorridors = async () => {
        setLoadingCorridors(true);
        try {
            const data = await api.getHifiCorridors();
            setCorridors(data.filter(c => c.supports_payin));
        } catch {
            setCorridors([]);
        } finally {
            setLoadingCorridors(false);
        }
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(address);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const resetHifiState = () => {
        setSelectedCorridor(null);
        setStep('SELECT_COUNTRY');
        setAmount('');
        setFirstName('');
        setLastName('');
        setEmail('');
        setPhone('');
        setAdditionalIdType('');
        setAdditionalIdNumber('');
        setError('');
        setTxResult(null);
    };

    const handleClose = () => {
        resetHifiState();
        setTab('crypto');
        onClose();
    };

    const handleSubmitDeposit = async () => {
        if (!selectedCorridor) return;
        setSubmitting(true);
        setError('');
        try {
            const result = await api.hifiDeposit({
                country_code: selectedCorridor.country_code,
                amount: parseFloat(amount),
                payment_method: paymentMethod,
                first_name: firstName,
                last_name: lastName,
                email,
                phone,
                ...(selectedCorridor.requires_additional_id ? {
                    additional_id_type: additionalIdType,
                    additional_id_number: additionalIdNumber,
                } : {}),
            });
            setTxResult({ transaction_id: result.transaction_id, estimated_delivery: result.estimated_delivery });
            setStep('SUCCESS');
        } catch (e: any) {
            setError(e.message || 'Deposit failed');
        } finally {
            setSubmitting(false);
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
                            onClick={handleClose}
                            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 transition-all"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none p-4"
                        >
                            <div className="relative w-full max-w-md bg-bg-card border border-border-medium rounded-2xl p-6 shadow-2xl overflow-hidden pointer-events-auto max-h-[90vh] overflow-y-auto">
                                <div className="absolute top-0 right-0 w-32 h-32 bg-accent-primary/10 rounded-full blur-3xl -z-10" />

                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="font-display text-lg font-semibold uppercase tracking-wider text-text-primary">Deposit Assets</h3>
                                    <button onClick={handleClose} className="p-2 hover:bg-bg-tertiary rounded-full transition-colors">
                                        <X className="w-5 h-5 text-text-secondary" />
                                    </button>
                                </div>

                                {/* Tab Switcher */}
                                <div className="flex gap-1 p-1 bg-bg-tertiary rounded-xl mb-6">
                                    <button
                                        onClick={() => { setTab('crypto'); resetHifiState(); }}
                                        className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${tab === 'crypto' ? 'bg-accent-primary text-bg-primary' : 'text-text-secondary hover:text-text-primary'}`}
                                    >
                                        Crypto
                                    </button>
                                    <button
                                        onClick={() => setTab('local')}
                                        className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${tab === 'local' ? 'bg-accent-primary text-bg-primary' : 'text-text-secondary hover:text-text-primary'}`}
                                    >
                                        Local Currency
                                    </button>
                                </div>

                                {/* Crypto Tab */}
                                {tab === 'crypto' && (
                                    <div className="flex flex-col items-center gap-6">
                                        <div className="p-4 bg-white rounded-xl">
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
                                )}

                                {/* Local Currency Tab */}
                                {tab === 'local' && (
                                    <div className="flex flex-col gap-4">
                                        {loadingCorridors && (
                                            <div className="flex items-center justify-center py-8">
                                                <Loader2 className="w-6 h-6 animate-spin text-accent-primary" />
                                            </div>
                                        )}

                                        {!loadingCorridors && corridors.length === 0 && (
                                            <div className="text-center py-8">
                                                <p className="text-sm text-text-secondary">Local currency deposits are not available yet.</p>
                                            </div>
                                        )}

                                        {/* Step: Select Country */}
                                        {!loadingCorridors && corridors.length > 0 && step === 'SELECT_COUNTRY' && (
                                            <>
                                                <p className="text-xs text-text-tertiary uppercase tracking-widest">Select Country</p>
                                                <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto">
                                                    {corridors.map(c => (
                                                        <button
                                                            key={c.country_code}
                                                            onClick={() => { setSelectedCorridor(c); setStep('FORM'); }}
                                                            className="flex items-center gap-2 p-3 bg-bg-tertiary border border-border-medium rounded-xl hover:border-accent-primary/50 transition-all text-left"
                                                        >
                                                            <span className="text-sm font-medium text-text-primary">{c.country_name}</span>
                                                            <span className="text-xs text-text-tertiary ml-auto">{c.currency}</span>
                                                        </button>
                                                    ))}
                                                </div>
                                                <div className="p-3 bg-accent-primary/5 border border-accent-primary/10 rounded-xl">
                                                    <p className="text-xs text-text-secondary">
                                                        Deposit via bank transfer or mobile money. Powered by HIFI Africa Rail (Beta).
                                                    </p>
                                                </div>
                                            </>
                                        )}

                                        {/* Step: Deposit Form */}
                                        {step === 'FORM' && selectedCorridor && (
                                            <>
                                                <div className="flex items-center gap-2 mb-2">
                                                    <button onClick={() => setStep('SELECT_COUNTRY')} className="text-xs text-accent-primary hover:underline">
                                                        &larr; Back
                                                    </button>
                                                    <span className="text-sm font-medium text-text-primary">
                                                        {selectedCorridor.country_name} ({selectedCorridor.currency})
                                                    </span>
                                                </div>

                                                {/* Payment Method */}
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => setPaymentMethod('mobile_money')}
                                                        className={`flex-1 flex items-center gap-2 p-3 rounded-xl border transition-all ${paymentMethod === 'mobile_money' ? 'border-accent-primary bg-accent-primary/10' : 'border-border-medium bg-bg-tertiary'}`}
                                                    >
                                                        <Smartphone className="w-4 h-4" />
                                                        <span className="text-sm">Mobile Money</span>
                                                    </button>
                                                    <button
                                                        onClick={() => setPaymentMethod('bank_transfer')}
                                                        className={`flex-1 flex items-center gap-2 p-3 rounded-xl border transition-all ${paymentMethod === 'bank_transfer' ? 'border-accent-primary bg-accent-primary/10' : 'border-border-medium bg-bg-tertiary'}`}
                                                    >
                                                        <Building2 className="w-4 h-4" />
                                                        <span className="text-sm">Bank Transfer</span>
                                                    </button>
                                                </div>

                                                {/* Amount */}
                                                <div>
                                                    <label className="text-xs text-text-tertiary mb-1 block">Amount ({selectedCorridor.currency})</label>
                                                    <input
                                                        type="number"
                                                        value={amount}
                                                        onChange={e => setAmount(e.target.value)}
                                                        placeholder="0.00"
                                                        className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent-primary"
                                                    />
                                                </div>

                                                {/* KYC Fields */}
                                                <div className="grid grid-cols-2 gap-3">
                                                    <div>
                                                        <label className="text-xs text-text-tertiary mb-1 block">First Name</label>
                                                        <input type="text" value={firstName} onChange={e => setFirstName(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary focus:outline-none focus:border-accent-primary" />
                                                    </div>
                                                    <div>
                                                        <label className="text-xs text-text-tertiary mb-1 block">Last Name</label>
                                                        <input type="text" value={lastName} onChange={e => setLastName(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary focus:outline-none focus:border-accent-primary" />
                                                    </div>
                                                </div>
                                                <div>
                                                    <label className="text-xs text-text-tertiary mb-1 block">Email</label>
                                                    <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary focus:outline-none focus:border-accent-primary" />
                                                </div>
                                                <div>
                                                    <label className="text-xs text-text-tertiary mb-1 block">Phone</label>
                                                    <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary focus:outline-none focus:border-accent-primary" />
                                                </div>

                                                {/* Nigeria Additional ID */}
                                                {selectedCorridor.requires_additional_id && (
                                                    <div className="grid grid-cols-2 gap-3">
                                                        <div>
                                                            <label className="text-xs text-text-tertiary mb-1 block">Additional ID Type</label>
                                                            <select value={additionalIdType} onChange={e => setAdditionalIdType(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary focus:outline-none focus:border-accent-primary">
                                                                <option value="">Select...</option>
                                                                <option value="BVN">BVN</option>
                                                                <option value="NIN">NIN</option>
                                                            </select>
                                                        </div>
                                                        <div>
                                                            <label className="text-xs text-text-tertiary mb-1 block">Additional ID Number</label>
                                                            <input type="text" value={additionalIdNumber} onChange={e => setAdditionalIdNumber(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary focus:outline-none focus:border-accent-primary" />
                                                        </div>
                                                    </div>
                                                )}

                                                {error && (
                                                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
                                                        <p className="text-xs text-red-400">{error}</p>
                                                    </div>
                                                )}

                                                <button
                                                    onClick={handleSubmitDeposit}
                                                    disabled={submitting || !amount || !firstName || !lastName || !email || !phone}
                                                    className="w-full flex items-center justify-center gap-2 py-3 bg-accent-primary text-bg-primary rounded-xl font-medium hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                                >
                                                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                                                    {submitting ? 'Processing...' : `Deposit ${amount || '0'} ${selectedCorridor.currency}`}
                                                </button>

                                                <p className="text-xs text-text-tertiary text-center">
                                                    {paymentMethod === 'mobile_money' ? 'Instant to 1 day' : '1-3 business days'} &middot; HIFI Africa Rail (Beta)
                                                </p>
                                            </>
                                        )}

                                        {/* Step: Success */}
                                        {step === 'SUCCESS' && txResult && (
                                            <div className="flex flex-col items-center gap-4 py-4">
                                                <div className="w-16 h-16 rounded-full bg-color-success/10 flex items-center justify-center">
                                                    <Check className="w-8 h-8 text-color-success" />
                                                </div>
                                                <h4 className="text-lg font-semibold text-text-primary">Deposit Initiated</h4>
                                                <p className="text-sm text-text-secondary text-center">
                                                    Your {selectedCorridor?.currency} deposit is being processed.
                                                </p>
                                                <div className="w-full bg-bg-tertiary rounded-xl p-3">
                                                    <p className="text-xs text-text-tertiary">Transaction ID</p>
                                                    <p className="text-sm text-text-primary font-mono truncate">{txResult.transaction_id}</p>
                                                </div>
                                                {txResult.estimated_delivery && (
                                                    <p className="text-xs text-text-tertiary">Est. delivery: {txResult.estimated_delivery}</p>
                                                )}
                                                <button
                                                    onClick={handleClose}
                                                    className="w-full py-3 bg-accent-primary text-bg-primary rounded-xl font-medium hover:opacity-90 transition-all"
                                                >
                                                    Done
                                                </button>
                                            </div>
                                        )}
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
