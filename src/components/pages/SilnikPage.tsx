'use client';

import { Flag, AlertTriangle, CheckCircle, FileText } from 'lucide-react';
import dynamic from 'next/dynamic';

const redFlags = [
  { id: 1, desc: 'Brak odwodnienia w przedmiarze', impact: '12 500 zł', page: 's. 12', severity: 'high' as const },
  { id: 2, desc: 'Niekonkurencyjna cena transportu', impact: '8 200 zł', page: 's. 15', severity: 'medium' as const },
  { id: 3, desc: 'Błąd w obmiarze nasypów', impact: '4 100 zł', page: 's. 22', severity: 'low' as const },
  { id: 4, desc: 'Brak uwzględnienia składowania gruntu', impact: '6 000 zł', page: 's. 28', severity: 'high' as const },
];

// Dynamic import to avoid SSR issues with motion
const MotionDiv = dynamic(() => import('motion/react').then((m) => m.motion.div), { ssr: false });

export function SilnikPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#FF3300]/20 flex items-center justify-center">
            <Flag className="w-6 h-6 text-[#FF3300]" />
          </div>
          <div>
            <h1 className="text-3xl font-display font-bold text-[#F4F4F0]">SILNIK RYZYKA</h1>
            <p className="text-neutral-400">Analiza ryzyk i czerwone flagi w dokumentacji.</p>
          </div>
        </div>
        <button className="btn-primary text-sm">
          <FileText className="w-4 h-4 mr-2 inline" />
          Generuj raport
        </button>
      </div>

      {/* Red Flags */}
      <MotionDiv
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card"
      >
        <h3 className="font-display font-bold text-lg mb-6 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-[#FF3300]" />
          Wykryte ryzyka
        </h3>
        <div className="space-y-4">
          {redFlags.map((flag, index) => (
            <MotionDiv
              key={flag.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`p-4 rounded-r border-l-4 ${
                flag.severity === 'high' ? 'bg-[#FF3300]/10 border-[#FF3300]' :
                flag.severity === 'medium' ? 'bg-[#6B6B68]/10 border-[#6B6B68]' :
                'bg-[#00FF94]/10 border-[#00FF94]'
              }`}
            >
              <div className={`font-mono text-sm mb-1 ${
                flag.severity === 'high' ? 'text-[#FF3300]' :
                flag.severity === 'medium' ? 'text-[#6B6B68]' :
                'text-[#00FF94]'
              }`}>{flag.desc}</div>
              <div className="flex justify-between text-xs text-neutral-400">
                <span>Strata: {flag.impact}</span>
                <span>Strona: {flag.page}</span>
              </div>
            </MotionDiv>
          ))}
        </div>
      </MotionDiv>

      {/* Summary */}
      <MotionDiv
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
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
    </div>
  );
}
