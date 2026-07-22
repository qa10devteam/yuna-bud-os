'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'motion/react';
import {
  FileText, Download, Calendar, BarChart2, FileBarChart, Plus, Clock, CheckCircle, Loader2,
} from 'lucide-react';
import { PageShell } from '@/components/PageShell';
import { useAuthFetch } from '@/lib/api-v2';

// ── Types ─────────────────────────────────────────────────────────────────────

interface MonthlyRow {
  month: string;
  count: number;
  total_value: number;
}

interface Report {
  id: string;
  title: string;
  type: 'monthly' | 'project' | 'financial' | 'custom';
  generated_at: string;
  status: 'ready' | 'generating' | 'scheduled';
  pages: number;
}

const TYPE_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  monthly:   { label: 'Miesięczny',     icon: <Calendar className="w-3.5 h-3.5" />,    color: 'text-info' },
  project:   { label: 'Projekt',        icon: <FileBarChart className="w-3.5 h-3.5" />, color: 'text-success' },
  financial: { label: 'Finansowy',      icon: <BarChart2 className="w-3.5 h-3.5" />,   color: 'text-warning' },
  custom:    { label: 'Niestandardowy', icon: <FileText className="w-3.5 h-3.5" />,    color: 'text-violet' },
};

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item      = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.3 } } };

