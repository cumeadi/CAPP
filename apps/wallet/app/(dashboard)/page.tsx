"use client";

import { Send, Download, QrCode, Settings, Wallet, TrendingUp, Link as LinkIcon, Unplug } from "lucide-react";
import { Button } from "@/components/Shared/Button";
import { AssetCard } from "@/components/Dashboard/AssetCard";
import Link from "next/link";
import { useAccount, useBalance } from "wagmi";
import { useEffect, useState } from "react";
import { api, YieldStatsResponse } from "@/services/api";
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useWallet } from "@aptos-labs/wallet-adapter-react";

export default function DashboardPage() {
  const { address, isConnected } = useAccount();

  // Aptos Wallet Hook
  const { account: aptosAccount, connected: isAptosConnected, connect: connectAptos, disconnect: disconnectAptos, wallets: aptosWallets } = useWallet();
  const [aptosBalance, setAptosBalance] = useState<number>(0);

  // Fetch real ETH Balance
  const { data: ethBalance } = useBalance({
    address: address,
  });

  const [mounted, setMounted] = useState(false);
  const [yieldStats, setYieldStats] = useState<YieldStatsResponse | null>(null);

  useEffect(() => {
    setMounted(true);
    fetchYieldStats();
  }, []);

  useEffect(() => {
    if (isAptosConnected && aptosAccount?.address) {
      fetchAptosBalance(aptosAccount.address.toString());
    }
  }, [isAptosConnected, aptosAccount]);

  const fetchAptosBalance = async (address: string) => {
    try {
      const response = await fetch(`https://api.testnet.aptoslabs.com/v1/accounts/${address}/resource/0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>`);
      if (response.ok) {
        const data = await response.json();
        setAptosBalance(Number(data.data.coin.value) / 100_000_000);
      } else {
        setAptosBalance(0);
      }
    } catch (e) {
      console.error("Failed to fetch Aptos balance", e);
      setAptosBalance(0);
    }
  };

  const fetchYieldStats = async () => {
    try {
      const stats = await api.getYieldStats();
      setYieldStats(stats);
    } catch (e) {
      console.error("Failed to fetch yield stats", e);
    }
  };

  const handleConnectAptos = () => {
    console.log("Available Aptos Wallets:", aptosWallets);

    // 1. Find installed wallets (ReadyState.Installed is best, but string check for now)
    // Note: readyState is usually "Installed", "NotDetected", "Loadable"
    const installedWallet = aptosWallets.find(w => w.readyState === "Installed");

    if (installedWallet) {
      console.log("Connecting to installed wallet:", installedWallet.name);
      connectAptos(installedWallet.name);
    } else {
      // Fallback: Try "Petra" specifically if it exists in list even if readyState is weird
      const petra = aptosWallets.find(w => w.name === "Petra" || w.name === "Petra Wallet");
      if (petra) {
        console.log("Connecting to Petra fallback:", petra.name);
        connectAptos(petra.name);
      } else {
        alert("No installed Aptos wallet found. Please install Petra from https://petra.app/");
      }
    }
  };

  if (!mounted) return null;

  // Calculate Total Value
  const ethValue = ethBalance ? (Number(ethBalance.value) / 10 ** ethBalance.decimals * 2000) : 0; // Mock ETH price $2000
  const usdcValue = (yieldStats?.hot_wallet_balance || 0) + (yieldStats?.yield_balance || 0);

  // Use connected balance if available, otherwise backend stats
  const displayAptosBalance = isAptosConnected ? aptosBalance : (yieldStats?.aptos_balance || 0);
  const aptosValue = displayAptosBalance * 10; // Mock APT price $10

  const totalValue = ethValue + usdcValue + aptosValue;

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

        <div className="flex gap-2">
          {/* Aptos Connect Button */}
          {!isAptosConnected ? (
            <Button variant="outline" size="sm" onClick={handleConnectAptos} icon={LinkIcon} className="bg-[var(--bg-tertiary)] border-[var(--border-medium)] text-teal-400 hover:border-teal-400">
              LINK APTOS
            </Button>
          ) : (
            <div className="px-3 py-1 bg-[var(--bg-tertiary)] rounded-full border border-teal-500/50 flex items-center gap-2 cursor-pointer" onClick={() => disconnectAptos()}>
              <div className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
              <span className="text-xs text-white font-mono">APT: {aptosAccount?.address?.toString().slice(0, 4)}...{aptosAccount?.address?.toString().slice(-4)}</span>
              <Unplug className="w-3 h-3 text-red-400 ml-1 hover:text-red-300" />
            </div>
          )}

          <ConnectButton.Custom>
            {/* ... (RainbowKit Custom Button Implementation remains same, assuming I can keep it or better to just let it replace the whole block) */}
            {/* Since I am replacing the whole file content or large chunk, I'll paste the previous RainbowKit code here */}
            {({
              account,
              chain,
              openAccountModal,
              openChainModal,
              openConnectModal,
              authenticationStatus,
              mounted,
            }) => {
              const ready = mounted && authenticationStatus !== 'loading';
              const connected =
                ready &&
                account &&
                chain &&
                (!authenticationStatus ||
                  authenticationStatus === 'authenticated');

              return (
                <div
                  {...(!ready && {
                    'aria-hidden': true,
                    'style': {
                      opacity: 0,
                      pointerEvents: 'none',
                      userSelect: 'none',
                    },
                  })}
                >
                  {(() => {
                    if (!connected) {
                      return (
                        <div className="px-3 py-1 bg-[var(--bg-tertiary)] rounded-full border border-[var(--border-medium)] flex items-center gap-2">
                          <Button variant="primary" size="sm" onClick={openConnectModal}>
                            CONNECT EVM
                          </Button>
                        </div>
                      );
                    }

                    if (chain.unsupported) {
                      return (
                        <button onClick={openChainModal} type="button" className="px-3 py-1 bg-red-500/20 text-red-400 rounded-full border border-red-500/50 text-xs font-bold">
                          Wrong network
                        </button>
                      );
                    }

                    return (
                      <div className="flex gap-3">
                        <button
                          onClick={openChainModal}
                          style={{ display: 'flex', alignItems: 'center' }}
                          type="button"
                          className="px-3 py-1 bg-[var(--bg-tertiary)] rounded-full border border-[var(--border-medium)] flex items-center gap-2 text-white hover:border-[var(--accent-cyan)] transition-colors"
                        >
                          {chain.hasIcon && (
                            <div
                              style={{
                                background: chain.iconBackground,
                                width: 12,
                                height: 12,
                                borderRadius: 999,
                                overflow: 'hidden',
                                marginRight: 4,
                              }}
                            >
                              {chain.iconUrl && (
                                <img
                                  alt={chain.name ?? 'Chain icon'}
                                  src={chain.iconUrl}
                                  style={{ width: 12, height: 12 }}
                                />
                              )}
                            </div>
                          )}
                          <span className="text-xs font-bold">{chain.name}</span>
                        </button>

                        <div className="px-3 py-1 bg-[var(--bg-tertiary)] rounded-full border border-[var(--border-medium)] flex items-center gap-2">
                          <div className="flex items-center gap-2 cursor-pointer" onClick={openAccountModal}>
                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                            <span className="text-xs text-white font-mono">{account.displayName}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              );
            }}
          </ConnectButton.Custom>
        </div>
      </div>

      {/* Hero Section: Total Balance */}
      <div className="text-center py-10 relative">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-[var(--accent-primary)]/10 blur-[100px] -z-10 rounded-full pointer-events-none" />

        <p className="text-[var(--accent-cyan)] font-mono text-sm tracking-[0.2em] mb-4 uppercase">Total Portfolio Value</p>
        <h2 className="text-6xl md:text-7xl font-bold text-white tracking-tighter mb-4 text-glow font-mono">
          {(isConnected || isAptosConnected) ? `$${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "$0.00"}
        </h2>
        {yieldStats?.is_sweeping && (
          <div className="flex items-center justify-center gap-2 text-[var(--accent-cyan)] bg-[rgba(0,255,179,0.1)] w-fit mx-auto px-4 py-1 rounded-full border border-[rgba(0,255,179,0.2)] animate-pulse">
            <TrendingUp className="w-4 h-4" />
            <span className="font-bold text-xs tracking-wider">SMART SWEEP ACTIVE ({yieldStats.apy}% APY)</span>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap justify-center gap-4">
        <Link href="/send">
          <Button variant="outline" size="lg" icon={Send} className="min-w-[160px] border-[var(--accent-cyan)] text-[var(--accent-cyan)] hover:bg-[var(--accent-cyan)] hover:text-black hover:shadow-[0_0_20px_rgba(0,255,179,0.4)]" disabled={!isConnected && !isAptosConnected}>SEND</Button>
        </Link>
        <Button variant="secondary" size="lg" icon={Download} className="min-w-[160px]" disabled={!isConnected && !isAptosConnected}>DEPOSIT</Button>
        <Link href="/receive">
          <Button variant="secondary" size="lg" icon={QrCode} className="min-w-[160px]" disabled={!isConnected && !isAptosConnected}>RECEIVE</Button>
        </Link>
        <Link href="/settings">
          <Button variant="secondary" size="lg" icon={Settings} className="min-w-[160px]" disabled={!isConnected && !isAptosConnected}>SETTINGS</Button>
        </Link>
      </div>

      {/* Asset Cards */}
      {(isConnected || isAptosConnected) && (
        <div className="space-y-6">
          <div className="flex justify-between items-end border-b border-[var(--border-subtle)] pb-4">
            <h3 className="text-lg font-bold text-white tracking-wider">YOUR ASSETS</h3>
            <span className="text-xs text-[var(--text-secondary)] font-mono cursor-pointer hover:text-[var(--accent-cyan)]">View All</span>
          </div>

          <div className="flex gap-6 overflow-x-auto pb-8 -mx-4 px-4 custom-scrollbar snap-x">
            <AssetCard
              symbol="ETH"
              balance={`${ethBalance ? (Number(ethBalance.value) / 10 ** ethBalance.decimals).toFixed(4) : "0"} ETH`}
              value={`$${ethValue.toFixed(2)}`}
              change={1.2}
              icon={<div className="text-purple-400">Ξ</div>}
            />

            <AssetCard
              symbol="USDC"
              balance={`${((yieldStats?.hot_wallet_balance || 0) + (yieldStats?.yield_balance || 0)).toLocaleString()} USDC`}
              value={`$${((yieldStats?.hot_wallet_balance || 0) + (yieldStats?.yield_balance || 0)).toLocaleString()}`}
              change={0.01}
              icon={<div className="text-blue-400">$</div>}
            />

            <AssetCard
              symbol="APT"
              balance={`${displayAptosBalance.toLocaleString()} APT`}
              value={`$${(displayAptosBalance * 10).toLocaleString()}`}
              change={-2.5}
              icon={<div className="text-teal-400">A</div>}
            />
          </div>
        </div>
      )}

    </div>
  );
}

