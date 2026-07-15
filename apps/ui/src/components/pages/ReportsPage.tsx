'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'motion/react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
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

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtMln(v: number): string {
  const n = v ?? 0;
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + ' M';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + ' tys.';
  return String(n);
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

  const readyCount = reports.filter(r => r.status === 'ready').length;
  const totalPages = reports.reduce((s, r) => s + r.pages, 0);

  const actions = (
    <button className="btn-primary flex items-center gap-2">
      <Plus className="w-4 h-4" /> Generuj raport
    </button>
  );

  return (
    <PageShell title="Raporty" subtitle="Raporty analityczne przetargów" actions={actions}>
      <motion.div className="flex flex-col gap-6" variants={container} initial="hidden" animate="show">

        {/* Stats */}
        <motion.div variants={item} className="grid grid-cols-3 gap-3">
          <div className="card rounded-token-lg p-4 shadow-token-sm">
            <div className="flex items-center gap-2 text-earth-500 text-xs mb-2">
              <CheckCircle className="w-3.5 h-3.5" /> Gotowe
            </div>
            <p className="text-2xl font-bold text-success">{readyCount}</p>
          </div>
          <div className="card rounded-token-lg p-4 shadow-token-sm">
            <div className="flex items-center gap-2 text-earth-500 text-xs mb-2">
              <FileText className="w-3.5 h-3.5" /> Łącznie stron
            </div>
            <p className="text-2xl font-bold text-earth-200">{totalPages}</p>
          </div>
          <div className="card rounded-token-lg p-4 shadow-token-sm">
            <div className="flex items-center gap-2 text-earth-500 text-xs mb-2">
              <Clock className="w-3.5 h-3.5" /> Zaplanowane
            </div>
            <p className="text-2xl font-bold text-info">{reports.filter(r => r.status === 'scheduled').length}</p>
          </div>
        </motion.div>

        {/* Monthly Bar Chart */}
        <motion.div variants={item} className="card rounded-token-lg p-5 shadow-token-sm">
          <h3 className="text-sm font-semibold text-earth-200 mb-4 flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-accent-primary" />
            Przetargi miesięcznie
          </h3>
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 text-earth-500 animate-spin" />
            </div>
          ) : monthlyData.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <BarChart2 className="w-8 h-8 text-earth-700 mb-2" />
              <p className="text-earth-500 text-sm">Brak danych miesięcznych</p>
              <p className="text-earth-600 text-xs mt-1">Dane pojawią się po zaindeksowaniu przetargów</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={monthlyData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <XAxis
                  dataKey="month"
                  tick={{ fill: '#94A3B8', fontSize: 11 }}
                  axisLine={{ stroke: '#1E293B' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#64748B', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v: number) => fmtMln(v)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontSize: 12,
                  }}
                  labelStyle={{ color: '#E2E8F0' }}
                  formatter={(value: number, name: string) => [
                    name === 'total_value' ? fmtMln(value) + ' zł' : value,
                    name === 'total_value' ? 'Wartość' : 'Liczba',
                  ]}
                />
                <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} name="Liczba" />
                <Bar dataKey="total_value" fill="#22C55E" radius={[4, 4, 0, 0]} name="Wartość" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Report List */}
        <motion.div variants={item} className="space-y-3">
          {reports.map(r => {
            const meta = TYPE_META[r.type];
            return (
              <div key={r.id} className="card rounded-token-lg p-5 card-hover shadow-token-sm flex items-center gap-4">
                <div className={`w-10 h-10 rounded-token-lg bg-earth-800 flex items-center justify-center border border-earth-700/40 ${meta.color}`}>
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
                  <button className="btn-secondary flex items-center gap-1.5 text-xs px-3 py-1.5">
                    <Download className="w-3.5 h-3.5" /> Pobierz PDF
                  </button>
                )}
                {r.status === 'scheduled' && (
                  <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-token bg-info/10 text-info text-xs font-medium border border-info/20">
                    <Clock className="w-3.5 h-3.5" /> Zaplanowany
                  </span>
                )}
                {r.status === 'generating' && (
                  <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-token bg-warning/10 text-warning text-xs font-medium border border-warning/20">
                    <div className="w-3 h-3 border-2 border-warning border-t-transparent rounded-full animate-spin" /> Generowanie…
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
          <h3 className="section-label mb-3">Szablony raportów</h3>
          <div className="grid grid-cols-3 gap-3">
            {[
              { name: 'Miesięczne podsumowanie', desc: 'Przychody, koszty, postępy projektów', icon: Calendar },
              { name: 'Raport per projekt', desc: 'Timeline, budżet, ryzyka, KPI', icon: FileBarChart },
              { name: 'Analiza porównawcza ofert', desc: 'Benchmarking ofert, ranking wykonawców', icon: BarChart2 },
            ].map(t => (
              <button
                key={t.name}
                className="card rounded-token-lg p-4 text-left card-hover group border border-earth-800/40"
              >
                <t.icon className="w-5 h-5 text-earth-500 group-hover:text-accent-primary transition-colors mb-2" />
                <p className="text-sm font-medium text-earth-200">{t.name}</p>
                <p className="text-xs text-earth-500 mt-0.5">{t.desc}</p>
              </button>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </PageShell>
  );
}
