'use client';


import { X, Shield, Bot, Zap, Activity, Save, Loader2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, AgentConfig } from '@/services/api';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

type Tab = 'GENERAL' | 'AGENTS' | 'SECURITY';
type RiskProfile = 'CONSERVATIVE' | 'BALANCED' | 'AGGRESSIVE';
type AutonomyLevel = 'HUMAN_LOOP' | 'AUTONOMOUS';

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const [activeTab, setActiveTab] = useState<Tab>('AGENTS');

    // State for Settings
    const [riskProfile, setRiskProfile] = useState<RiskProfile>('BALANCED');
    const [autonomy, setAutonomy] = useState<AutonomyLevel>('HUMAN_LOOP');
    const [hedgeThreshold, setHedgeThreshold] = useState(5);
    const [network, setNetwork] = useState('TESTNET');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    // Load Config on Mount
    useEffect(() => {
        if (isOpen) {
            setLoading(true);
            api.getAgentConfig()
                .then(config => {
                    setRiskProfile(config.risk_profile as RiskProfile);
                    setAutonomy(config.autonomy_level as AutonomyLevel);
                    setHedgeThreshold(config.hedge_threshold);
                    setNetwork(config.network);
                })
                .catch(err => console.error("Failed to load settings:", err))
                .finally(() => setLoading(false));
        }
    }, [isOpen]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await api.updateAgentConfig({
                risk_profile: riskProfile,
                autonomy_level: autonomy,
                hedge_threshold: hedgeThreshold,
                network: network
            });
            onClose();
        } catch (e) {
            console.error("Failed to save:", e);
            alert("Failed to save configuration.");
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-bg-primary/80 backdrop-blur-sm" onClick={onClose} />
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="relative w-full max-w-2xl bg-bg-card border border-border-medium rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]"
            >
                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-border-medium bg-bg-secondary/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-accent-primary/10 rounded-lg">
                            <SettingsIcon className="w-5 h-5 text-accent-primary" />
                        </div>
                        <h3 className="font-display text-lg font-semibold uppercase tracking-wider text-text-primary">System Configuration</h3>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-bg-tertiary rounded-full transition-colors">
                        <X className="w-5 h-5 text-text-secondary" />
                    </button>
                </div>

                <div className="flex flex-1 overflow-hidden">
                    {/* Sidebar Tabs */}
                    <div className="w-48 bg-bg-tertiary/30 border-r border-border-medium p-4 space-y-2">
                        <TabButton
                            active={activeTab === 'GENERAL'}
                            onClick={() => setActiveTab('GENERAL')}
                            icon={<Zap className="w-4 h-4" />}
                            label="General"
                        />
                        <TabButton
                            active={activeTab === 'AGENTS'}
                            onClick={() => setActiveTab('AGENTS')}
                            icon={<Bot className="w-4 h-4" />}
                            label="AI Agents"
                        />
                        <TabButton
                            active={activeTab === 'SECURITY'}
                            onClick={() => setActiveTab('SECURITY')}
                            icon={<Shield className="w-4 h-4" />}
                            label="Security"
                        />
                    </div>

                    {/* Content Area */}
                    <div className="flex-1 p-8 overflow-y-auto">
                        <AnimatePresence mode='wait'>
                            {activeTab === 'AGENTS' && (
                                <motion.div
                                    key="agents"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    className="space-y-8"
                                >
                                    {/* Risk Profile Section */}
                                    <section>
                                        <h4 className="flex items-center gap-2 text-sm font-bold text-text-secondary uppercase tracking-widest mb-4">
                                            <Activity className="w-4 h-4 text-accent-primary" />
                                            Treasury Risk Profile
                                        </h4>
                                        <div className="grid grid-cols-3 gap-3">
                                            <RiskOption
                                                label="Conservative"
                                                desc="Capital Preservation"
                                                selected={riskProfile === 'CONSERVATIVE'}
                                                onClick={() => setRiskProfile('CONSERVATIVE')}
                                                color="text-color-success"
                                            />
                                            <RiskOption
                                                label="Balanced"
                                                desc="Growth & Stability"
                                                selected={riskProfile === 'BALANCED'}
                                                onClick={() => setRiskProfile('BALANCED')}
                                                color="text-accent-secondary"
                                            />
                                            <RiskOption
                                                label="Aggressive"
                                                desc="Max Yield"
                                                selected={riskProfile === 'AGGRESSIVE'}
                                                onClick={() => setRiskProfile('AGGRESSIVE')}
                                                color="text-accent-warning"
                                            />
                                        </div>
                                    </section>

                                    {/* Autonomy Level */}
                                    <section>
                                        <h4 className="flex items-center gap-2 text-sm font-bold text-text-secondary uppercase tracking-widest mb-4">
                                            <Bot className="w-4 h-4 text-accent-primary" />
                                            Agent Autonomy
                                        </h4>
                                        <div className="bg-bg-tertiary rounded-xl p-1 flex mb-4">
                                            <button
                                                onClick={() => setAutonomy('HUMAN_LOOP')}
                                                className={`flex-1 py-2 text-xs font-bold uppercase tracking-wide rounded-lg transition-all ${autonomy === 'HUMAN_LOOP' ? 'bg-accent-primary text-bg-primary shadow-lg' : 'text-text-tertiary hover:text-text-primary'}`}
                                            >
                                                Human Review
                                            </button>
                                            <button
                                                onClick={() => setAutonomy('AUTONOMOUS')}
                                                className={`flex-1 py-2 text-xs font-bold uppercase tracking-wide rounded-lg transition-all ${autonomy === 'AUTONOMOUS' ? 'bg-accent-danger text-white shadow-lg shadow-accent-danger/20' : 'text-text-tertiary hover:text-text-primary'}`}
                                            >
                                                Fully Autonomous
                                            </button>
                                        </div>

                                        <div className="space-y-4">
                                            <div>
                                                <div className="flex justify-between text-xs text-text-secondary mb-2">
                                                    <span>Auto-Hedge Volatility Threshold</span>
                                                    <span className="font-mono text-accent-primary">{hedgeThreshold}%</span>
                                                </div>
                                                <input
                                                    type="range"
                                                    min="1"
                                                    max="20"
                                                    value={hedgeThreshold}
                                                    onChange={(e) => setHedgeThreshold(parseInt(e.target.value))}
                                                    className="w-full h-2 bg-bg-tertiary rounded-lg appearance-none cursor-pointer accent-accent-primary"
                                                />
                                            </div>
                                        </div>
                                    </section>
                                </motion.div>
                            )}

                            {activeTab === 'GENERAL' && (
                                <motion.div
                                    key="general"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="space-y-6"
                                >
                                    <section>
                                        <h4 className="text-sm font-bold text-text-secondary uppercase tracking-widest mb-4">Network Settings</h4>
                                        <div className="flex gap-4">
                                            <label className="flex items-center gap-3 p-4 border border-accent-primary/50 bg-accent-primary/5 rounded-xl cursor-pointer w-full">
                                                <div className="w-3 h-3 rounded-full bg-accent-primary shadow-[0_0_10px_theme(colors.accent.primary)]"></div>
                                                <div>
                                                    <div className="text-sm font-bold text-text-primary">Aptos Testnet</div>
                                                    <div className="text-xs text-text-tertiary">Current Environment</div>
                                                </div>
                                            </label>
                                        </div>
                                    </section>
                                </motion.div>
                            )}
                            {activeTab === 'SECURITY' && (
                                <motion.div
                                    key="security"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="text-center text-text-tertiary py-12"
                                >
                                    <Shield className="w-12 h-12 mx-auto mb-4 opacity-50" />
                                    <p>Security configurations are managed by the admin policy.</p>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-border-medium bg-bg-secondary/50 flex justify-end">
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex items-center gap-2 px-6 py-3 bg-accent-primary text-bg-primary rounded-xl font-bold uppercase tracking-wide hover:bg-white transition-colors disabled:opacity-50"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        {saving ? 'Saving...' : 'Save Configuration'}
                    </button>
                </div>

            </motion.div>
        </div>
    );
}

function TabButton({ active, onClick, icon, label }: { active: boolean, onClick: () => void, icon: React.ReactNode, label: string }) {
    return (
        <button
            onClick={onClick}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${active ? 'bg-bg-secondary text-text-primary border border-border-medium shadow-sm' : 'text-text-tertiary hover:text-text-secondary hover:bg-bg-secondary/50'}`}
        >
            {icon}
            <span className="text-sm font-medium">{label}</span>
        </button>
    );
}

function RiskOption({ label, desc, selected, onClick, color }: { label: string, desc: string, selected: boolean, onClick: () => void, color: string }) {
    return (
        <button
            onClick={onClick}
            className={`p-3 rounded-xl border transition-all text-left ${selected ? `bg-bg-secondary border-${color.split('-')[1]}-primary ring-1 ring-${color.split('-')[1]}-primary` : 'bg-bg-tertiary border-transparent hover:border-border-medium'}`}
        >
            <div className={`text-sm font-bold mb-1 ${selected ? color : 'text-text-secondary'}`}>{label}</div>
            <div className="text-[10px] text-text-tertiary">{desc}</div>
        </button>
    );
}

import { Settings as SettingsIcon } from 'lucide-react';
