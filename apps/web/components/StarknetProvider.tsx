"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { connect, disconnect } from "starknetkit";
import { AccountInterface, ProviderInterface } from "starknet";

interface StarknetContextType {
    account: AccountInterface | null;
    address: string | null;
    provider: ProviderInterface | null;
    connectWallet: () => Promise<void>;
    disconnectWallet: () => Promise<void>;
    isConnected: boolean;
}

const StarknetContext = createContext<StarknetContextType | null>(null);

export const StarknetProvider = ({ children }: { children: ReactNode }) => {
    const [account, setAccount] = useState<AccountInterface | null>(null);
    const [address, setAddress] = useState<string | null>(null);
    const [provider, setProvider] = useState<ProviderInterface | null>(null);
    const [isConnected, setIsConnected] = useState(false);

    // Auto-connect on load if previously connected
    useEffect(() => {
        const init = async () => {
            const { wallet } = await connect({ modalMode: "neverAsk" });

            if (wallet) {
                const w = wallet as any;
                setAccount(w.account);
                setAddress(w.selectedAddress);
                setProvider(w.provider);
                setIsConnected(true);
            }
        };
        init();
    }, []);

    const connectWallet = async () => {
        try {
            const { wallet } = await connect({
                modalMode: "alwaysAsk", // or "canAsk"
                modalTheme: "dark"
            });

            if (wallet && (wallet as any).isConnected) {
                const w = wallet as any;
                setAccount(w.account);
                setAddress(w.selectedAddress);
                setProvider(w.provider);
                setIsConnected(true);
            }
        } catch (error) {
            console.error("Failed to connect Starknet wallet:", error);
        }
    };

    const disconnectWallet = async () => {
        await disconnect();
        setAccount(null);
        setAddress(null);
        setProvider(null);
        setIsConnected(false);
    };

    return (
        <StarknetContext.Provider
            value={{
                account,
                address,
                provider,
                connectWallet,
                disconnectWallet,
                isConnected,
            }}
        >
            {children}
        </StarknetContext.Provider>
    );
};

export const useStarknet = () => {
    const context = useContext(StarknetContext);
    if (!context) {
        throw new Error("useStarknet must be used within a StarknetProvider");
    }
    return context;
};
