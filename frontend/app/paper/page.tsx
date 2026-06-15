'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  getPaperAccount, getPaperTrades, getMonitored, rebalancePaper,
  PaperAccount, PaperTrade, MonitoredStrategy,
} from '@/lib/api';
import { Card, StatTile, Pct } from '@/components/ui';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Wallet, RefreshCw, Ban, ArrowDownRight, ArrowUpRight } from 'lucide-react';

export default function PaperPage() {
  const [acct, setAcct] = useState<PaperAccount | null>(null);
  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [strategies, setStrategies] = useState<MonitoredStrategy[]>([]);
  const [rebalancing, setRebalancing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [a, t, s] = await Promise.all([getPaperAccount(), getPaperTrades(), getMonitored()]);
      setAcct(a); setTrades(t); setStrategies(s);
    } catch { /* noop */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  const rebalance = async (id: number) => {
    setRebalancing(true);
    try { await rebalancePaper(id); await load(); } finally { setRebalancing(false); }
  };

  const pnlTone = (acct?.pnl ?? 0) >= 0 ? 'good' : 'bad';

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <Wallet className="text-emerald-400" size={26} /> Paper Trading
          </h1>
          <p className="text-slate-400 mt-1">Risk-gated paper execution of approved strategies. No real money.</p>
        </div>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Equity" value={acct ? `$${acct.equity.toLocaleString()}` : '—'} />
        <StatTile label="Cash" value={acct ? `$${acct.cash.toLocaleString()}` : '—'} />
        <StatTile label="P&L" value={acct ? `$${acct.pnl.toLocaleString()}` : '—'} tone={pnlTone} />
        <StatTile label="Return" value={<Pct v={acct?.pnl_pct} sign />} tone={pnlTone} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Account Equity</h3>
          <div className="h-56">
            {acct && acct.equity_curve.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={acct.equity_curve}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 10 }} interval="preserveStartEnd" minTickGap={50} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} width={48} />
                  <Tooltip contentStyle={{ backgroundColor: '#0c1220', borderColor: '#1e293b', borderRadius: 12 }} formatter={(v: number) => [`$${v.toLocaleString()}`, 'Equity']} />
                  <Line type="monotone" dataKey="value" stroke="#34d399" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="h-full flex items-center justify-center text-slate-500 text-sm">No history yet.</div>}
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Rebalance into strategy</h3>
          {strategies.length === 0 ? (
            <p className="text-slate-500 text-sm">No monitored strategies. Approve and promote one first.</p>
          ) : (
            <div className="space-y-2">
              {strategies.map(s => (
                <button key={s.id} onClick={() => rebalance(s.id)} disabled={rebalancing}
                  className="w-full text-left border border-slate-800 hover:border-emerald-500/40 rounded-xl p-3 transition-colors disabled:opacity-50 group">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-200 group-hover:text-emerald-300">{s.name}</span>
                    <RefreshCw size={14} className={`text-slate-500 ${rebalancing ? 'animate-spin' : ''}`} />
                  </div>
                  <span className="text-[11px] text-slate-500">{(s.universe ?? []).join(', ')}</span>
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Open Positions</h3>
          {acct && acct.positions.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[11px] text-slate-500 uppercase border-b border-slate-800">
                  <th className="text-left font-medium pb-2">Ticker</th>
                  <th className="text-right font-medium pb-2">Shares</th>
                  <th className="text-right font-medium pb-2">Last</th>
                  <th className="text-right font-medium pb-2">Value</th>
                  <th className="text-right font-medium pb-2">P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {acct.positions.map(p => (
                  <tr key={p.ticker}>
                    <td className="py-2 text-slate-200 font-medium">{p.ticker}</td>
                    <td className="py-2 text-right mono text-slate-400">{p.shares.toFixed(1)}</td>
                    <td className="py-2 text-right mono text-slate-400">${p.last_price.toFixed(2)}</td>
                    <td className="py-2 text-right mono text-slate-300">${p.market_value.toLocaleString()}</td>
                    <td className={`py-2 text-right mono ${p.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      <Pct v={p.unrealized_pct} sign />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="text-slate-500 text-sm">No open positions.</p>}
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Trade Blotter</h3>
          <div className="space-y-1.5 max-h-72 overflow-y-auto">
            {trades.length === 0 ? <p className="text-slate-500 text-sm">No trades yet.</p> : trades.map(t => (
              <div key={t.id} className="flex items-center gap-2 text-sm py-1.5 border-b border-slate-800/40 last:border-0">
                {t.status === 'blocked'
                  ? <Ban size={15} className="text-rose-400 shrink-0" />
                  : t.side === 'buy'
                    ? <ArrowUpRight size={15} className="text-emerald-400 shrink-0" />
                    : <ArrowDownRight size={15} className="text-amber-400 shrink-0" />}
                <span className="text-slate-200 font-medium w-16">{t.ticker}</span>
                {t.status === 'blocked'
                  ? <span className="text-rose-300 text-xs flex-1">{t.reason}</span>
                  : <span className="text-slate-400 text-xs flex-1 mono">{t.side} {t.shares.toFixed(1)} @ ${t.price.toFixed(2)}</span>}
                <span className="text-[10px] text-slate-600">{t.created_at ? new Date(t.created_at).toLocaleTimeString() : ''}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
