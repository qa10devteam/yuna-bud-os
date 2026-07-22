// Violin-like p10/p50/p90 chart dla Engine L2 wyników
import {
  ComposedChart,
  Bar,
  ErrorBar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

// ── Colour constants ───────────────────────────────────────────────────────────
const PRIMARY = '#10b981';
const DANGER  = '#ef4444';
const WARNING = '#f59e0b';
const COMPACT_FMT = new Intl.NumberFormat('pl-PL', { notation: 'compact' });

interface RiskChartProps {
  p10: number;
  p50: number;
  p90: number;
  current_price?: number;
  currency?: string;
}

const PLN_CURRENCY_FMT = new Intl.NumberFormat('pl-PL', {
  style: 'currency',
  currency: 'PLN',
  maximumFractionDigits: 0,
});

export function RiskChart({ p10, p50, p90, current_price, currency = 'PLN' }: RiskChartProps) {
  const fmt = (v: number) => PLN_CURRENCY_FMT.format(v);

  const data = [{ name: 'Ryzyko', center: p50, error: [[p50 - p10], [p90 - p50]] }];

  return (
    <div className="w-full h-48 rounded-xl bg-ink-900 border border-ink-800 p-3">
      <div className="flex justify-between text-sm mb-2">
        <span className="text-nogo font-medium">P10: {fmt(p10)}</span>
        <span className="font-semibold text-slate-100">P50: {fmt(p50)}</span>
        <span className="text-warn font-medium">P90: {fmt(p90)}</span>
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <ComposedChart data={data} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <XAxis dataKey="name" tick={{ fill: 'var(--color-slate-400)', fontSize: 11 }} />
          <YAxis
            domain={[p10 * 0.95, p90 * 1.05]}
            tickFormatter={(v) =>
              COMPACT_FMT.format(v)
            }
            tick={{ fill: 'var(--color-slate-400)', fontSize: 11 }}
          />
          <Tooltip
            formatter={(v: number) => fmt(v)}
            contentStyle={{
              background: 'var(--color-ink-800)',
              border: '1px solid var(--color-ink-700)',
              borderRadius: 8,
              color: 'var(--color-slate-100)',
            }}
          />
          <Bar dataKey="center" fill={PRIMARY} barSize={40}>
            <ErrorBar dataKey="error" width={4} strokeWidth={2} stroke={WARNING} />
            <Cell fill={PRIMARY} />
          </Bar>
        </ComposedChart>
      </ResponsiveContainer>
      {current_price && (
        <div className="text-xs text-center text-slate-500 mt-1">
          Twoja cena: {fmt(current_price)} —{' '}
          {current_price < p50 ? (
            <span className="text-warn">⚠️ Poniżej mediany ryzyka</span>
          ) : (
            <span className="text-em">✅ Powyżej mediany</span>
          )}
        </div>
      )}
    </div>
  );
}
