'use client';

export default function SettingsPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

  return (
    <div className="space-y-8 max-w-2xl">
      <header>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-slate-400 mt-1">Platform configuration</p>
      </header>

      <div className="bg-slate-900 rounded-xl border border-slate-800 divide-y divide-slate-800">
        <div className="p-6">
          <h2 className="text-lg font-semibold mb-4">Connection</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-slate-400 text-sm">Backend API</span>
              <code className="text-xs bg-slate-800 px-3 py-1.5 rounded text-blue-300">{apiUrl}</code>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400 text-sm">API Version</span>
              <code className="text-xs bg-slate-800 px-3 py-1.5 rounded text-blue-300">v1</code>
            </div>
          </div>
        </div>

        <div className="p-6">
          <h2 className="text-lg font-semibold mb-4">Risk Controls</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-white">CVaR Limit</p>
                <p className="text-xs text-slate-500 mt-0.5">Workflow halts if portfolio CVaR exceeds this threshold</p>
              </div>
              <span className="text-slate-300 text-sm font-mono">Set via RISK_CVAR_LIMIT env var</span>
            </div>
          </div>
        </div>

        <div className="p-6">
          <h2 className="text-lg font-semibold mb-4">LLM Configuration</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-white">Provider</p>
                <p className="text-xs text-slate-500 mt-0.5">Falls back to offline mock if API key is unset</p>
              </div>
              <span className="text-slate-300 text-sm">OpenAI (GPT-4o)</span>
            </div>
          </div>
        </div>

        <div className="p-6">
          <h2 className="text-lg font-semibold mb-2">About Quantora</h2>
          <p className="text-slate-400 text-sm">
            Multi-agent quantitative finance platform. Strategy generation → Backtesting →
            Risk management → Portfolio optimization, powered by real market data and AI.
          </p>
          <p className="text-slate-600 text-xs mt-3">v0.1.0 · MIT License</p>
        </div>
      </div>
    </div>
  );
}
