"use client";

import { createConfig, http, WagmiProvider } from "wagmi";
import { mainnet, polygon, arbitrum, optimism } from "wagmi/chains";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { injected } from "wagmi/connectors";

// 1. Create Wagmi Config
export const config = createConfig({
    chains: [mainnet, polygon, arbitrum, optimism],
    transports: {
        [mainnet.id]: http(),
        [polygon.id]: http(),
        [arbitrum.id]: http(),
        [optimism.id]: http(),
    },
    connectors: [
        injected(), // Metamask, Rabby, etc.
    ],
    ssr: true,
});

// 2. Create Query Client
const queryClient = new QueryClient();

export function Web3Provider({ children }: { children: React.ReactNode }) {
    return (
        <WagmiProvider config={config}>
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        </WagmiProvider>
    );
}
