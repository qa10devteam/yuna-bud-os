'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileText, DollarSign, Clock, AlertCircle, TrendingUp, Plus, Filter,
} from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Contract {
  id: string;
  title: string;
  client: string;
  value_pln: number;
  paid_pln: number;
  status: 'active' | 'completed' | 'overdue' | 'draft';
  start_date: string;
  end_date: string;
  progress_pct: number;
}

// ── Demo data ─────────────────────────────────────────────────────────────────
const DEMO_CONTRACTS: Contract[] = [
  { id: '1', title: 'Budowa drogi gminnej — Pieszyce', client: 'Gmina Pieszyce', value_pln: 850000, paid_pln: 340000, status: 'active', start_date: '2026-03-01', end_date: '2026-09-30', progress_pct: 45 },
  { id: '2', title: 'Kanalizacja sanitarna Łagiewniki', client: 'ZWiK Łagiewniki', value_pln: 1200000, paid_pln: 600000, status: 'active', start_date: '2026-02-15', end_date: '2026-11-30', progress_pct: 52 },
  { id: '3', title: 'Centrum kultury Świdnica', client: 'Urząd Miasta Świdnica', value_pln: 4200000, paid_pln: 0, status: 'draft', start_date: '2026-08-01', end_date: '2027-06-30', progress_pct: 0 },
  { id: '4', title: 'Rowy melioracyjne — pow. dzierżoniowski', client: 'Starostwo Powiatowe', value_pln: 320000, paid_pln: 320000, status: 'completed', start_date: '2025-09-01', end_date: '2026-04-15', progress_pct: 100 },
  { id: '5', title: 'Remont mostu na Bystrzycy', client: 'GDDKiA Wrocław', value_pln: 1850000, paid_pln: 740000, status: 'overdue', start_date: '2025-11-01', end_date: '2026-06-30', progress_pct: 65 },
];

const STATUS_META: Record<string, { label: string; bg: string }> = {
  active: { label: 'Aktywny', bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  completed: { label: 'Zakończony', bg: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  overdue: { label: 'Opóźniony', bg: 'bg-red-500/10 text-red-400 border-red-500/20' },
  draft: { label: 'Wersja robocza', bg: 'bg-earth-700/30 text-earth-400 border-earth-700/40' },
};

function fmtPLN(v: number) {
  return new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 }).format(v);
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.3 } } };

export function ContractsPage() {
  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'overdue'>('all');

  const contracts = DEMO_CONTRACTS.filter(c => filter === 'all' || c.status === filter);

  const totals = {
    value: DEMO_CONTRACTS.reduce((s, c) => s + c.value_pln, 0),
    paid: DEMO_CONTRACTS.reduce((s, c) => s + c.paid_pln, 0),
    active: DEMO_CONTRACTS.filter(c => c.status === 'active').length,
    overdue: DEMO_CONTRACTS.filter(c => c.status === 'overdue').length,
  };

  return (
    <motion.div
      className="flex flex-col gap-6 p-6 h-full overflow-y-auto"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {/* Header */}
      <motion.div variants={item} className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-earth-100">Kontrakty</h2>
          <p className="text-earth-500 text-sm mt-0.5">Tracker kontraktów i cashflow</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary text-earth-950 font-semibold text-sm hover:bg-emerald-400 transition-colors">
          <Plus className="w-4 h-4" /> Nowy kontrakt
        </button>
      </motion.div>

      {/* Stats */}
      <motion.div variants={item} className="grid grid-cols-4 gap-3">
        {[
          { label: 'Wartość kontraktów', value: fmtPLN(totals.value), icon: DollarSign, color: 'text-accent-primary' },
          { label: 'Zapłacono', value: fmtPLN(totals.paid), icon: TrendingUp, color: 'text-emerald-400' },
          { label: 'Aktywne', value: String(totals.active), icon: Clock, color: 'text-amber-400' },
          { label: 'Opóźnione', value: String(totals.overdue), icon: AlertCircle, color: 'text-red-400' },
        ].map(s => (
          <div key={s.label} className="glass-card rounded-xl p-4 border border-earth-800/40">
            <div className="flex items-center gap-2 text-earth-500 text-xs mb-2">
              <s.icon className="w-3.5 h-3.5" />
              {s.label}
            </div>
            <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </motion.div>

      {/* Filter tabs */}
      <motion.div variants={item} className="flex items-center gap-3">
        <Filter className="w-4 h-4 text-earth-600" />
        <div className="flex gap-1 p-1 rounded-lg bg-earth-900 border border-earth-800/60">
          {([['all', 'Wszystkie'], ['active', 'Aktywne'], ['completed', 'Zakończone'], ['overdue', 'Opóźnione']] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                filter === key ? 'bg-earth-800 text-earth-100' : 'text-earth-500 hover:text-earth-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Contract cards */}
      <motion.div variants={item} className="space-y-3">
        {contracts.map(c => {
          const meta = STATUS_META[c.status];
          const cashPct = c.value_pln > 0 ? Math.round((c.paid_pln / c.value_pln) * 100) : 0;
          return (
            <div key={c.id} className="glass-card rounded-xl p-5 border border-earth-800/40 hover:border-earth-700/60 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-earth-800 flex items-center justify-center border border-earth-700/40 shrink-0">
                    <FileText className="w-5 h-5 text-earth-500" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-earth-200 truncate">{c.title}</h3>
                    <p className="text-xs text-earth-500 mt-0.5">{c.client}</p>
                  </div>
                </div>
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium border ${meta.bg}`}>
                  {meta.label}
                </span>
              </div>

              <div className="mt-4 grid grid-cols-4 gap-4 text-xs">
                <div>
                  <p className="text-earth-600">Wartość</p>
                  <p className="text-earth-200 font-mono font-semibold mt-0.5">{fmtPLN(c.value_pln)}</p>
                </div>
                <div>
                  <p className="text-earth-600">Zapłacono</p>
                  <p className="text-earth-200 font-mono font-semibold mt-0.5">{fmtPLN(c.paid_pln)}</p>
                </div>
                <div>
                  <p className="text-earth-600">Termin</p>
                  <p className="text-earth-200 mt-0.5">{c.start_date} → {c.end_date}</p>
                </div>
                <div>
                  <p className="text-earth-600">Postęp</p>
                  <p className="text-earth-200 font-semibold mt-0.5">{c.progress_pct}%</p>
                </div>
              </div>

              {/* Progress bars */}
              <div className="mt-3 space-y-2">
                <div>
                  <div className="flex justify-between text-xs text-earth-600 mb-1">
                    <span>Postęp prac</span>
                    <span>{c.progress_pct}%</span>
                  </div>
                  <div className="h-1.5 bg-earth-800 rounded-full overflow-hidden">
                    <div className="h-full bg-accent-primary rounded-full transition-all" style={{ width: `${c.progress_pct}%` }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-earth-600 mb-1">
                    <span>Cashflow</span>
                    <span>{cashPct}%</span>
                  </div>
                  <div className="h-1.5 bg-earth-800 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-400 rounded-full transition-all" style={{ width: `${cashPct}%` }} />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </motion.div>
    </motion.div>
  );
}
