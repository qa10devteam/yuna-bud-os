'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileText, Download, Calendar, BarChart2, FileBarChart, Plus,
  Clock, CheckCircle,
} from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Report {
  id: string;
  title: string;
  type: 'monthly' | 'project' | 'financial' | 'custom';
  generated_at: string;
  status: 'ready' | 'generating' | 'scheduled';
  pages: number;
}

const DEMO_REPORTS: Report[] = [
  { id: '1', title: 'Raport miesięczny — Czerwiec 2026', type: 'monthly', generated_at: '2026-07-01 08:00', status: 'ready', pages: 12 },
  { id: '2', title: 'Podsumowanie: Droga gminna Pieszyce', type: 'project', generated_at: '2026-07-08 14:30', status: 'ready', pages: 8 },
  { id: '3', title: 'Analiza finansowa Q2 2026', type: 'financial', generated_at: '2026-07-05 09:15', status: 'ready', pages: 15 },
  { id: '4', title: 'Raport miesięczny — Lipiec 2026', type: 'monthly', generated_at: '', status: 'scheduled', pages: 0 },
  { id: '5', title: 'Porównanie ofert: Kanalizacja Łagiewniki', type: 'custom', generated_at: '2026-07-09 16:45', status: 'ready', pages: 6 },
];

const TYPE_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  monthly: { label: 'Miesięczny', icon: <Calendar className="w-3.5 h-3.5" />, color: 'text-blue-400' },
  project: { label: 'Projekt', icon: <FileBarChart className="w-3.5 h-3.5" />, color: 'text-emerald-400' },
  financial: { label: 'Finansowy', icon: <BarChart2 className="w-3.5 h-3.5" />, color: 'text-amber-400' },
  custom: { label: 'Niestandardowy', icon: <FileText className="w-3.5 h-3.5" />, color: 'text-purple-400' },
};

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.3 } } };

export function ReportsPage() {
  const [reports] = useState<Report[]>(DEMO_REPORTS);

  const readyCount = reports.filter(r => r.status === 'ready').length;
  const totalPages = reports.reduce((s, r) => s + r.pages, 0);

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
          <h2 className="text-xl font-semibold text-earth-100">Raporty</h2>
          <p className="text-earth-500 text-sm mt-0.5">Generowanie i pobieranie raportów PDF</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary text-earth-950 font-semibold text-sm hover:bg-emerald-400 transition-colors">
          <Plus className="w-4 h-4" /> Generuj raport
        </button>
      </motion.div>

      {/* Stats */}
      <motion.div variants={item} className="grid grid-cols-3 gap-3">
        <div className="glass-card rounded-xl p-4 border border-earth-800/40">
          <div className="flex items-center gap-2 text-earth-500 text-xs mb-2">
            <CheckCircle className="w-3.5 h-3.5" /> Gotowe
          </div>
          <p className="text-2xl font-bold text-emerald-400">{readyCount}</p>
        </div>
        <div className="glass-card rounded-xl p-4 border border-earth-800/40">
          <div className="flex items-center gap-2 text-earth-500 text-xs mb-2">
            <FileText className="w-3.5 h-3.5" /> Łącznie stron
          </div>
          <p className="text-2xl font-bold text-earth-200">{totalPages}</p>
        </div>
        <div className="glass-card rounded-xl p-4 border border-earth-800/40">
          <div className="flex items-center gap-2 text-earth-500 text-xs mb-2">
            <Clock className="w-3.5 h-3.5" /> Zaplanowane
          </div>
          <p className="text-2xl font-bold text-blue-400">{reports.filter(r => r.status === 'scheduled').length}</p>
        </div>
      </motion.div>

      {/* Report List */}
      <motion.div variants={item} className="space-y-3">
        {reports.map(r => {
          const meta = TYPE_META[r.type];
          return (
            <div key={r.id} className="glass-card rounded-xl p-5 border border-earth-800/40 hover:border-earth-700/60 transition-colors flex items-center gap-4">
              <div className={`w-10 h-10 rounded-lg bg-earth-800 flex items-center justify-center border border-earth-700/40 ${meta.color}`}>
                {meta.icon}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-earth-200 truncate">{r.title}</h3>
                <div className="flex items-center gap-3 mt-1 text-xs text-earth-500">
                  <span className={`flex items-center gap-1 ${meta.color}`}>{meta.icon} {meta.label}</span>
                  {r.generated_at && <span>{r.generated_at}</span>}
                  {r.pages > 0 && <span>{r.pages} stron</span>}
                </div>
              </div>
              {r.status === 'ready' && (
                <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-earth-800 text-earth-300 text-xs font-medium hover:bg-earth-700 transition-colors border border-earth-700/40">
                  <Download className="w-3.5 h-3.5" /> Pobierz PDF
                </button>
              )}
              {r.status === 'scheduled' && (
                <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 text-xs font-medium border border-blue-500/20">
                  <Clock className="w-3.5 h-3.5" /> Zaplanowany
                </span>
              )}
              {r.status === 'generating' && (
                <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 text-xs font-medium border border-amber-500/20">
                  <div className="w-3 h-3 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" /> Generowanie…
                </span>
              )}
            </div>
          );
        })}
        {reports.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <FileText className="w-10 h-10 text-earth-600 mb-3" />
            <p className="text-earth-400 text-sm font-medium">Brak raportów</p>
            <p className="text-earth-600 text-xs mt-1">Wygeneruj pierwszy raport</p>
          </div>
        )}
      </motion.div>

      {/* Templates section */}
      <motion.div variants={item} className="mt-2">
        <h3 className="text-sm font-semibold text-earth-300 mb-3">Szablony raportów</h3>
        <div className="grid grid-cols-3 gap-3">
          {[
            { name: 'Miesięczne podsumowanie', desc: 'Przychody, koszty, postępy projektów', icon: Calendar },
            { name: 'Raport per projekt', desc: 'Timeline, budżet, ryzyka, KPI', icon: FileBarChart },
            { name: 'Analiza porównawcza ofert', desc: 'Benchmarking ofert, ranking wykonawców', icon: BarChart2 },
          ].map(t => (
            <button
              key={t.name}
              className="glass-card rounded-xl p-4 border border-earth-800/40 text-left hover:border-accent-primary/30 transition-colors group"
            >
              <t.icon className="w-5 h-5 text-earth-500 group-hover:text-accent-primary transition-colors mb-2" />
              <p className="text-sm font-medium text-earth-200">{t.name}</p>
              <p className="text-xs text-earth-500 mt-0.5">{t.desc}</p>
            </button>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}
