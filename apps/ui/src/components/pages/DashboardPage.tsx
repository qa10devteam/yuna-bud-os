'use client';

import { motion } from 'motion/react';
import { useStore } from '@/store/useStore';
import { useDashboardStats, useTenders } from '@/lib/api';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import MarketKPIBar from '@/components/MarketKPIBar';
import {
  TrendingUp,
  FileText,
  AlertTriangle,
  Target,
  Zap,
  ArrowRight,
  Clock,
  Radar,
  Calculator,
  Brain,
  BarChart3,
  Info,
} from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

// ── Spark data ────────────────────────────────────────────────────────────────
// sparkData now comes from API (weekly_activity)

// ── Animation variants ────────────────────────────────────────────────────────
const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.07 } },
};
const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.38, ease: [0, 0, 0.2, 1] as const } },
};

// ── Pipeline stages config ────────────────────────────────────────────────────
const pipelineStages = [
  { key: 'new',          label: 'Nowy',        color: '#3B82F6' },
  { key: 'matched',      label: 'Dopasowany',  color: '#8B5CF6' },
  { key: 'watching',     label: 'Obserwowany', color: '#0EA5E9' },
  { key: 'analyzing',    label: 'Analiza',     color: '#F59E0B' },
  { key: 'estimated',    label: 'Wyceniony',   color: '#10b981' },
  { key: 'decided_go',   label: 'GO ✓',        color: '#22C55E' },
  { key: 'decided_nogo', label: 'NO-GO ✗',     color: '#EF4444' },
];

// ── Status badge config ───────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
  new:          'bg-accent-info/15 text-accent-info',
  matched:      'bg-accent-violet/15 text-accent-violet',
  watching:     'bg-sky-500/15 text-sky-400',
  analyzing:    'bg-accent-warning/15 text-accent-warning',
  estimated:    'bg-accent-primary/15 text-accent-primary',
  decided_go:   'bg-accent-primary/20 text-accent-primary',
  decided_nogo: 'bg-accent-danger/15 text-accent-danger',
  archived:     'bg-earth-700/40 text-earth-500',
};
const STATUS_LABELS: Record<string, string> = {
  new:          'Nowy',
  matched:      'Dopasowany',
  watching:     'Obserwowany',
  analyzing:    'Analiza',
  estimated:    'Wyceniony',
  decided_go:   'GO ✓',
  decided_nogo: 'NO-GO ✗',
  archived:     'Archiwum',
};

// ── Formatters ────────────────────────────────────────────────────────────────
/** Formatuje liczbę jako polską wartość PLN: 1 200 000 zł */
function fmtPLN(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1).replace('.0', '') + ' M zł';
  if (v >= 1_000) return (v / 1_000).toFixed(0) + ' tys. zł';
  return v.toFixed(0) + ' zł';
}

/** Formatuje datę w formacie DD.MM.YYYY */
function fmtDate(s: string | null | undefined): string {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('pl-PL', {
    day:   '2-digit',
    month: '2-digit',
    year:  'numeric',
  });
}

/** Kolor match score: >=80% zielony, 60-79% żółty, <60% czerwony */
function matchColor(score: number): string {
  if (score >= 80) return '#10b981';   // zielony
  if (score >= 60) return '#F59E0B';   // żółty
  return '#EF4444';                    // czerwony
}

// ── Tooltip ───────────────────────────────────────────────────────────────────
function Tooltip({ text }: { text: string }) {
  return (
    <span
      className="relative group inline-flex items-center"
      title={text}
    >
      <Info className="w-3 h-3 text-earth-600 hover:text-earth-400 cursor-help transition-colors" />
    </span>
  );
}

