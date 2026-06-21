'use client';

import { Sidebar } from '@/components/Sidebar';
import { Brain, CheckCircle, AlertTriangle, FileText } from 'lucide-react';
import { motion } from 'motion/react';

const stats = [
  { label: 'Wartość przetargu', value: '4 500 000 zł', icon: FileText },
  { label: 'Twój koszt', value: '3 230 000 zł', icon: Brain },
  { label: 'Zysk brutto', value: '1 270 000 zł', icon: CheckCircle, success: true },
  { label: 'Ryzyka', value: '3 wykryte', icon: AlertTriangle, warning: true },
];

export default function DecyzjaPage() {
  return (
    <div className="flex min-h-screen bg-surface-base text-text-primary font-body">
      <Sidebar />
      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        <div className="flex items-center gap-3 mb-8">
          <Brain className="w-8 h-8 text-accent-success" />
          <div>
            <h1 className="text-3xl font-display font-bold text-neutral-600">
              DECYZJA — Moduł 3: Łyżka
            </h1>
            <p className="text-neutral-400">Podsumowanie i decyzja o złożeniu oferty.</p>
          </div>
        </div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8"
        >
          {stats.map((stat) => (
            <div key={stat.label} className="card">
              <div className="flex items-center gap-3 mb-2">
                <stat.icon className={`w-5 h-5 ${stat.success ? 'text-accent-success' : stat.warning ? 'text-accent-warning' : 'text-neutral-400'}`} />
                <span className="text-sm text-neutral-400">{stat.label}</span>
              </div>
              <div className={`text-2xl font-mono font-bold ${stat.success ? 'text-accent-success' : stat.warning ? 'text-accent-warning' : 'text-neutral-600'}`}>
                {stat.value}
              </div>
            </div>
          ))}
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-neutral-600 text-neutral-100 rounded-xl p-8 flex flex-col items-center gap-6"
        >
          <h2 className="text-2xl font-display font-bold text-center">
            Decyzja końcowa
          </h2>
          <p className="text-neutral-300 text-center max-w-2xl">
            System zaleca złożenie oferty. Wykryto ryzyka, które zostały uwzględnione w koszcie.
            Marża brutto wynosi 28%.
          </p>
          <div className="flex gap-4">
            <button className="btn-secondary">
              ODPUŚĆ
            </button>
            <button className="btn-primary text-lg px-8">
              STARTUJMY — ZŁÓŻ OFERTĘ
            </button>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
