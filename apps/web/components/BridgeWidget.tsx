import { useState, useEffect } from 'react';
import { useAccount, useWalletClient } from 'wagmi';
import { getBridgeQuote, executeBridgeRoute, getSupportedChains, getSupportedTokens } from '../services/lifi';
import { Route, Chain, Token } from '@lifi/sdk';
import { ArrowRight, Loader2, Wallet, AlertCircle } from 'lucide-react';

export default function BridgeWidget() {
    const { address, isConnected } = useAccount();
    const { data: walletClient } = useWalletClient();

    const [chains, setChains] = useState<Chain[]>([]);
    const [tokens, setTokens] = useState<Token[]>([]);

    // Default to Arbitrum (42161) -> Morph Testnet (approx for now or Sepolia 11155111)
    // For this implementation, we allow bridging FROM any chain TO Sepolia (as a proxy for our target L2)
    const TARGET_CHAIN_ID = 11155111; // Sepolia

    const [fromChainId, setFromChainId] = useState<number>(42161); // Default Arbitrum One
    const [fromTokenAddress, setFromTokenAddress] = useState<string>('0x0000000000000000000000000000000000000000'); // ETH
    const [amount, setAmount] = useState<string>('');
    const [routes, setRoutes] = useState<Route[]>([]);
    const [loading, setLoading] = useState(false);
    const [executing, setExecuting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);

    // Initial Data Load
    useEffect(() => {
        const loadChains = async () => {
            const c = await getSupportedChains();
            setChains(c);
            // Load tokens for default chain
            const t = await getSupportedTokens(fromChainId);
            setTokens(t);
        };
        loadChains();
    }, []);

    // Update tokens when chain changes
    useEffect(() => {
        const loadTokens = async () => {
            const t = await getSupportedTokens(fromChainId);
            setTokens(t);
            // Reset token to ETH/Native if available or first token
            // Simplified: Default to first token or ETH if found
            setFromTokenAddress('0x0000000000000000000000000000000000000000');
        };
        loadTokens();
    }, [fromChainId]);

    // Fetch Quote Debounced
    useEffect(() => {
        const timer = setTimeout(async () => {
            if (!amount || parseFloat(amount) <= 0 || !address) return;

            setLoading(true);
            setError(null);
            setRoutes([]);

            try {
                // Convert amount to wei (simplified, assuming 18 decimals for ETH/USDC for now)
                // In production, use proper decimals from Token object
                const amountWei = (parseFloat(amount) * 1e18).toString();

                const routes = await getBridgeQuote({
                    fromChain: fromChainId,
                    toChain: TARGET_CHAIN_ID,
                    fromToken: fromTokenAddress,
                    toToken: '0x0000000000000000000000000000000000000000', // Target ETH
                    fromAmount: amountWei,
                    fromAddress: address,
                });
                setRoutes(routes);
            } catch (e: any) {
                console.error(e);
                setError("Failed to fetch routes. " + e.message);
            } finally {
                setLoading(false);
            }
        }, 800);

        return () => clearTimeout(timer);
    }, [amount, fromChainId, fromTokenAddress, address]);

    const handleBridge = async () => {
        if (!routes.length || !walletClient) return;

        setExecuting(true);
        setStatus('Initiating Bridge...');
        try {
            // Need to switch chain if not on fromChain?
            // walletClient.switchChain might be needed or let LiFi handle it?
            // LiFi usually handles it if we pass the signer/client correctly.

            // NOTE: We need an adapter for Viem WalletClient -> Ethers Signer if LiFi requires it.
            // For now, attempting to pass walletClient directly (as per v3 docs hint).
            // If this fails, we need the `walletClientToSigner` adapter.

            await executeBridgeRoute(walletClient, routes[0]);
            setStatus('Bridge Completed!');
        } catch (e: any) {
            setError(e.message || 'Bridge Failed');
            setStatus(null);
        } finally {
            setExecuting(false);
        }
    };

    const bestRoute = routes[0];

    return (
        <div className="p-6 bg-bg-secondary rounded-2xl border border-border-subtle max-w-md mx-auto shadow-2xl">
            <h2 className="text-xl font-display font-bold mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
                Interchain Bridge
            </h2>

            {/* From */}
            <div className="space-y-2 mb-4">
                <label className="text-xs text-text-tertiary uppercase tracking-wider">From Network</label>
                <select
                    value={fromChainId}
                    onChange={(e) => setFromChainId(Number(e.target.value))}
                    className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-sm focus:border-accent-primary outline-none"
                >
                    {chains.map(c => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                </select>
            </div>

            {/* Token & Amount */}
            <div className="space-y-2 mb-6">
                <label className="text-xs text-text-tertiary uppercase tracking-wider">Send Amount</label>
                <div className="relative">
                    <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        placeholder="0.0"
                        className="w-full bg-bg-tertiary border border-border-medium rounded-xl p-3 text-lg font-mono focus:border-accent-primary outline-none pr-20"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-bold text-text-secondary">
                        ETH
                    </span>
                </div>
            </div>

            {/* To (Fixed) */}
            <div className="flex items-center gap-2 mb-6 opacity-50">
                <ArrowRight className="w-4 h-4 text-text-tertiary" />
                <div className="flex-1 p-3 bg-bg-tertiary/50 border border-border-subtle rounded-xl flex justify-between items-center px-4">
                    <span className="text-sm font-medium">Sepolia / Morph</span>
                    <span className="text-xs text-text-tertiary">Target</span>
                </div>
            </div>

            {/* Quote Card */}
            {loading ? (
                <div className="h-24 flex items-center justify-center border border-dashed border-border-medium rounded-xl mb-6">
                    <Loader2 className="w-5 h-5 animate-spin text-text-tertiary" />
                </div>
            ) : bestRoute ? (
                <div className="mb-6 p-4 bg-accent-primary/5 border border-accent-primary/20 rounded-xl">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-xs text-text-tertiary uppercase">Estimated Recieve</span>
                        <span className="font-mono font-bold text-accent-primary">
                            {(Number(bestRoute.toAmount) / 1e18).toFixed(4)} ETH
                        </span>
                    </div>
                    <div className="flex justify-between items-center text-xs text-text-secondary">
                        <span>Gas Cost</span>
                        <span>${bestRoute.gasCostUSD || '0.00'}</span>
                    </div>
                    <div className="flex justify-between items-center text-xs text-text-secondary mt-1">
                        <span>Time</span>
                        <span>~{Math.ceil(bestRoute.insurance?.state === 'INSURED' ? 1 : 10)} min</span>
                        {/* simplified time */}
                    </div>
                </div>
            ) : amount ? (
                <div className="mb-6 p-4 text-center text-sm text-text-tertiary">
                    No routes found.
                </div>
            ) : null}

            {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    {error}
                </div>
            )}

            {/* Actions */}
            <div className="space-y-3">
                {!isConnected ? (
                    <div className="w-full py-3 bg-bg-tertiary text-text-tertiary rounded-xl text-center text-sm">
                        Connect Wallet to Bridge
                    </div>
                ) : (
                    <button
                        onClick={handleBridge}
                        disabled={!bestRoute || executing || loading}
                        className="w-full py-4 bg-gradient-to-r from-accent-primary to-accent-secondary rounded-xl text-bg-primary font-bold uppercase tracking-wider shadow-lg hover:shadow-accent-primary/20 disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
                    >
                        {executing ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                {status || 'Processing...'}
                            </>
                        ) : (
                            'Bridge Funds'
                        )}
                    </button>
                )}
            </div>

            <div className="mt-4 text-[10px] text-center text-text-tertiary">
                Powered by LI.FI
            </div>
        </div>
    );
}
