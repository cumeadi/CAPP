import type { Metadata } from "next";
import { JetBrains_Mono, Syne } from "next/font/google"; // Using Syne for display if needed, matches globals.css var
import "./globals.css";
import { Web3Provider } from "@/components/Providers/Web3Provider";

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

const syne = Syne({
  variable: "--font-syne",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CAPP Wallet",
  description: "Advanced Multi-Chain Personal Wallet",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${jetbrainsMono.variable} ${syne.variable} font-mono bg-[var(--bg-primary)] text-[var(--text-primary)] antialiased relative`}
      >
        <div className="background-grid" />
        <Web3Provider>
          {children}
        </Web3Provider>
      </body>
    </html>
  );
}