// ── Skeleton cards ────────────────────────────────────────────────────────────
function SkeletonStatCard() {
  return (
    <div className="glass-card p-5 animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-3 bg-earth-700 rounded w-24" />
        <div className="w-4 h-4 bg-earth-700 rounded" />
      </div>
      <div className="flex items-end justify-between gap-4">
        <div className="h-8 bg-earth-700 rounded w-16" />
        <div className="w-16 h-8 bg-earth-800 rounded" />
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function DashboardPage() {
  const { setCurrentModule, setSelectedTender } = useStore();
  const { data: stats, isLoading, error: statsError } = useDashboardStats();
  const { data: tenders } = useTenders();

  const pipelineCounts = stats?.pipelineCounts || {};
  const totalPipeline = Object.values(pipelineCounts).reduce((s, v) => s + v, 0) || 1;

  // Real spark data from API (7 days of activity)
  const sparkData = (stats?.weeklyActivity ?? []).map(d => ({ v: d.count }));
  const newThisWeek = stats?.newThisWeek ?? 0;

  const statCards = [
    {
      label:   'Aktywne przetargi',
      tooltip: 'Liczba przetargów w toku — od nowych po wycenione',
      value:   String(stats?.activeTenders ?? 0),
      unit:    'szt.',
      icon:    FileText,
      color:   'text-accent-primary',
      sparkColor: '#10b981',
      trend:   newThisWeek > 0 ? `+${newThisWeek} w tym tygodniu` : 'brak nowych',
    },
    {
      label:   'Wartość pipeline',
      tooltip: 'Łączna szacunkowa wartość wszystkich aktywnych przetargów',
      value:   fmtPLN(stats?.totalValue ?? 0),
      unit:    '',
      icon:    TrendingUp,
      color:   'text-accent-warning',
      sparkColor: '#F59E0B',
      trend:   stats?.totalValue ? `${(stats.totalValue / 1_000_000).toFixed(1)}M PLN` : 'brak danych',
    },
    {
      label:   'Średni score',
      tooltip: 'Średnie dopasowanie profilu firmy do przetargów (0–100%)',
      value:   `${stats?.avgScore ?? 0}%`,
      unit:    '',
      icon:    Target,
      color:   'text-accent-info',
      sparkColor: '#3B82F6',
      trend:   `top-5 > ${stats?.avgScore ?? 0}%`,
    },
    {
      label:   'Czerwone flagi',
      tooltip: 'Liczba przetargów z decyzją NO-GO lub ryzykiem blokującym',
      value:   String(stats?.redFlags ?? 0),
      unit:    'szt.',
      icon:    AlertTriangle,
      color:   'text-accent-danger',
      sparkColor: '#EF4444',
      trend:   (stats?.redFlags ?? 0) > 0 ? `${stats!.redFlags} wymagają uwagi` : 'brak alertów',
    },
  ];

  const quickActions = [
    {
      label:    'Skanuj przetargi BZP',
      desc:     'Wyszukaj nowe przetargi z rynku',
      icon:     Radar,
      module:   'zwiad' as const,
    },
    {
      label:    'Nowy kosztorys',
      desc:     'Przygotuj wycenę robót budowlanych',
      icon:     Calculator,
      module:   'kosztorys' as const,
    },
    {
      label:    'Analiza ryzyka AI',
      desc:     'Oceń ryzyko i szanse wygranej',
      icon:     Brain,
      module:   'silnik' as const,
    },
  ];

  return (
    <ErrorBoundary>
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
      className="p-6 md:p-8 max-w-7xl mx-auto space-y-6"
    >
      {/* ── Header ─────────────────────────────────────────────── */}
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-earth-50 tracking-tight">Panel główny</h1>
          <p className="text-sm text-earth-500 mt-0.5">Podsumowanie aktywności — pipeline przetargów budowlanych</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-earth-800/60 border border-earth-700/40">
          <BarChart3 className="w-3.5 h-3.5 text-accent-primary" />
          <span className="text-xs text-earth-400">{stats?.activeTenders ?? 0} aktywnych przetargów</span>
        </div>
      </motion.div>

      {/* ── Market Intelligence KPI ────────────────────────────── */}
      <motion.div variants={item}>
        <MarketKPIBar />
      </motion.div>

      {/* ── Stat Cards ─────────────────────────────────────────── */}
      <motion.div variants={item} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => <SkeletonStatCard key={i} />)
          : statCards.map((stat) => (
            <div key={stat.label} className="glass-card card-hover p-5 group">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold text-earth-400 uppercase tracking-wider">
                    {stat.label}
                  </span>
                  <Tooltip text={stat.tooltip} />
                </div>
                <stat.icon className={`w-4 h-4 ${stat.color} opacity-60 group-hover:opacity-100 transition-opacity`} />
              </div>
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="text-3xl font-bold text-earth-50 tabular-nums leading-none">
                    {stat.value}
                  </p>
                  {stat.unit && (
                    <p className="text-xs text-earth-500 mt-1 font-medium">{stat.unit}</p>
                  )}
                  <p className="text-xs text-earth-600 mt-0.5">{stat.trend}</p>
                </div>
                <div className="w-16 h-10 shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={sparkData}>
                      <Line
                        type="monotone"
                        dataKey="v"
                        stroke={stat.sparkColor}
                        strokeWidth={1.5}
                        dot={false}
                        strokeOpacity={0.7}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          ))}
      </motion.div>

      {/* ── Pipeline Bar ───────────────────────────────────────── */}
      <motion.div variants={item} className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-earth-300 uppercase tracking-wider">
            Pipeline przetargów
          </h3>
          <span className="text-xs text-earth-500 bg-earth-800/60 px-2 py-0.5 rounded">{totalPipeline} łącznie</span>
        </div>
        <div className="flex items-stretch h-10 rounded-xl overflow-hidden bg-earth-800/40 gap-px">
          {pipelineStages.map((stage) => {
            const count = pipelineCounts[stage.key] || 0;
            const pct = (count / totalPipeline) * 100;
            if (pct < 1 && count === 0) return null;
            return (
              <div
                key={stage.key}
                className="h-full flex items-center justify-center text-xs font-semibold transition-all duration-700 cursor-default"
                style={{
                  width: `${Math.max(pct, count > 0 ? 6 : 0)}%`,
                  backgroundColor: stage.color + '28',
                  borderTop: `2px solid ${stage.color}`,
                  color: stage.color,
                }}
                title={`${stage.label}: ${count} (${pct.toFixed(0)}%)`}
              >
                {count > 0 && count}
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 mt-3 flex-wrap">
          {pipelineStages.map((stage) => (
            <div key={stage.key} className="flex items-center gap-1.5 text-xs text-earth-500">
              <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: stage.color }} />
              <span className="font-medium">{stage.label}</span>
              <span className="text-earth-700">({pipelineCounts[stage.key] || 0})</span>
            </div>
          ))}
        </div>
      </motion.div>

      {/* ── Bottom grid ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* ── Recent tenders table ─── */}
        <motion.div variants={item} className="lg:col-span-2 glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-earth-300 uppercase tracking-wider">
              Ostatnie przetargi
            </h3>
            <Clock className="w-3.5 h-3.5 text-earth-600" />
          </div>
          <div className="overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-earth-800/60">
                  <th className="text-left pb-2.5 text-xs text-earth-500 font-semibold uppercase tracking-wider">Przetarg / Zamawiający</th>
                  <th className="text-right pb-2.5 text-xs text-earth-500 font-semibold uppercase tracking-wider pr-3">Wartość</th>
                  <th className="text-right pb-2.5 text-xs text-earth-500 font-semibold uppercase tracking-wider pr-3">Status</th>
                  <th className="text-right pb-2.5 text-xs text-earth-500 font-semibold uppercase tracking-wider">Score</th>
                  <th className="text-right pb-2.5 text-xs text-earth-500 font-semibold uppercase tracking-wider pl-3">Termin</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-earth-800/30">
                {(stats?.recentTenders || []).slice(0, 5).map((t, i) => {
                  const score = (t as { match_score?: number }).match_score;
                  const scorePct = score != null ? Math.round(score * 100) : null;
                  return (
                    <tr
                      key={t.id || i}
                      onClick={() => {
                        setSelectedTender(t as unknown as Parameters<typeof setSelectedTender>[0]);
                        setCurrentModule('zwiad');
                      }}
                      className="group cursor-pointer hover:bg-earth-800/30 transition-colors duration-150"
                    >
                      <td className="py-3 pr-3">
                        <p className="text-earth-100 text-sm font-medium line-clamp-1 group-hover:text-white transition-colors">
                          {t.title}
                        </p>
                        <p className="text-earth-500 text-xs mt-0.5 truncate">{t.buyer}</p>
                      </td>
                      <td className="py-3 pr-3 text-right whitespace-nowrap">
                        <span className="text-earth-200 text-sm font-semibold tabular-nums">
                          {fmtPLN((t as { value_pln?: number }).value_pln)}
                        </span>
                      </td>
                      <td className="py-3 pr-3 text-right">
                        <span className={`inline-block text-xs px-2 py-1 rounded-md font-semibold ${STATUS_COLORS[t.status] ?? 'bg-earth-700 text-earth-400'}`}>
                          {STATUS_LABELS[t.status] ?? t.status}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        {scorePct != null ? (
                          <span
                            className="text-sm font-bold tabular-nums"
                            style={{ color: matchColor(scorePct) }}
                          >
                            {scorePct}%
                          </span>
                        ) : (
                          <span className="text-earth-700 text-xs">—</span>
                        )}
                      </td>
                      <td className="py-3 text-right text-earth-400 text-sm whitespace-nowrap pl-3">
                        {fmtDate((t as { deadline_at?: string }).deadline_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {(!stats?.recentTenders || stats.recentTenders.length === 0) && (
              <div className="py-10 text-center">
                <FileText className="w-8 h-8 text-earth-700 mx-auto mb-3" />
                <p className="text-earth-400 text-sm font-medium">Brak przetargów do wyświetlenia</p>
                <p className="text-earth-600 text-xs mt-1">Uruchom skanowanie w module <strong className="text-earth-500">Zwiad</strong>, aby pobrać przetargi z BZP</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* ── Right column ─── */}
        <motion.div variants={item} className="flex flex-col gap-4">

          {/* Quick actions */}
          <div className="glass-card p-5">
            <h3 className="text-sm font-semibold text-earth-300 uppercase tracking-wider mb-4">
              Szybkie akcje
            </h3>
            <div className="space-y-2">
              {quickActions.map((action) => (
                <button
                  key={action.label}
                  onClick={() => setCurrentModule(action.module)}
                  aria-label={action.label}
                  className="w-full flex items-center gap-3 p-3 rounded-xl bg-earth-800/30 border border-earth-700/30 hover:border-accent-primary/40 hover:bg-earth-800/60 transition-all duration-200 group text-left"
                >
                  <div className="w-8 h-8 rounded-lg bg-earth-700/50 flex items-center justify-center group-hover:bg-accent-primary/15 transition-colors shrink-0">
                    <action.icon className="w-4 h-4 text-earth-400 group-hover:text-accent-primary transition-colors" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-earth-200 font-semibold group-hover:text-white transition-colors leading-tight">
                      {action.label}
                    </p>
                    <p className="text-xs text-earth-600 mt-0.5 group-hover:text-earth-500 transition-colors">
                      {action.desc}
                    </p>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-earth-600 group-hover:text-accent-primary group-hover:translate-x-0.5 transition-all shrink-0" />
                </button>
              ))}
            </div>
          </div>

          {/* Top tenders preview */}
          <div className="glass-card p-5 flex-1">
            <h3 className="text-sm font-semibold text-earth-300 uppercase tracking-wider mb-4">
              Top przetargi
            </h3>
            <div className="space-y-3">
              {(Array.isArray(tenders) ? tenders : []).slice(0, 4).map((t) => {
                const pct = Math.round(t.match_score * 100);
                return (
                  <div
                    key={t.id}
                    onClick={() => {
                      setSelectedTender(t as unknown as Parameters<typeof setSelectedTender>[0]);
                      setCurrentModule('zwiad');
                    }}
                    className="flex items-start gap-2.5 cursor-pointer group"
                  >
                    <Zap className="w-3.5 h-3.5 mt-0.5 text-accent-primary shrink-0" />
                    <span className="text-xs text-earth-400 line-clamp-2 flex-1 group-hover:text-earth-200 transition-colors leading-relaxed">
                      {t.title}
                    </span>
                    <span
                      className="text-sm font-bold shrink-0 tabular-nums"
                      style={{ color: matchColor(pct) }}
                    >
                      {pct}%
                    </span>
                  </div>
                );
              })}
              {tenders.length === 0 && (
                <div className="py-4 text-center">
                  <p className="text-xs text-earth-600">Brak przetargów</p>
                  <p className="text-xs text-earth-700 mt-0.5">Uruchom skanowanie BZP</p>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
      </motion.div>
    </ErrorBoundary>
  );
}
