'use client';

import { motion } from 'framer-motion';
import { ArrowRightLeft, ArrowDown, ArrowUp, Settings, Send, TrendingUp, CreditCard } from 'lucide-react';
import Link from 'next/link';
import { ConnectButton } from '@rainbow-me/rainbowkit';

import { useState, useEffect } from 'react';
import DepositModal from './DepositModal';
import WithdrawModal from './WithdrawModal';
import SettingsModal from './SettingsModal';
import BridgeModal from './BridgeModal';
import TransferModal from './TransferModal';

import { FiatModal } from './FiatModal';
import { api } from '@/services/api';
import { useTreasury } from '@/hooks/useTreasury';

interface TreasuryCardProps {
    balance: {
        totalUsd: number;
        apt: number;
        usdc: number;
        eth: number;
        starknet?: number;
        baseUsdc?: number;
        arbitrumUsdc?: number;
    };
    address: string;
}

export default function TreasuryCard({ balance, address }: TreasuryCardProps) {
    const [isDepositOpen, setIsDepositOpen] = useState(false);
    const [isWithdrawOpen, setIsWithdrawOpen] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isBridgeOpen, setIsBridgeOpen] = useState(false);
    const [isTransferOpen, setIsTransferOpen] = useState(false);
    const [isFiatOpen, setIsFiatOpen] = useState(false);

    const { data: yieldStats, loading } = useTreasury();

    // Fallback to prop balance if yield stats not ready or if specific value missing
    const totalValue = yieldStats?.total_value_usd ?? balance.totalUsd;
    const hotBalance = yieldStats?.hot_wallet_balance ?? balance.totalUsd;
    const yieldBalance = yieldStats?.yield_balance ?? 0;

    return (
        <div className="treasury-card p-4 md:p-8 rounded-2xl relative overflow-hidden">
            {/* Card Header and Balance sections unchanged... */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
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
                <div className="w-full md:w-auto">
                    <ConnectButton showBalance={false} accountStatus="address" chainStatus="icon" />
                </div>
            </div>

            {/* Balance Display */}
            <div className="mb-12">
                <div className="text-xs text-text-tertiary uppercase tracking-widest mb-2 font-mono">
                    Total Value (USD)
                </div>
                <div className="font-display text-4xl md:text-6xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-br from-white to-text-secondary mb-2">
                    ${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <div className="flex items-center gap-4 text-sm font-medium">
                    <div className="text-color-success flex items-center gap-1">
                        <TrendingUp className="w-4 h-4" />
                        +$12,450 (24h)
                    </div>
                    {yieldStats && (
                        <div className="flex items-center gap-2 text-text-secondary border-l border-border-medium pl-4">
                            <span className="text-xs uppercase tracking-widest">Smart Sweep:</span>
                            <span className="text-accent-primary font-bold">Everything &gt; $15k Auto-Yielding</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Asset Allocation Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div className="p-4 bg-bg-tertiary border border-border-subtle rounded-xl hover:border-accent-primary transition-colors group">
                    <div className="text-[10px] text-text-tertiary uppercase tracking-widest mb-1">Hot Wallet (Liquid)</div>
                    <div className="font-display text-xl font-semibold mb-1">${hotBalance.toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
                    <div className="text-xs text-text-secondary">Instant Settlement</div>
                </div>
                <div className="p-4 bg-bg-tertiary border border-border-subtle rounded-xl hover:border-accent-primary transition-colors group">
                    <div className="text-[10px] text-text-tertiary uppercase tracking-widest mb-1">Base USDC</div>
                    <div className="font-display text-xl font-semibold mb-1">${(balance.baseUsdc || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
                    <div className="text-xs text-text-secondary">L2 • Spending</div>
                </div>

                {/* Starknet Card */}
                <div className="p-4 bg-bg-tertiary border border-border-subtle rounded-xl hover:border-accent-secondary transition-colors group">
                    <div className="text-[10px] text-text-tertiary uppercase tracking-widest mb-1 text-accent-secondary">Starknet ETH</div>
                    <div className="font-display text-xl font-semibold mb-1">${(balance.starknet || 0).toLocaleString('en-US', { maximumFractionDigits: 4 })}</div>
                    <div className="text-xs text-text-secondary">ZK-Rollup • L2</div>
                </div>

                <div className="p-4 bg-bg-tertiary border border-border-subtle rounded-xl hover:border-color-success transition-colors group relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-1">
                        <div className="flex items-center gap-1 bg-color-success/10 text-color-success px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide">
                            <TrendingUp className="w-3 h-3" />
                            {yieldStats ? yieldStats.apy : 5.2}% APY
                        </div>
                    </div>
                    <div className="text-[10px] text-text-tertiary uppercase tracking-widest mb-1">Yield Protocol</div>
                    <div className="font-display text-xl font-semibold mb-1">${yieldBalance.toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
                    <div className="text-xs text-text-secondary flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-color-success animate-pulse"></span>
                        Aave V3 Strategy
                    </div>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <button
                    onClick={() => setIsTransferOpen(true)}
                    className="flex items-center justify-center gap-2 px-6 py-4 bg-bg-secondary border border-border-medium rounded-xl text-sm font-medium uppercase tracking-wide hover:border-accent-primary hover:text-accent-primary transition-all text-text-secondary"
                >
                    <Send className="w-4 h-4" />
                    Send
                </button>
                <button
                    onClick={() => setIsFiatOpen(true)}
                    className="flex items-center justify-center gap-2 px-6 py-4 bg-bg-secondary border border-border-medium rounded-xl text-sm font-medium uppercase tracking-wide hover:border-color-success hover:text-color-success transition-all text-text-secondary"
                >
                    <CreditCard className="w-4 h-4" />
                    Buy
                </button>
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
                <button
                    onClick={() => setIsBridgeOpen(true)}
                    className="flex items-center justify-center gap-2 px-6 py-4 bg-bg-secondary border border-border-medium rounded-xl text-sm font-medium uppercase tracking-wide hover:border-accent-secondary hover:text-accent-secondary transition-all text-text-secondary"
                >
                    <ArrowRightLeft className="w-4 h-4" />
                    Bridge
                </button>
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
            <BridgeModal isOpen={isBridgeOpen} onClose={() => setIsBridgeOpen(false)} address={address} />
            <TransferModal isOpen={isTransferOpen} onClose={() => setIsTransferOpen(false)} />
            <FiatModal isOpen={isFiatOpen} onClose={() => setIsFiatOpen(false)} />
        </div>
    );
}
