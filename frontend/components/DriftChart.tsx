'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
    { name: 'Day 1', psi: 0.05, threshold: 0.2 },
    { name: 'Day 2', psi: 0.08, threshold: 0.2 },
    { name: 'Day 3', psi: 0.12, threshold: 0.2 },
    { name: 'Day 4', psi: 0.15, threshold: 0.2 },
    { name: 'Day 5', psi: 0.22, threshold: 0.2 },
    { name: 'Day 6', psi: 0.18, threshold: 0.2 },
    { name: 'Day 7', psi: 0.25, threshold: 0.2 },
];

const DriftChart = () => {
    return (
        <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="name" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                    />
                    <Line type="monotone" dataKey="psi" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 8 }} />
                    <Line type="monotone" dataKey="threshold" stroke="#ef4444" strokeDasharray="5 5" />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
};

export default DriftChart;
