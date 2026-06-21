'use client';

import { Sidebar } from '@/components/Sidebar';
import { Flag, AlertTriangle } from 'lucide-react';
import { motion } from 'motion/react';
import { ChartClient } from '@/components/ChartClient';

const redFlags = [
  { id: 1, desc: 'Brak odwodnienia w przedmiarze', impact: '12 500 zł', page: 's. 12' },
  { id: 2, desc: 'Niekonkurencyjna cena transportu', impact: '8 200 zł', page: 's. 15' },
  { id: 3, desc: 'Błąd w obmiarze nasypów', impact: '4 100 zł', page: 's. 22' },
];

export default function SilnikPage() {
  return (
    <div className="flex min-h-screen bg-[#F4F4F0] text-[#1A1A1A] font-sans">
      <Sidebar />
      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        <div className="flex items-center gap-3 mb-8">
          <Flag className="w-8 h-8 text-[#00FF94]" />
          <div>
            <h1 className="text-3xl font-display font-bold text-[#1A1A1A]">
              SILNIK — Moduł 2: Przetwarzanie
            </h1>
            <p className="text-[#6B6B68]">Analiza ryzyk i czerwone flagi w dokumentacji.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="card"
          >
            <h3 className="font-display font-bold text-lg mb-4">Rozkład ryzyk</h3>
            <div className="h-64">
              <ChartClient />
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="card"
          >
            <h3 className="font-display font-bold text-lg mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-[#FF3300]" />
              Wykryte ryzyka
            </h3>
            <div className="space-y-4">
              {redFlags.map((flag) => (
                <div key={flag.id} className="p-3 bg-[#FF3300]/10 border-l-4 border-[#FF3300] rounded-r">
                  <div className="font-mono text-sm text-[#FF3300] mb-1">{flag.desc}</div>
                  <div className="flex justify-between text-xs text-[#6B6B68]">
                    <span>Strata: {flag.impact}</span>
                    <span>Strona: {flag.page}</span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        <div className="flex justify-end">
          <button className="btn-primary">
            PRZEJDŹ DO DECYZJI
          </button>
        </div>
      </main>
    </div>
  );
}
