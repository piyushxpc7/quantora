'use client';

import { useEffect, useState } from 'react';
import { getDriftSummary, getDriftHistory, analyzeDrift, DriftSummary, DriftHistoryItem } from '@/lib/api';
import DriftChart from '@/components/DriftChart';

export default function DriftPage() {
  const [summary, setSummary] = useState<DriftSummary | null>(null);
  const [history, setHistory] = useState<DriftHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const refresh = async () => {
    const [s, h] = await Promise.all([getDriftSummary(), getDriftHistory()]);
    setSummary(s);
    setHistory(h);
  };

  useEffect(() => {
    let cancelled = false;
    Promise.all([getDriftSummary(), getDriftHistory()])
      .then(([s, h]) => {
        if (cancelled) return;
        setSummary(s);
        setHistory(h);
        setLoading(false);
      })
      .catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const runSampleDrift = async () => {
    setRunning(true);
    // Generate two distributions: one stable, one slightly shifted (simulates real drift scenario)
    const ref = Array.from({ length: 100 }, () => Math.random() * 2 + 0.5);
    const curr = Array.from({ length: 100 }, () => Math.random() * 2 + 0.9); // mean shifted
    await analyzeDrift(ref, curr, 'momentum_feature').catch(console.error);
    await refresh();
    setRunning(false);
  };

  const fmt = (n: number | null | undefined, decimals = 3) =>
    n == null ? '—' : n.toFixed(decimals);

  const severityStyle = (s: string | null | undefined) => {
    if (s === 'high') return 'bg-red-500/10 text-red-400 border-red-500/20';
    if (s === 'medium') return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    return 'bg-green-500/10 text-green-400 border-green-500/20';
  };

  // Build chart data from history (last 20 points, oldest first)
  const chartData = [...history].reverse().slice(-20).map((r, i) => ({
    name: `Check ${i + 1}`,
    psi: r.psi_value,
    threshold: 0.2,
  }));

  return (
    <div className="space-y-8">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Drift Lab</h1>
          <p className="text-slate-400 mt-1">The PSI + KS engine that powers live regime monitoring — run ad-hoc distribution checks here.</p>
        </div>
        <button
          onClick={runSampleDrift}
          disabled={running}
          className="bg-sky-600 hover:bg-sky-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          {running ? 'Analyzing...' : 'Run Drift Check'}
        </button>
      </header>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card p-6 animate-pulse h-28" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card p-6">
            <h3 className="text-slate-400 text-sm font-medium">Current PSI</h3>
            <p className={`text-3xl font-bold mt-2 ${(summary?.latest_psi ?? 0) >= 0.2 ? 'text-red-400' : (summary?.latest_psi ?? 0) >= 0.1 ? 'text-yellow-400' : 'text-green-400'}`}>
              {fmt(summary?.latest_psi)}
            </p>
            <span className={`text-xs mt-2 block ${(summary?.latest_psi ?? 0) >= 0.2 ? 'text-red-400/70' : 'text-green-400/70'}`}>
              {(summary?.latest_psi ?? 0) >= 0.2 ? 'Significant Drift' : (summary?.latest_psi ?? 0) >= 0.1 ? 'Moderate Drift' : 'Stable'}
            </span>
          </div>
          <div className="card p-6">
            <h3 className="text-slate-400 text-sm font-medium">KS Test P-Value</h3>
            <p className={`text-3xl font-bold mt-2 ${(summary?.latest_ks_p_value ?? 1) < 0.05 ? 'text-yellow-400' : 'text-white'}`}>
              {fmt(summary?.latest_ks_p_value)}
            </p>
            <span className={`text-xs mt-2 block ${(summary?.latest_ks_p_value ?? 1) < 0.05 ? 'text-yellow-400/70' : 'text-green-400/70'}`}>
              {(summary?.latest_ks_p_value ?? 1) < 0.05 ? 'Distribution Shift (p < 0.05)' : 'No Significant Shift'}
            </span>
          </div>
          <div className="card p-6">
            <h3 className="text-slate-400 text-sm font-medium">Drift Alerts</h3>
            <p className={`text-3xl font-bold mt-2 ${(summary?.alert_count ?? 0) > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
              {summary?.alert_count ?? '—'}
            </p>
            <span className="text-xs text-slate-500 mt-2 block">
              of {summary?.total_checks ?? 0} checks
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="card p-6">
          <h2 className="text-xl font-semibold mb-6">PSI Trend</h2>
          <DriftChart data={chartData} />
        </div>
        <div className="card p-6">
          <h2 className="text-xl font-semibold mb-6">Severity Distribution</h2>
          <div className="space-y-3 mt-4">
            {(['high', 'medium', 'low'] as const).map(sev => {
              const count = history.filter(r => r.severity === sev).length;
              const pct = history.length ? (count / history.length) * 100 : 0;
              return (
                <div key={sev}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="capitalize text-slate-300">{sev}</span>
                    <span className="text-slate-400">{count} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${sev === 'high' ? 'bg-red-500' : sev === 'medium' ? 'bg-yellow-500' : 'bg-green-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
            {history.length === 0 && <p className="text-slate-500 text-sm">No checks yet. Click &quot;Run Drift Check&quot; above.</p>}
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="p-6 border-b border-slate-800">
          <h2 className="text-xl font-semibold">Recent Drift Reports</h2>
        </div>
        <table className="w-full text-left text-sm text-slate-400">
          <thead className="bg-slate-950 text-slate-200 uppercase font-medium">
            <tr>
              <th className="px-6 py-4">Timestamp</th>
              <th className="px-6 py-4">Feature</th>
              <th className="px-6 py-4">PSI</th>
              <th className="px-6 py-4">KS P-Value</th>
              <th className="px-6 py-4">Severity</th>
              <th className="px-6 py-4">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {history.map(r => (
              <tr key={r.id} className="hover:bg-slate-800/50 transition-colors">
                <td className="px-6 py-4">{new Date(r.timestamp).toLocaleString()}</td>
                <td className="px-6 py-4">{r.feature_name}</td>
                <td className="px-6 py-4">{fmt(r.psi_value)}</td>
                <td className="px-6 py-4">{fmt(r.ks_p_value)}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs border capitalize ${severityStyle(r.severity)}`}>
                    {r.severity}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs border ${r.overall_drift ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-green-500/10 text-green-400 border-green-500/20'}`}>
                    {r.overall_drift ? 'Drift' : 'Stable'}
                  </span>
                </td>
              </tr>
            ))}
            {history.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                  No drift reports yet. Click &quot;Run Drift Check&quot; to analyze.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
