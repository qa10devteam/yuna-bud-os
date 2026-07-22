'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import {
  Search, ChevronDown, ChevronLeft, ChevronRight,
  CheckCircle2, BarChart3, Brain, Sparkles, Activity,
  ExternalLink, LayoutList, LayoutGrid, Loader2,
} from 'lucide-react';
import { GlassCard }   from '@/components/ui/GlassCard';
import { Button }      from '@/components/ui/Button';
import { PageShell }   from '@/components/PageShell';
import { useAuthFetch } from '@/lib/api-v2';
import { useStore }     from '@/store/useStore';
import { PageTransition } from '@/components/ui/PageTransition';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Przetarg {
  id: number | string;
  title: string;
  buyer: string;
  deadline: string;
  value: string;
  valueSortKey: number;
  score: number;
  verdict: 'GO' | 'UWAGA' | 'NO-GO';
  wojewodztwo: string;
  branza: string;
}

// Backend shape from GET /api/v2/tenders
interface BackendTender {
  id: number | string;
  title: string | null;
  org_name: string | null;
  value_min: number | null;
  value_max: number | null;
  deadline: string | null;
  cpv_code: string | null;
  province: string | null;
  source: string | null;
  go_score: number | null;
  match_score: number | null;
  status: string | null;
  pipeline_status: string | null;
  created_at: string | null;
}

// ─── CPV → Branża mapping ─────────────────────────────────────────────────────

function cpvToBranza(cpv: string | null): string {
  if (!cpv) return 'Kubatura';
  const n = cpv.replace(/\D/g, '');
  if (n.startsWith('4523')) return 'Drogi';
  if (n.startsWith('4522')) return 'Mosty';
  if (n.startsWith('45232') || n.startsWith('45330') || n.startsWith('45231')) return 'Wod-Kan';
  if (n.startsWith('45234') || n.startsWith('45213')) return 'Kolej';
  if (n.startsWith('4531') || n.startsWith('45316')) return 'Sieci';
  return 'Kubatura';
}

// ─── Province capitalizer ─────────────────────────────────────────────────────

function toProvinceLabel(raw: string | null): string {
  if (!raw) return 'Nieznane';
  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
}

// ─── Format PLN ───────────────────────────────────────────────────────────────

function fmtValueStr(v: number | null): string {
  if (v == null) return '—';
  if (v >= 1_000_000_000) return (v / 1_000_000_000).toFixed(1).replace('.0', '') + ' mld PLN';
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1).replace('.0', '') + ' mln PLN';
  if (v >= 1_000) return Math.round(v / 1_000) + ' tys PLN';
  return v.toFixed(0) + ' PLN';
}

// ─── Mapping ──────────────────────────────────────────────────────────────────

function mapBackendToPrezetarg(t: BackendTender): Przetarg {
  const rawScore = t.go_score ?? t.match_score ?? 0.5;
  const verdict: 'GO' | 'UWAGA' | 'NO-GO' =
    rawScore >= 0.65 ? 'GO' : rawScore >= 0.35 ? 'UWAGA' : 'NO-GO';
  const valueSortKey = t.value_max ?? t.value_min ?? 0;

  return {
    id:           t.id,
    title:        t.title ?? '',
    buyer:        t.org_name ?? '—',
    deadline:     t.deadline ?? '',
    value:        fmtValueStr(valueSortKey),
    valueSortKey,
    score:        Math.round(rawScore * 100),
    verdict,
    wojewodztwo:  toProvinceLabel(t.province),
    branza:       cpvToBranza(t.cpv_code),
  };
}

// ─── Statics ──────────────────────────────────────────────────────────────────

const WOJEWODZTWA = [
  'Wszystkie',
  'Dolnośląskie',
  'Kujawsko-Pomorskie',
  'Lubelskie',
  'Lubuskie',
  'Łódzkie',
  'Małopolskie',
  'Mazowieckie',
  'Opolskie',
  'Podkarpackie',
  'Podlaskie',
  'Pomorskie',
  'Śląskie',
  'Świętokrzyskie',
  'Warmińsko-Mazurskie',
  'Wielkopolskie',
  'Zachodniopomorskie',
];

