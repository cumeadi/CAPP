"use client";

import { useState, useEffect } from "react";
import { ArrowDown, RefreshCw, Info, CheckCircle2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/Shared/Button";
import { clsx } from "clsx";
import { motion, AnimatePresence } from "framer-motion";

const TOKENS = [
    { symbol: "APT", name: "Aptos Coin", icon: "A", balance: 14.5, price: 9.85 },
    { symbol: "USDC", name: "USD Coin", icon: "$", balance: 2500.00, price: 1.00 },
    { symbol: "ETH", name: "Ethereum", icon: "Ξ", balance: 1.2, price: 2350.00 },
    { symbol: "WETH", name: "Wrapped Ether", icon: "W", balance: 0.0, price: 2350.00 },
];

export default function SwapPage() {
    const [fromToken, setFromToken] = useState(TOKENS[0]);
    const [toToken, setToToken] = useState(TOKENS[1]);
    const [amount, setAmount] = useState("");
    const [loading, setLoading] = useState(false);
    const [step, setStep] = useState<"input" | "confirm" | "success">("input");

    // Mock Quote Calculation
    const rate = fromToken.price / toToken.price;
    const outputAmount = amount ? (parseFloat(amount) * rate).toFixed(6) : "0.00";
    const priceImpact = parseFloat(amount) > 1000 ? 0.35 : 0.01; // Mock impact

    const handleSwap = () => {
        setStep("confirm");
    };

    const confirmSwap = () => {
        setLoading(true);
        setTimeout(() => {
            setLoading(false);
            setStep("success");
            setAmount("");
        }, 2000);
    };

    const handleSwitch = () => {
        setFromToken(toToken);
        setToToken(fromToken);
    };

    return (
        <div className="max-w-md mx-auto animate-in fade-in duration-500">

            <div className="mb-8 text-center">
                <h1 className="text-2xl font-bold text-white tracking-widest mb-2">SWAP TOKENS</h1>
                <p className="text-[var(--text-secondary)] text-sm">Instant swaps with zero slippage on Aptos.</p>
            </div>

            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-2xl p-4 shadow-xl relative overflow-hidden">

                {/* Background Glow */}
                <div className="absolute top-0 right-0 w-[200px] h-[200px] bg-[var(--accent-primary)]/5 blur-[80px] -z-10 rounded-full pointer-events-none" />

                <AnimatePresence mode="wait">
                    {step === "input" && (
                        <motion.div
                            key="input"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            className="space-y-4"
                        >
                            {/* FROM */}
                            <div className="bg-[var(--bg-primary)] p-4 rounded-xl border border-[var(--border-subtle)] hover:border-[var(--border-medium)] transition-colors">
                                <div className="flex justify-between mb-2">
                                    <span className="text-xs text-[var(--text-secondary)] font-bold">PAY</span>
                                    <span className="text-xs text-[var(--text-secondary)] cursor-pointer hover:text-[var(--accent-cyan)]">
                                        Balance: {fromToken.balance}
                                    </span>
                                </div>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="number"
                                        placeholder="0.00"
                                        value={amount}
                                        onChange={(e) => setAmount(e.target.value)}
                                        className="w-full bg-transparent text-3xl font-mono text-white placeholder-[var(--text-tertiary)] outline-none"
                                    />
                                    <SwapTokenSelect selected={fromToken} onSelect={setFromToken} />
                                </div>
                                <div className="mt-2 text-xs text-[var(--text-tertiary)]">
                                    ~${(parseFloat(amount || "0") * fromToken.price).toFixed(2)}
                                </div>
                            </div>

                            {/* Switcher */}
                            <div className="relative h-4">
                                <button
                                    onClick={handleSwitch}
                                    className="absolute left-1/2 -translate-x-1/2 -top-6 w-10 h-10 bg-[var(--bg-card)] border border-[var(--border-medium)] rounded-xl flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--accent-cyan)] hover:border-[var(--accent-cyan)] transition-all z-10 shadow-lg"
                                >
                                    <ArrowDown className="w-5 h-5" />
                                </button>
                            </div>

                            {/* TO */}
                            <div className="bg-[var(--bg-primary)] p-4 rounded-xl border border-[var(--border-subtle)] hover:border-[var(--border-medium)] transition-colors">
                                <div className="flex justify-between mb-2">
                                    <span className="text-xs text-[var(--text-secondary)] font-bold">RECEIVE</span>
                                    <span className="text-xs text-[var(--text-secondary)] cursor-pointer hover:text-[var(--accent-cyan)]">
                                        Balance: {toToken.balance}
                                    </span>
                                </div>
                                <div className="flex items-center gap-4">
                                    <div className="w-full text-3xl font-mono text-[var(--text-secondary)] truncate">
                                        {amount ? outputAmount : "0.00"}
                                    </div>
                                    <SwapTokenSelect selected={toToken} onSelect={setToToken} />
                                </div>
                                <div className="mt-2 text-xs text-[var(--text-tertiary)]">
                                    ~${(parseFloat(outputAmount) * toToken.price).toFixed(2)}
                                </div>
                            </div>

                            {/* Details Accordion (Always open for MVP) */}
                            {amount && (
                                <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] space-y-2 text-xs">
                                    <div className="flex justify-between text-[var(--text-secondary)]">
                                        <span>Rate</span>
                                        <span className="font-mono">1 {fromToken.symbol} = {rate.toFixed(4)} {toToken.symbol}</span>
                                    </div>
                                    <div className="flex justify-between text-[var(--text-secondary)]">
                                        <span>Network Fee</span>
                                        <span className="font-mono text-[var(--accent-cyan)]">~$0.001 (APT)</span>
                                    </div>
                                    <div className="flex justify-between text-[var(--text-secondary)]">
                                        <span>Price Impact</span>
                                        <span className={clsx("font-mono", priceImpact > 1 ? "text-red-400" : "text-green-400")}>
                                            ~{priceImpact}%
                                        </span>
                                    </div>
                                </div>
                            )}

                            <Button
                                variant="primary"
                                size="lg"
                                className="w-full justify-center py-6 text-lg"
                                onClick={handleSwap}
                                disabled={!amount || parseFloat(amount) <= 0}
                            >
                                REVIEW SWAP
                            </Button>
                        </motion.div>
                    )}

                    {step === "confirm" && (
                        <motion.div
                            key="confirm"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="space-y-6 text-center py-6"
                        >
                            <h3 className="text-xl font-bold text-white">Confirm Swap</h3>

                            <div className="flex items-center justify-center gap-4 text-2xl font-mono font-bold text-white">
                                <span>{amount} {fromToken.symbol}</span>
                                <span className="text-[var(--text-tertiary)]">→</span>
                                <span className="text-[var(--accent-cyan)]">{outputAmount} {toToken.symbol}</span>
                            </div>

                            <p className="text-[var(--text-secondary)] text-sm max-w-[200px] mx-auto">
                                Output is estimated. You will receive at least <span className="text-white">{(parseFloat(outputAmount) * 0.995).toFixed(4)} {toToken.symbol}</span> or the transaction will revert.
                            </p>

                            <div className="flex gap-3">
                                <Button variant="secondary" onClick={() => setStep("input")} className="flex-1 justify-center">CANCEL</Button>
                                <Button variant="primary" onClick={confirmSwap} disabled={loading} className="flex-1 justify-center">
                                    {loading ? "SWAPPING..." : "CONFIRM SWAP"}
                                </Button>
                            </div>
                        </motion.div>
                    )}

                    {step === "success" && (
                        <motion.div
                            key="success"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="text-center py-8 space-y-6"
                        >
                            <div className="w-20 h-20 rounded-full bg-green-500/10 flex items-center justify-center mx-auto border-2 border-green-500 text-green-500">
                                <CheckCircle2 className="w-10 h-10" />
                            </div>

                            <div>
                                <h3 className="text-2xl font-bold text-white mb-2">Swap Successful!</h3>
                                <p className="text-[var(--text-secondary)]">
                                    You swapped {fromToken.symbol} for {toToken.symbol}
                                </p>
                            </div>

                            <div className="bg-[var(--bg-primary)] p-3 rounded-lg flex items-center gap-2 justify-center text-xs text-[var(--accent-cyan)] font-mono">
                                <span>View on Explorer</span>
                                <ArrowDown className="w-3 h-3 -rotate-90" />
                            </div>

                            <Button variant="primary" onClick={() => setStep("input")} className="w-full justify-center">
                                SWAP AGAIN
                            </Button>
                        </motion.div>
                    )}
                </AnimatePresence>

            </div>
        </div>
    );
}

