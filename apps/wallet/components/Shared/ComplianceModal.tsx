import { AlertTriangle, ShieldAlert, CheckCircle, ShieldCheck } from "lucide-react";
import { Button } from "@/components/Shared/Button";

interface ComplianceModalProps {
    isOpen: boolean;
    type: "BLOCK" | "WARNING" | "SAFE";
    title: string;
    message: string;
    riskScore: number;
    violations: string[];
    onClose: () => void;
    onProceed?: () => void;
}

export function ComplianceModal({ isOpen, type, title, message, riskScore, violations, onClose, onProceed }: ComplianceModalProps) {
    if (!isOpen) return null;

    const isBlock = type === "BLOCK";
    const isWarning = type === "WARNING";

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="w-full max-w-md bg-[var(--bg-card)] border border-[var(--border-medium)] rounded-2xl p-6 shadow-2xl animate-in zoom-in-95 duration-200 relative overflow-hidden">

                {/* Status Indicator */}
                <div className={`absolute top-0 left-0 w-full h-1 ${isBlock ? "bg-red-500" : isWarning ? "bg-yellow-500" : "bg-green-500"}`} />

                <div className="flex flex-col items-center text-center mb-6">
                    <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 ${isBlock ? "bg-red-500/10 text-red-500" : isWarning ? "bg-yellow-500/10 text-yellow-500" : "bg-green-500/10 text-green-500"
                        }`}>
                        {isBlock ? <ShieldAlert className="w-8 h-8" /> : isWarning ? <AlertTriangle className="w-8 h-8" /> : <ShieldCheck className="w-8 h-8" />}
                    </div>
                    <h2 className="text-xl font-bold text-white mb-2">{title}</h2>
                    <p className="text-[var(--text-secondary)] text-sm">{message}</p>
                </div>

                {/* Risk Details */}
                {(isBlock || isWarning) && (
                    <div className="bg-[var(--bg-primary)] rounded-xl p-4 mb-6 border border-[var(--border-subtle)] text-left">
                        <div className="flex justify-between items-center mb-2">
                            <span className="text-xs font-bold text-[var(--text-secondary)] uppercase">Risk Score</span>
                            <span className={`font-mono font-bold ${isBlock ? "text-red-500" : "text-yellow-500"}`}>{riskScore}/100</span>
                        </div>
                        {violations.length > 0 && (
                            <div className="space-y-1">
                                {violations.map((v, i) => (
                                    <div key={i} className="text-xs text-red-400 flex items-center gap-2">
                                        <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                                        {v}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                <div className="flex gap-3">
                    {isBlock ? (
                        <Button variant="primary" onClick={onClose} className="w-full justify-center bg-red-600 hover:bg-red-700 border-none">
                            ACKNOWLEDGE & CLOSE
                        </Button>
                    ) : (
                        <>
                            <Button variant="secondary" onClick={onClose} className="flex-1 justify-center">CANCEL</Button>
                            <Button variant="primary" onClick={onProceed} className={`flex-1 justify-center ${isWarning ? "bg-yellow-600 hover:bg-yellow-700 border-none text-black" : ""}`}>
                                {isWarning ? "PROCEED ANYWAY" : "CONFIRM"}
                            </Button>
                        </>
                    )}
                </div>

            </div>
        </div>
    );
}
