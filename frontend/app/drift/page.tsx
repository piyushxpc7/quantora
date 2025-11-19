'use client';

import DriftChart from '@/components/DriftChart';

export default function DriftPage() {
    return (
        <div className="space-y-8">
            <header>
                <h1 className="text-3xl font-bold text-white">Drift Monitoring</h1>
                <p className="text-slate-400 mt-1">Real-time Model Performance & Data Drift Analysis</p>
            </header>

            {/* Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-slate-900 p-6 rounded-xl border border-slate-800">
                    <h3 className="text-slate-400 text-sm font-medium">Current PSI</h3>
                    <p className="text-3xl font-bold text-red-400 mt-2">0.25</p>
                    <span className="text-red-400/70 text-xs mt-2 block">Significant Drift Detected</span>
                </div>
                <div className="bg-slate-900 p-6 rounded-xl border border-slate-800">
                    <h3 className="text-slate-400 text-sm font-medium">KS Test P-Value</h3>
                    <p className="text-3xl font-bold text-white mt-2">0.03</p>
                    <span className="text-yellow-400/70 text-xs mt-2 block">Distribution Shift (p &lt; 0.05)</span>
                </div>
                <div className="bg-slate-900 p-6 rounded-xl border border-slate-800">
                    <h3 className="text-slate-400 text-sm font-medium">Autoencoder Loss</h3>
                    <p className="text-3xl font-bold text-white mt-2">0.012</p>
                    <span className="text-green-400/70 text-xs mt-2 block">Within Normal Range</span>
                </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="bg-slate-900 p-6 rounded-xl border border-slate-800">
                    <h2 className="text-xl font-semibold mb-6">Population Stability Index (PSI) Trend</h2>
                    <DriftChart />
                </div>

                <div className="bg-slate-900 p-6 rounded-xl border border-slate-800">
                    <h2 className="text-xl font-semibold mb-6">Feature Distribution Comparison</h2>
                    <div className="h-64 flex items-center justify-center bg-slate-950 rounded-lg border border-slate-800/50">
                        <p className="text-slate-500">Distribution Chart Placeholder</p>
                    </div>
                </div>
            </div>

            {/* Alerts Table */}
            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                <div className="p-6 border-b border-slate-800">
                    <h2 className="text-xl font-semibold">Recent Drift Alerts</h2>
                </div>
                <table className="w-full text-left text-sm text-slate-400">
                    <thead className="bg-slate-950 text-slate-200 uppercase font-medium">
                        <tr>
                            <th className="px-6 py-4">Timestamp</th>
                            <th className="px-6 py-4">Metric</th>
                            <th className="px-6 py-4">Severity</th>
                            <th className="px-6 py-4">Message</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        <tr className="hover:bg-slate-800/50 transition-colors">
                            <td className="px-6 py-4">2023-10-27 14:30</td>
                            <td className="px-6 py-4">PSI</td>
                            <td className="px-6 py-4"><span className="bg-red-500/10 text-red-400 px-2 py-1 rounded text-xs border border-red-500/20">High</span></td>
                            <td className="px-6 py-4 text-slate-300">PSI exceeded 0.2 threshold on Tech Sector features.</td>
                        </tr>
                        <tr className="hover:bg-slate-800/50 transition-colors">
                            <td className="px-6 py-4">2023-10-27 10:15</td>
                            <td className="px-6 py-4">KS Test</td>
                            <td className="px-6 py-4"><span className="bg-yellow-500/10 text-yellow-400 px-2 py-1 rounded text-xs border border-yellow-500/20">Medium</span></td>
                            <td className="px-6 py-4 text-slate-300">Distribution shift detected in Volatility feature.</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    );
}
