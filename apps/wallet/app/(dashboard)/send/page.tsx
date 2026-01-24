"use client";

import { useState, useEffect } from "react";
import { ArrowLeft, ScanLine, Info, User, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/Shared/Button";
import { RoutingComparisonWidget } from "@/components/Send/RoutingComparisonWidget";
import { api, Contact } from "@/services/api"; // Updated import
import { ComplianceModal } from "@/components/Shared/ComplianceModal";

export default function SendPage() {
    const router = useRouter();
    const [amount, setAmount] = useState("");
    const [recipient, setRecipient] = useState("");
    const [asset, setAsset] = useState("USDC");
    const [description, setDescription] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [selectedRoute, setSelectedRoute] = useState<"standard" | "capp">("capp");

    // Contacts Integration
    const [isContactModalOpen, setIsContactModalOpen] = useState(false);
    const [contacts, setContacts] = useState<Contact[]>([]);

    // Compliance State
    const [complianceModal, setComplianceModal] = useState<{
        isOpen: boolean;
        type: "BLOCK" | "WARNING" | "SAFE";
        title: string;
        message: string;
        riskScore: number;
        violations: string[];
    }>({
        isOpen: false,
        type: "SAFE",
        title: "",
        message: "",
        riskScore: 0,
        violations: []
    });

    useEffect(() => {
        const fetchContacts = async () => {
            try {
                const data = await api.getContacts();
                setContacts(data);
            } catch (error) {
                console.error("Failed to fetch contacts", error);
            }
        };
        fetchContacts();
    }, []);

    const handleSelectContact = (contact: Contact) => {
        setRecipient(contact.address);
        setDescription(contact.name); // Suggest name as note
        setIsContactModalOpen(false);
    };

    const initiateSend = async () => {
        if (!amount || !recipient) return;
        setIsSubmitting(true);
        try {
            // 1. Smart Compliance Pre-Flight Check
            const compliancePayload = {
                sender_name: "Wallet User",
                sender_country: "US",
                recipient_name: description || "Unknown",
                recipient_country: "KE",
                recipient_address: recipient,
                amount: parseFloat(amount),
                currency: asset,
                payment_method: "CRYPTO_TRANSFER"
            };

            const check = await api.checkCompliance(compliancePayload);

            if (!check.is_compliant) {
                setComplianceModal({
                    isOpen: true,
                    type: "BLOCK",
                    title: "Transaction Blocked",
                    message: check.reasoning,
                    riskScore: check.risk_score,
                    violations: check.violations
                });
                setIsSubmitting(false);
                return;
            }

            if (check.risk_score > 30) {
                setComplianceModal({
                    isOpen: true,
                    type: "WARNING",
                    title: "Security Warning",
                    message: check.reasoning,
                    riskScore: check.risk_score,
                    violations: check.violations
                });
                setIsSubmitting(false);
                return;
            }

            // If safe, execute directly
            executeSend(check.risk_score);

        } catch (e) {
            console.error(e);
            alert("Compliance check failed");
            setIsSubmitting(false);
        }
    };

    const executeSend = async (riskScore: number = 0) => {
        setIsSubmitting(true);
        try {
            const payload = {
                reference_id: `REF-${Date.now()}`,
                payment_type: "personal_remittance",
                payment_method: "crypto",
                amount: parseFloat(amount),
                currency: asset,
                from_currency: asset,
                to_currency: asset,
                sender_name: "Wallet User",
                sender_phone: "+0000000000",
                sender_country: "US",
                recipient_name: "Crypto Recipient",
                recipient_phone: "+0000000000",
                recipient_country: "KE",
                description: description || "Wallet transfer",
                priority_cost: selectedRoute === "capp",
                priority_speed: selectedRoute === "standard",
                metadata: {
                    target_chain: "ethereum",
                    source_chain: "ethereum",
                    compliance_id: `COMP-${Date.now()}`,
                    risk_score: riskScore
                }
            };

            await api.createPayment(payload);
            router.push("/history");
        } catch (e) {
            console.error("Payment failed", e);
            alert("Payment failed: " + (e as Error).message);
        } finally {
            setIsSubmitting(false);
            setComplianceModal(prev => ({ ...prev, isOpen: false }));
        }
    };

    return (
        <div className="max-w-2xl mx-auto animate-in slide-in-from-right-4 duration-500 relative">

            {/* Header */}
            <div className="mb-8 flex items-center gap-4">
                <Link href="/">
                    <div className="p-2 rounded-full border border-[var(--border-medium)] hover:bg-[var(--bg-tertiary)] text-white transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                    </div>
                </Link>
                <h1 className="text-2xl font-bold text-white tracking-widest">SEND CRYPTO</h1>
            </div>

            <div className="space-y-6">

                {/* Asset Selection */}
                <div className="space-y-2">
                    <label className="text-xs text-[var(--text-secondary)] uppercase tracking-wider font-bold ml-1">Select Asset</label>
                    <div className="relative">
                        <select
                            value={asset}
                            onChange={(e) => setAsset(e.target.value)}
                            className="w-full p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-medium)] text-white appearance-none focus:outline-none focus:border-[var(--accent-cyan)]"
                        >
                            <option value="USDC">USDC (USD Coin)</option>
                            <option value="ETH">ETH (Ethereum)</option>
                            <option value="CAPP">CAPP (CAPP Token)</option>
                        </select>
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-[var(--text-secondary)]">▼</div>
                    </div>
                    <div className="flex justify-between px-1 text-xs text-[var(--text-secondary)]">
                        <span>Balance: 5,000.00 USDC</span>
                    </div>
                </div>

                {/* Recipient */}
                <div className="space-y-2">
                    <label className="text-xs text-[var(--text-secondary)] uppercase tracking-wider font-bold ml-1">Recipient Address</label>
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="0x..."
                            value={recipient}
                            onChange={(e) => setRecipient(e.target.value)}
                            className="w-full p-4 pr-24 rounded-xl bg-[var(--bg-card)] border border-[var(--border-medium)] text-white focus:outline-none focus:border-[var(--accent-cyan)] font-mono placeholder:text-gray-600"
                        />
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1">
                            <button
                                onClick={() => setIsContactModalOpen(true)}
                                className="p-2 text-[var(--accent-cyan)] hover:bg-[var(--accent-cyan)]/10 rounded-lg transition-colors"
                                title="Contacts"
                            >
                                <User className="w-5 h-5" />
                            </button>
                            <button className="p-2 text-[var(--accent-cyan)] hover:bg-[var(--accent-cyan)]/10 rounded-lg transition-colors" title="Scan QR">
                                <ScanLine className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Amount */}
                <div className="space-y-2">
                    <label className="text-xs text-[var(--text-secondary)] uppercase tracking-wider font-bold ml-1">Amount</label>
                    <div className="relative">
                        <input
                            type="number"
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                            placeholder="0.00"
                            className="w-full p-4 pr-20 rounded-xl bg-[var(--bg-card)] border border-[var(--border-medium)] text-white focus:outline-none focus:border-[var(--accent-cyan)] font-mono text-2xl font-bold placeholder:text-gray-700"
                        />
                        <button className="absolute right-3 top-1/2 -translate-y-1/2 px-3 py-1 bg-[var(--bg-tertiary)] text-[var(--accent-cyan)] text-xs font-bold rounded hover:bg-[var(--accent-cyan)] hover:text-black transition-colors">
                            MAX
                        </button>
                    </div>
                </div>

                {/* Description / Notes */}
                <div className="space-y-2">
                    <label className="text-xs text-[var(--text-secondary)] uppercase tracking-wider font-bold ml-1">Note (Optional)</label>
                    <div className="relative">
                        <input
                            type="text"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="e.g. Lunch, Rent, Invoice #123"
                            className="w-full p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-medium)] text-white focus:outline-none focus:border-[var(--accent-cyan)] placeholder:text-gray-600"
                        />
                    </div>
                </div>

                <div className="h-[1px] bg-[var(--border-medium)] w-full my-8" />

                {/* CAPP Routing Widget */}
                <div className="space-y-4">
                    <div className="flex items-center gap-2">
                        <label className="text-xs text-[var(--accent-cyan)] uppercase tracking-wider font-bold">Smart Routing Optimization</label>
                        <Info className="w-3 h-3 text-[var(--text-secondary)]" />
                    </div>
                    <RoutingComparisonWidget
                        amount={parseFloat(amount) || 0}
                        recipient={recipient}
                        onRouteSelected={(route) => setSelectedRoute(route)}
                    />
                </div>

                <div className="pt-4">
                    <Button
                        variant="primary"
                        size="lg"
                        onClick={initiateSend}
                        isLoading={isSubmitting}
                        className="w-full shadow-[0_0_30px_rgba(0,255,179,0.3)] hover:shadow-[0_0_50px_rgba(0,255,179,0.5)]"
                    >
                        {isSubmitting ? "VERIFYING..." : "SEND WITH CAPP"}
                    </Button>
                    <div className="text-center mt-4">
                        <button className="text-xs text-[var(--text-secondary)] underline decoration-dotted hover:text-white">Send using standard route (Slower)</button>
                    </div>
                </div>

            </div>

            {/* Contacts Modal */}
            {isContactModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                    <div className="w-full max-w-md bg-[var(--bg-card)] border border-[var(--border-medium)] rounded-2xl p-6 shadow-2xl animate-in zoom-in-95 duration-200">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-bold text-white">Select Contact</h2>
                            <button onClick={() => setIsContactModalOpen(false)} className="text-[var(--text-secondary)] hover:text-white">
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        <div className="space-y-2 max-h-[300px] overflow-y-auto">
                            {contacts.length === 0 ? (
                                <div className="text-center py-8 text-[var(--text-secondary)]">
                                    <User className="w-10 h-10 mx-auto mb-2 opacity-50" />
                                    No contacts found.
                                    <br />
                                    <Link href="/contacts" className="text-[var(--accent-cyan)] underline">Add a contact first</Link>
                                </div>
                            ) : (
                                contacts.map(contact => (
                                    <button
                                        key={contact.id}
                                        onClick={() => handleSelectContact(contact)}
                                        className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-[var(--bg-tertiary)] border border-transparent hover:border-[var(--border-subtle)] transition-all group text-left"
                                    >
                                        <div className="w-10 h-10 rounded-full bg-[var(--bg-secondary)] flex items-center justify-center font-bold text-[var(--accent-cyan)] border border-[var(--border-medium)] group-hover:border-[var(--accent-cyan)]">
                                            {contact.name.charAt(0).toUpperCase()}
                                        </div>
                                        <div>
                                            <div className="font-bold text-white">{contact.name}</div>
                                            <div className="text-xs text-[var(--text-secondary)] font-mono">{contact.address.slice(0, 6)}...{contact.address.slice(-4)}</div>
                                        </div>
                                    </button>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            )}

            <ComplianceModal
                {...complianceModal}
                onClose={() => setComplianceModal(prev => ({ ...prev, isOpen: false }))}
                onProceed={() => executeSend(complianceModal.riskScore)}
            />
        </div>
    );
}
