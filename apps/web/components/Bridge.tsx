"use client";

import React, { useState, useEffect } from "react";
import { useStarknet } from "./StarknetProvider";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Wallet, Lock, Activity } from "lucide-react";

export default function Bridge() {
    const { account, address, connectWallet, isConnected, provider } = useStarknet();
    const [amount, setAmount] = useState("");
    const [status, setStatus] = useState<"IDLE" | "LOCKING" | "RELAYING" | "SUCCESS" | "FAILED">("IDLE");
    const [logs, setLogs] = useState<string[]>([]);
    const [starknetBalance, setStarknetBalance] = useState("0");

    // Fetch Balance on Connect
    useEffect(() => {
        if (isConnected && address) {
            // Mock fetch or call API
            // Since we don't have a direct contract yet, we'll confirm 0 or fetch via API if needed
            // Ideally call backend: /starknet/balance/{address}
            fetch(`http://localhost:8000/starknet/balance/${address}`)
                .then(res => res.json())
                .then(data => setStarknetBalance(data.balance_eth.toFixed(4)))
                .catch(err => console.error("Balance fetch error", err));
        }
    }, [isConnected, address]);

    const addLog = (msg: string) => setLogs(prev => [msg, ...prev]);

    const handleBridge = async () => {
        if (!account || !amount) return;

        try {
            setStatus("LOCKING");
            addLog(`Initiating Bridge Transfer of ${amount} ETH...`);

            // 1. Prepare Transaction
            // In a real app, this would call the BRIDGE CONTRACT.
            // For MVP "Liquidity Bridge", we transfer to the CAPP SYSTEM ADDRESS.
            // (This should be in .env/config, for now using a demo address)
            const BRIDGE_WALLET = "0x012345...SYSTEM_WALLET";

            // 2. Execute Transfer on Starknet
            // We use the StarknetProvider account object
            addLog("Signing transaction on Starknet...");

            const { transaction_hash } = await account.execute({
                contractAddress: "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7", // ETH Token
                entrypoint: "transfer",
                calldata: [
                    BRIDGE_WALLET, // recipient
                    // uint256 is low, high. Assuming amount is small enough for low part for demo.
                    // Real app needs uint256 conversion util.
                    (parseFloat(amount) * 1e18).toString(),
                    "0"
                ]
            });

            addLog(`Trasaction Submited: ${transaction_hash.slice(0, 10)}...`);
            addLog("Waiting for Acceptance...");

            await provider?.waitForTransaction(transaction_hash);

            setStatus("RELAYING");
            addLog("Assets Locked. Waiting for Settlement Agent Relay...");

            // 3. Simulate Relay (Backend would pick this up)
            setTimeout(() => {
                setStatus("SUCCESS");
                addLog("Funds Relayed to Aptos Wallet! 🚀");
            }, 3000);

        } catch (e: any) {
            console.error(e);
            setStatus("FAILED");
            addLog(`Error: ${e.message}`);
        }
    };

    return (
        <div className="glass-panel p-6 rounded-2xl border border-border-subtle relative overflow-hidden">
            <h2 className="text-xl font-display font-medium mb-6 flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent-primary" />
                Liquidity Bridge
            </h2>

            {/* Wallet Connection */}
            <div className="mb-6">
                {!isConnected ? (
                    <button
                        onClick={connectWallet}
                        className="w-full py-3 bg-accent-primary/10 border border-accent-primary/20 text-accent-primary rounded-xl font-medium hover:bg-accent-primary/20 transition-all flex items-center justify-center gap-2"
                    >
                        <Wallet className="w-4 h-4" />
                        Connect Starknet Wallet
                    </button>
                ) : (
                    <div className="px-4 py-3 bg-bg-tertiary rounded-xl border border-border-medium flex justify-between items-center bg-gray-900/40">
                        <div className="flex flex-col">
                            <span className="text-xs text-text-tertiary uppercase">Starknet Source</span>
                            <span className="font-mono text-sm text-text-primary">
                                {address?.slice(0, 6)}...{address?.slice(-4)}
                            </span>
                        </div>
                        <div className="text-right">
                            <span className="text-xs text-text-tertiary">Balance</span>
                            <div className="font-bold text-accent-primary">{starknetBalance} ETH</div>
                        </div>
                    </div>
                )}
            </div>

            {/* Bridge Input */}
            <div className="relative mb-6">
                <div className="flex justify-between items-center mb-2">
                    <label className="text-xs text-text-tertiary uppercase">Amount to Bridge</label>
                    <div className="text-xs text-text-tertiary">Max: 5.0 ETH</div>
                </div>

                <div className="flex gap-4 items-center">
                    <div className="relative flex-1">
                        <input
                            type="number"
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                            placeholder="0.0"
                            className="w-full bg-bg-tertiary border border-border-medium rounded-xl px-4 py-3 text-lg font-mono placeholder-text-tertiary focus:outline-none focus:border-accent-primary transition-colors"
                            disabled={!isConnected || status === 'LOCKING'}
                        />
                        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-text-tertiary font-bold">ETH</span>
                    </div>

                    <div className="flex items-center justify-center">
                        <ArrowRight className="text-text-tertiary w-6 h-6 animate-pulse" />
                    </div>

                    <div className="relative flex-1 opacity-60">
                        <div className="w-full bg-bg-tertiary border border-border-medium rounded-xl px-4 py-3 text-lg font-mono text-text-tertiary select-none">
                            {amount || "0.0"}
                        </div>
                        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-text-tertiary font-bold">APT</span>
                    </div>
                </div>
            </div>

            {/* Action Button */}
            <button
                onClick={handleBridge}
                disabled={!isConnected || !amount || status === 'LOCKING'}
                className={`w-full py-4 rounded-xl font-bold tracking-wide uppercase transition-all shadow-lg ${status === 'LOCKING' ? 'bg-bg-tertiary text-text-tertiary cursor-wait' :
                        status === 'SUCCESS' ? 'bg-green-500/20 text-green-400 border border-green-500/50' :
                            'bg-accent-primary text-bg-primary hover:shadow-[0_0_20px_rgba(0,255,163,0.3)]'
                    }`}
            >
                {status === 'IDLE' && 'Bridge Assets'}
                {status === 'LOCKING' && 'Locking Assets...'}
                {status === 'RELAYING' && 'Relaying...'}
                {status === 'SUCCESS' && 'Success!'}
                {status === 'FAILED' && 'Retry'}
            </button>

            {/* Logs */}
            <div className="mt-6 font-mono text-xs text-text-tertiary space-y-1 max-h-32 overflow-y-auto">
                {logs.map((log, i) => (
                    <div key={i} className="flex gap-2">
                        <span className="opacity-50">{new Date().toLocaleTimeString()}</span>
                        <span>{log}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
