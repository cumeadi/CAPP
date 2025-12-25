'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAccount } from 'wagmi';
import TreasuryCard from '@/components/TreasuryCard';
import AiPanel from '@/components/AiPanel';
import TransferForm from '@/components/TransferForm';
import { api } from '@/services/api';

// Mock Data Types
interface MarketStatus {
   sentiment: string;
   volatility: string;
   aptPrice: number;
   reasoning: string;
}

export default function Home() {
   // State
   const { address, isConnected } = useAccount();
   const [marketStatus, setMarketStatus] = useState<MarketStatus>({
      sentiment: 'NEUTRAL',
      volatility: 'UNKNOWN',
      aptPrice: 0,
      reasoning: "Initializing analysis..."
   });

   const [view, setView] = useState<'DASHBOARD' | 'TRANSFER'>('DASHBOARD');
   const [isAuthenticated, setIsAuthenticated] = useState(false);

   const [balance, setBalance] = useState({
      totalUsd: 0,
      apt: 0,
      usdc: 0,
      eth: 0
   });

   // Auto-Hedge Toggle State
   const [autoHedge, setAutoHedge] = useState(true);

   // Feed State
   const [decisionFeed, setDecisionFeed] = useState<Array<{
      id: number;
      type: 'REBALANCE' | 'ANALYSIS' | 'APPROVAL' | 'USER';
      title: string;
      description: string;
      time: string;
      meta?: { label: string; value: string };
   }>>([
      {
         id: 1,
         type: 'ANALYSIS',
         title: 'Market Analysis Intialized',
         description: 'AI Analyst active. Monitoring APT/USD volatility.',
         time: 'Just now',
         meta: { label: 'Status', value: 'Active' }
      }
   ]);

   const [lastReasoning, setLastReasoning] = useState("");

   const handleAiAction = async (query: string) => {
      // 1. Add User Query to Feed
      const userMsgId = Date.now();
      setDecisionFeed(prev => [{
         id: userMsgId,
         type: 'USER',
         title: 'SYSTEM COMMAND',
         description: `> Executing: ${query}...`,
         time: 'Just now'
      }, ...prev]);

      try {
         // 2. Call API
         const res = await api.chatWithAnalyst(query);

         // 3. Add Analyst Response
         setDecisionFeed(prev => [{
            id: Date.now(),
            type: 'ANALYSIS',
            title: 'ANALYST',
            description: res.response,
            time: 'Just now'
         }, ...prev]);
      } catch (e) {
         console.error("Chat failed", e);
      }
   };




   useEffect(() => {
      const fetchData = async () => {
         try {
            const walletAddress = address || "0x123"; // Fallback to demo if not connected
            const [balanceData, marketData, polygonGas] = await Promise.all([
               api.getWalletBalance(walletAddress),
               api.analyzeMarket('APT'),
               api.getPolygonGas().catch(() => ({ gas_price_gwei: 0 }))
            ]);

            setBalance({
               totalUsd: (balanceData.balance_apt * 10.5) + balanceData.balance_usdc + (balanceData.balance_eth * 2800),
               apt: balanceData.balance_apt,
               usdc: balanceData.balance_usdc || 0,
               eth: balanceData.balance_eth || 0
            });

            const newReasoning = `${marketData.reasoning} [Gas: ${polygonGas.gas_price_gwei}]`;

            setMarketStatus({
               sentiment: marketData.recommendation,
               volatility: marketData.risk_level,
               aptPrice: 10.5,
               reasoning: newReasoning
            });

            setDecisionFeed(prev => {
               // Avoid duplicate entries if the reasoning hasn't changed essentially
               if (prev.length > 0 && prev[0].description === marketData.reasoning) return prev;

               const newItem = {
                  id: Date.now(),
                  type: 'ANALYSIS' as const,
                  title: `Market Analysis: ${marketData.risk_level}`,
                  description: marketData.reasoning,
                  time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                  meta: { label: 'Risk', value: marketData.risk_level }
               };
               return [newItem, ...prev].slice(0, 50);
            });

         } catch (e) {
            console.error(e);
         }
      };

      fetchData();
      const interval = setInterval(fetchData, 8000); // 8s interval
      return () => clearInterval(interval);
   }, []);

   return (
      <div className="min-h-screen relative font-mono text-text-primary">
         {/* Background Grid */}
         <div className="background-grid"></div>

         <div className="container mx-auto px-6 py-8 relative z-10 max-w-[1400px]">

            {/* Header */}
            <header className="flex flex-col md:flex-row justify-between items-center mb-12 pb-6 border-b border-border-subtle">
               <div className="flex items-center gap-4 mb-4 md:mb-0">
                  <div className="w-10 h-10 bg-gradient-to-br from-accent-primary to-accent-secondary rounded-lg flex items-center justify-center font-display font-extrabold text-xl text-bg-primary animate-[bounce_3s_infinite]">
                     ₵
                  </div>
                  <div>
                     <div className="font-display text-2xl font-bold tracking-tight">CAPP Treasury</div>
                     <div className="text-xs text-text-tertiary uppercase tracking-widest">Autonomous Asset Management</div>
                  </div>
               </div>

               <div className="flex items-center gap-4">
                  <button
                     onClick={() => setAutoHedge(!autoHedge)}
                     className={`flex items-center gap-2 px-4 py-2 rounded-full border text-xs font-medium uppercase tracking-wider transition-all ${autoHedge
                        ? 'bg-bg-card border-border-medium text-text-primary shadow-[0_0_15px_rgba(0,255,163,0.1)]'
                        : 'bg-bg-tertiary border-border-subtle text-text-tertiary'
                        }`}
                  >
                     <div className={`w-2 h-2 rounded-full transition-all ${autoHedge ? 'bg-accent-primary animate-pulse' : 'bg-text-tertiary'}`}></div>
                     Auto-Hedge {autoHedge ? 'ON' : 'OFF'}
                  </button>
               </div>
            </header>

            {/* Main Grid Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-8">

               {/* Left Column: Treasury Overview */}
               <TreasuryCard balance={balance} address={address || "Wait..."} />

               {/* Right Column: AI Intelligence */}
               <AiPanel marketStatus={marketStatus} decisionFeed={decisionFeed} onChat={handleAiAction} />

            </div>
         </div>
      </div>
   );
}
