'use client';

import { motion } from 'framer-motion';
import { ArrowRightLeft, ArrowDown, ArrowUp, Settings, ShieldCheck, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { ConnectButton } from '@rainbow-me/rainbowkit';

import { useState } from 'react';
import DepositModal from './DepositModal';
import WithdrawModal from './WithdrawModal';
import SettingsModal from './SettingsModal';

interface TreasuryCardProps {
    balance: {
        totalUsd: number;
        apt: number;
        usdc: number;
    };
    address: string;
}

export default function TreasuryCard({ balance, address }: TreasuryCardProps) {
    const [isDepositOpen, setIsDepositOpen] = useState(false);
    const [isWithdrawOpen, setIsWithdrawOpen] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    return (
        <div className="treasury-card p-8 rounded-2xl relative overflow-hidden">
            {/* Card Header */}
            {/* Card Header */}
            <div className="flex justify-between items-start mb-8">
                <div>
                    <div className="font-display text-lg font-bold text-text-primary uppercase tracking-wider mb-1">
                        CAPP Treasury
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-accent-primary animate-pulse"></span>
                        <span className="text-xs font-mono text-accent-primary tracking-widest uppercase">Multi-Chain Active</span>
                    </div>
                </div>

                {/* Wallet Connect */}
                <div>
                    <ConnectButton showBalance={false} accountStatus="address" chainStatus="icon" />
                </div>
            </div>

            {/* Balance Display */}
            <div className="mb-12">
                <div className="text-xs text-text-tertiary uppercase tracking-widest mb-2 font-mono">
                    Total Value (USD)
                </div>
                <div className="font-display text-6xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-br from-white to-text-secondary mb-2">
                    ${balance.totalUsd.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <div className="flex items-center gap-1 text-sm font-medium text-color-success">
                    <TrendingUp className="w-4 h-4" />
                    +$12,450 (24h)
                </div>
            </div>

            {/* Asset Allocation Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div className="p-4 bg-bg-tertiary border border-border-subtle rounded-xl hover:border-accent-primary transition-colors group">
                    <div className="text-[10px] text-text-tertiary uppercase tracking-widest mb-1">USDC</div>
                    <div className="font-display text-xl font-semibold mb-1">${(balance.totalUsd * 0.9).toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
                    <div className="text-xs text-text-secondary">90% • Stable</div>
                </div>
                <div className="p-4 bg-bg-tertiary border border-border-subtle rounded-xl hover:border-accent-primary transition-colors group">
                    <div className="text-[10px] text-text-tertiary uppercase tracking-widest mb-1">APT</div>
                    <div className="font-display text-xl font-semibold mb-1">${balance.apt.toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
                    <div className="text-xs text-text-secondary">9% • Growth</div>
                </div>
                <div className="p-4 bg-bg-tertiary border border-border-subtle rounded-xl hover:border-accent-primary transition-colors group">
                    <div className="text-[10px] text-text-tertiary uppercase tracking-widest mb-1">ETH</div>
                    <div className="font-display text-xl font-semibold mb-1">$8,036</div>
                    <div className="text-xs text-text-secondary">1% • Reserve</div>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <button
                    onClick={() => setIsDepositOpen(true)}
                    className="flex items-center justify-center gap-2 px-6 py-4 bg-bg-secondary border border-border-medium rounded-xl text-sm font-medium uppercase tracking-wide hover:border-accent-primary hover:text-accent-primary transition-all text-text-secondary"
                >
                    <ArrowDown className="w-4 h-4" />
                    Deposit
                </button>
                <button
                    onClick={() => setIsWithdrawOpen(true)}
                    className="flex items-center justify-center gap-2 px-6 py-4 bg-bg-secondary border border-border-medium rounded-xl text-sm font-medium uppercase tracking-wide hover:border-accent-primary hover:text-accent-primary transition-all text-text-secondary"
                >
                    <ArrowUp className="w-4 h-4" />
                    Withdraw
                </button>
                <Link href="/send" className="flex items-center justify-center gap-2 px-6 py-4 rounded-xl text-sm font-bold uppercase tracking-wide btn-gradient transition-all">
                    <ArrowRightLeft className="w-4 h-4" />
                    Transfer
                </Link>
                <button
                    onClick={() => setIsSettingsOpen(true)}
                    className="flex items-center justify-center gap-2 px-6 py-4 bg-bg-secondary border border-border-medium rounded-xl text-sm font-medium uppercase tracking-wide hover:border-accent-primary hover:text-accent-primary transition-all text-text-secondary"
                >
                    <Settings className="w-4 h-4" />
                    Settings
                </button>
            </div>

            <DepositModal isOpen={isDepositOpen} onClose={() => setIsDepositOpen(false)} address={address} />
            <WithdrawModal isOpen={isWithdrawOpen} onClose={() => setIsWithdrawOpen(false)} />
            <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        </div>
    );
}