const BRANZE  = ['Wszystkie', 'Drogi', 'Mosty', 'Wod-Kan', 'Kubatura', 'Sieci', 'Kolej'];
const STATUSY = ['Wszystkie', 'GO', 'UWAGA', 'NO-GO'];

const CPV_CHIPS = ['Drogi', 'Wod-Kan', 'Kubatura', 'Mosty', 'Kolej'] as const;

// ─── Score ring (circular progress SVG) ───────────────────────────────────────

function ScoreRing({ score }: { score: number }) {
  const color =
    score >= 70 ? '#10b981'
    : score >= 40 ? '#eab308'
    : '#ef4444';

  const radius = 12;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center w-9 h-9 shrink-0">
      <svg className="w-9 h-9 -rotate-90" viewBox="0 0 32 32">
        <circle
          cx="16" cy="16" r={radius}
          fill="none" stroke="currentColor" strokeWidth="2.5"
          className="text-white/[0.06]"
        />
        <circle
          cx="16" cy="16" r={radius}
          fill="none" stroke={color} strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center font-mono text-[10px] font-bold tabular-nums"
        style={{ color }}
      >
        {score}
      </span>
    </div>
  );
}

// ─── Verdict badge ────────────────────────────────────────────────────────────

function VerdictBadge({ verdict }: { verdict: 'GO' | 'UWAGA' | 'NO-GO' }) {
  const styles = {
    'GO':    'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    'UWAGA': 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    'NO-GO': 'bg-red-500/15 text-red-400 border-red-500/30',
  } as const;

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${styles[verdict]}`}>
      {verdict}
    </span>
  );
}

// ─── Glass Select ─────────────────────────────────────────────────────────────

interface GlassSelectProps {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  label: string;
}

function GlassSelect({ value, onChange, options, label }: GlassSelectProps) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={[
          'appearance-none w-full pl-3 pr-8 py-2 rounded-lg text-sm text-slate-200',
          'bg-white/[0.05] border border-white/[0.09]',
          'focus:outline-none focus:border-emerald-500/50 focus:bg-white/[0.08]',
          'transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200 cursor-pointer',
        ].join(' ')}
        aria-label={label}
      >
        {options.map((o) => (
          <option key={o} value={o} className="bg-slate-900 text-slate-200">
            {o}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
    </div>
  );
}

// ─── KPI Badge ────────────────────────────────────────────────────────────────

interface KpiBadgeProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  color?: string;
}

function KpiBadge({ icon, label, value, color = 'text-slate-200' }: KpiBadgeProps) {
  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.07]">
      <span className="text-slate-500 w-4 h-4 shrink-0">{icon}</span>
      <span className="text-slate-500 text-xs whitespace-nowrap">{label}:</span>
      <span className={`text-xs font-semibold tabular-nums ${color}`}>{value}</span>
    </div>
  );
}

// ─── Skeleton row ─────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr className="border-b border-white/[0.04] animate-pulse">
      <td className="pl-5 py-3.5 pr-4">
        <div className="h-3.5 bg-white/[0.07] rounded w-3/4 mb-1" />
        <div className="h-2.5 bg-white/[0.04] rounded w-1/3" />
      </td>
      <td className="py-3.5 pr-4"><div className="h-3 bg-white/[0.06] rounded w-24" /></td>
      <td className="py-3.5 pr-4"><div className="h-3 bg-white/[0.05] rounded w-20" /></td>
      <td className="py-3.5 pr-4 text-right"><div className="h-3 bg-white/[0.06] rounded w-20 ml-auto" /></td>
      <td className="py-3.5 pr-4"><div className="mx-auto w-9 h-9 rounded-full bg-white/[0.05]" /></td>
      <td className="py-3.5 pr-4"><div className="mx-auto h-5 bg-white/[0.05] rounded-full w-14" /></td>
      <td className="py-3.5 pr-5"><div className="mx-auto h-7 bg-white/[0.04] rounded-lg w-20" /></td>
    </tr>
  );
}

// ─── Kanban Card ──────────────────────────────────────────────────────────────

function KanbanCard({ p }: { p: Przetarg }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="p-3 rounded-lg bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.06] transition-colors"
    >
      <p className="text-sm font-medium text-slate-200 line-clamp-2 leading-snug mb-2">
        {p.title}
      </p>
      <p className="text-[11px] text-slate-500 mb-2">{p.buyer}</p>
      <div className="flex items-center justify-between">
        <ScoreRing score={p.score} />
        <span className="font-mono text-[11px] text-slate-400 tabular-nums">{p.value}</span>
      </div>
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.06]">
        <span className="text-[10px] text-slate-500">{p.deadline}</span>
        <span className="text-[10px] text-slate-500">{p.branza}</span>
      </div>
    </motion.div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function ZwiadPage() {
  const shouldReduceMotion = useReducedMotion();
  const authFetch = useAuthFetch();
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { } = useStore();

  // ── State ─────────────────────────────────────────────────────────────────
  const [tenders, setTenders]         = useState<Przetarg[]>([]);
  const [apiTotal, setApiTotal]       = useState(0);
  const [loading, setLoading]         = useState(true);

  // Search & filters
  const [search, setSearch]           = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [woj, setWoj]                 = useState('Wszystkie');
  const [branza, setBranza]           = useState('Wszystkie');
  const [status, setStatus]           = useState('Wszystkie');
  const [page, setPage]               = useState(1);
  const [viewMode, setViewMode]       = useState<'list' | 'kanban'>('list');
  const [cpvFilters, setCpvFilters]   = useState<Set<string>>(new Set());

  const PER_PAGE = 8;

  // ── Debounced search ──────────────────────────────────────────────────────
  const handleSearchChange = (value: string) => {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(value);
      setPage(1);
    }, 300);
  };

  // ── CPV toggle ────────────────────────────────────────────────────────────
  const toggleCpv = useCallback((chip: string) => {
    setCpvFilters((prev) => {
      const next = new Set(prev);
      if (next.has(chip)) next.delete(chip);
      else next.add(chip);
      return next;
    });
  }, []);

  // ── API fetch ─────────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const params = new URLSearchParams({ limit: '100', offset: '0', sort: 'go_score:desc' });
    if (debouncedSearch) params.set('q', debouncedSearch);

    authFetch(`/api/v2/tenders?${params}`)
      .then((d: { items?: BackendTender[]; total?: number }) => {
        if (!cancelled) {
          setTenders((d.items ?? []).map(mapBackendToPrezetarg));
          setApiTotal(d.total ?? 0);
        }
      })
      .catch(() => {
        if (!cancelled) { setTenders([]); setApiTotal(0); }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [authFetch, debouncedSearch]);

  // ── Reset page on filter change ───────────────────────────────────────────
  useEffect(() => { setPage(1); }, [woj, branza, status, cpvFilters]);

  // ── Client-side filter ────────────────────────────────────────────────────
  const filtered = tenders.filter((p) => {
    const matchW   = woj === 'Wszystkie'    || p.wojewodztwo === woj;
    const matchB   = branza === 'Wszystkie' || p.branza === branza;
    const matchS   = status === 'Wszystkie' || p.verdict === status;
    const matchCpv = cpvFilters.size === 0  || cpvFilters.has(p.branza);
    return matchW && matchB && matchS && matchCpv;
  });

  const totalPages = Math.ceil(filtered.length / PER_PAGE);
  const paginated  = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  // ── KPIs (derived from real data) ────────────────────────────────────────
  const kpiAktywne  = apiTotal;
  const kpiGo       = tenders.filter((p) => p.verdict === 'GO').length;
  const kpiAvgScore = tenders.length > 0
    ? Math.round(tenders.reduce((s, p) => s + p.score, 0) / tenders.length)
    : 0;

  // ── Kanban columns ────────────────────────────────────────────────────────
  const kanbanColumns = [
    { key: 'GO'    as const, label: 'GO',    color: 'border-emerald-500/40' },
    { key: 'UWAGA' as const, label: 'UWAGA', color: 'border-amber-500/40'   },
    { key: 'NO-GO' as const, label: 'NO-GO', color: 'border-red-500/40'     },
  ];

  // ── Animation variants ────────────────────────────────────────────────────
  const rowVariants = {
    hidden:  { opacity: 0, y: shouldReduceMotion ? 0 : 8 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1] as [number,number,number,number] } },
  };

  const fadeIn = {
    hidden:  { opacity: 0, y: shouldReduceMotion ? 0 : 12 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] as [number,number,number,number] } },
  };

  // ──────────────────────────────────────────────────────────────────────────

  return (
    <PageShell title="Zwiad AI" subtitle="Monitoring przetargów publicznych">
      <div className="flex flex-col gap-6 px-1">

        {/* ── Header ─────────────────────────────────────────────────────────── */}
        <motion.div
          variants={fadeIn}
          initial="hidden"
          animate="visible"
          className="flex flex-col gap-3"
        >
          {/* Title row */}
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <Brain className="w-6 h-6 text-emerald-400 shrink-0" />
                <h1 className="text-[28px] font-bold text-white leading-none tracking-tight">
                  Zwiad AI
                </h1>
              </div>
              <p className="text-sm text-slate-400 pl-8">
                Monitoring{' '}
                {loading ? (
                  <span className="inline-flex items-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin" />
                  </span>
                ) : (
                  <span className="text-slate-200 font-semibold tabular-nums">
                    {kpiAktywne.toLocaleString('pl-PL')}
                  </span>
                )}{' '}
                przetargów publicznych
              </p>
            </div>

            {/* View toggle + KPI badges */}
            <div className="flex flex-wrap items-center gap-2 sm:justify-end">
              {/* List/Kanban toggle */}
              <div className="flex items-center rounded-lg border border-white/[0.09] bg-white/[0.04] p-0.5">
                <button
                  type="button"
                  onClick={() => setViewMode('list')}
                  className={[
                    'p-1.5 rounded-md transition-colors',
                    viewMode === 'list'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'text-slate-500 hover:text-slate-300',
                  ].join(' ')}
                  aria-label="Widok listy"
                >
                  <LayoutList className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('kanban')}
                  className={[
                    'p-1.5 rounded-md transition-colors',
                    viewMode === 'kanban'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'text-slate-500 hover:text-slate-300',
                  ].join(' ')}
                  aria-label="Widok kanban"
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
              </div>

              <KpiBadge
                icon={<Activity className="w-4 h-4" />}
                label="Aktywne"
                value={loading ? '…' : kpiAktywne}
                color="text-slate-200"
              />
              <KpiBadge
                icon={<Sparkles className="w-4 h-4" />}
                label="Załadowano"
                value={loading ? '…' : tenders.length}
                color="text-sky-400"
              />
              <KpiBadge
                icon={<CheckCircle2 className="w-4 h-4" />}
                label="GO"
                value={loading ? '…' : kpiGo}
                color="text-emerald-400"
              />
              <KpiBadge
                icon={<BarChart3 className="w-4 h-4" />}
                label="Avg score"
                value={loading ? '…' : kpiAvgScore}
                color="text-indigo-400"
              />
            </div>
          </div>
        </motion.div>

        {/* ── Search + Filters ────────────────────────────────────────────────── */}
        <motion.div
          variants={fadeIn}
          initial="hidden"
          animate="visible"
          className="flex flex-col gap-3"
        >
          {/* Search */}
          <div className="relative">
            <Search
              className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Szukaj przetargów, zamawiających..."
              className={[
                'w-full pl-10 pr-4 py-2.5 rounded-lg text-sm text-slate-200',
                'bg-white/[0.05] border border-white/[0.09]',
                'placeholder:text-slate-500',
                'focus:outline-none focus:border-emerald-500/50 focus:bg-white/[0.08]',
                'transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200',
              ].join(' ')}
            />
            {loading && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 animate-spin" />
            )}
          </div>

          {/* CPV Chips inline filters */}
          <div className="flex flex-wrap gap-2">
            {CPV_CHIPS.map((chip) => {
              const active = cpvFilters.has(chip);
              return (
                <button
                  key={chip}
                  type="button"
                  onClick={() => toggleCpv(chip)}
                  className={[
                    'px-3 py-1.5 rounded-full text-xs font-medium border transition-colors',
                    active
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400'
                      : 'bg-white/[0.04] border-white/[0.09] text-slate-400 hover:text-slate-200 hover:border-white/[0.15]',
                  ].join(' ')}
                >
                  {chip}
                </button>
              );
            })}
          </div>

          {/* Filter dropdowns */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <GlassSelect value={woj}    onChange={setWoj}    options={WOJEWODZTWA} label="Województwo" />
            <GlassSelect value={branza} onChange={setBranza} options={BRANZE}      label="Branża" />
            <GlassSelect value={status} onChange={setStatus} options={STATUSY}     label="Status" />
          </div>
        </motion.div>

        {/* ── Content: List or Kanban ──────────────────────────────────────────── */}
        {viewMode === 'list' ? (
          /* ── Table view ─────────────────────────────────────────────────────── */
          <motion.div
            variants={fadeIn}
            initial="hidden"
            animate="visible"
          >
            <GlassCard className="overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  {/* Head */}
                  <thead>
                    <tr className="border-b border-white/[0.07]">
                      {[
                        { label: 'Tytuł',        cls: 'text-left pl-5 py-3 w-[30%] min-w-[200px]' },
                        { label: 'Zamawiający',   cls: 'text-left py-3 min-w-[130px]' },
                        { label: 'Deadline',      cls: 'text-left py-3 min-w-[100px]' },
                        { label: 'Wartość',       cls: 'text-right py-3 min-w-[110px]' },
                        { label: 'AI Score',      cls: 'text-center py-3 min-w-[80px]' },
                        { label: 'Status',        cls: 'text-center py-3 min-w-[80px]' },
                        { label: 'Akcja',         cls: 'text-center py-3 pr-5 min-w-[90px]' },
                      ].map(({ label, cls }) => (
                        <th
                          key={label}
                          className={`${cls} text-[11px] font-semibold uppercase tracking-wider text-slate-500`}
                        >
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>

                  {/* Body */}
                  <tbody>
                    {loading ? (
                      [0, 1, 2].map((i) => <SkeletonRow key={i} />)
                    ) : paginated.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-16 text-center text-slate-500 text-sm">
                          Brak wyników dla podanych filtrów.
                        </td>
                      </tr>
                    ) : (
                      paginated.map((p) => (
                        <motion.tr
                          key={p.id}
                          variants={rowVariants}
                          initial="hidden"
                          animate="visible"
                          className={[
                            'group border-b border-white/[0.04] last:border-0',
                            'hover:bg-white/[0.03] transition-colors duration-150',
                          ].join(' ')}
                        >
                          {/* Tytuł */}
                          <td className="pl-5 py-3.5 pr-4">
                            <span
                              className="font-medium text-slate-200 group-hover:text-white transition-colors line-clamp-2 leading-snug"
                              title={p.title}
                            >
                              {p.title}
                            </span>
                            <span className="block mt-0.5 text-[11px] text-slate-500">
                              {p.wojewodztwo} · {p.branza}
                            </span>
                          </td>

                          {/* Zamawiający */}
                          <td className="py-3.5 pr-4">
                            <span className="text-slate-300 whitespace-nowrap">{p.buyer}</span>
                          </td>

                          {/* Deadline */}
                          <td className="py-3.5 pr-4">
                            <span className="font-mono text-slate-400 text-xs tabular-nums whitespace-nowrap">
                              {p.deadline}
                            </span>
                          </td>

                          {/* Wartość */}
                          <td className="py-3.5 pr-4 text-right">
                            <span className="font-mono text-slate-200 text-xs tabular-nums whitespace-nowrap">
                              {p.value}
                            </span>
                          </td>

                          {/* AI Score */}
                          <td className="py-3.5 pr-4">
                            <div className="flex justify-center">
                              <ScoreRing score={p.score} />
                            </div>
                          </td>

                          {/* Status */}
                          <td className="py-3.5 pr-4">
                            <div className="flex justify-center">
                              <VerdictBadge verdict={p.verdict} />
                            </div>
                          </td>

                          {/* Akcja */}
                          <td className="py-3.5 pr-5">
                            <div className="flex justify-center">
                              <Button
                                variant="ghost"
                                size="sm"
                                iconRight={<ExternalLink className="w-3 h-3" />}
                                className="text-emerald-400 border-emerald-500/30 hover:border-emerald-400/60 hover:text-emerald-300 text-xs"
                              >
                                Analizuj
                              </Button>
                            </div>
                          </td>
                        </motion.tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* ── Pagination footer ───────────────────────────────────────── */}
              {!loading && (
                <div className="flex items-center justify-between px-5 py-3 border-t border-white/[0.07]">
                  <span className="text-xs text-slate-500 tabular-nums">
                    {filtered.length === 0 ? (
                      'Brak wyników'
                    ) : (
                      <>
                        Pokazuje{' '}
                        <span className="text-slate-300 font-medium">
                          {(page - 1) * PER_PAGE + 1}–
                          {Math.min(page * PER_PAGE, filtered.length)}
                        </span>{' '}
                        z{' '}
                        <span className="text-slate-300 font-medium">
                          {filtered.length < tenders.length
                            ? filtered.length
                            : kpiAktywne.toLocaleString('pl-PL')}
                        </span>{' '}
                        przetargów
                      </>
                    )}
                  </span>

                  {totalPages > 1 && (
                    <div className="flex items-center gap-1">
                      <button type="button"
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page === 1}
                        aria-label="Poprzednia strona"
                        className={[
                          'p-1.5 rounded-md transition-colors',
                          page === 1
                            ? 'text-slate-700 cursor-not-allowed'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.06]',
                        ].join(' ')}
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>

                      {/* Page pills */}
                      {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                        const pg = totalPages <= 5
                          ? i + 1
                          : page <= 3
                            ? i + 1
                            : page >= totalPages - 2
                              ? totalPages - 4 + i
                              : page - 2 + i;
                        return (
                          <button type="button"
                            key={pg}
                            onClick={() => setPage(pg)}
                            className={[
                              'min-w-[28px] h-7 px-1.5 rounded-md text-xs font-medium transition-colors tabular-nums',
                              pg === page
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.06]',
                            ].join(' ')}
                          >
                            {pg}
                          </button>
                        );
                      })}

                      <button type="button"
                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages || totalPages === 0}
                        aria-label="Następna strona"
                        className={[
                          'p-1.5 rounded-md transition-colors',
                          page === totalPages || totalPages === 0
                            ? 'text-slate-700 cursor-not-allowed'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.06]',
                        ].join(' ')}
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
              )}
            </GlassCard>
          </motion.div>
        ) : (
          /* ── Kanban view ────────────────────────────────────────────────────── */
          <motion.div
            variants={fadeIn}
            initial="hidden"
            animate="visible"
            className="grid grid-cols-1 md:grid-cols-3 gap-4"
          >
            {loading ? (
              /* Kanban skeleton */
              [0, 1, 2].map((i) => (
                <div key={i} className="flex flex-col gap-3 rounded-xl border-t-2 border-white/[0.08] p-1 animate-pulse">
                  <div className="flex items-center justify-between px-2 pt-2">
                    <div className="h-5 bg-white/[0.07] rounded-full w-16" />
                    <div className="h-4 bg-white/[0.05] rounded w-6" />
                  </div>
                  {[0, 1].map((j) => (
                    <div key={j} className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.06] mx-1">
                      <div className="h-3 bg-white/[0.06] rounded w-full mb-1" />
                      <div className="h-3 bg-white/[0.04] rounded w-3/4 mb-3" />
                      <div className="h-2 bg-white/[0.04] rounded w-1/2" />
                    </div>
                  ))}
                </div>
              ))
            ) : (
              kanbanColumns.map((col) => {
                const items = filtered.filter((p) => p.verdict === col.key);
                return (
                  <div key={col.key} className={`flex flex-col gap-3 rounded-xl border-t-2 ${col.color} p-1`}>
                    <div className="flex items-center justify-between px-2 pt-2">
                      <VerdictBadge verdict={col.key} />
                      <span className="text-[11px] text-slate-500 font-medium tabular-nums">
                        {items.length}
                      </span>
                    </div>
                    <div className="flex flex-col gap-2 px-1 pb-2">
                      {items.length === 0 ? (
                        <p className="text-center text-slate-600 text-xs py-8">Brak</p>
                      ) : (
                        items.map((p) => <KanbanCard key={p.id} p={p} />)
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </motion.div>
        )}

      </div>
    </PageShell>
  );
}
