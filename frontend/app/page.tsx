export default function Home() {
  return (
    <div className="space-y-8">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 mt-1">Market Overview & System Status</p>
        </div>
        <div className="flex space-x-4">
          <span className="px-3 py-1 bg-green-500/10 text-green-400 rounded-full text-sm border border-green-500/20 flex items-center">
            <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
            System Operational
          </span>
        </div>
      </header>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-slate-900 p-6 rounded-xl border border-slate-800 hover:border-blue-500/50 transition-colors">
          <h3 className="text-slate-400 text-sm font-medium">Active Strategies</h3>
          <p className="text-3xl font-bold text-white mt-2">12</p>
          <span className="text-green-400 text-xs mt-2 block">↑ 2 new today</span>
        </div>
        <div className="bg-slate-900 p-6 rounded-xl border border-slate-800 hover:border-blue-500/50 transition-colors">
          <h3 className="text-slate-400 text-sm font-medium">Total AUM</h3>
          <p className="text-3xl font-bold text-white mt-2">$1.2M</p>
          <span className="text-green-400 text-xs mt-2 block">+4.5% vs last month</span>
        </div>
        <div className="bg-slate-900 p-6 rounded-xl border border-slate-800 hover:border-blue-500/50 transition-colors">
          <h3 className="text-slate-400 text-sm font-medium">Drift Alerts</h3>
          <p className="text-3xl font-bold text-white mt-2">3</p>
          <span className="text-yellow-400 text-xs mt-2 block">Requires attention</span>
        </div>
        <div className="bg-slate-900 p-6 rounded-xl border border-slate-800 hover:border-blue-500/50 transition-colors">
          <h3 className="text-slate-400 text-sm font-medium">Daily PnL</h3>
          <p className="text-3xl font-bold text-white mt-2">+$12.4k</p>
          <span className="text-green-400 text-xs mt-2 block">+1.2% today</span>
        </div>
      </div>

      {/* Recent Activity & Market Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 bg-slate-900 p-6 rounded-xl border border-slate-800">
          <h2 className="text-xl font-semibold mb-4">Market Regime Analysis</h2>
          <div className="h-64 bg-slate-950 rounded-lg flex items-center justify-center border border-slate-800/50">
            <p className="text-slate-500">Market Chart Placeholder (Recharts)</p>
          </div>
        </div>

        <div className="bg-slate-900 p-6 rounded-xl border border-slate-800">
          <h2 className="text-xl font-semibold mb-4">Recent Alerts</h2>
          <div className="space-y-4">
            <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
              <p className="text-sm text-yellow-200 font-medium">Drift Detected: Momentum Strategy</p>
              <p className="text-xs text-yellow-500/70 mt-1">PSI &gt; 0.25 on Tech Sector</p>
            </div>
            <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <p className="text-sm text-blue-200 font-medium">New Strategy Generated</p>
              <p className="text-xs text-blue-500/70 mt-1">Mean Reversion on Energy</p>
            </div>
            <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
              <p className="text-sm text-green-200 font-medium">Portfolio Rebalanced</p>
              <p className="text-xs text-green-500/70 mt-1">Optimized for low volatility</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
