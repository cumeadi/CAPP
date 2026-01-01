'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAccount } from 'wagmi';
import TreasuryCard from '@/components/TreasuryCard';
import AiPanel from '@/components/AiPanel';
import AutonomyDial, { AutonomyLevel } from '@/components/AutonomyDial';
import { api } from '@/services/api';

// Mock Data Types
interface MarketStatus {
   sentiment: string;
   volatility: string;
   aptPrice: number;
   reasoning: string;
   top_apy?: number;
   active_protocols?: string[];
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


   const [isAuthenticated, setIsAuthenticated] = useState(false);

   const [balance, setBalance] = useState({
      totalUsd: 0,
      apt: 0,
      usdc: 0,
      eth: 0,
      starknet: 0
   });

   // Autonomy State
   const [autonomyLevel, setAutonomyLevel] = useState<AutonomyLevel>('GUARDED');

   const [systemHealth, setSystemHealth] = useState<{ status: string }>({ status: 'unknown' });

   // Feed State
   const [decisionFeed, setDecisionFeed] = useState<Array<{
      id: string | number;
      type: 'REBALANCE' | 'ANALYSIS' | 'APPROVAL' | 'USER' | 'ERROR';
      title: string;
      description: string;
      time: string;
      meta?: { label: string; value: string };
   }>>([
      {
         id: 1,
         type: 'ANALYSIS',
         title: 'System Initialized',
         description: 'Connecting to CAPP Neural Core...',
         time: 'Just now',
         meta: { label: 'Status', value: 'Active' }
      }
   ]);

   const [lastReasoning, setLastReasoning] = useState("");

   const handleAiAction = async (query: string) => {
      // 1. Add User Query to Feed (Optimistic)
      setDecisionFeed(prev => [{
         id: Date.now(),
         type: 'USER',
         title: 'SYSTEM COMMAND',
         description: `> Executing: ${query}...`,
         time: 'Just now'
      }, ...prev]);

      try {
         await api.chatWithAnalyst(query);
         // Response will appear via the polling feed naturally
      } catch (e) {
         console.error("Chat failed", e);
      }
   };

   useEffect(() => {
      const fetchData = async () => {
         try {
            const walletAddress = address || "0x123";
            const [balanceData, marketData, polygonGas, activityFeed, health] = await Promise.all([
               api.getWalletBalance(walletAddress),
               api.analyzeMarket('APT'),
               api.getPolygonGas().catch(() => ({ gas_price_gwei: 0 })),
               api.getAgentFeed(10),
               api.getSystemStatus().catch(() => ({ status: 'offline' }))
            ]);

            setSystemHealth(health);

            setBalance({
               totalUsd: (balanceData.balance_apt * 10.5) + balanceData.balance_usdc + (balanceData.balance_eth * 2800) + ((balanceData.balance_starknet || 0) * 2800),
               apt: balanceData.balance_apt,
               usdc: balanceData.balance_usdc || 0,
               eth: balanceData.balance_eth || 0,
               starknet: balanceData.balance_starknet || 0
            });

            const newReasoning = `${marketData.reasoning} [Gas: ${polygonGas.gas_price_gwei}]`;

            setMarketStatus({
               sentiment: marketData.recommendation,
               volatility: marketData.risk_level,
               aptPrice: 10.5,
               reasoning: newReasoning
            });

            // Merge Live Feed
            const formattedFeed = activityFeed.map(item => {
               const type = mapActionType(item.action_type);
               // IMPORTANT: For actionable items, we MUST use the request_id from metadata, 
               // otherwise the API call with fail with 404 because it expects the Request UUID, not the Log UUID.
               const id = (type === 'APPROVAL' || type === 'OPPORTUNITY') && item.metadata?.request_id
                  ? item.metadata.request_id
                  : item.id;

               return {
                  id: id,
                  type: type,
                  title: mapAgentTitle(item.agent_type),
                  description: item.message,
                  time: new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                  meta: item.metadata?.risk_level ? { label: 'Risk', value: item.metadata.risk_level } : undefined
               };
            });

            setDecisionFeed(prev => {
               // Simple merge: Keep USER messages, replace others with backend source
               const userMessages = prev.filter(p => p.type === 'USER');
               // Deduplicate based on ID to avoid flicker if mixing
               const combined = [...userMessages, ...formattedFeed].sort((a, b) => (a.time < b.time ? 1 : -1));
               return formattedFeed; // For now, just show backend feed to ensure it's working clean.
            });

         } catch (e) {
            console.error(e);
            setSystemHealth({ status: 'offline' });
         }
      };

      fetchData();
      const interval = setInterval(fetchData, 3000); // 3s polling for "Live" feel
      return () => clearInterval(interval);
   }, []);

