"use client";

import { useMemo } from "react";
import '@rainbow-me/rainbowkit/styles.css';
import { getDefaultConfig, RainbowKitProvider, darkTheme } from '@rainbow-me/rainbowkit';
import { mainnet, polygon, arbitrum, optimism, sepolia, polygonAmoy, arbitrumSepolia, optimismSepolia } from "wagmi/chains";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from "wagmi";
import { useSettings } from "@/components/Context/SettingsContext";

// 1. Create Wagmi Config with RainbowKit
// Note: This export is mainly for static usage, dynamic config is in the component
export const config = getDefaultConfig({
    appName: 'CAPP Wallet',
    projectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || '3a8170812b534d0ff9d794f3580db841',
    chains: [mainnet, polygon, arbitrum, optimism],
    ssr: true,
});

// 2. Create Query Client
const queryClient = new QueryClient();

export function Web3Provider({ children }: { children: React.ReactNode }) {
    const { testnetMode, customNetworks } = useSettings();

    const config = useMemo(() => {
        const chains = testnetMode
            ? [sepolia, polygonAmoy, arbitrumSepolia, optimismSepolia] as const
            : [mainnet, polygon, arbitrum, optimism] as const;

        return getDefaultConfig({
            appName: 'CAPP Wallet',
            projectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || '3a8170812b534d0ff9d794f3580db841',
            chains: chains,
            ssr: true,
        });
    }, [testnetMode]);

    return (
        <WagmiProvider config={config}>
            <QueryClientProvider client={queryClient}>
                <RainbowKitProvider
                    theme={darkTheme({
                        accentColor: '#00ffb3',
                        borderRadius: 'medium',
                    })}
                >
                    {children}
                </RainbowKitProvider>
            </QueryClientProvider>
        </WagmiProvider>
    );
}
