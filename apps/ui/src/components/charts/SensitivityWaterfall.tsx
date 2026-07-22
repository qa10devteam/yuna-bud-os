// Top-5 cost drivers waterfall
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from 'recharts';

// ── Colour constants ───────────────────────────────────────────────────────────
const PRIMARY = '#10b981';
const WARNING = '#f59e0b';
const INFO    = '#3b82f6';
const VIOLET  = '#8b5cf6';
const DANGER  = '#ef4444';

interface Driver {
  name: string;
  sobol_s1: number;
}

interface SensitivityWaterfallProps {
  drivers: Driver[];
}

// Ordered palette using M1 accent consts
const COLORS = [PRIMARY, WARNING, INFO, VIOLET, DANGER];

export function SensitivityWaterfall({ drivers }: SensitivityWaterfallProps) {
  const top5 = [...drivers].sort((a, b) => b.sobol_s1 - a.sobol_s1).slice(0, 5);

  return (
    <div className="w-full rounded-xl bg-ink-900 border border-ink-800 p-3">
      <p className="section-label mb-2">Główne czynniki kosztów</p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={top5} layout="vertical">
          <XAxis
            type="number"
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            tick={{ fill: 'var(--color-slate-400)', fontSize: 11 }}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={120}
            tick={{ fontSize: 12, fill: 'var(--color-slate-300)' }}
          />
          <Tooltip
            formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
            contentStyle={{
              background: 'var(--color-ink-800)',
              border: '1px solid var(--color-ink-700)',
              borderRadius: 8,
              color: 'var(--color-slate-100)',
            }}
          />
          <Bar dataKey="sobol_s1">
            {top5.map((_, i) => (
              <Cell key={`item-${i}`} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
