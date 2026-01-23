"use client";

import { useState } from "react";
import { ArrowLeft, Briefcase, FileText, ShieldCheck, Download, AlertTriangle, Loader2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/Shared/Button";
import { clsx } from "clsx";
import { useSettings } from "@/components/Context/SettingsContext";
import { api } from "@/services/api";

export default function ComplianceSettingsPage() {
    const { complianceLevel, setComplianceLevel } = useSettings();
    const [downloading, setDownloading] = useState<string | null>(null);

    const handleDownload = async (year: number, format: 'PDF' | 'CSV', id: string) => {
        setDownloading(id);
        try {
            await api.downloadComplianceReport(year, format);
        } catch (e) {
            console.error(e);
            alert("Failed to download report");
        } finally {
            setDownloading(null);
        }
    };

    return (
        <div className="max-w-2xl mx-auto animate-in slide-in-from-right-4 duration-500">

            <div className="mb-8 flex items-center gap-4">
                <Link href="/settings">
                    <div className="p-2 rounded-full border border-[var(--border-medium)] hover:bg-[var(--bg-tertiary)] text-white transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </div>
                </Link>
                <h1 className="text-2xl font-bold text-white tracking-widest">COMPLIANCE</h1>
            </div>

            <div className="space-y-6">

                {/* Compliance Level Selection */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div
                        onClick={() => setComplianceLevel("BASIC")}
                        className={clsx(
                            "p-5 rounded-2xl border cursor-pointer transition-all relative overflow-hidden",
                            complianceLevel === "BASIC"
                                ? "bg-[var(--accent-cyan)]/5 border-[var(--accent-cyan)]"
                                : "bg-[var(--bg-card)] border-[var(--border-subtle)] opacity-60 hover:opacity-100"
                        )}
                    >
                        {complianceLevel === "BASIC" && <div className="absolute top-3 right-3 w-2 h-2 bg-[var(--accent-cyan)] rounded-full animate-pulse" />}
                        <ShieldCheck className={clsx("w-8 h-8 mb-4", complianceLevel === "BASIC" ? "text-[var(--accent-cyan)]" : "text-[var(--text-secondary)]")} />
                        <h3 className="text-white font-bold mb-1">Personal / Basic</h3>
                        <p className="text-xs text-[var(--text-secondary)]">Standard transaction limits. Travel rule checks enabled.</p>
                    </div>

                    <div
                        onClick={() => setComplianceLevel("PRO")}
                        className={clsx(
                            "p-5 rounded-2xl border cursor-pointer transition-all relative overflow-hidden",
                            complianceLevel === "PRO"
                                ? "bg-[var(--accent-cyan)]/5 border-[var(--accent-cyan)]"
                                : "bg-[var(--bg-card)] border-[var(--border-subtle)] opacity-60 hover:opacity-100"
                        )}
                    >
                        {complianceLevel === "PRO" && <div className="absolute top-3 right-3 w-2 h-2 bg-[var(--accent-cyan)] rounded-full animate-pulse" />}
                        <Briefcase className={clsx("w-8 h-8 mb-4", complianceLevel === "PRO" ? "text-[var(--accent-cyan)]" : "text-[var(--text-secondary)]")} />
                        <h3 className="text-white font-bold mb-1">Business / Pro</h3>
                        <p className="text-xs text-[var(--text-secondary)]">Higher limits. KYB Verification required for detailed reporting.</p>
                    </div>
                </div>

                {/* Audit Logs */}
                <div className="p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                    <div className="flex justify-between items-start mb-6">
                        <div className="flex gap-4">
                            <div className="p-3 bg-[var(--bg-tertiary)] rounded-xl text-[var(--text-secondary)] h-fit">
                                <FileText className="w-6 h-6" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-white">Compliance Reports</h3>
                                <p className="text-sm text-[var(--text-secondary)] mt-1">
                                    Download tax and audit logs for your records
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-medium)]">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-[var(--bg-tertiary)] rounded text-[var(--text-tertiary)]">PDF</div>
                                <div className="text-sm text-white">2024 Transaction Report</div>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                icon={downloading === 'pdf-2024' ? Loader2 : Download}
                                className={downloading === 'pdf-2024' ? "animate-spin" : ""}
                                onClick={() => handleDownload(2024, 'PDF', 'pdf-2024')}
                                disabled={!!downloading}
                            />
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-medium)]">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-[var(--bg-tertiary)] rounded text-[var(--text-tertiary)]">CSV</div>
                                <div className="text-sm text-white">2025 Audit Log</div>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                icon={downloading === 'csv-2025' ? Loader2 : Download}
                                className={downloading === 'csv-2025' ? "animate-spin" : ""}
                                onClick={() => handleDownload(2025, 'CSV', 'csv-2025')}
                                disabled={!!downloading}
                            />
                        </div>
                    </div>
                </div>

                {/* Travel Rule Status */}
                <div className="p-4 rounded-xl border border-yellow-500/20 bg-yellow-500/5 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                    <div>
                        <h4 className="text-yellow-500 font-bold text-sm">Travel Rule Active</h4>
                        <p className="text-xs text-[var(--text-secondary)] mt-1">
                            Transactions over $3,000 USD require counterparty information to verify destination wallet ownership.
                        </p>
                    </div>
                </div>

            </div>
        </div>
    );
}
