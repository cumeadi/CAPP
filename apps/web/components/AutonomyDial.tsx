'use client';

import { motion } from 'framer-motion';
import { Shield, ShieldCheck, Zap } from 'lucide-react';

export type AutonomyLevel = 'COPILOT' | 'GUARDED' | 'SOVEREIGN';

interface AutonomyDialProps {
    value: AutonomyLevel;
    onChange: (level: AutonomyLevel) => void;
}

export default function AutonomyDial({ value, onChange }: AutonomyDialProps) {
    const levels: { id: AutonomyLevel; label: string; icon: any; color: string; ring: string }[] = [
        { id: 'COPILOT', label: 'Copilot', icon: Shield, color: 'bg-blue-500', ring: 'border-blue-500' },
        { id: 'GUARDED', label: 'Guarded', icon: ShieldCheck, color: 'bg-emerald-500', ring: 'border-emerald-500' },
        { id: 'SOVEREIGN', label: 'Sovereign', icon: Zap, color: 'bg-purple-600', ring: 'border-purple-600' },
    ];

    const currentIndex = levels.findIndex(l => l.id === value);

    return (
        <div className="flex flex-col gap-2">
            <div className="flex bg-bg-tertiary p-1 rounded-xl border border-border-subtle relative">
                {levels.map((level) => {
                    const Icon = level.icon;
                    const isActive = value === level.id;

                    return (
                        <button
                            key={level.id}
                            onClick={() => onChange(level.id)}
                            className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-sm font-medium transition-colors relative z-10 
                                ${isActive ? 'text-text-primary' : 'text-text-tertiary hover:text-text-secondary'}
                            `}
                        >
                            {isActive && (
                                <motion.div
                                    layoutId="autonomy-pill"
                                    className={`absolute inset-0 rounded-lg ${level.color} opacity-20 border ${level.ring} border-opacity-50`}
                                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                />
                            )}
                            <div className="relative z-10 flex items-center gap-2">
                                <Icon className={`w-4 h-4 ${isActive ? 'scale-110' : ''} transition-transform`} />
                                {level.label}
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Description Text */}
            <div className="text-xs text-text-tertiary text-center h-4">
                {value === 'COPILOT' && "Approves nothing. You are the pilot."}
                {value === 'GUARDED' && "Approves small actions. Asks for big ones."}
                {value === 'SOVEREIGN' && "Full autonomy within daily limits."}
            </div>
        </div>
    );
}
