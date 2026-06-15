'use client';

import { ReactNode } from 'react';

export function Card({ children, className = '', hover = false }: { children?: ReactNode; className?: string; hover?: boolean }) {
  return <div className={`card ${hover ? 'card-hover' : ''} ${className}`}>{children}</div>;
}

export function StatTile({
  label, value, sub, tone = 'default',
}: { label: string; value: ReactNode; sub?: ReactNode; tone?: 'default' | 'good' | 'warn' | 'bad' }) {
  const toneColor = {
    default: 'text-slate-100',
    good: 'text-emerald-400',
    warn: 'text-amber-400',
    bad: 'text-rose-400',
  }[tone];
  return (
    <Card hover className="p-5">
      <p className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">{label}</p>
      <p className={`text-3xl font-semibold mt-2 mono ${toneColor}`}>{value}</p>
      {sub != null && <p className="text-xs text-slate-500 mt-1.5">{sub}</p>}
    </Card>
  );
}

export type Verdict = 'Robust' | 'Fragile' | 'Likely Overfit' | string;

export function verdictTone(v?: Verdict): 'good' | 'warn' | 'bad' {
  if (v === 'Robust') return 'good';
  if (v === 'Fragile') return 'warn';
  return 'bad';
}

export function VerdictBadge({ verdict }: { verdict?: Verdict }) {
  const tone = verdictTone(verdict);
  const cls = {
    good: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    warn: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    bad: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
  }[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${cls}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {verdict ?? 'Pending'}
    </span>
  );
}

/** Circular honesty-score gauge (0–100). */
export function ScoreGauge({ score, verdict, size = 168 }: { score: number; verdict?: Verdict; size?: number }) {
  const tone = verdictTone(verdict);
  const color = { good: '#34d399', warn: '#fbbf24', bad: '#f87171' }[tone];
  const r = size / 2 - 12;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score)) / 100;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#1e293b" strokeWidth={10} fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={10} fill="none"
          strokeDasharray={c} strokeDashoffset={c * (1 - pct)} strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.9s cubic-bezier(0.22,1,0.36,1)' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-bold mono" style={{ color }}>{Math.round(score)}</span>
        <span className="text-[10px] uppercase tracking-widest text-slate-500">/ 100</span>
      </div>
    </div>
  );
}

export function Pct({ v, digits = 1, sign = false }: { v?: number | null; digits?: number; sign?: boolean }) {
  if (v == null) return <span className="text-slate-500">—</span>;
  const pct = v * 100;
  const tone = pct >= 0 ? 'text-emerald-400' : 'text-rose-400';
  const s = `${sign && pct >= 0 ? '+' : ''}${pct.toFixed(digits)}%`;
  return <span className={sign ? tone : ''}>{s}</span>;
}

export function Num({ v, digits = 2 }: { v?: number | null; digits?: number }) {
  if (v == null) return <span className="text-slate-500">—</span>;
  return <span className="mono">{v.toFixed(digits)}</span>;
}
