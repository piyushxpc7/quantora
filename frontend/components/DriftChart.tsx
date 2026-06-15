'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface DriftDataPoint {
  name: string;
  psi: number;
  threshold: number;
}

const FALLBACK_DATA: DriftDataPoint[] = [
  { name: 'D1', psi: 0.05, threshold: 0.2 },
  { name: 'D2', psi: 0.08, threshold: 0.2 },
  { name: 'D3', psi: 0.12, threshold: 0.2 },
  { name: 'D4', psi: 0.09, threshold: 0.2 },
  { name: 'D5', psi: 0.15, threshold: 0.2 },
];

interface Props {
  data?: DriftDataPoint[];
}

const DriftChart = ({ data }: Props) => {
  const chartData = data && data.length > 0 ? data : FALLBACK_DATA;

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="name" stroke="#94a3b8" tick={{ fontSize: 11 }} />
          <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} domain={[0, 'auto']} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
            formatter={(v: number) => [v.toFixed(4), '']}
          />
          <ReferenceLine y={0.2} stroke="#ef4444" strokeDasharray="5 5" label={{ value: 'Threshold 0.2', fill: '#ef4444', fontSize: 11 }} />
          <Line type="monotone" dataKey="psi" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 6 }} name="PSI" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DriftChart;
