'use client';

import { Sidebar } from '@/components/Sidebar';
import { Brain, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import dynamic from 'next/dynamic';

// Dynamic import to avoid SSR issues with motion
const MotionDiv = dynamic(() => import('motion/react').then((m) => m.motion.div), { ssr: false });

const decisions = [
  { id: 1, desc: 'Oferuj cenę: 285 000 zł', recommendation: 'accept', confidence: 92, reason: 'Realistyczne ryzyka, konkurencyjna cena' },
  { id: 2, desc: 'Wymagaj odwodnienia', recommendation: 'accept', confidence: 98, reason: 'Brak w dokumencie, realna potrzeba' },
  { id: 3, desc: 'Zaoferuj alternatywę transportu', recommendation: 'accept', confidence: 85, reason: 'Twoje koszty transportu niższe o 18%' },
  { id: 4, desc: 'Zignoruj cenę składowania', recommendation: 'decline', confidence: 70, reason: 'Cena w dokumencie zaniżona, ale realna' },
];

export default function DecyzjaPage() {
  return (
    <div className="flex min-h-screen bg-[#0A0A0A] text-[#F4F4F0] font-sans">
      <Sidebar />
      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#3B82F6]/20 flex items-center justify-center">
              <Brain className="w-6 h-6 text-[#3B82F6]" />
            </div>
            <div>
              <h1 className="text-3xl font-display font-bold text-[#F4F4F0]">
                DECYZJA
              </h1>
              <p className="text-neutral-400">Mózg systemowy — rekomendacje i podsumowanie.</p>
            </div>
          </div>
        </div>

        {/* Recommendations */}
        <div className="space-y-4 mb-8">
          {decisions.map((decision) => (
            <MotionDiv
              key={decision.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card flex items-start gap-4"
            >
              <div className={`p-3 rounded-lg ${
                decision.recommendation === 'accept' ? 'bg-[#00FF94]/20 text-[#00FF94]' :
                'bg-[#FF3300]/20 text-[#FF3300]'
              }`}>
                {decision.recommendation === 'accept' ? (
                  <CheckCircle className="w-6 h-6" />
                ) : (
                  <XCircle className="w-6 h-6" />
                )}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-display font-bold text-lg">{decision.desc}</h3>
                  <span className={`badge-tech`}>{decision.confidence}% pewności</span>
                </div>
                <p className="text-neutral-400 text-sm">{decision.reason}</p>
              </div>
              <div className="flex gap-2">
                <button className={`btn-primary text-sm ${
                  decision.recommendation === 'accept' ? '' : 'opacity-50'
                }`}>
                  AKCEPTUJ
                </button>
                <button className={`btn-secondary text-sm ${
                  decision.recommendation !== 'accept' ? '' : 'opacity-50'
                }`}>
                  ODRZUĆ
                </button>
              </div>
            </MotionDiv>
          ))}
        </div>

        {/* Summary */}
        <MotionDiv
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-display font-bold text-lg mb-2">Finalna rekomendacja</h3>
              <p className="text-neutral-400">
                Oferuj cenę <span className="text-[#00FF94] font-bold">285 000 zł</span> z wymogiem odwodnienia i alternatywnym transportem.
              </p>
            </div>
            <button className="btn-primary">
              GENERUJ OFERTĘ
            </button>
          </div>
        </MotionDiv>
      </main>
    </div>
  );
}
