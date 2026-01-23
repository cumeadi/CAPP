"use client";

import { useState } from "react";
import { ArrowLeft, Globe, Wifi, Plus, Trash2, Loader2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/Shared/Button";
import { clsx } from "clsx";
import { useSettings } from "@/components/Context/SettingsContext";

export default function NetworksSettingsPage() {
    const { testnetMode, setTestnetMode, customNetworks, addCustomNetwork, removeCustomNetwork } = useSettings();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [newRpc, setNewRpc] = useState({ name: "", url: "" });
    const [loading, setLoading] = useState(false);

    const networks = [
        { name: "Ethereum", chainId: 1, status: "Operational", color: "text-green-400", type: "Mainnet" },
        { name: "Starknet", chainId: "SN_MAIN", status: "Operational", color: "text-green-400", type: "Layer 2" },
        { name: "Aptos", chainId: 1, status: "Operational", color: "text-green-400", type: "Move VM" },
        { name: "Polygon", chainId: 137, status: "Congested", color: "text-yellow-400", type: "Sidechain" },
    ];

    const handleAddRpc = async () => {
        if (!newRpc.name || !newRpc.url) return;
        setLoading(true);
        // Simulate connection check
        await new Promise(r => setTimeout(r, 600));

        addCustomNetwork({
            id: Date.now().toString(),
            name: newRpc.name,
            rpcUrl: newRpc.url
        });
        setNewRpc({ name: "", url: "" });
        setIsModalOpen(false);
        setLoading(false);
    };

    return (
        <div className="max-w-2xl mx-auto animate-in slide-in-from-right-4 duration-500 relative">

            <div className="mb-8 flex items-center gap-4">
                <Link href="/settings">
                    <div className="p-2 rounded-full border border-[var(--border-medium)] hover:bg-[var(--bg-tertiary)] text-white transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </div>
                </Link>
                <h1 className="text-2xl font-bold text-white tracking-widest">NETWORKS</h1>
            </div>

            <div className="space-y-6">

                {/* Testnet Toggle */}
                <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex items-center justify-between">
                    <div className="flex gap-4 items-center">
                        <div className="p-2 bg-[var(--bg-tertiary)] rounded-lg text-[var(--accent-cyan)]">
                            <Globe className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 className="text-base font-bold text-white">Developer Mode</h3>
                            <p className="text-xs text-[var(--text-secondary)]">Show Testnets</p>
                        </div>
                    </div>
                    <button
                        onClick={() => setTestnetMode(!testnetMode)}
                        className={clsx(
                            "w-10 h-6 rounded-full transition-all duration-300 relative border",
                            testnetMode ? "bg-[var(--accent-cyan)] border-[var(--accent-cyan)]" : "bg-[var(--bg-primary)] border-[var(--border-medium)]"
                        )}
                    >
                        <div className={clsx(
                            "absolute top-1 left-1 w-3.5 h-3.5 rounded-full bg-white transition-transform duration-300 shadow-sm",
                            testnetMode ? "translate-x-4" : "translate-x-0"
                        )} />
                    </button>
                </div>

                <div className="h-[1px] bg-[var(--border-subtle)] w-full" />

                {/* Network List */}
                <div className="space-y-3">
                    <h3 className="text-xs font-bold text-[var(--text-tertiary)] uppercase tracking-widest ml-1">Active Networks</h3>

                    {networks.map((net) => (
                        <div key={net.name} className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex items-center justify-between group hover:border-[var(--accent-primary)] transition-colors">
                            <div className="flex items-center gap-4">
                                <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]" />
                                <div>
                                    <h4 className="text-white font-mono font-bold text-sm flex items-center gap-2">
                                        {net.name}
                                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-medium)]">{net.type}</span>
                                    </h4>
                                    <p className="text-xs text-[var(--text-secondary)] mt-0.5">Chain ID: {net.chainId}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <span className={clsx("text-xs font-mono", net.color)}>{net.status}</span>
                                <Wifi className="w-4 h-4 text-[var(--text-tertiary)]" />
                            </div>
                        </div>
                    ))}

                    {/* Custom Networks */}
                    {customNetworks && customNetworks.map((net) => (
                        <div key={net.id} className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex items-center justify-between group hover:border-[var(--accent-primary)] transition-colors">
                            <div className="flex items-center gap-4">
                                <div className="w-2 h-2 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.4)]" />
                                <div>
                                    <h4 className="text-white font-mono font-bold text-sm flex items-center gap-2">
                                        {net.name}
                                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-medium)]">Custom</span>
                                    </h4>
                                    <p className="text-xs text-[var(--text-secondary)] mt-0.5 text-ellipsis overflow-hidden w-40">{net.rpcUrl}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => removeCustomNetwork(net.id)}
                                    className="p-2 text-[var(--text-tertiary)] hover:text-red-400 transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                                <Wifi className="w-4 h-4 text-[var(--text-tertiary)]" />
                            </div>
                        </div>
                    ))}

                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="w-full p-4 rounded-xl border border-dashed border-[var(--border-medium)] text-[var(--text-secondary)] hover:text-white hover:border-[var(--accent-cyan)] hover:bg-[var(--accent-cyan)]/5 transition-all flex items-center justify-center gap-2 text-sm font-bold"
                    >
                        <Plus className="w-4 h-4" />
                        Add Custom RPC
                    </button>
                </div>

            </div>

            {/* Add RPC Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] p-6 rounded-2xl w-full max-w-md shadow-2xl">
                        <h2 className="text-xl font-bold text-white mb-4">Add Custom Network</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="text-xs text-[var(--text-secondary)] mb-1 block">Network Name</label>
                                <input
                                    className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-medium)] rounded-lg p-3 text-white text-sm focus:border-[var(--accent-cyan)] outline-none transition-colors"
                                    placeholder="e.g. My Private Chain"
                                    value={newRpc.name}
                                    onChange={(e) => setNewRpc({ ...newRpc, name: e.target.value })}
                                    autoFocus
                                />
                            </div>
                            <div>
                                <label className="text-xs text-[var(--text-secondary)] mb-1 block">RPC URL</label>
                                <input
                                    className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-medium)] rounded-lg p-3 text-white text-sm focus:border-[var(--accent-cyan)] outline-none transition-colors"
                                    placeholder="https://"
                                    value={newRpc.url}
                                    onChange={(e) => setNewRpc({ ...newRpc, url: e.target.value })}
                                />
                            </div>
                            <div className="flex gap-3 pt-4">
                                <Button
                                    variant="ghost"
                                    className="flex-1 bg-[var(--bg-tertiary)] text-white hover:bg-[var(--bg-tertiary)]/80"
                                    onClick={() => setIsModalOpen(false)}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    icon={loading ? Loader2 : Plus}
                                    disabled={loading}
                                    className={clsx("flex-1 bg-[var(--accent-cyan)] text-black hover:bg-[var(--accent-cyan)]/90", loading && "animate-pulse")}
                                    onClick={handleAddRpc}
                                >
                                    {loading ? "Adding..." : "Add Network"}
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
