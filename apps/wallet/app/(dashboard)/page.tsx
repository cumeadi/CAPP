"use client";

import { Send, Download, QrCode, Settings, Wallet } from "lucide-react";
import { Button } from "@/components/Shared/Button";
import { AssetCard } from "@/components/Dashboard/AssetCard";
import Link from "next/link";
import { useAccount, useBalance, useConnect, useDisconnect } from "wagmi";
import { injected } from "wagmi/connectors";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const { address, isConnected } = useAccount();
  const { connect } = useConnect();
  const { disconnect } = useDisconnect();

  // Fetch real ETH Balance
  const { data: ethBalance } = useBalance({
    address: address,
  });

  // Client-side mounted state check to avoid hydration mismatch
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null; // Avoid hydration mismatch on initial load

  return (
    <div className="space-y-12 animate-in fade-in duration-500">

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold text-white tracking-widest flex items-center gap-3">
            <Wallet className="w-6 h-6 text-[var(--accent-cyan)]" />
            CAPP WALLET
          </h1>
          <p className="text-[var(--text-secondary)] text-sm font-mono mt-2">
            {isConnected ? `Welcome back, ${address?.slice(0, 6)}...${address?.slice(-4)}` : "Please connect your wallet"}
          </p>
        </div>
        <div className="px-3 py-1 bg-[var(--bg-tertiary)] rounded-full border border-[var(--border-medium)] flex items-center gap-2">
          {isConnected ? (
            <div className="flex items-center gap-2 cursor-pointer" onClick={() => disconnect()}>
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs text-white font-mono">Connected</span>
            </div>
          ) : (
            <Button variant="primary" size="sm" onClick={() => connect({ connector: injected() })}>
              CONNECT WALLET
            </Button>
          )}
        </div>
      </div>

      {/* Hero Section: Total Balance */}
      <div className="text-center py-10 relative">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-[var(--accent-primary)]/10 blur-[100px] -z-10 rounded-full pointer-events-none" />

        <p className="text-[var(--accent-cyan)] font-mono text-sm tracking-[0.2em] mb-4 uppercase">Total Portfolio Value</p>
        <h2 className="text-6xl md:text-7xl font-bold text-white tracking-tighter mb-4 text-glow font-mono">
          {isConnected ? `$${ethBalance ? (Number(ethBalance.value) / 10 ** ethBalance.decimals * 2000).toFixed(2) : "0.00"}` : "$0.00"}
        </h2>
        <div className="flex items-center justify-center gap-2 text-green-400 bg-[rgba(0,255,179,0.1)] w-fit mx-auto px-4 py-1 rounded-full border border-[rgba(0,255,179,0.2)]">
          <span className="font-bold">+$0.00</span>
          <span className="text-xs opacity-80">(24h)</span>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap justify-center gap-4">
        <Link href="/send">
          <Button variant="outline" size="lg" icon={Send} className="min-w-[160px] border-[var(--accent-cyan)] text-[var(--accent-cyan)] hover:bg-[var(--accent-cyan)] hover:text-black hover:shadow-[0_0_20px_rgba(0,255,179,0.4)]" disabled={!isConnected}>SEND</Button>
        </Link>
        <Button variant="secondary" size="lg" icon={Download} className="min-w-[160px]" disabled={!isConnected}>DEPOSIT</Button>
        <Link href="/receive">
          <Button variant="secondary" size="lg" icon={QrCode} className="min-w-[160px]" disabled={!isConnected}>RECEIVE</Button>
        </Link>
        <Link href="/settings">
          <Button variant="secondary" size="lg" icon={Settings} className="min-w-[160px]" disabled={!isConnected}>SETTINGS</Button>
        </Link>
      </div>

      {/* Asset Cards */}
      {isConnected && (
        <div className="space-y-6">
          <div className="flex justify-between items-end border-b border-[var(--border-subtle)] pb-4">
            <h3 className="text-lg font-bold text-white tracking-wider">YOUR ASSETS</h3>
            <span className="text-xs text-[var(--text-secondary)] font-mono cursor-pointer hover:text-[var(--accent-cyan)]">View All</span>
          </div>

          <div className="flex gap-6 overflow-x-auto pb-8 -mx-4 px-4 custom-scrollbar snap-x">
            <AssetCard
              symbol="ETH"
              balance={`${ethBalance ? (Number(ethBalance.value) / 10 ** ethBalance.decimals).toFixed(4) : "0"} ETH`}
              value={`$${ethBalance ? (Number(ethBalance.value) / 10 ** ethBalance.decimals * 2000).toFixed(2) : "0.00"}`}
              change={0.0}
              icon={<div className="text-purple-400">Ξ</div>}
            />
            {/* Mock other assets for now until we have token hooks */}
            <AssetCard
              symbol="USDC"
              balance="0 USDC"
              value="$0.00"
              change={0.00}
              icon={<div className="text-blue-400">$</div>}
            />
          </div>
        </div>
      )}

    </div>
  );
}
