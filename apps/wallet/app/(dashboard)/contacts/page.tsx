"use client";

import { useState, useEffect } from "react";
import { User, Plus, Search, Trash2, Edit2, Copy, Check, Send } from "lucide-react";
import { Button } from "@/components/Shared/Button";
import Link from "next/link";
import { clsx } from "clsx";
import { api, Contact } from "@/services/api"; // Updated import

export default function ContactsPage() {
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [search, setSearch] = useState("");
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [copiedId, setCopiedId] = useState<number | null>(null);

    // Form State
    const [newName, setNewName] = useState("");
    const [newAddress, setNewAddress] = useState("");
    const [newNetwork, setNewNetwork] = useState("Aptos");
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadContacts();
    }, []);

    const loadContacts = async () => {
        try {
            const data = await api.getContacts();
            setContacts(data);
        } catch (error) {
            console.error("Failed to load contacts", error);
        }
    };

    const handleAdd = async () => {
        if (!newName || !newAddress) return;
        setLoading(true);
        try {
            await api.addContact({
                name: newName,
                address: newAddress,
                network: newNetwork
            });
            await loadContacts();
            setIsAddModalOpen(false);
            setNewName("");
            setNewAddress("");
        } catch (error) {
            console.error("Failed to add contact", error);
            alert("Failed to add contact");
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to delete this contact?")) return;
        try {
            await api.deleteContact(id);
            await loadContacts(); // Refresh list
        } catch (error) {
            console.error("Failed to delete", error);
        }
    };

    const handleCopy = (text: string, id: number) => {
        navigator.clipboard.writeText(text);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
    };

    const filtered = contacts.filter(c =>
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        c.address.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold text-white tracking-widest mb-2 flex items-center gap-3">
                        <User className="w-6 h-6 text-[var(--accent-cyan)]" />
                        ADDRESS BOOK
                    </h1>
                    <p className="text-[var(--text-secondary)] text-sm font-mono">Manage your trusted beneficiaries.</p>
                </div>
                <Button variant="primary" size="sm" icon={Plus} onClick={() => setIsAddModalOpen(true)}>ADD CONTACT</Button>
            </div>

            {/* Search */}
            <div className="relative">
                <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]" />
                <input
                    type="text"
                    placeholder="Search by name or address..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl pl-12 pr-4 py-4 text-white focus:outline-none focus:border-[var(--accent-cyan)] transition-colors"
                />
            </div>

            {/* List */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filtered.length === 0 ? (
                    <div className="col-span-full text-center py-20 border border-dashed border-[var(--border-subtle)] rounded-xl">
                        <User className="w-12 h-12 text-[var(--text-tertiary)] mx-auto mb-4 opacity-50" />
                        <p className="text-[var(--text-secondary)]">No contacts found.</p>
                    </div>
                ) : (
                    filtered.map((contact) => (
                        <div key={contact.id} className="group relative p-5 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl hover:border-[var(--accent-primary)] transition-all">
                            <div className="flex justify-between items-start mb-3">
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[var(--bg-tertiary)] to-[var(--bg-secondary)] flex items-center justify-center text-lg font-bold text-[var(--accent-cyan)] border border-[var(--border-medium)]">
                                    {contact.name.charAt(0).toUpperCase()}
                                </div>
                                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onClick={() => handleDelete(contact.id)} className="p-2 hover:bg-red-500/20 text-[var(--text-secondary)] hover:text-red-400 rounded-lg transition-colors">
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>

                            <h3 className="text-lg font-bold text-white mb-1">{contact.name}</h3>
                            <div className="flex items-center gap-2 mb-4">
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-subtle)]">
                                    {contact.network}
                                </span>
                            </div>

                            <div className="flex items-center gap-2 bg-[var(--bg-primary)] p-2 rounded-lg border border-[var(--border-subtle)] group-hover:border-[var(--accent-primary)]/30 transition-colors">
                                <code className="text-xs text-[var(--text-secondary)] truncate flex-1 font-mono">
                                    {contact.address}
                                </code>
                                <button
                                    onClick={() => handleCopy(contact.address, contact.id)}
                                    className="p-1.5 hover:bg-[var(--bg-tertiary)] rounded text-[var(--accent-cyan)] transition-colors"
                                >
                                    {copiedId === contact.id ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                                </button>
                            </div>

                            <div className="mt-4">
                                <Link href={`/send?recipient=${contact.address}`}>
                                    <Button variant="outline" size="sm" icon={Send} className="w-full justify-center">SEND</Button>
                                </Link>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Modal */}
            {isAddModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                    <div className="w-full max-w-md bg-[var(--bg-card)] border border-[var(--border-medium)] rounded-2xl p-6 shadow-2xl animate-in zoom-in-95 duration-200">
                        <h2 className="text-xl font-bold text-white mb-6">Add New Contact</h2>

                        <form onSubmit={(e) => { e.preventDefault(); handleAdd(); }}>
                            <div className="space-y-4">
                                <div>
                                    <label className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2 block">Name</label>
                                    <input
                                        autoFocus
                                        type="text"
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-3 text-white focus:border-[var(--accent-cyan)] outline-none"
                                        placeholder="e.g. Alice"
                                    />
                                </div>

                                <div>
                                    <label className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2 block">Network</label>
                                    <select
                                        value={newNetwork}
                                        onChange={(e) => setNewNetwork(e.target.value)}
                                        className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-3 text-white focus:border-[var(--accent-cyan)] outline-none"
                                    >
                                        <option value="Aptos">Aptos</option>
                                        <option value="Ethereum">Ethereum</option>
                                        <option value="Polygon">Polygon</option>
                                        <option value="Starknet">Starknet</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2 block">Address</label>
                                    <input
                                        type="text"
                                        value={newAddress}
                                        onChange={(e) => setNewAddress(e.target.value)}
                                        className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-3 text-white focus:border-[var(--accent-cyan)] outline-none font-mono text-sm"
                                        placeholder="0x..."
                                    />
                                </div>
                            </div>

                            <div className="flex gap-3 mt-8">
                                <Button type="button" variant="secondary" onClick={() => setIsAddModalOpen(false)} className="flex-1 justify-center">CANCEL</Button>
                                <Button type="submit" variant="primary" disabled={!newName || !newAddress} className="flex-1 justify-center">SAVE CONTACT</Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
