import type { Metadata } from "next";
import { JetBrains_Mono, Syne } from "next/font/google";
import "./globals.css";
import { Web3Provider } from "@/components/Providers/Web3Provider";
import { SettingsProvider } from "@/components/Context/SettingsContext";
import { AptosProvider } from "@/components/Providers/AptosProvider";

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
        <SettingsProvider>
          <Web3Provider>
            <AptosProvider>
              {children}
            </AptosProvider>
          </Web3Provider>
        </SettingsProvider>
      </body>
    </html>
  );
}
