import { PieChart, Pie, Cell, Tooltip } from 'recharts'

interface WinProbGaugeProps { probability: number }  // 0.0 - 1.0

export function WinProbGauge({ probability }: WinProbGaugeProps) {
  const pct = Math.round(probability * 100)
  const color = pct >= 60 ? '#2D6A4F' : pct >= 40 ? '#E9C46A' : '#E76F51'
  return (
    <div className="flex flex-col items-center">
      <PieChart width={120} height={70}>
        <Pie data={[{v: pct},{v: 100-pct}]} cx={55} cy={60} startAngle={180} endAngle={0}
             innerRadius={40} outerRadius={55} dataKey="v">
          <Cell fill={color} />
          <Cell fill="#E5E0D8" />
        </Pie>
      </PieChart>
      <div className="-mt-6 text-2xl font-bold" style={{color}}>{pct}%</div>
      <div className="text-xs text-gray-500">Prawdopodobieństwo wygranej</div>
    </div>
  )
}
