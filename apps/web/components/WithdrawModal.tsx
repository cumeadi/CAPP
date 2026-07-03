'use client';

import { X, ArrowRight, Loader2, Check, Building2, Smartphone } from 'lucide-react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, HifiCorridor } from '@/services/api';
import Portal from './Portal';

interface WithdrawModalProps {
    isOpen: boolean;
    onClose: () => void;
}

type WithdrawTab = 'crypto' | 'local';
type LocalStep = 'SELECT_COUNTRY' | 'FORM' | 'PROCESSING' | 'SUCCESS';

export default function WithdrawModal({ isOpen, onClose }: WithdrawModalProps) {
    const [tab, setTab] = useState<WithdrawTab>('crypto');

    // Crypto state
    const [step, setStep] = useState<'INPUT' | 'PROCESSING' | 'SUCCESS'>('INPUT');
    const [recipient, setRecipient] = useState('');
    const [amount, setAmount] = useState('');
    const [txHash, setTxHash] = useState('');

    // HIFI state
    const [corridors, setCorridors] = useState<HifiCorridor[]>([]);
    const [loadingCorridors, setLoadingCorridors] = useState(false);
    const [selectedCorridor, setSelectedCorridor] = useState<HifiCorridor | null>(null);
    const [localStep, setLocalStep] = useState<LocalStep>('SELECT_COUNTRY');
    const [paymentMethod, setPaymentMethod] = useState<'bank_transfer' | 'mobile_money'>('mobile_money');
    const [localAmount, setLocalAmount] = useState('');
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [bankAccountNumber, setBankAccountNumber] = useState('');
    const [bankCode, setBankCode] = useState('');
    const [mobileMoneyNumber, setMobileMoneyNumber] = useState('');
    const [additionalIdType, setAdditionalIdType] = useState('');
    const [additionalIdNumber, setAdditionalIdNumber] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [localTxResult, setLocalTxResult] = useState<{ transaction_id: string; estimated_delivery?: string } | null>(null);

    useEffect(() => {
        if (isOpen && tab === 'local' && corridors.length === 0) {
            loadCorridors();
        }
    }, [isOpen, tab]);

    const loadCorridors = async () => {
        setLoadingCorridors(true);
        try {
            const data = await api.getHifiCorridors();
            setCorridors(data.filter(c => c.supports_payout));
        } catch {
            setCorridors([]);
        } finally {
            setLoadingCorridors(false);
        }
    };

    const resetLocalState = () => {
        setSelectedCorridor(null);
        setLocalStep('SELECT_COUNTRY');
        setLocalAmount('');
        setFirstName('');
        setLastName('');
        setEmail('');
        setPhone('');
        setBankAccountNumber('');
        setBankCode('');
        setMobileMoneyNumber('');
        setAdditionalIdType('');
        setAdditionalIdNumber('');
        setError('');
        setLocalTxResult(null);
    };

    const handleClose = () => {
        setStep('INPUT');
        setRecipient('');
        setAmount('');
        setTxHash('');
        resetLocalState();
        setTab('crypto');
        onClose();
    };

    const handleWithdraw = async () => {
        if (!recipient || !amount) return;
        setStep('PROCESSING');
        try {
            const targetChain = (window as any).selectedChain || undefined;
            const result = await api.executeTransfer(recipient, parseFloat(amount), targetChain);
            setTxHash(result.tx_hash);
            setStep('SUCCESS');
        } catch (e) {
            console.error(e);
            setStep('INPUT');
            alert("Withdrawal failed. Check console.");
        }
    };

    const handleLocalWithdraw = async () => {
        if (!selectedCorridor) return;
        setSubmitting(true);
        setError('');
        try {
            const result = await api.hifiWithdraw({
                country_code: selectedCorridor.country_code,
                amount: parseFloat(localAmount),
                payment_method: paymentMethod,
                first_name: firstName,
                last_name: lastName,
                email,
                phone,
                ...(paymentMethod === 'bank_transfer' ? {
                    bank_account_number: bankAccountNumber,
                    bank_code: bankCode,
                } : {
                    mobile_money_number: mobileMoneyNumber,
                }),
                ...(selectedCorridor.requires_additional_id ? {
                    additional_id_type: additionalIdType,
                    additional_id_number: additionalIdNumber,
                } : {}),
            });
            setLocalTxResult({ transaction_id: result.transaction_id, estimated_delivery: result.estimated_delivery });
            setLocalStep('SUCCESS');
        } catch (e: any) {
            setError(e.message || 'Withdrawal failed');
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
                            <div className="w-full max-w-md bg-bg-card border border-border-medium rounded-2xl p-6 shadow-2xl pointer-events-auto max-h-[90vh] overflow-y-auto">
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="font-display text-lg font-semibold uppercase tracking-wider text-text-primary">Withdraw Funds</h3>
                                    <button onClick={handleClose} className="p-2 hover:bg-bg-tertiary rounded-full transition-colors">
                                        <X className="w-5 h-5 text-text-secondary" />
                                    </button>
                                </div>

                                {/* Tab Switcher */}
                                <div className="flex gap-1 p-1 bg-bg-tertiary rounded-xl mb-6">
                                    <button
                                        onClick={() => { setTab('crypto'); resetLocalState(); }}
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
                                    <>
                                        {step === 'INPUT' && (
                                            <div className="space-y-6">
                                                <div>
                                                    <label className="text-xs text-text-tertiary uppercase tracking-widest mb-2 block">Recipient Address</label>
                                                    <input type="text" value={recipient} onChange={(e) => setRecipient(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 font-mono text-sm text-text-primary focus:border-accent-primary focus:outline-none transition-colors" placeholder="0x..." />
                                                </div>
                                                <div>
                                                    <label className="text-xs text-text-tertiary uppercase tracking-widest mb-2 block">Amount (APT)</label>
                                                    <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 font-mono text-sm text-text-primary focus:border-accent-primary focus:outline-none transition-colors" placeholder="0.00" />
                                                </div>
                                                <div>
                                                    <label className="text-xs text-text-tertiary uppercase tracking-widest mb-2 block">Destination Network</label>
                                                    <select onChange={(e) => { (window as any).selectedChain = e.target.value; }} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 font-mono text-sm text-text-primary focus:border-accent-primary focus:outline-none transition-colors">
                                                        <option value="">Aptos (Direct)</option>
                                                        <option value="base">Base (L2)</option>
                                                        <option value="arbitrum">Arbitrum (L2)</option>
                                                        <option value="ethereum">Ethereum (L1)</option>
                                                    </select>
                                                </div>
                                                <button onClick={handleWithdraw} className="w-full py-4 bg-accent-primary text-bg-primary rounded-xl font-bold uppercase tracking-wide hover:bg-white transition-all shadow-lg shadow-accent-primary/20 flex items-center justify-center gap-2">
                                                    Confirm Withdrawal <ArrowRight className="w-4 h-4" />
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
                                                <p className="text-sm text-text-secondary mb-6 max-w-xs">Your funds have been securely transferred to the destination wallet.</p>
                                                <div className="bg-bg-tertiary p-3 rounded-lg font-mono text-xs text-text-tertiary break-all mb-6">{txHash}</div>
                                                <button onClick={handleClose} className="px-8 py-3 bg-bg-tertiary hover:bg-bg-secondary text-text-primary rounded-xl font-medium transition-colors">Close</button>
                                            </div>
                                        )}
                                    </>
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
                                                <p className="text-sm text-text-secondary">Local currency withdrawals are not available yet.</p>
                                            </div>
                                        )}

                                        {/* Select Country */}
                                        {!loadingCorridors && corridors.length > 0 && localStep === 'SELECT_COUNTRY' && (
                                            <>
                                                <p className="text-xs text-text-tertiary uppercase tracking-widest">Select Destination Country</p>
                                                <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto">
                                                    {corridors.map(c => (
                                                        <button key={c.country_code} onClick={() => { setSelectedCorridor(c); setLocalStep('FORM'); }} className="flex items-center gap-2 p-3 bg-bg-tertiary border border-border-medium rounded-xl hover:border-accent-primary/50 transition-all text-left">
                                                            <span className="text-sm font-medium text-text-primary">{c.country_name}</span>
                                                            <span className="text-xs text-text-tertiary ml-auto">{c.currency}</span>
                                                        </button>
                                                    ))}
                                                </div>
                                                <div className="p-3 bg-accent-primary/5 border border-accent-primary/10 rounded-xl">
                                                    <p className="text-xs text-text-secondary">Withdraw to bank account or mobile money. Powered by HIFI Africa Rail (Beta).</p>
                                                </div>
                                            </>
                                        )}

                                        {/* Withdraw Form */}
                                        {localStep === 'FORM' && selectedCorridor && (
                                            <>
                                                <div className="flex items-center gap-2 mb-2">
                                                    <button onClick={() => setLocalStep('SELECT_COUNTRY')} className="text-xs text-accent-primary hover:underline">&larr; Back</button>
                                                    <span className="text-sm font-medium text-text-primary">{selectedCorridor.country_name} ({selectedCorridor.currency})</span>
                                                </div>

                                                {/* Payment Method */}
                                                <div className="flex gap-2">
                                                    <button onClick={() => setPaymentMethod('mobile_money')} className={`flex-1 flex items-center gap-2 p-3 rounded-xl border transition-all ${paymentMethod === 'mobile_money' ? 'border-accent-primary bg-accent-primary/10' : 'border-border-medium bg-bg-tertiary'}`}>
                                                        <Smartphone className="w-4 h-4" /><span className="text-sm">Mobile Money</span>
                                                    </button>
                                                    <button onClick={() => setPaymentMethod('bank_transfer')} className={`flex-1 flex items-center gap-2 p-3 rounded-xl border transition-all ${paymentMethod === 'bank_transfer' ? 'border-accent-primary bg-accent-primary/10' : 'border-border-medium bg-bg-tertiary'}`}>
                                                        <Building2 className="w-4 h-4" /><span className="text-sm">Bank Transfer</span>
                                                    </button>
                                                </div>

                                                {/* Amount */}
                                                <div>
                                                    <label className="text-xs text-text-tertiary mb-1 block">Amount ({selectedCorridor.currency})</label>
                                                    <input type="number" value={localAmount} onChange={e => setLocalAmount(e.target.value)} placeholder="0.00" className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent-primary" />
                                                </div>

                                                {/* Recipient Details */}
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

                                                {/* Payment-method-specific fields */}
                                                {paymentMethod === 'bank_transfer' && (
                                                    <div className="grid grid-cols-2 gap-3">
                                                        <div>
                                                            <label className="text-xs text-text-tertiary mb-1 block">Bank Account Number</label>
                                                            <input type="text" value={bankAccountNumber} onChange={e => setBankAccountNumber(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary focus:outline-none focus:border-accent-primary" />
                                                        </div>
                                                        <div>
                                                            <label className="text-xs text-text-tertiary mb-1 block">Bank Code</label>
                                                            <input type="text" value={bankCode} onChange={e => setBankCode(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary focus:outline-none focus:border-accent-primary" />
                                                        </div>
                                                    </div>
                                                )}
                                                {paymentMethod === 'mobile_money' && (
                                                    <div>
                                                        <label className="text-xs text-text-tertiary mb-1 block">Mobile Money Number</label>
                                                        <input type="tel" value={mobileMoneyNumber} onChange={e => setMobileMoneyNumber(e.target.value)} className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm text-text-primary focus:outline-none focus:border-accent-primary" placeholder="+254..." />
                                                    </div>
                                                )}

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
                                                    onClick={handleLocalWithdraw}
                                                    disabled={submitting || !localAmount || !firstName || !lastName || !email || !phone}
                                                    className="w-full flex items-center justify-center gap-2 py-3 bg-accent-primary text-bg-primary rounded-xl font-medium hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                                >
                                                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                                                    {submitting ? 'Processing...' : `Withdraw ${localAmount || '0'} ${selectedCorridor.currency}`}
                                                </button>

                                                <p className="text-xs text-text-tertiary text-center">
                                                    {paymentMethod === 'mobile_money' ? 'Instant to 1 day' : '1-3 business days'} &middot; HIFI Africa Rail (Beta)
                                                </p>
                                            </>
                                        )}

                                        {/* Success */}
                                        {localStep === 'SUCCESS' && localTxResult && (
                                            <div className="flex flex-col items-center gap-4 py-4">
                                                <div className="w-16 h-16 rounded-full bg-color-success/10 flex items-center justify-center">
                                                    <Check className="w-8 h-8 text-color-success" />
                                                </div>
                                                <h4 className="text-lg font-semibold text-text-primary">Withdrawal Initiated</h4>
                                                <p className="text-sm text-text-secondary text-center">
                                                    Your {selectedCorridor?.currency} withdrawal is being processed.
                                                </p>
                                                <div className="w-full bg-bg-tertiary rounded-xl p-3">
                                                    <p className="text-xs text-text-tertiary">Transaction ID</p>
                                                    <p className="text-sm text-text-primary font-mono truncate">{localTxResult.transaction_id}</p>
                                                </div>
                                                {localTxResult.estimated_delivery && (
                                                    <p className="text-xs text-text-tertiary">Est. delivery: {localTxResult.estimated_delivery}</p>
                                                )}
                                                <button onClick={handleClose} className="w-full py-3 bg-accent-primary text-bg-primary rounded-xl font-medium hover:opacity-90 transition-all">Done</button>
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
