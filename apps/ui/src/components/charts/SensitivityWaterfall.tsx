// Top-5 cost drivers waterfall
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from 'recharts'

interface Driver { name: string; sobol_s1: number }
interface SensitivityWaterfallProps { drivers: Driver[] }

export function SensitivityWaterfall({ drivers }: SensitivityWaterfallProps) {
  const top5 = [...drivers].sort((a,b) => b.sobol_s1 - a.sobol_s1).slice(0, 5)
  const COLORS = ['#8B6914','#B8860B','#D4A017','#E9C46A','#F5DEB3']
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={top5} layout="vertical">
        <XAxis type="number" tickFormatter={v => `${(v*100).toFixed(0)}%`} />
        <YAxis type="category" dataKey="name" width={120} tick={{fontSize:12}} />
        <Tooltip formatter={(v: number) => `${(v*100).toFixed(1)}%`} />
        <Bar dataKey="sobol_s1">
          {top5.map((_,i) => <Cell key={i} fill={COLORS[i]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