// Static chart data — fallback / always-visible
const STATIC_CHART: { month: string; count: number }[] = [
  { month: 'Lut', count: 12 },
  { month: 'Mar', count: 18 },
  { month: 'Kwi', count: 15 },
  { month: 'Maj', count: 22 },
  { month: 'Cze', count: 19 },
  { month: 'Lip', count: 24 },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtMln(v: number): string {
  const n = v ?? 0;
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + ' M';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + ' tys.';
  return String(n);
}

// ── Inline Bar Chart ──────────────────────────────────────────────────────────

function InlineBarChart({ data }: { data: { month: string; count: number }[] }) {
  const max = Math.max(...data.map(d => d.count), 1);
  return (
    <div className="space-y-2.5">
      {data.map(({ month, count }) => {
        const pct = Math.round((count / max) * 100);
        return (
          <div key={month} className="flex items-center gap-3">
            <span className="w-8 text-right text-xs text-slate-400 shrink-0">{month}</span>
            <div className="flex-1 bg-slate-700/40 rounded-r h-5 overflow-hidden">
              <div
                className="bg-emerald-500/70 rounded-r h-5 transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-6 text-xs text-slate-300 font-medium tabular-nums shrink-0">{count}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ReportsPage() {
  const authFetch = useAuthFetch();
  const [monthlyData, setMonthlyData] = useState<MonthlyRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [reports, setReports] = useState<Report[]>([]);

  const fetchMonthly = useCallback(async () => {
    setLoading(true);
    try {
      const data = await authFetch('/api/v2/reports/monthly');
      const rows: MonthlyRow[] = data?.items ?? data?.data ?? data ?? [];
      setMonthlyData(Array.isArray(rows) ? rows : []);
    } catch {
      // Use empty fallback
      setMonthlyData([]);
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { fetchMonthly(); }, [fetchMonthly]);

  // Build static report list (could later come from API)
  useEffect(() => {
    setReports([
      { id: '1', title: 'Raport miesięczny — Czerwiec 2026', type: 'monthly', generated_at: '2026-07-01 08:00', status: 'ready', pages: 12 },
      { id: '2', title: 'Podsumowanie: Droga gminna Pieszyce', type: 'project', generated_at: '2026-07-08 14:30', status: 'ready', pages: 8 },
      { id: '3', title: 'Analiza finansowa Q2 2026', type: 'financial', generated_at: '2026-07-05 09:15', status: 'ready', pages: 15 },
      { id: '4', title: 'Raport miesięczny — Lipiec 2026', type: 'monthly', generated_at: '', status: 'scheduled', pages: 0 },
    ]);
  }, []);

  const readyCount     = reports.filter(r => r.status === 'ready').length;
  const totalPages     = reports.reduce((s, r) => s + r.pages, 0);
  const scheduledCount = reports.filter(r => r.status === 'scheduled').length;

  // Derive chart rows: prefer API data when available, otherwise static
  const chartRows: { month: string; count: number }[] =
    monthlyData.length > 0
      ? monthlyData.map(r => ({ month: r.month, count: r.count }))
      : STATIC_CHART;

  const actions = (
    <button type="button" className="btn-primary flex items-center gap-2">
      <Plus className="w-4 h-4" /> Generuj raport
    </button>
  );

  return (
    <PageShell title="Raporty" subtitle="Raporty analityczne przetargów" actions={actions}>
      <motion.div className="flex flex-col gap-6" variants={container} initial="hidden" animate="show">

        {/* KPI Stats */}
        <motion.div variants={item} className="grid grid-cols-3 gap-3">
          {/* Gotowe */}
          <div className="card rounded-xl p-4 shadow-md-sm flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-400/10 flex items-center justify-center shrink-0">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-emerald-400 leading-none">{readyCount}</p>
              <p className="text-xs text-slate-500 mt-0.5">Gotowe</p>
            </div>
          </div>

          {/* Łącznie stron */}
          <div className="card rounded-xl p-4 shadow-md-sm flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-slate-700/60 flex items-center justify-center shrink-0">
              <FileText className="w-4 h-4 text-slate-300" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-200 leading-none">{totalPages}</p>
              <p className="text-xs text-slate-500 mt-0.5">Łącznie stron</p>
            </div>
          </div>

          {/* Zaplanowane */}
          <div className="card rounded-xl p-4 shadow-md-sm flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-sky-400/10 flex items-center justify-center shrink-0">
              <Clock className="w-4 h-4 text-sky-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-sky-400 leading-none">{scheduledCount}</p>
              <p className="text-xs text-slate-500 mt-0.5">Zaplanowane</p>
            </div>
          </div>
        </motion.div>

        {/* Inline Bar Chart — Aktywność przetargowa */}
        <motion.div variants={item} className="card rounded-xl p-5 shadow-md-sm">
          <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-emerald-400" />
            Aktywność przetargowa — ostatnie 6 miesięcy
          </h3>
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 text-slate-500 animate-spin" />
            </div>
          ) : (
            <InlineBarChart data={chartRows} />
          )}
        </motion.div>

        {/* Report List */}
        <motion.div variants={item} className="space-y-3">
          {reports.map(r => {
            const meta = TYPE_META[r.type];
            return (
              <div
                key={r.id}
                className="rounded-xl bg-slate-800/50 border border-slate-700/50 p-4 flex items-center gap-4"
              >
                {/* File icon */}
                <div className="w-10 h-10 rounded-lg bg-emerald-400/10 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5 text-emerald-400" />
                </div>

                {/* Title + subtitle */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-bold text-slate-200 truncate">{r.title}</h3>
                  <div className="flex items-center gap-3 mt-0.5 text-xs text-slate-400">
                    <span className={`flex items-center gap-1 ${meta.color}`}>{meta.icon} {meta.label}</span>
                    {r.pages > 0 && <span>{r.pages} stron</span>}
                    {r.generated_at && <span>{r.generated_at}</span>}
                  </div>
                </div>

                {/* Action badge / button */}
                {r.status === 'ready' && (
                  <button
                    type="button"
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-emerald-400/30 text-emerald-400 hover:bg-emerald-400/10 transition-colors whitespace-nowrap"
                  >
                    <Download className="w-3.5 h-3.5" /> Pobierz PDF
                  </button>
                )}
                {r.status === 'scheduled' && (
                  <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-info/10 text-info text-xs font-medium border border-info/20">
                    <Clock className="w-3.5 h-3.5" /> Zaplanowany
                  </span>
                )}
                {r.status === 'generating' && (
                  <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-warning/10 text-warning text-xs font-medium border border-warning/20">
                    <div className="w-3 h-3 border-2 border-warning border-t-transparent rounded-full animate-spin" /> Generowanie…
                  </span>
                )}
              </div>
            );
          })}
          {reports.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <FileText className="w-10 h-10 text-slate-600 mb-3" />
              <p className="text-slate-400 text-sm font-medium">Brak raportów</p>
              <p className="text-slate-600 text-xs mt-1">Wygeneruj pierwszy raport</p>
            </div>
          )}
        </motion.div>

        {/* Templates section */}
        <motion.div variants={item} className="mt-2">
          <h3 className="section-label mb-3">Szablony raportów</h3>
          <div className="grid grid-cols-3 gap-3">
            {[
              { name: 'Miesięczne podsumowanie', desc: 'Przychody, koszty, postępy projektów', icon: Calendar },
              { name: 'Raport per projekt', desc: 'Timeline, budżet, ryzyka, KPI', icon: FileBarChart },
              { name: 'Analiza porównawcza ofert', desc: 'Benchmarking ofert, ranking wykonawców', icon: BarChart2 },
            ].map(t => (
              <button type="button"
                key={t.name}
                className="card rounded-xl p-4 text-left card-hover group border border-ink-800/40"
              >
                <t.icon className="w-5 h-5 text-slate-500 group-hover:text-em transition-colors mb-2" />
                <p className="text-sm font-medium text-slate-200">{t.name}</p>
                <p className="text-xs text-slate-500 mt-0.5">{t.desc}</p>
              </button>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </PageShell>
  );
}