// Simple internal component for token selection
function SwapTokenSelect({ selected, onSelect }: { selected: any, onSelect: (t: any) => void }) {
    const [open, setOpen] = useState(false);

    return (
        <div className="relative">
            <button
                onClick={() => setOpen(!open)}
                className="flex items-center gap-2 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-primary)]/10 border border-[var(--border-medium)] hover:border-[var(--accent-primary)] px-3 py-1.5 rounded-full transition-all"
            >
                <div className="w-6 h-6 rounded-full bg-white text-black flex items-center justify-center font-bold text-xs">
                    {selected.icon}
                </div>
                <span className="font-bold text-white">{selected.symbol}</span>
                <ArrowDown className="w-3 h-3 text-[var(--text-secondary)]" />
            </button>

            {open && (
                <>
                    <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
                    <div className="absolute right-0 top-full mt-2 w-48 bg-[var(--bg-card)] border border-[var(--border-medium)] rounded-xl shadow-xl z-20 overflow-hidden py-1">
                        {TOKENS.map(token => (
                            <button
                                key={token.symbol}
                                onClick={() => {
                                    onSelect(token);
                                    setOpen(false);
                                }}
                                className="w-full text-left px-4 py-3 hover:bg-[var(--bg-tertiary)] flex items-center gap-3 transition-colors"
                            >
                                <div className="w-6 h-6 rounded-full bg-[var(--bg-secondary)] flex items-center justify-center font-bold text-xs text-white">
                                    {token.icon}
                                </div>
                                <span className="font-bold text-white text-sm">{token.symbol}</span>
                            </button>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}
