'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  streamWorkflow, AgentEvent, BacktestData, Honesty, StrategyBlueprint, promoteToMonitor,
} from '@/lib/api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Card, ScoreGauge, VerdictBadge, Pct, Num, verdictTone } from '@/components/ui';
import {
  Brain, FlaskConical, ShieldCheck, PieChart, Activity, CheckCircle2, XCircle,
  Sparkles, Loader2, ArrowUpRight,
} from 'lucide-react';

interface TraceItem {
  kind: 'thought' | 'tool';
  text?: string;
  tool?: string;
  args?: Record<string, unknown>;
  summary?: Record<string, unknown>;
  done?: boolean;
}

const TOOL_META: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  run_backtest: { label: 'Honest Backtest', icon: FlaskConical, color: 'text-violet-300' },
  check_regime_drift: { label: 'Regime Drift Check', icon: Activity, color: 'text-amber-300' },
  optimize_portfolio: { label: 'Portfolio Optimization', icon: PieChart, color: 'text-emerald-300' },
  finalize: { label: 'Final Verdict', icon: ShieldCheck, color: 'text-sky-300' },
};

const EXAMPLES = [
  'Momentum strategy on AAPL, MSFT, NVDA',
  'Mean reversion on oversold TSLA and AMD',
  'Trend following breakout on SPY and QQQ',
];

