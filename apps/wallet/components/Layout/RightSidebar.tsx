"use client";

import { Activity, ArrowUpRight, ArrowDownLeft, CheckCircle2 } from "lucide-react";

export function RightSidebar() {
    return (
        <aside className="w-80 h-screen sticky top-0 border-l border-[var(--border-medium)] bg-[var(--bg-secondary)]/50 backdrop-blur-sm hidden xl:flex flex-col p-6 z-20">

            {/* Network Status Module */}
            <div className="mb-8">
                <h3 className="text-xs font-bold text-[var(--text-tertiary)] mb-4 tracking-widest flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-[var(--accent-cyan)] animate-pulse shadow-[0_0_8px_var(--accent-cyan)]" />
                    NETWORK STATUS
                </h3>
                <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                        <span className="text-sm font-medium">Ethereum</span>
                        <span className="text-xs text-[var(--accent-cyan)]">Operational</span>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                        <span className="text-sm font-medium">Polygon</span>
                        <span className="text-xs text-[var(--accent-cyan)]">Operational</span>
                    </div>
                </div>
            </div>

            {/* Transaction Feed */}
            <div className="flex-1 overflow-hidden flex flex-col">
                <h3 className="text-xs font-bold text-[var(--text-tertiary)] mb-4 tracking-widest flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    TRANSACTION FEED
                </h3>

                <div className="space-y-4 overflow-y-auto pr-2 custom-scrollbar flex-1">
                    {/* Mock Tx 1 */}
                    <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] transition-colors group">
                        <div className="flex items-start justify-between mb-2">
                            <div className="p-2 rounded-lg bg-[var(--bg-tertiary)] text-[var(--accent-cyan)]">
                                <ArrowUpRight className="w-4 h-4" />
                            </div>
                            <span className="text-xs text-[var(--text-tertiary)] mt-1">10:45 AM</span>
                        </div>
                        <div className="font-bold text-white mb-1 group-hover:text-[var(--accent-cyan)] transition-colors">Sent 0.1 ETH</div>
                        <div className="text-xs text-[var(--text-secondary)] mb-2 font-mono">To 0xAB...CDEF</div>
                        <div className="flex items-center gap-1 text-[var(--accent-cyan)] text-[10px] uppercase tracking-wider">
                            <CheckCircle2 className="w-3 h-3" /> Confirmed
                        </div>
                    </div>

                    {/* Mock Tx 2 */}
                    <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] transition-colors group">
                        <div className="flex items-start justify-between mb-2">
                            <div className="p-2 rounded-lg bg-[var(--bg-tertiary)] text-[var(--accent-secondary)]">
                                <ArrowDownLeft className="w-4 h-4" />
                            </div>
                            <span className="text-xs text-[var(--text-tertiary)] mt-1">09:30 AM</span>
                        </div>
                        <div className="font-bold text-white mb-1 group-hover:text-[var(--accent-cyan)] transition-colors">Received 1,000 USDC</div>
                        <div className="text-xs text-[var(--text-secondary)] mb-2 font-mono">From 0x12...3456</div>
                        <div className="flex items-center gap-1 text-[var(--accent-cyan)] text-[10px] uppercase tracking-wider">
                            <CheckCircle2 className="w-3 h-3" /> Confirmed
                        </div>
                    </div>

                    {/* Mock Tx 3 */}
                    <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] transition-colors group opacity-75">
                        <div className="flex items-start justify-between mb-2">
                            <div className="p-2 rounded-lg bg-[var(--bg-tertiary)] text-[var(--accent-warning)]">
                                <ArrowUpRight className="w-4 h-4" />
                            </div>
                            <span className="text-xs text-[var(--text-tertiary)] mt-1">Yesterday</span>
                        </div>
                        <div className="font-bold text-white mb-1 group-hover:text-[var(--accent-cyan)] transition-colors">Minted NFT #456</div>
                        <div className="text-xs text-[var(--text-secondary)] mb-2 font-mono">CAPP Pass</div>
                        <div className="flex items-center gap-1 text-[var(--accent-cyan)] text-[10px] uppercase tracking-wider">
                            <CheckCircle2 className="w-3 h-3" /> Confirmed
                        </div>
                    </div>

                </div>
            </div>
        </aside>
    );
}
