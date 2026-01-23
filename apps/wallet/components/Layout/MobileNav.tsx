"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Send, QrCode, History, Settings } from "lucide-react";
import { clsx } from "clsx";

const NAV_ITEMS = [
    { icon: Home, label: "Home", href: "/" },
    { icon: Send, label: "Send", href: "/send" },
    { icon: QrCode, label: "Receive", href: "/receive" },
    { icon: History, label: "History", href: "/history" },
    { icon: Settings, label: "Settings", href: "/settings" },
];

export function MobileNav() {
    const pathname = usePathname();

    return (
        <nav className="fixed bottom-0 left-0 right-0 h-20 bg-[var(--bg-secondary)] border-t border-[var(--border-medium)] flex items-center justify-around px-2 z-50 backdrop-blur-lg safe-pb">
            {NAV_ITEMS.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;

                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={clsx(
                            "flex flex-col items-center justify-center w-14 h-14 rounded-xl transition-all duration-300",
                            isActive
                                ? "text-[var(--accent-cyan)]"
                                : "text-[var(--text-secondary)] hover:text-white"
                        )}
                    >
                        <div className={clsx(
                            "p-2 rounded-xl transition-all duration-300 mb-1",
                            isActive && "bg-[var(--bg-tertiary)] shadow-[0_0_10px_rgba(0,255,179,0.2)]"
                        )}>
                            <Icon className="w-5 h-5" />
                        </div>
                        <span className="text-[10px] font-medium tracking-wide">
                            {item.label}
                        </span>
                    </Link>
                );
            })}
        </nav>
    );
}
