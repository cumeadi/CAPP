"use client";

import { clsx } from "clsx";
import { Copy } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "outline" | "ghost";
    size?: "sm" | "md" | "lg";
    icon?: React.ElementType;
    isLoading?: boolean;
}

export function Button({
    children,
    variant = "primary",
    size = "md",
    className,
    icon: Icon,
    isLoading,
    disabled,
    ...props
}: ButtonProps) {
    const variants = {
        primary: "bg-[var(--accent-cyan)] text-black hover:bg-[#00DDA0] shadow-[0_0_15px_rgba(0,255,179,0.3)] border-none",
        secondary: "bg-[var(--bg-tertiary)] text-white border border-[var(--border-medium)] hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)]",
        outline: "bg-transparent border border-[var(--accent-cyan)] text-[var(--accent-cyan)] hover:bg-[rgba(0,255,179,0.1)]",
        ghost: "bg-transparent text-[var(--text-secondary)] hover:text-white"
    };

    const sizes = {
        sm: "px-3 py-1.5 text-xs rounded-lg",
        md: "px-5 py-2.5 text-sm rounded-xl",
        lg: "px-8 py-4 text-base rounded-2xl font-bold"
    };

    return (
        <button
            className={clsx(
                "flex items-center justify-center gap-2 transition-all duration-300 font-mono tracking-wide active:scale-95 disabled:opacity-50 disabled:pointer-events-none cursor-pointer",
                variants[variant],
                sizes[size],
                className
            )}
            disabled={disabled || isLoading}
            {...props}
        >
            {isLoading ? (
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
                Icon && <Icon className="w-4 h-4" />
            )}
            {children}
        </button>
    );
}
