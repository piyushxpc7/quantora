const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// --- Dashboard ---
export interface DashboardStats {
  total_strategies: number;
  approved_strategies: number;
  latest_cagr: number;
  avg_sharpe: number;
}
export const getDashboardStats = (): Promise<DashboardStats> =>
  apiFetch('/api/v1/agents/stats');

// --- Drift ---
export interface DriftSummary {
  latest_psi: number | null;
  latest_ks_p_value: number | null;
  latest_severity: string | null;
  alert_count: number;
  total_checks: number;
}
export const getDriftSummary = (): Promise<DriftSummary> =>
  apiFetch('/api/v1/drift/summary');

export interface DriftHistoryItem {
  id: number;
  feature_name: string;
  psi_value: number;
  ks_statistic: number;
  ks_p_value: number;
  overall_drift: boolean;
  severity: string;
  timestamp: string;
}
export const getDriftHistory = (): Promise<DriftHistoryItem[]> =>
  apiFetch('/api/v1/drift/history');

export const analyzeDrift = (
  reference_data: number[],
  current_data: number[],
  feature_name = 'default'
) =>
  apiFetch('/api/v1/drift/analyze', {
    method: 'POST',
    body: JSON.stringify({ reference_data, current_data, feature_name }),
  });

// --- Agents ---
export interface WorkflowResult {
  status: string;
  workflow_log: WorkflowStep[];
  final_output: WorkflowStep;
}
export interface WorkflowStep {
  agent: string;
  status: string;
  output?: string;
  metrics?: Record<string, number>;
  risk_metrics?: Record<string, number>;
  risk_approved?: boolean;
  final_allocation?: Record<string, number>;
  equity_curve?: { date: string; value: number }[];
  strategy_params?: Record<string, unknown>;
}
export const runWorkflow = (request: string): Promise<WorkflowResult> =>
  apiFetch('/api/v1/agents/workflow', {
    method: 'POST',
    body: JSON.stringify({ request }),
  });

// --- Agentic research stream (SSE over fetch) ---
export interface Honesty {
  score: number;
  verdict: string;
  reasons: string[];
  components?: Record<string, number | boolean>;
}
export interface BacktestData {
  universe: string[];
  signal_type: string;
  metrics?: Record<string, number>;
  metrics_is?: Record<string, number>;
  metrics_oos?: Record<string, number>;
  gross_cagr?: number;
  benchmark?: Record<string, number | boolean>;
  equity_curve?: { date: string; value: number; benchmark?: number }[];
  sensitivity?: { lookback: number; entry: number; oos_sharpe: number }[];
  robustness?: {
    deflated_sharpe?: { dsr: number; expected_max_sharpe_ann: number };
    pbo?: { pbo: number; n_configs: number };
    permutation?: { p_value: number; actual_sharpe: number; skill_detected: boolean };
  };
  honesty?: Honesty;
  exposure?: number;
  strategy_blueprint?: StrategyBlueprint;
  strategy_params?: Record<string, unknown>;
}
export interface StrategyBlueprint {
  name: string;
  entry_logic: string;
  entry: string[];
  exit_logic: string;
  exit: string[];
}
export type AgentEvent =
  | { type: 'agent_start'; live: boolean }
  | { type: 'thought'; text: string }
  | { type: 'tool_call'; tool: string; args: Record<string, unknown> }
  | { type: 'tool_result'; tool: string; summary: Record<string, unknown>; data: BacktestData & Record<string, unknown> }
  | { type: 'verdict'; recommendation: 'approve' | 'reject'; honesty: Honesty; risk_ok: boolean; text: string }
  | { type: 'complete'; result: Record<string, unknown> }
  | { type: 'saved'; run_id: number }
  | { type: 'save_error'; message: string }
  | { type: 'error'; message: string };

export async function streamWorkflow(
  request: string,
  onEvent: (ev: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/api/v1/agents/workflow/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`Stream failed: ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const frames = buf.split('\n\n');
    buf = frames.pop() ?? '';
    for (const frame of frames) {
      const line = frame.split('\n').find(l => l.startsWith('data:'));
      if (!line) continue;
      try { onEvent(JSON.parse(line.slice(5).trim()) as AgentEvent); } catch { /* ignore */ }
    }
  }
}

// --- Monitoring ---
export interface MonitoredStrategy {
  id: number;
  run_id: number;
  name: string;
  universe: string[];
  signal_type: string;
  honesty_score: number | null;
  latest_psi: number | null;
  regime_status: string;
  active: boolean;
  created_at: string;
  last_checked: string | null;
}
export interface DriftAlert {
  id: number;
  strategy_id: number;
  strategy_name: string;
  psi_value: number;
  severity: string;
  message: string;
  created_at: string;
}
export const getMonitored = (): Promise<MonitoredStrategy[]> => apiFetch('/api/v1/monitoring/monitored');
export const getAlerts = (): Promise<DriftAlert[]> => apiFetch('/api/v1/monitoring/alerts');
export const promoteToMonitor = (run_id: number): Promise<MonitoredStrategy> =>
  apiFetch('/api/v1/monitoring/monitor', { method: 'POST', body: JSON.stringify({ run_id }) });
export const checkMonitored = (id: number) =>
  apiFetch(`/api/v1/monitoring/monitored/${id}/check`, { method: 'POST' });
export const stopMonitored = (id: number) =>
  apiFetch(`/api/v1/monitoring/monitored/${id}/stop`, { method: 'POST' });

// --- Paper trading ---
export interface PaperAccount {
  cash: number;
  equity: number;
  starting_cash: number;
  pnl: number;
  pnl_pct: number;
  positions: PaperPosition[];
  equity_curve: { date: string; value: number }[];
}
export interface PaperPosition {
  ticker: string;
  shares: number;
  avg_price: number;
  last_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pct: number;
  weight: number;
}
export interface PaperTrade {
  id: number;
  ticker: string;
  side: string;
  shares: number;
  price: number;
  status: string;
  reason: string;
  created_at: string;
}
export const getPaperAccount = (): Promise<PaperAccount> => apiFetch('/api/v1/paper/account');
export const getPaperTrades = (): Promise<PaperTrade[]> => apiFetch('/api/v1/paper/trades');
export const rebalancePaper = (strategy_id: number) =>
  apiFetch('/api/v1/paper/rebalance', { method: 'POST', body: JSON.stringify({ strategy_id }) });

export interface WorkflowRun {
  id: number;
  user_request: string;
  strategy_name: string;
  universe: string[];
  cagr: number;
  sharpe_ratio: number;
  oos_sharpe: number | null;
  max_drawdown: number;
  risk_approved: boolean;
  honesty_score: number | null;
  verdict: string | null;
  recommendation: string | null;
  pbo: number | null;
  is_monitored: boolean;
  final_allocation: Record<string, number>;
  created_at: string;
}
export const getWorkflowRuns = (): Promise<WorkflowRun[]> =>
  apiFetch('/api/v1/agents/runs');

// --- Market data ---
export const getLatestPrice = (ticker: string): Promise<{ ticker: string; price: number }> =>
  apiFetch(`/api/v1/market-data/price/${ticker}`);
