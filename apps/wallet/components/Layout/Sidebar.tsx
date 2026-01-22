"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Send, QrCode, History, Settings, Layers } from "lucide-react";
import { clsx } from "clsx";

const NAV_ITEMS = [
    { icon: Home, label: "Home", href: "/" },
    { icon: Send, label: "Send", href: "/send" },
    { icon: QrCode, label: "Receive", href: "/receive" },
    { icon: History, label: "History", href: "/history" },
    { icon: Settings, label: "Settings", href: "/settings" },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="w-20 h-screen sticky top-0 border-r border-[var(--border-medium)] bg-[var(--bg-secondary)] flex flex-col items-center py-6 z-20">
            <div className="mb-12">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] flex items-center justify-center shadow-[0_0_15px_var(--accent-primary)]">
                    <Layers className="text-white w-6 h-6" />
                </div>
            </div>

            <nav className="flex-1 flex flex-col gap-8 w-full px-2">
                {NAV_ITEMS.map((item) => {
                    const isActive = pathname === item.href;
                    const Icon = item.icon;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={clsx(
                                "group relative flex items-center justify-center w-12 h-12 rounded-xl transition-all duration-300 mx-auto",
                                isActive
                                    ? "bg-[var(--bg-tertiary)] text-[var(--accent-cyan)] shadow-[0_0_10px_rgba(0,255,179,0.2)] border border-[var(--border-medium)]"
                                    : "text-[var(--text-secondary)] hover:text-white hover:bg-[var(--bg-tertiary)]"
                            )}
                        >
                            <Icon className={clsx("w-6 h-6", isActive && "drop-shadow-[0_0_5px_rgba(0,255,179,0.5)]")} />

                            {/* Tooltip */}
                            <span className="absolute left-14 bg-[var(--bg-tertiary)] text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity border border-[var(--border-subtle)] pointer-events-none whitespace-nowrap z-50">
                                {item.label}
                            </span>

                            {/* Active Indicator */}
                            {isActive && (
                                <div className="absolute -left-3 w-1 h-6 bg-[var(--accent-cyan)] rounded-r-full shadow-[0_0_8px_var(--accent-cyan)]" />
                            )}
                        </Link>
                    );
                })}
            </nav>
        </aside>
    );
}
