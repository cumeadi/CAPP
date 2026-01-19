'use client';
import { useState } from 'react';
import { api } from '@/services/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowRight, Zap, Clock, Shield } from 'lucide-react';

export function RouteEstimator() {
    const [amount, setAmount] = useState('100');
    const [recipient, setRecipient] = useState('0xRecipient');
    const [preference, setPreference] = useState('CHEAPEST');
    const [loading, setLoading] = useState(false);
    const [routes, setRoutes] = useState<any[]>([]);
    const [selectedRoute, setSelectedRoute] = useState<any>(null);
    const [executionStatus, setExecutionStatus] = useState<string>('');

    const handleCalculate = async () => {
        setLoading(true);
        setRoutes([]);
        setSelectedRoute(null);
        try {
            const res = await api.calculateRoute(Number(amount), "USDC", recipient, preference);
            setRoutes(res.routes || []);
            if (res.recommended_route) {
                setSelectedRoute(res.recommended_route);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleExecute = async () => {
        if (!selectedRoute) return;
        setExecutionStatus('PROCESSING');
        try {
            // Adapt the route object to what the API expects
            const payload = {
                amount: Number(amount),
                to_chain: 'Polygon', // Hardcoded for demo/MVP if not in route
                recipient: recipient,
                ...selectedRoute
            };

            await api.relayPayment(payload);
            setExecutionStatus('COMPLETED');
            setTimeout(() => setExecutionStatus(''), 5000);
        } catch (e) {
            console.error(e);
            setExecutionStatus('FAILED');
        }
    };

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <label className="text-xs text-muted-foreground">Amount (USDC)</label>
                    <Input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        className="bg-black/20"
                    />
                </div>
                <div className="space-y-2">
                    <label className="text-xs text-muted-foreground">Recipient</label>
                    <Input
                        value={recipient}
                        onChange={(e) => setRecipient(e.target.value)}
                        className="bg-black/20"
                    />
                </div>
            </div>

            <div className="flex gap-2">
                <Select value={preference} onValueChange={setPreference}>
                    <SelectTrigger className="w-[180px] bg-black/20">
                        <SelectValue placeholder="Preference" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="CHEAPEST">Cheapest</SelectItem>
                        <SelectItem value="FASTEST">Fastest</SelectItem>
                    </SelectContent>
                </Select>

                <Button onClick={handleCalculate} disabled={loading} className="flex-1 bg-white/10 hover:bg-white/20">
                    {loading ? "Calculating..." : "Find Routes"}
                </Button>
            </div>

            {/* Results */}
            {routes.length > 0 && (
                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2">
                    <h3 className="text-sm font-medium text-muted-foreground">Best Routes</h3>
                    <div className="grid gap-3">
                        {routes.map((route, idx) => (
                            <div
                                key={idx}
                                onClick={() => setSelectedRoute(route)}
                                className={`p-4 rounded-lg border cursor-pointer transition-all ${selectedRoute === route
                                        ? 'border-blue-500 bg-blue-500/10'
                                        : 'border-white/5 bg-white/5 hover:border-white/20'
                                    }`}
                            >
                                <div className="flex justify-between items-center mb-2">
                                    <div className="flex items-center gap-2">
                                        <span className="font-bold">{route.chain}</span>
                                        {idx === 0 && <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full">RECOMMENDED</span>}
                                    </div>
                                    <div className="text-sm font-mono">${route.fee_usd} USD</div>
                                </div>
                                <div className="flex justify-between text-xs text-muted-foreground">
                                    <div className="flex items-center gap-1">
                                        <Clock size={12} />
                                        {Math.round(route.eta_seconds / 60)} min
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Shield size={12} />
                                        Score: {Math.round(route.recommendation_score * 100)}%
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="pt-4 border-t border-white/10">
                        <Button
                            onClick={handleExecute}
                            disabled={!selectedRoute || executionStatus === 'PROCESSING'}
                            className={`w-full ${executionStatus === 'COMPLETED' ? 'bg-emerald-600' :
                                    executionStatus === 'FAILED' ? 'bg-red-600' :
                                        'bg-blue-600 hover:bg-blue-500'
                                }`}
                        >
                            {executionStatus === 'PROCESSING' && "Relaying..."}
                            {executionStatus === 'COMPLETED' && "Payment Executed!"}
                            {executionStatus === 'FAILED' && "Execution Failed"}
                            {executionStatus === '' && (
                                <span className="flex items-center gap-2">
                                    Execute Route <ArrowRight size={16} />
                                </span>
                            )}
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
