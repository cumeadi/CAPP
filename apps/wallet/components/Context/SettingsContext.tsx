"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export type Currency = "USD" | "EUR" | "GBP";
export type ComplianceLevel = "BASIC" | "PRO";

interface SettingsContextType {
    // Preferences
    currency: Currency;
    setCurrency: (c: Currency) => void;
    notificationsEnabled: boolean;
    setNotificationsEnabled: (enabled: boolean) => void;

    // Networks
    testnetMode: boolean; // Developer mode
    setTestnetMode: (enabled: boolean) => void;

    // Compliance
    complianceLevel: ComplianceLevel;
    setComplianceLevel: (level: ComplianceLevel) => void;

    // Security (Local State Only)
    biometricsEnabled: boolean;
    setBiometricsEnabled: (enabled: boolean) => void;

    // Custom Networks
    customNetworks: CustomNetwork[];
    addCustomNetwork: (network: CustomNetwork) => void;
    removeCustomNetwork: (id: string) => void;
}

export interface CustomNetwork {
    id: string;
    name: string;
    rpcUrl: string;
    chainId?: number;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
    // Initialize state with default values
    const [currency, setCurrencyState] = useState<Currency>("USD");
    const [notificationsEnabled, setNotificationsEnabledState] = useState(true);
    const [testnetMode, setTestnetModeState] = useState(false);
    const [complianceLevel, setComplianceLevelState] = useState<ComplianceLevel>("BASIC");
    const [biometricsEnabled, setBiometricsEnabledState] = useState(false);
    const [customNetworks, setCustomNetworks] = useState<CustomNetwork[]>([]);

    const [mounted, setMounted] = useState(false);

    // Load from localStorage on mount
    useEffect(() => {
        try {
            const savedSettings = localStorage.getItem("capp_settings");
            if (savedSettings) {
                const parsed = JSON.parse(savedSettings);
                if (parsed.currency) setCurrencyState(parsed.currency);
                if (parsed.notificationsEnabled !== undefined) setNotificationsEnabledState(parsed.notificationsEnabled);
                if (parsed.testnetMode !== undefined) setTestnetModeState(parsed.testnetMode);
                if (parsed.complianceLevel) setComplianceLevelState(parsed.complianceLevel);
                if (parsed.biometricsEnabled !== undefined) setBiometricsEnabledState(parsed.biometricsEnabled);
                if (parsed.customNetworks) setCustomNetworks(parsed.customNetworks);
            }
        } catch (e) {
            console.error("Failed to load settings", e);
        } finally {
            setMounted(true);
        }
    }, []);

    // Save to localStorage on change
    useEffect(() => {
        if (!mounted) return;
        const settings = {
            currency,
            notificationsEnabled,
            testnetMode,
            complianceLevel,
            biometricsEnabled,
            customNetworks
        };
        localStorage.setItem("capp_settings", JSON.stringify(settings));
    }, [currency, notificationsEnabled, testnetMode, complianceLevel, biometricsEnabled, customNetworks, mounted]);

    // Wrappers to update state
    const setCurrency = (c: Currency) => setCurrencyState(c);
    const setNotificationsEnabled = (e: boolean) => setNotificationsEnabledState(e);
    const setTestnetMode = (e: boolean) => setTestnetModeState(e);
    const setComplianceLevel = (l: ComplianceLevel) => setComplianceLevelState(l);
    const setBiometricsEnabled = (e: boolean) => setBiometricsEnabledState(e);

    const addCustomNetwork = (network: CustomNetwork) => {
        setCustomNetworks(prev => [...prev, network]);
    };

    const removeCustomNetwork = (id: string) => {
        setCustomNetworks(prev => prev.filter(n => n.id !== id));
    };

    return (
        <SettingsContext.Provider value={{
            currency, setCurrency,
            notificationsEnabled, setNotificationsEnabled,
            testnetMode, setTestnetMode,
            complianceLevel, setComplianceLevel,
            biometricsEnabled, setBiometricsEnabled,
            customNetworks, addCustomNetwork, removeCustomNetwork
        }}>
            {children}
        </SettingsContext.Provider>
    );
}

export function useSettings() {
    const context = useContext(SettingsContext);
    if (context === undefined) {
        throw new Error("useSettings must be used within a SettingsProvider");
    }
    return context;
}
