'use client';
import { BalanceCard } from '@/components/dashboard/BalanceCard';
import { RouteEstimator } from '@/components/dashboard/RouteEstimator';

export default function DashboardPage() {
    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-blue-400 to-emerald-400 text-transparent bg-clip-text">
                    Command Center
                </h1>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <BalanceCard />
                {/* Metrics placeholders */}
                <div className="p-6 rounded-xl border border-white/10 bg-black/40 backdrop-blur-sm">
                    <h3 className="text-sm font-medium text-muted-foreground">Active Agents</h3>
                    <div className="mt-2 text-2xl font-bold">3</div>
                </div>
                <div className="p-6 rounded-xl border border-white/10 bg-black/40 backdrop-blur-sm">
                    <h3 className="text-sm font-medium text-muted-foreground">Routes (24h)</h3>
                    <div className="mt-2 text-2xl font-bold">128</div>
                </div>
                <div className="p-6 rounded-xl border border-white/10 bg-black/40 backdrop-blur-sm">
                    <h3 className="text-sm font-medium text-muted-foreground">Volume (24h)</h3>
                    <div className="mt-2 text-2xl font-bold">$12.4k</div>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
                {/* Main Content Area */}
                <div className="col-span-4 p-6 rounded-xl border border-white/10 bg-black/40 backdrop-blur-sm min-h-[400px]">
                    <h2 className="text-xl font-semibold mb-4">Route Estimator & Execution</h2>
                    <RouteEstimator />
                </div>

                {/* Sidebar / Feed */}
                <div className="col-span-3 p-6 rounded-xl border border-white/10 bg-black/40 backdrop-blur-sm">
                    <h2 className="text-xl font-semibold mb-4">Relayer Activity</h2>
                    <div className="space-y-4">
                        {/* Mock items */}
                        <div className="flex justify-between items-center text-sm p-2 rounded hover:bg-white/5">
                            <div>
                                <div className="font-medium">USDC Bridge</div>
                                <div className="text-xs text-muted-foreground">Aptos -> Polygon</div>
                            </div>
                            <span className="text-emerald-400">Completed</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
