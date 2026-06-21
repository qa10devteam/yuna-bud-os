'use client';

import { Sidebar } from '@/components/Sidebar';
import { Flag, AlertTriangle, CheckCircle, FileText } from 'lucide-react';
import dynamic from 'next/dynamic';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

// Dynamic import to avoid SSR issues with motion
const MotionDiv = dynamic(() => import('motion/react').then((m) => m.motion.div), { ssr: false });

const riskData = [
  { name: 'Niskie ryzyko', value: 40, color: '#00FF94' },
  { name: 'Średnie ryzyko', value: 30, color: '#FF3300' },
  { name: 'Wysokie ryzyko', value: 20, color: '#6B6B68' },
  { name: 'Krytyczne', value: 10, color: '#1A1A1A' },
];

const redFlags = [
  { id: 1, desc: 'Brak odwodnienia w przedmiarze', impact: '12 500 zł', page: 's. 12', severity: 'high' },
  { id: 2, desc: 'Niekonkurencyjna cena transportu', impact: '8 200 zł', page: 's. 15', severity: 'medium' },
  { id: 3, desc: 'Błąd w obmiarze nasypów', impact: '4 100 zł', page: 's. 22', severity: 'low' },
  { id: 4, desc: 'Brak uwzględnienia składowania gruntu', impact: '6 000 zł', page: 's. 28', severity: 'high' },
];

// RechartsChart component wrapper
function RiskChart() {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={riskData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={80}
          paddingAngle={5}
          dataKey="value"
        >
          {riskData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: '#1A1A1A',
            border: '1px solid #3D3D3C',
            borderRadius: '8px',
          }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

const DynamicRiskChart = dynamic(() => Promise.resolve(RiskChart), { ssr: false });

export default function SilnikPage() {
  return (
    <div className="flex min-h-screen bg-[#0A0A0A] text-[#F4F4F0] font-sans">
      <Sidebar />
      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#FF3300]/20 flex items-center justify-center">
              <Flag className="w-6 h-6 text-[#FF3300]" />
            </div>
            <div>
              <h1 className="text-3xl font-display font-bold text-[#F4F4F0]">
                SILNIK RYZYKA
              </h1>
              <p className="text-neutral-400">Analiza ryzyk i czerwone flagi w dokumentacji.</p>
            </div>
          </div>
          <button className="btn-primary text-sm">
            <FileText className="w-4 h-4 mr-2 inline" />
            Generuj raport
          </button>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <MotionDiv
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="card"
          >
            <h3 className="font-display font-bold text-lg mb-4">Rozkład ryzyk</h3>
            <div className="h-64">
              <DynamicRiskChart />
            </div>
          </MotionDiv>

          <MotionDiv
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
            className="card"
          >
            <h3 className="font-display font-bold text-lg mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-[#FF3300]" />
              Wykryte ryzyka
            </h3>
            <div className="space-y-4">
              {redFlags.map((flag) => (
                <div key={flag.id} className={`p-3 rounded-r border-l-4 ${
                  flag.severity === 'high' ? 'bg-[#FF3300]/10 border-[#FF3300]' :
                  flag.severity === 'medium' ? 'bg-[#6B6B68]/10 border-[#6B6B68]' :
                  'bg-[#00FF94]/10 border-[#00FF94]'
                }`}>
                  <div className={`font-mono text-sm mb-1 ${
                    flag.severity === 'high' ? 'text-[#FF3300]' :
                    flag.severity === 'medium' ? 'text-[#6B6B68]' :
                    'text-[#00FF94]'
                  }`}>{flag.desc}</div>
                  <div className="flex justify-between text-xs text-neutral-400">
                    <span>Strata: {flag.impact}</span>
                    <span>Strona: {flag.page}</span>
                  </div>
                </div>
              ))}
            </div>
          </MotionDiv>
        </div>

        {/* Summary */}
        <MotionDiv
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-display font-bold text-lg mb-2">Podsumowanie analizy</h3>
              <p className="text-neutral-400">
                Wykryto <span className="text-[#FF3300] font-bold">4 ryzyka</span> o łącznej wartości <span className="text-[#FF3300] font-bold">30 800 zł</span>.
              </p>
            </div>
            <button className="btn-primary">
              PRZEJDŹ DO DECYZJI
            </button>
          </div>
        </MotionDiv>
      </main>
    </div>
  );
}