   // Helpers
   const mapActionType = (action: string): any => {
      if (action === 'PAYMENT') return 'PAYMENT';
      if (action === 'DECISION' || action === 'CHAT') return 'ANALYSIS';
      if (action === 'REBALANCE') return 'REBALANCE';
      if (action === 'REVIEW') return 'APPROVAL';
      if (action === 'APPROVAL') return 'APPROVAL'; // Direct mapping
      if (action === 'OPPORTUNITY') return 'OPPORTUNITY';
      if (action === 'ERROR') return 'ERROR';
      return 'ANALYSIS';
   }

   const mapAgentTitle = (agentType: string): string => {
      if (agentType === 'MARKET') return 'MARKET ANALYST';
      if (agentType === 'COMPLIANCE') return 'COMPLIANCE OFFICER';
      if (agentType === 'LIQUIDITY') return 'LIQUIDITY MANAGER';
      return agentType;
   }

   // Handle Autonomy Change
   const handleAutonomyChange = async (level: AutonomyLevel) => {
      setAutonomyLevel(level);
      try {
         // Map UI level to Backend level
         // UI: COPILOT, GUARDED, SOVEREIGN
         // Backend: COPILOT, GUARDED, SOVEREIGN
         await api.updateAgentConfig({
            risk_profile: 'BALANCED', // TODO: Fetch current
            autonomy_level: level as any,
            hedge_threshold: 5, // TODO: Fetch current
            network: 'TESTNET'
         });
      } catch (e) {
         console.error("Failed to update autonomy", e);
      }
   };

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
                     <div className="font-display text-2xl font-bold tracking-tight flex items-center gap-3">
                        CAPP Treasury
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest ${systemHealth.status === 'healthy' ? 'bg-color-success/10 text-color-success border border-color-success/30' :
                              systemHealth.status === 'degraded' ? 'bg-accent-warning/10 text-accent-warning border border-accent-warning/30' :
                                 'bg-text-tertiary/10 text-text-tertiary border border-text-tertiary/30'
                           }`}>
                           <span className={`w-1.5 h-1.5 rounded-full mr-1 ${systemHealth.status === 'healthy' ? 'bg-color-success animate-pulse' :
                                 systemHealth.status === 'degraded' ? 'bg-accent-warning' : 'bg-text-tertiary'
                              }`} />
                           {systemHealth.status === 'healthy' ? 'System Online' : systemHealth.status}
                        </span>
                     </div>
                     <div className="text-xs text-text-tertiary uppercase tracking-widest">Autonomous Asset Management</div>
                  </div>
               </div>

               <div className="flex items-center gap-4">
                  <div className="w-auto min-w-[320px]">
                     <AutonomyDial value={autonomyLevel} onChange={handleAutonomyChange} />
                  </div>
               </div>
            </header>

            {/* Main Grid Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-8">

               {/* Left Column: Treasury Overview & Actions */}
               <div className="flex flex-col gap-8">
                  <TreasuryCard balance={balance} address={address || "Wait..."} />
               </div>

               {/* Right Column: AI Panel */}
               <div>
                  <AiPanel
                     marketStatus={marketStatus}
                     decisionFeed={decisionFeed}
                     onChat={handleAiAction}
                     onApprove={async (id) => {
                        // Optimistically update to show processing/approved
                        // Note: API call is handled inside AiPanel with signature
                        setDecisionFeed(prev => prev.map(item =>
                           item.id === id ? { ...item, type: 'REBALANCE', title: 'APPROVED', description: 'Agent authorized. Processing...' } : item
                        ));
                     }}
                     onReject={async (id) => {
                        try {
                           await api.rejectRequest(String(id));
                           setDecisionFeed(prev => prev.filter(item => item.id !== id));
                        } catch (e) {
                           console.error("Rejection failed", e);
                           alert(`Failed to reject request (${id})`);
                        }
                     }}
                  />
               </div>

            </div>
         </div>
      </div>
   );
}
