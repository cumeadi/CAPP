'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import TreasuryCard from '@/components/TreasuryCard';
import AiPanel from '@/components/AiPanel';
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
   const [marketStatus, setMarketStatus] = useState<MarketStatus>({
      sentiment: 'NEUTRAL',
      volatility: 'UNKNOWN',
      aptPrice: 0,
      reasoning: "Initializing analysis..."
   });

   const [balance, setBalance] = useState({
      totalUsd: 0,
      apt: 0,
      usdc: 0
   });

   // Auto-Hedge Toggle State
   const [autoHedge, setAutoHedge] = useState(true);

   useEffect(() => {
      const fetchData = async () => {
         try {
            const demoAddress = "0x123";
            const balanceData = await api.getWalletBalance(demoAddress);
            const marketData = await api.analyzeMarket('APT');

            setBalance({
               totalUsd: balanceData.balance_apt * 10.5,  // Mock price $10.5
               apt: balanceData.balance_apt,
               usdc: 0
            });

            setMarketStatus({
               sentiment: marketData.recommendation,
               volatility: marketData.risk_level,
               aptPrice: 10.5,
               reasoning: marketData.reasoning
            });
         } catch (e) {
            console.error("Failed to fetch dashboard data:", e);
         }
      };

      fetchData();
      const interval = setInterval(fetchData, 10000);
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
               <TreasuryCard balance={balance} address="0x123...abc" />

               {/* Right Column: AI Intelligence */}
               <AiPanel marketStatus={marketStatus} />

            </div>
         </div>
      </div>
   );
}