export default function ResearchPage() {
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const [live, setLive] = useState<boolean | null>(null);
  const [trace, setTrace] = useState<TraceItem[]>([]);
  const [backtest, setBacktest] = useState<BacktestData | null>(null);
  const [portfolio, setPortfolio] = useState<Record<string, number> | null>(null);
  const [drift, setDrift] = useState<Record<string, unknown> | null>(null);
  const [verdict, setVerdict] = useState<{ rec: string; honesty: Honesty; text: string } | null>(null);
  const [runId, setRunId] = useState<number | null>(null);
  const [promoted, setPromoted] = useState(false);
  const traceEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { traceEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [trace]);

  const handleEvent = useCallback((ev: AgentEvent) => {
    switch (ev.type) {
      case 'agent_start':
        setLive((ev as { live: boolean }).live);
        break;
      case 'thought':
        setTrace(t => [...t, { kind: 'thought', text: (ev as { text: string }).text }]);
        break;
      case 'tool_call':
        setTrace(t => [...t, { kind: 'tool', tool: ev.tool, args: ev.args, done: false }]);
        break;
      case 'tool_result': {
        setTrace(t => {
          const copy = [...t];
          for (let i = copy.length - 1; i >= 0; i--) {
            if (copy[i].kind === 'tool' && copy[i].tool === ev.tool && !copy[i].done) {
              copy[i] = { ...copy[i], done: true, summary: ev.summary }; break;
            }
          }
          return copy;
        });
        if (ev.tool === 'run_backtest' && ev.data && !('error' in ev.data)) {
          setBacktest(prev => {
            const next = ev.data as BacktestData;
            // keep the higher-honesty backtest as the headline
            if (!prev) return next;
            return (next.honesty?.score ?? 0) >= (prev.honesty?.score ?? 0) ? next : prev;
          });
        }
        if (ev.tool === 'optimize_portfolio') setPortfolio((ev.data as { weights?: Record<string, number> }).weights ?? null);
        if (ev.tool === 'check_regime_drift') setDrift(ev.data as Record<string, unknown>);
        break;
      }
      case 'verdict':
        setVerdict({ rec: ev.recommendation, honesty: ev.honesty, text: ev.text });
        break;
      case 'saved':
        setRunId(ev.run_id);
        break;
    }
  }, []);

  const run = async (text: string) => {
    if (!text.trim() || running) return;
    setRunning(true);
    setTrace([]); setBacktest(null); setPortfolio(null); setDrift(null);
    setVerdict(null); setRunId(null); setPromoted(false); setLive(null);
    try {
      await streamWorkflow(text, handleEvent);
    } catch (e) {
      setTrace(t => [...t, { kind: 'thought', text: `Error: ${e instanceof Error ? e.message : 'stream failed'}` }]);
    } finally {
      setRunning(false);
    }
  };

  const promote = async () => {
    if (runId == null) return;
    try { await promoteToMonitor(runId); setPromoted(true); } catch { /* noop */ }
  };

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <Sparkles className="text-sky-400" size={26} /> Research Copilot
          </h1>
          <p className="text-slate-400 mt-1">
            A skeptical quant agent that tries to <span className="text-slate-200">disprove</span> your edge before approving it.
          </p>
        </div>
        {live != null && (
          <span className={`text-xs px-3 py-1 rounded-full border ${live ? 'border-sky-500/30 text-sky-300 bg-sky-500/10' : 'border-slate-600 text-slate-400 bg-slate-800/40'}`}>
            {live ? 'Live LLM' : 'Offline mock (real engines)'}
          </span>
        )}
      </header>

      {/* Input */}
      <Card className="p-4">
        <div className="flex gap-3">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run(input)}
            placeholder="Describe a trading idea in plain English…"
            className="flex-1 bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/60 transition-colors"
          />
          <button
            onClick={() => run(input)}
            disabled={running}
            className="bg-sky-600 hover:bg-sky-500 text-white px-6 py-3 rounded-xl font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {running ? <Loader2 className="animate-spin" size={18} /> : <Brain size={18} />}
            {running ? 'Researching…' : 'Research'}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {EXAMPLES.map(ex => (
            <button key={ex} onClick={() => { setInput(ex); run(ex); }} disabled={running}
              className="text-xs text-slate-400 border border-slate-800 hover:border-slate-600 hover:text-slate-200 rounded-full px-3 py-1 transition-colors disabled:opacity-40">
              {ex}
            </button>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Agent trace */}
        <div className="lg:col-span-2 space-y-3">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Agent Reasoning</h2>
          <Card className="p-4 min-h-[300px] max-h-[680px] overflow-y-auto">
            {trace.length === 0 && !running && (
              <p className="text-slate-500 text-sm py-8 text-center">The agent&apos;s thoughts and tool calls will stream here.</p>
            )}
            <div className="space-y-3">
              {trace.map((item, i) => <TraceCard key={i} item={item} />)}
              {running && (
                <div className="flex items-center gap-2 text-slate-400 text-sm pl-1">
                  <Loader2 className="animate-spin" size={14} /> thinking…
                </div>
              )}
              <div ref={traceEndRef} />
            </div>
          </Card>
        </div>

        {/* Honesty report */}
        <div className="lg:col-span-3 space-y-6">
          {!backtest && (
            <Card className="p-10 flex flex-col items-center justify-center text-center min-h-[300px]">
              <ShieldCheck className="text-slate-700 mb-3" size={48} />
              <p className="text-slate-400 font-medium">The Honesty Report appears once the backtest completes.</p>
              <p className="text-slate-600 text-sm mt-1">Out-of-sample decay · deflated Sharpe · overfitting probability · cost &amp; benchmark reality.</p>
            </Card>
          )}

          {backtest && (
            <>
              <HonestyReport backtest={backtest} verdict={verdict} />
              {backtest.strategy_blueprint && <StrategyBlueprintCard bp={backtest.strategy_blueprint} exposure={backtest.exposure} />}
              {backtest.equity_curve && backtest.equity_curve.length > 0 && (
                <EquityChart data={backtest.equity_curve} />
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {backtest.sensitivity && backtest.sensitivity.length > 0 && (
                  <SensitivityHeatmap cells={backtest.sensitivity} />
                )}
                <SidePanels portfolio={portfolio} drift={drift} backtest={backtest} />
              </div>

              {verdict && (
                <Card className="p-5 flex items-center justify-between flex-wrap gap-3">
                  <div className="flex items-center gap-3">
                    {verdict.rec === 'approve'
                      ? <CheckCircle2 className="text-emerald-400" size={28} />
                      : <XCircle className="text-rose-400" size={28} />}
                    <div>
                      <p className="text-white font-semibold capitalize">{verdict.rec === 'approve' ? 'Approved for deployment' : 'Rejected'}</p>
                      <p className="text-slate-400 text-sm max-w-xl">{verdict.text}</p>
                    </div>
                  </div>
                  {verdict.rec === 'approve' && runId != null && (
                    <button
                      onClick={promote}
                      disabled={promoted}
                      className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white px-4 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-colors"
                    >
                      {promoted ? <><CheckCircle2 size={16} /> Monitoring</> : <><ArrowUpRight size={16} /> Promote to Live Monitoring</>}
                    </button>
                  )}
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function TraceCard({ item }: { item: TraceItem }) {
  if (item.kind === 'thought') {
    return (
      <div className="animate-in flex gap-2.5">
        <Brain size={16} className="text-sky-400 mt-0.5 shrink-0" />
        <p className="text-sm text-slate-300 leading-relaxed">{item.text}</p>
      </div>
    );
  }
  const meta = TOOL_META[item.tool ?? ''] ?? { label: item.tool ?? 'Tool', icon: Activity, color: 'text-slate-300' };
  const Icon = meta.icon;
  const score = item.summary?.honesty_score as number | undefined;
  const v = item.summary?.verdict as string | undefined;
  return (
    <div className="animate-in border border-slate-800 bg-slate-900/40 rounded-xl p-3">
      <div className="flex items-center justify-between">
        <span className={`text-xs font-semibold flex items-center gap-1.5 ${meta.color}`}>
          <Icon size={14} /> {meta.label}
        </span>
        {item.done
          ? <CheckCircle2 size={14} className="text-emerald-400" />
          : <Loader2 size={14} className="animate-spin text-slate-500" />}
      </div>
      {item.args && Object.keys(item.args).length > 0 && (
        <p className="text-[11px] text-slate-500 mt-1 mono truncate">
          {Object.entries(item.args).map(([k, val]) => `${k}=${Array.isArray(val) ? val.join(',') : val}`).join('  ')}
        </p>
      )}
      {score != null && (
        <div className="mt-2 flex items-center gap-2">
          <VerdictBadge verdict={v} />
          <span className="text-xs text-slate-400">honesty {score}/100</span>
        </div>
      )}
    </div>
  );
}

function HonestyReport({ backtest, verdict }: { backtest: BacktestData; verdict: { honesty: Honesty } | null }) {
  const h = backtest.honesty;
  const rob = backtest.robustness ?? {};
  const bench = backtest.benchmark ?? {};
  const reasons = h?.reasons ?? verdict?.honesty?.reasons ?? [];
  return (
    <Card className="p-6">
      <div className="flex flex-col md:flex-row gap-6 items-center md:items-start">
        <div className="flex flex-col items-center shrink-0">
          <ScoreGauge score={h?.score ?? 0} verdict={h?.verdict} />
          <div className="mt-2"><VerdictBadge verdict={h?.verdict} /></div>
          <p className="text-[11px] text-slate-500 mt-1">Strategy Honesty Score</p>
        </div>
        <div className="flex-1 w-full">
          <p className="text-xs uppercase tracking-wider text-slate-400 mb-2">Why this score</p>
          <ul className="space-y-1.5">
            {reasons.map((r, i) => (
              <li key={i} className="text-sm text-slate-300 flex gap-2">
                <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${
                  verdictTone(h?.verdict) === 'good' ? 'bg-emerald-400' : verdictTone(h?.verdict) === 'warn' ? 'bg-amber-400' : 'bg-rose-400'}`} />
                {r}
              </li>
            ))}
            {reasons.length === 0 && <li className="text-sm text-slate-500">No notable robustness flags.</li>}
          </ul>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
        <MiniStat label="In-Sample Sharpe" value={<Num v={backtest.metrics_is?.sharpe_ratio} />} />
        <MiniStat label="Out-of-Sample Sharpe" value={<Num v={backtest.metrics_oos?.sharpe_ratio} />}
          tone={(backtest.metrics_oos?.sharpe_ratio ?? 0) > 0 ? 'good' : 'bad'} />
        <MiniStat label="Deflated Sharpe" value={<Num v={rob.deflated_sharpe?.dsr} />} />
        <MiniStat label="Overfit Prob (PBO)" value={<Pct v={rob.pbo?.pbo} digits={0} />}
          tone={(rob.pbo?.pbo ?? 0) > 0.5 ? 'bad' : 'good'} />
        <MiniStat label="Net CAGR" value={<Pct v={backtest.metrics?.cagr} sign />} />
        <MiniStat label="Gross CAGR" value={<Pct v={backtest.gross_cagr} sign />} />
        <MiniStat label="Permutation p" value={<Num v={rob.permutation?.p_value} />}
          tone={(rob.permutation?.p_value ?? 1) < 0.05 ? 'good' : 'bad'} />
        <MiniStat label="Beats Benchmark" value={bench.beats_benchmark ? 'Yes' : 'No'}
          tone={bench.beats_benchmark ? 'good' : 'bad'} />
      </div>
    </Card>
  );
}

function MiniStat({ label, value, tone = 'default' }: { label: string; value: React.ReactNode; tone?: 'default' | 'good' | 'bad' }) {
  const c = { default: 'text-slate-100', good: 'text-emerald-400', bad: 'text-rose-400' }[tone];
  return (
    <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-2.5">
      <p className="text-[10px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`text-lg font-semibold mono mt-0.5 ${c}`}>{value}</p>
    </div>
  );
}

function RuleList({ title, logic, rules, tone }: { title: string; logic: string; rules: string[]; tone: 'good' | 'bad' }) {
  const dot = tone === 'good' ? 'bg-emerald-400' : 'bg-rose-400';
  return (
    <div className="flex-1">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wide">{title}</span>
        <span className="text-[10px] text-slate-500 border border-slate-700 rounded px-1.5 py-0.5">match {logic.toUpperCase()}</span>
      </div>
      <div className="space-y-1.5">
        {rules.map((r, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dot}`} />
            <span className="mono text-slate-300">{r}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StrategyBlueprintCard({ bp, exposure }: { bp: StrategyBlueprint; exposure?: number }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <FlaskConical size={15} className="text-violet-300" /> Strategy Blueprint
          <span className="text-slate-500 font-normal">· {bp.name}</span>
        </h3>
        {exposure != null && (
          <span className="text-[11px] text-slate-500">avg exposure <span className="mono text-slate-300">{(exposure * 100).toFixed(0)}%</span></span>
        )}
      </div>
      <div className="flex flex-col md:flex-row gap-6">
        <RuleList title="Enter when" logic={bp.entry_logic} rules={bp.entry} tone="good" />
        <div className="hidden md:block w-px bg-slate-800" />
        <RuleList title="Exit when" logic={bp.exit_logic} rules={bp.exit} tone="bad" />
      </div>
    </Card>
  );
}

function EquityChart({ data }: { data: { date: string; value: number; benchmark?: number }[] }) {
  const hasBench = data.some(d => d.benchmark != null);
  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">Out-of-sample equity · strategy vs benchmark</h3>
      <div className="h-60">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 10 }} interval="preserveStartEnd" minTickGap={40} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} tickFormatter={v => v.toFixed(2)} width={42} />
            <Tooltip contentStyle={{ backgroundColor: '#0c1220', borderColor: '#1e293b', borderRadius: 12, color: '#e2e8f0' }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="value" name="Strategy" stroke="#5b8cff" strokeWidth={2} dot={false} />
            {hasBench && <Line type="monotone" dataKey="benchmark" name="Benchmark" stroke="#64748b" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function SensitivityHeatmap({ cells }: { cells: { lookback: number; entry: number; oos_sharpe: number }[] }) {
  const lookbacks = Array.from(new Set(cells.map(c => c.lookback))).sort((a, b) => a - b);
  const entries = Array.from(new Set(cells.map(c => c.entry))).sort((a, b) => a - b);
  const vals = cells.map(c => c.oos_sharpe);
  const min = Math.min(...vals), max = Math.max(...vals);
  const color = (v: number) => {
    const t = max === min ? 0.5 : (v - min) / (max - min);
    // rose → slate → emerald
    const r = Math.round(248 - t * (248 - 52));
    const g = Math.round(113 + t * (211 - 113));
    const b = Math.round(113 + t * (153 - 113));
    return `rgba(${r},${g},${b},0.85)`;
  };
  const get = (lb: number, en: number) => cells.find(c => c.lookback === lb && c.entry === en)?.oos_sharpe;
  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-1">Parameter sensitivity</h3>
      <p className="text-[11px] text-slate-500 mb-3">Sharpe across the param grid. Smooth = robust, patchy = fragile.</p>
      <div className="overflow-x-auto">
        <table className="border-separate" style={{ borderSpacing: 3 }}>
          <thead>
            <tr>
              <th className="text-[10px] text-slate-500 font-normal pr-2">lb \ entry</th>
              {entries.map(en => <th key={en} className="text-[10px] text-slate-500 font-normal px-1">{en}</th>)}
            </tr>
          </thead>
          <tbody>
            {lookbacks.map(lb => (
              <tr key={lb}>
                <td className="text-[10px] text-slate-500 pr-2 mono">{lb}</td>
                {entries.map(en => {
                  const v = get(lb, en);
                  return (
                    <td key={en}>
                      <div className="w-10 h-8 rounded flex items-center justify-center text-[10px] mono text-slate-900 font-semibold"
                        style={{ background: v == null ? '#1e293b' : color(v) }}
                        title={`lb=${lb} entry=${en} → Sharpe ${v?.toFixed(2)}`}>
                        {v == null ? '' : v.toFixed(1)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function SidePanels({ portfolio, drift, backtest }: {
  portfolio: Record<string, number> | null;
  drift: Record<string, unknown> | null;
  backtest: BacktestData;
}) {
  return (
    <div className="space-y-6">
      {portfolio && Object.keys(portfolio).length > 0 && (
        <Card className="p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2"><PieChart size={15} className="text-emerald-300" /> HRP Allocation</h3>
          <div className="space-y-2">
            {Object.entries(portfolio).sort((a, b) => b[1] - a[1]).map(([t, w]) => (
              <div key={t}>
                <div className="flex justify-between text-xs mb-0.5">
                  <span className="text-slate-300 font-medium">{t}</span>
                  <span className="text-slate-400 mono">{(w * 100).toFixed(1)}%</span>
                </div>
                <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500/70 rounded-full" style={{ width: `${w * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
      <Card className="p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2"><Activity size={15} className="text-amber-300" /> Regime Drift</h3>
        {drift && drift.available ? (
          <div className="grid grid-cols-2 gap-3">
            <MiniStat label="PSI" value={<Num v={drift.psi as number} />} tone={(drift.psi as number) >= 0.2 ? 'bad' : 'default'} />
            <MiniStat label="KS p-value" value={<Num v={drift.ks_p_value as number} />} />
            <MiniStat label="Regime shift" value={drift.regime_shift ? 'Detected' : 'Stable'} tone={drift.regime_shift ? 'bad' : 'good'} />
            <MiniStat label="Severity" value={String(drift.severity ?? '—')} />
          </div>
        ) : <p className="text-sm text-slate-500">No regime divergence vs backtest window.</p>}
      </Card>
      <Card className="p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Risk</h3>
        <div className="grid grid-cols-2 gap-3">
          <MiniStat label="Max Drawdown" value={<Pct v={backtest.metrics?.max_drawdown} />} tone="bad" />
          <MiniStat label="CVaR 95%" value={<Pct v={backtest.metrics?.cvar_95} />} />
          <MiniStat label="Volatility" value={<Pct v={backtest.metrics?.annual_volatility} />} />
          <MiniStat label="Sortino" value={<Num v={backtest.metrics?.sortino_ratio} />} />
        </div>
      </Card>
    </div>
  );
}
