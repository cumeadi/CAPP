'use client';

import '@rainbow-me/rainbowkit/styles.css';
import { getDefaultConfig, RainbowKitProvider, darkTheme } from '@rainbow-me/rainbowkit';
import { WagmiProvider } from 'wagmi';
import { polygon } from 'wagmi/chains';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';

import { ReactNode } from 'react';

const config = getDefaultConfig({
    appName: 'CAPP Treasury',
    projectId: 'YOUR_PROJECT_ID', // TODO: Get WalletConnect ID
    chains: [polygon],
    ssr: true, // If your dApp uses server side rendering (SSR)
});

const queryClient = new QueryClient();

export function Web3Provider({ children }: { children: ReactNode }) {
    return (
        <WagmiProvider config={config}>
            <QueryClientProvider client={queryClient}>
                <RainbowKitProvider theme={darkTheme({
                    accentColor: '#a855f7', // Canza Violet Accent
                    accentColorForeground: 'white',
                    borderRadius: 'medium',
                })}>
                    {children as any}
                </RainbowKitProvider>
            </QueryClientProvider>
        </WagmiProvider>
    );
}
