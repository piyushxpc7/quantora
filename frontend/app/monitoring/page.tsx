'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  getMonitored, getAlerts, checkMonitored, stopMonitored,
  MonitoredStrategy, DriftAlert,
} from '@/lib/api';
import { Card, VerdictBadge } from '@/components/ui';
import { Radar, RefreshCw, AlertTriangle, CircleStop, Activity } from 'lucide-react';

const STATUS = {
  ok: { label: 'Stable', cls: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30', dot: 'bg-emerald-400' },
  watch: { label: 'Watch', cls: 'text-amber-300 bg-amber-500/10 border-amber-500/30', dot: 'bg-amber-400' },
  shifted: { label: 'Regime Shift', cls: 'text-rose-300 bg-rose-500/10 border-rose-500/30', dot: 'bg-rose-400 pulse-ring' },
} as const;

function statusOf(s: string | null | undefined) {
  return STATUS[(s as keyof typeof STATUS)] ?? STATUS.ok;
}

export default function MonitoringPage() {
  const [strategies, setStrategies] = useState<MonitoredStrategy[]>([]);
  const [alerts, setAlerts] = useState<DriftAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, a] = await Promise.all([getMonitored(), getAlerts()]);
      setStrategies(s); setAlerts(a);
    } catch { /* noop */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const check = async (id: number) => {
    setChecking(id);
    try { await checkMonitored(id); await load(); } finally { setChecking(null); }
  };
  const stop = async (id: number) => { await stopMonitored(id); await load(); };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-white flex items-center gap-2">
          <Radar className="text-sky-400" size={26} /> Live Monitoring
        </h1>
        <p className="text-slate-400 mt-1">Approved strategies, watched for regime drift away from their validated conditions.</p>
      </header>

      {loading ? (
        <div className="grid md:grid-cols-2 gap-4">{[0, 1].map(i => <Card key={i} className="h-40 animate-pulse" />)}</div>
      ) : strategies.length === 0 ? (
        <Card className="p-10 text-center">
          <Radar className="mx-auto text-slate-700 mb-3" size={42} />
          <p className="text-slate-400">No strategies under monitoring yet.</p>
          <p className="text-slate-600 text-sm mt-1">Approve one in the Research Copilot and click &ldquo;Promote to Live Monitoring&rdquo;.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {strategies.map(s => {
            const st = statusOf(s.regime_status);
            const psiPct = Math.min(100, ((s.latest_psi ?? 0) / 0.3) * 100);
            return (
              <Card key={s.id} hover className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-white font-semibold">{s.name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{(s.universe ?? []).join(' · ')}</p>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${st.cls}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} /> {st.label}
                  </span>
                </div>

                <div className="mt-4 flex items-center gap-4">
                  <div className="flex-1">
                    <div className="flex justify-between text-xs text-slate-400 mb-1">
                      <span>Regime drift (PSI)</span>
                      <span className="mono">{s.latest_psi != null ? s.latest_psi.toFixed(3) : '—'}</span>
                    </div>
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${st.dot.replace('pulse-ring', '')}`} style={{ width: `${psiPct}%` }} />
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-600 mt-0.5"><span>0</span><span>0.1</span><span>0.2</span><span>0.3+</span></div>
                  </div>
                  {s.honesty_score != null && (
                    <div className="text-center">
                      <p className="text-2xl font-bold mono text-slate-100">{Math.round(s.honesty_score)}</p>
                      <p className="text-[10px] text-slate-500 uppercase">Honesty</p>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between mt-4">
                  <span className="text-[11px] text-slate-500">
                    {s.last_checked ? `Checked ${new Date(s.last_checked).toLocaleString()}` : 'Not yet checked'}
                  </span>
                  <div className="flex gap-2">
                    <button onClick={() => check(s.id)} disabled={checking === s.id}
                      className="text-xs flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:border-sky-500/50 hover:text-sky-300 transition-colors disabled:opacity-50">
                      <RefreshCw size={13} className={checking === s.id ? 'animate-spin' : ''} /> Check now
                    </button>
                    {s.active && (
                      <button onClick={() => stop(s.id)}
                        className="text-xs flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 text-slate-400 hover:border-rose-500/50 hover:text-rose-300 transition-colors">
                        <CircleStop size={13} /> Stop
                      </button>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <div>
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
          <AlertTriangle size={15} className="text-amber-400" /> Regime Alerts
        </h2>
        <Card className="divide-y divide-slate-800/70">
          {alerts.length === 0 ? (
            <div className="p-6 text-center text-slate-500 text-sm flex items-center justify-center gap-2">
              <Activity size={15} /> No regime shifts detected. All monitored strategies are within their validated regime.
            </div>
          ) : alerts.map(a => (
            <div key={a.id} className="p-4 flex items-start gap-3">
              <span className={`mt-1 w-2 h-2 rounded-full shrink-0 ${a.severity === 'high' ? 'bg-rose-400' : a.severity === 'medium' ? 'bg-amber-400' : 'bg-slate-400'}`} />
              <div className="flex-1">
                <p className="text-sm text-slate-200">{a.message}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {a.strategy_name} · {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                </p>
              </div>
              <VerdictBadge verdict={a.severity === 'high' ? 'Likely Overfit' : a.severity === 'medium' ? 'Fragile' : 'Robust'} />
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
