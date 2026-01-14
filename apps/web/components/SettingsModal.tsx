'use client';


import { X, Shield, Bot, Zap, Activity, Save, Loader2, Settings as SettingsIcon, Bell, Wallet, FileText } from 'lucide-react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, AgentConfig } from '@/services/api';
import Portal from './Portal';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

type Tab = 'GENERAL' | 'AGENTS' | 'SECURITY';
type RiskProfile = 'CONSERVATIVE' | 'BALANCED' | 'AGGRESSIVE';
type AutonomyLevel = 'HUMAN_LOOP' | 'AUTONOMOUS';
type ComplianceStrictness = 'STRICT' | 'STANDARD' | 'FLEXIBLE';

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const [activeTab, setActiveTab] = useState<Tab>('AGENTS');

    // State for Settings
    const [riskProfile, setRiskProfile] = useState<RiskProfile>('BALANCED');
    const [autonomy, setAutonomy] = useState<AutonomyLevel>('HUMAN_LOOP');
    const [hedgeThreshold, setHedgeThreshold] = useState(5);
    const [network, setNetwork] = useState('TESTNET');

    // New States
    const [yieldPreferences, setYieldPreferences] = useState<string[]>(["Aave", "Compound"]);
    const [minYieldApy, setMinYieldApy] = useState(3.0);
    const [complianceStrictness, setComplianceStrictness] = useState<ComplianceStrictness>('STANDARD');
    const [sanctionsCheck, setSanctionsCheck] = useState(true);
    const [notifications, setNotifications] = useState(true);

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
                    // New fields
                    if (config.yield_preferences) setYieldPreferences(config.yield_preferences);
                    if (config.min_yield_apy) setMinYieldApy(config.min_yield_apy);
                    if (config.compliance_strictness) setComplianceStrictness(config.compliance_strictness);
                    if (config.sanctions_check_enabled !== undefined) setSanctionsCheck(config.sanctions_check_enabled);
                    if (config.notifications_enabled !== undefined) setNotifications(config.notifications_enabled);
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
                network: network,
                yield_preferences: yieldPreferences,
                min_yield_apy: minYieldApy,
                compliance_strictness: complianceStrictness,
                sanctions_check_enabled: sanctionsCheck,
                notifications_enabled: notifications
            } as AgentConfig);
            onClose();
        } catch (e) {
            console.error("Failed to save:", e);
            alert("Failed to save configuration.");
        } finally {
            setSaving(false);
        }
    };

    const toggleYieldProtocol = (protocol: string) => {
        setYieldPreferences(prev =>
            prev.includes(protocol)
                ? prev.filter(p => p !== protocol)
                : [...prev, protocol]
        );
    };

    return (
        <Portal>
            <AnimatePresence>
                {isOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={onClose}
                            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 transition-all"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none p-4"
                        >
                            <div className="bg-bg-card w-full max-w-2xl rounded-2xl border border-border-medium shadow-2xl overflow-hidden pointer-events-auto flex flex-col max-h-[85vh]">
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
                                        <TabButton
                                            active={activeTab === 'GENERAL'}
                                            onClick={() => setActiveTab('GENERAL')}
                                            icon={<Zap className="w-4 h-4" />}
                                            label="General"
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
                                                                desc="Preserve Capital"
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

                                                    {/* Yield Strategy */}
                                                    <section>
                                                        <h4 className="flex items-center gap-2 text-sm font-bold text-text-secondary uppercase tracking-widest mb-4">
                                                            <Wallet className="w-4 h-4 text-accent-primary" />
                                                            Yield Strategy
                                                        </h4>
                                                        <div className="space-y-4">
                                                            <div>
                                                                <div className="flex justify-between text-xs text-text-secondary mb-2">
                                                                    <span>Minimum APY Threshold</span>
                                                                    <span className="font-mono text-accent-primary">{minYieldApy.toFixed(1)}%</span>
                                                                </div>
                                                                <input
                                                                    type="range"
                                                                    min="0.5"
                                                                    max="15"
                                                                    step="0.5"
                                                                    value={minYieldApy}
                                                                    onChange={(e) => setMinYieldApy(parseFloat(e.target.value))}
                                                                    className="w-full h-2 bg-bg-tertiary rounded-lg appearance-none cursor-pointer accent-accent-primary"
                                                                />
                                                            </div>

                                                            <div className="grid grid-cols-2 gap-2">
                                                                {['Aave', 'Compound', 'Uniswap', 'Yearn'].map(proto => (
                                                                    <button
                                                                        key={proto}
                                                                        onClick={() => toggleYieldProtocol(proto)}
                                                                        className={`px-3 py-2 rounded-lg text-sm border transition-all ${yieldPreferences.includes(proto)
                                                                                ? 'bg-accent-primary/10 border-accent-primary text-text-primary'
                                                                                : 'bg-bg-tertiary border-transparent text-text-tertiary hover:border-border-medium'
                                                                            }`}
                                                                    >
                                                                        {proto}
                                                                    </button>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    </section>

                                                    {/* Operational Limits */}
                                                    <section>
                                                        <h4 className="flex items-center gap-2 text-sm font-bold text-text-secondary uppercase tracking-widest mb-4">
                                                            <Bot className="w-4 h-4 text-accent-primary" />
                                                            Operational Limits
                                                        </h4>
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

                                                    <section>
                                                        <h4 className="text-sm font-bold text-text-secondary uppercase tracking-widest mb-4">Notifications</h4>
                                                        <label className="flex items-center justify-between p-4 bg-bg-tertiary/30 rounded-xl cursor-pointer hover:bg-bg-tertiary/50 transition-colors">
                                                            <div className="flex items-center gap-3">
                                                                <Bell className={`w-5 h-5 ${notifications ? 'text-accent-primary' : 'text-text-tertiary'}`} />
                                                                <div>
                                                                    <div className="text-sm font-bold text-text-primary">System Alerts</div>
                                                                    <div className="text-xs text-text-tertiary">Receive updates on agent actions</div>
                                                                </div>
                                                            </div>
                                                            <div className={`w-10 h-5 rounded-full transition-colors relative ${notifications ? 'bg-accent-primary' : 'bg-bg-tertiary border border-border-medium'}`}>
                                                                <div className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-transform ${notifications ? 'translate-x-5' : 'translate-x-0'}`} />
                                                            </div>
                                                            <input type="checkbox" className="hidden" checked={notifications} onChange={(e) => setNotifications(e.target.checked)} />
                                                        </label>
                                                    </section>
                                                </motion.div>
                                            )}
                                            {activeTab === 'SECURITY' && (
                                                <motion.div
                                                    key="security"
                                                    initial={{ opacity: 0, x: 20 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    className="space-y-8"
                                                >
                                                    <section>
                                                        <h4 className="flex items-center gap-2 text-sm font-bold text-text-secondary uppercase tracking-widest mb-4">
                                                            <Shield className="w-4 h-4 text-accent-primary" />
                                                            Compliance Shield
                                                        </h4>

                                                        <div className="bg-bg-tertiary/20 rounded-xl p-4 border border-border-medium mb-6">
                                                            <div className="flex items-center justify-between mb-4">
                                                                <div className="flex items-center gap-3">
                                                                    <FileText className="w-5 h-5 text-accent-warning" />
                                                                    <div>
                                                                        <div className="text-sm font-bold text-text-primary">Sanctions Screening</div>
                                                                        <div className="text-xs text-text-tertiary">Check OFAC/UN lists before transfer</div>
                                                                    </div>
                                                                </div>
                                                                <label className={`w-10 h-5 rounded-full transition-colors relative cursor-pointer ${sanctionsCheck ? 'bg-accent-primary' : 'bg-bg-tertiary border border-border-medium'}`}>
                                                                    <div className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-transform ${sanctionsCheck ? 'translate-x-5' : 'translate-x-0'}`} />
                                                                    <input type="checkbox" className="hidden" checked={sanctionsCheck} onChange={(e) => setSanctionsCheck(e.target.checked)} />
                                                                </label>
                                                            </div>
                                                        </div>

                                                        <div className="space-y-3">
                                                            <h5 className="text-xs font-bold text-text-secondary uppercase">Strictness Level</h5>
                                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                                <button
                                                                    onClick={() => setComplianceStrictness('FLEXIBLE')}
                                                                    className={`p-3 rounded-xl border text-left transition-all ${complianceStrictness === 'FLEXIBLE' ? 'bg-bg-secondary border-accent-secondary ring-1 ring-accent-secondary' : 'bg-bg-tertiary border-transparent opacity-60'}`}
                                                                >
                                                                    <div className="text-sm font-bold">Flexible</div>
                                                                    <div className="text-[10px] text-text-tertiary">Alert only</div>
                                                                </button>
                                                                <button
                                                                    onClick={() => setComplianceStrictness('STANDARD')}
                                                                    className={`p-3 rounded-xl border text-left transition-all ${complianceStrictness === 'STANDARD' ? 'bg-bg-secondary border-accent-primary ring-1 ring-accent-primary' : 'bg-bg-tertiary border-transparent opacity-60'}`}
                                                                >
                                                                    <div className="text-sm font-bold">Standard</div>
                                                                    <div className="text-[10px] text-text-tertiary">Block High Risk</div>
                                                                </button>
                                                                <button
                                                                    onClick={() => setComplianceStrictness('STRICT')}
                                                                    className={`p-3 rounded-xl border text-left transition-all ${complianceStrictness === 'STRICT' ? 'bg-bg-secondary border-accent-warning ring-1 ring-accent-warning' : 'bg-bg-tertiary border-transparent opacity-60'}`}
                                                                >
                                                                    <div className="text-sm font-bold">Strict</div>
                                                                    <div className="text-[10px] text-text-tertiary">Block All Flagged</div>
                                                                </button>
                                                            </div>
                                                        </div>
                                                    </section>
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

                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </Portal>
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


