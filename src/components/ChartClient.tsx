'use client';

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { name: 'Niskie ryzyko', value: 40, color: '#00FF94' },
  { name: 'Średnie ryzyko', value: 30, color: '#FF3300' },
  { name: 'Wysokie ryzyko', value: 20, color: '#6B6B68' },
  { name: 'Krytyczne', value: 10, color: '#1A1A1A' },
];

export function ChartClient() {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={80}
          paddingAngle={5}
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}
