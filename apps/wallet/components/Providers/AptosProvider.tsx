"use client";

import { AptosWalletAdapterProvider } from "@aptos-labs/wallet-adapter-react";

import { PropsWithChildren } from "react";

export const AptosProvider = ({ children }: PropsWithChildren) => {
    return (
        <AptosWalletAdapterProvider autoConnect={true} optInWallets={["Petra"]}>
            {children}
        </AptosWalletAdapterProvider>
    );
};
