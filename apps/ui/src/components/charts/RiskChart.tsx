// Violin-like p10/p50/p90 chart dla Engine L2 wyników
import { ComposedChart, Bar, ErrorBar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { tokens } from '@/lib/tokens'

interface RiskChartProps {
  p10: number
  p50: number
  p90: number
  current_price?: number
  currency?: string
}

export function RiskChart({ p10, p50, p90, current_price, currency = 'PLN' }: RiskChartProps) {
  const fmt = (v: number) => new Intl.NumberFormat('pl-PL', { style: 'currency', currency, maximumFractionDigits: 0 }).format(v)
  const data = [{ name: 'Ryzyko', center: p50, error: [[p50 - p10], [p90 - p50]] }]

  return (
    <div className="w-full h-48">
      <div className="flex justify-between text-sm mb-2">
        <span className="text-red-600">P10: {fmt(p10)}</span>
        <span className="font-semibold">P50: {fmt(p50)}</span>
        <span className="text-orange-600">P90: {fmt(p90)}</span>
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <ComposedChart data={data} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <XAxis dataKey="name" />
          <YAxis domain={[p10 * 0.95, p90 * 1.05]} tickFormatter={v => new Intl.NumberFormat('pl-PL', { notation: 'compact' }).format(v)} />
          <Tooltip formatter={(v: number) => fmt(v)} />
          <Bar dataKey="center" fill={tokens.colors.primary[500]} barSize={40}>
            <ErrorBar dataKey="error" width={4} strokeWidth={2} stroke={tokens.colors.primary[700]} />
            <Cell fill={tokens.colors.primary[500]} />
          </Bar>
        </ComposedChart>
      </ResponsiveContainer>
      {current_price && (
        <div className="text-xs text-center text-gray-500">
          Twoja cena: {fmt(current_price)} — {current_price < p50 ? '⚠️ Poniżej mediany ryzyka' : '✅ Powyżej mediany'}
        </div>
      )}
    </div>
  )
}
