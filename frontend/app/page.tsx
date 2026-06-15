'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  getDashboardStats, getWorkflowRuns, getMonitored, getAlerts, getPaperAccount,
  WorkflowRun, MonitoredStrategy, DriftAlert, PaperAccount,
} from '@/lib/api';
import { AreaChart, Area, ResponsiveContainer, Tooltip, YAxis } from 'recharts';
import { Card, StatTile, VerdictBadge, Pct } from '@/components/ui';
import { Sparkles, Radar, Wallet, ShieldAlert, ArrowUpRight, Activity } from 'lucide-react';

interface Stats {
  total_strategies: number; approved_strategies: number; monitored_strategies: number;
  latest_cagr: number; avg_sharpe: number; avg_honesty: number | null; overfit_rejected: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [monitored, setMonitored] = useState<MonitoredStrategy[]>([]);
  const [alerts, setAlerts] = useState<DriftAlert[]>([]);
  const [paper, setPaper] = useState<PaperAccount | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getDashboardStats(), getWorkflowRuns(), getMonitored(), getAlerts(), getPaperAccount(),
    ]).then(([s, r, m, a, p]) => {
      setStats(s as Stats); setRuns(r); setMonitored(m); setAlerts(a); setPaper(p);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  const statusDot = (s: string) =>
    s === 'shifted' ? 'bg-rose-400 pulse-ring' : s === 'watch' ? 'bg-amber-400' : 'bg-emerald-400';

  return (
    <div className="space-y-7">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Command Center</h1>
          <p className="text-slate-400 mt-1">Research → Honest validation → Live monitoring → Paper execution.</p>
        </div>
        <Link href="/agents" className="bg-sky-600 hover:bg-sky-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-colors">
          <Sparkles size={16} /> New research
        </Link>
      </header>

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map(i => <Card key={i} className="h-28 animate-pulse" />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatTile label="Avg Honesty Score" value={stats?.avg_honesty ?? '—'}
            sub={`${stats?.total_strategies ?? 0} strategies researched`}
            tone={(stats?.avg_honesty ?? 0) >= 65 ? 'good' : (stats?.avg_honesty ?? 0) >= 40 ? 'warn' : 'bad'} />
          <StatTile label="Overfits Caught" value={stats?.overfit_rejected ?? 0}
            sub="rejected before deployment" tone="bad" />
          <StatTile label="Live Monitored" value={stats?.monitored_strategies ?? monitored.length}
            sub={`${alerts.length} regime alerts`} />
          <StatTile label="Paper P&L" value={paper ? <Pct v={paper.pnl_pct} sign /> : '—'}
            sub={paper ? `$${paper.equity.toLocaleString()} equity` : ''}
            tone={(paper?.pnl ?? 0) >= 0 ? 'good' : 'bad'} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent research */}
        <Card className="lg:col-span-2 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Recent Research</h2>
            <Link href="/agents" className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1">Open copilot <ArrowUpRight size={13} /></Link>
          </div>
          <div className="space-y-2">
            {runs.slice(0, 6).map(r => (
              <div key={r.id} className="flex items-center justify-between p-3 rounded-xl border border-slate-800/70 hover:border-slate-700 transition-colors">
                <div className="min-w-0">
                  <p className="text-sm text-slate-200 truncate">{r.strategy_name || r.user_request}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5 mono">
                    OOS Sharpe {r.oos_sharpe?.toFixed(2) ?? '—'} · CAGR {r.cagr != null ? `${(r.cagr * 100).toFixed(1)}%` : '—'}
                    {r.is_monitored && <span className="text-emerald-400"> · monitored</span>}
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {r.honesty_score != null && <span className="text-lg font-bold mono text-slate-300">{Math.round(r.honesty_score)}</span>}
                  <VerdictBadge verdict={r.verdict ?? undefined} />
                </div>
              </div>
            ))}
            {runs.length === 0 && <p className="text-slate-500 text-sm py-6 text-center">No research yet.</p>}
          </div>
        </Card>

        {/* Paper sparkline + monitored health */}
        <div className="space-y-6">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2"><Wallet size={15} className="text-emerald-400" /> Paper Equity</h2>
              <Link href="/paper" className="text-xs text-sky-400 hover:text-sky-300">Details</Link>
            </div>
            <div className="h-24">
              {paper && paper.equity_curve.length > 1 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={paper.equity_curve}>
                    <defs>
                      <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#34d399" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <YAxis hide domain={['auto', 'auto']} />
                    <Tooltip contentStyle={{ backgroundColor: '#0c1220', borderColor: '#1e293b', borderRadius: 10 }} formatter={(v: number) => [`$${v.toLocaleString()}`, 'Equity']} />
                    <Area type="monotone" dataKey="value" stroke="#34d399" strokeWidth={2} fill="url(#eq)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <div className="h-full flex items-center justify-center text-slate-600 text-xs">No paper activity</div>}
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2 mb-3"><Radar size={15} className="text-sky-400" /> Monitored Health</h2>
            <div className="space-y-2">
              {monitored.slice(0, 5).map(m => (
                <div key={m.id} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2 min-w-0">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${statusDot(m.regime_status)}`} />
                    <span className="text-slate-300 truncate">{m.name}</span>
                  </span>
                  <span className="text-xs text-slate-500 mono shrink-0">PSI {m.latest_psi?.toFixed(3) ?? '—'}</span>
                </div>
              ))}
              {monitored.length === 0 && <p className="text-slate-500 text-sm">Nothing monitored yet.</p>}
            </div>
          </Card>
        </div>
      </div>

      {/* Alerts strip */}
      {alerts.length > 0 && (
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2 mb-3"><ShieldAlert size={15} className="text-amber-400" /> Latest Regime Alerts</h2>
          <div className="space-y-2">
            {alerts.slice(0, 3).map(a => (
              <div key={a.id} className="flex items-start gap-2 text-sm">
                <Activity size={14} className="text-amber-400 mt-0.5 shrink-0" />
                <span className="text-slate-300">{a.message}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
