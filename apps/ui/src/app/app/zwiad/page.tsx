'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  RefreshCw,
  Search,
  SearchX,
  Calendar,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { useAuthFetch } from '@/lib/api-v2';

// ─── Types ────────────────────────────────────────────────────────────────────

type TenderStatus = 'go' | 'warn' | 'nogo';
type FilterType   = 'all' | 'go' | 'warn' | 'nogo';
type SortType     = 'score' | 'deadline' | 'budget';

interface Tender {
  id: string;
  title: string;
  org: string;
  deadline: string;
  budget: number;
  score: number;
  status: TenderStatus;
  tags: string[];
}

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

// ─── Sort map ─────────────────────────────────────────────────────────────────

const sortMap: Record<SortType, string> = {
  score:    'go_score:desc',
  deadline: 'deadline:asc',
  budget:   'value_max:desc',
};

// ─── Mapping ──────────────────────────────────────────────────────────────────

function mapTender(t: BackendTender): Tender {
  const rawScore = t.go_score ?? t.match_score ?? 0.5;
  return {
    id:       String(t.id),
    title:    t.title ?? '',
    org:      t.org_name ?? '',
    deadline: t.deadline ?? '',
    budget:   t.value_max ?? t.value_min ?? 0,
    score:    Math.round(rawScore * 100),
    status:   rawScore >= 0.65 ? 'go' : rawScore >= 0.35 ? 'warn' : 'nogo',
    tags:     t.cpv_code ? [t.cpv_code.slice(0, 2)] : [],
  };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatBudget(value: number): string {
  return value.toLocaleString('pl-PL') + ' zł';
}

function formatDate(iso: string): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('pl-PL', {
    day:   '2-digit',
    month: '2-digit',
    year:  'numeric',
  });
}

function scoreBarColor(score: number): string {
  if (score > 70)  return '#10b981';
  if (score >= 40) return '#f59e0b';
  return '#ef4444';
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function TenderSkeleton() {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.04] p-4 space-y-3 animate-pulse">
      <div className="flex items-start justify-between gap-4">
        <div className="h-4 bg-white/[0.08] rounded-lg w-2/3" />
        <div className="h-5 w-12 bg-white/[0.06] rounded-full shrink-0" />
      </div>
      <div className="flex gap-4">
        <div className="h-3 bg-white/[0.05] rounded-lg w-1/3" />
        <div className="h-3 bg-white/[0.05] rounded-lg w-1/4" />
      </div>
      <div className="h-3 bg-white/[0.07] rounded-lg w-1/4" />
      <div className="h-1 bg-white/[0.06] rounded-full" />
    </div>
  );
}

// ─── TenderCard ───────────────────────────────────────────────────────────────

function TenderCard({ tender, index }: { tender: Tender; index: number }) {
  const barColor = scoreBarColor(tender.score);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.25, delay: index * 0.04, ease: 'easeOut' }}
      whileHover={{ y: -2 }}
      className="relative rounded-xl border border-white/[0.08] bg-white/[0.04] backdrop-blur-sm p-4 space-y-3
                 hover:border-[#10b981]/30 hover:bg-white/[0.07] transition-colors duration-200 cursor-pointer group"
    >
      {/* Badge — prawy górny róg */}
      <div className="absolute top-3 right-3">
        <Badge variant={tender.status} dot>
          {tender.status === 'go' ? 'GO' : tender.status === 'warn' ? 'WARN' : 'NO-GO'}
        </Badge>
      </div>

      {/* Tytuł */}
      <p className="text-[16px] font-semibold text-white leading-snug pr-24 line-clamp-2">
        {tender.title}
      </p>

      {/* Org + Termin */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="text-[13px] text-white/40">{tender.org}</span>
        <span className="flex items-center gap-1 text-[13px] text-white/40">
          <Calendar size={12} className="shrink-0" />
          {formatDate(tender.deadline)}
        </span>
      </div>

      {/* Budżet */}
      <p className="text-[14px] font-semibold text-[#10b981]">
        {formatBudget(tender.budget)}
      </p>

      {/* Score bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-white/30">Trafność</span>
          <span className="text-[11px] font-bold tabular-nums" style={{ color: barColor }}>
            {tender.score}%
          </span>
        </div>
        <div className="h-1 w-full bg-white/[0.06] rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${tender.score}%` }}
            transition={{ duration: 0.6, delay: index * 0.04 + 0.1, ease: 'easeOut' }}
            className="h-full rounded-full"
            style={{ backgroundColor: barColor }}
          />
        </div>
      </div>

      {/* Tagi */}
      <div className="flex flex-wrap gap-1.5">
        {tender.tags.map((tag) => (
          <span
            key={tag}
            className="text-[10px] font-medium px-2 py-0.5 rounded-full
                       bg-white/[0.06] text-white/40 border border-white/[0.08]"
          >
            {tag}
          </span>
        ))}
      </div>
    </motion.div>
  );
}

// ─── Główna strona ─────────────────────────────────────────────────────────────

export default function ZwiadPage() {
  const authFetch = useAuthFetch();

  const [tenders, setTenders]               = useState<Tender[]>([]);
  const [total, setTotal]                   = useState(0);
  const [loading, setLoading]               = useState(true);
  const [page, setPage]                     = useState(0);
  const [searchQuery, setSearchQuery]       = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [activeFilter, setActiveFilter]     = useState<FilterType>('all');
  const [sortBy, setSortBy]                 = useState<SortType>('score');
  const [refreshKey, setRefreshKey]         = useState(0);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce search — update API query + reset page after 300 ms
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(value);
      setPage(0);
    }, 300);
  };

  // Sort change → reset to first page
  const handleSortChange = (sort: SortType) => {
    setSortBy(sort);
    setPage(0);
  };

  // ─── API fetch ────────────────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const params = new URLSearchParams({ limit: '20', offset: String(page * 20) });
    if (debouncedQuery) params.set('q', debouncedQuery);
    params.set('sort', sortMap[sortBy]);

    authFetch(`/api/v2/tenders?${params}`)
      .then((d: { items?: BackendTender[]; total?: number }) => {
        if (!cancelled) {
          setTenders((d.items ?? []).map(mapTender));
          setTotal(d.total ?? 0);
        }
      })
      .catch(() => {
        if (!cancelled) { setTenders([]); setTotal(0); }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [authFetch, page, debouncedQuery, sortBy, refreshKey]);

  // ─── Derived ──────────────────────────────────────────────────────────────

  const displayed = activeFilter === 'all'
    ? tenders
    : tenders.filter((t) => t.status === activeFilter);

  const totalPages = Math.ceil(total / 20);

  const filterPills: { key: FilterType; label: string }[] = [
    { key: 'all',  label: 'Wszystkie' },
    { key: 'go',   label: 'GO' },
    { key: 'warn', label: 'WARN' },
    { key: 'nogo', label: 'NO-GO' },
  ];

  const sortOptions: { key: SortType; label: string }[] = [
    { key: 'score',    label: 'Trafność' },
    { key: 'deadline', label: 'Termin' },
    { key: 'budget',   label: 'Budżet' },
  ];

  return (
    <div className="min-h-screen bg-[#050508] text-white">
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex items-start justify-between gap-4"
        >
          <div>
            <h1 className="text-[32px] font-bold text-white leading-tight">
              Zwiad Przetargowy
            </h1>
            <p className="text-[14px] text-white/40 mt-1">
              {loading ? 'Ładowanie…' : `${total} aktywnych ogłoszeń`}
            </p>
          </div>

          <button type="button"
            onClick={() => { setRefreshKey((k) => k + 1); }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-white/10
                       bg-white/[0.05] text-white/60 text-sm font-medium
                       hover:bg-white/[0.09] hover:text-white hover:border-[#10b981]/30
                       transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150 mt-1"
          >
            <RefreshCw size={14} />
            Odśwież
          </button>
        </motion.div>

        {/* ── Filtry ─────────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
          className="sticky top-4 z-20 rounded-xl border border-white/[0.08]
                     bg-[#050508]/80 backdrop-blur-xl p-4 space-y-3 shadow-lg"
        >
          {/* Search */}
          <div className="relative">
            <Search
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Szukaj przetargów, zamawiających, tagów…"
              className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-white/[0.08]
                         bg-white/[0.04] text-sm text-white placeholder-white/25
                         focus:outline-none focus:border-[#10b981]/40 focus:bg-white/[0.07]
                         transition-colors duration-150"
            />
          </div>

          {/* Filtry + Sort */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            {/* Filtr pills */}
            <div className="flex flex-wrap gap-2">
              {filterPills.map(({ key, label }) => (
                <button type="button"
                  key={key}
                  onClick={() => setActiveFilter(key)}
                  className={`px-3 py-1 rounded-full text-[12px] font-semibold border transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150
                    ${activeFilter === key
                      ? 'bg-[#10b981] border-[#10b981] text-[#050508]'
                      : 'bg-white/[0.04] border-white/[0.08] text-white/50 hover:text-white hover:border-white/20'
                    }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Sort */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-white/30 font-medium">Sortuj:</span>
              <div className="flex gap-1.5">
                {sortOptions.map(({ key, label }) => (
                  <button type="button"
                    key={key}
                    onClick={() => handleSortChange(key)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150
                      ${sortBy === key
                        ? 'bg-[#10b981]/15 border-[#10b981]/30 text-[#10b981]'
                        : 'bg-transparent border-white/[0.06] text-white/40 hover:text-white/70 hover:border-white/15'
                      }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* ── Lista ──────────────────────────────────────────────────────── */}
        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => <TenderSkeleton key={i} />)}
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
            {displayed.length > 0 ? (
              <motion.div
                key={`list-${page}-${sortBy}-${debouncedQuery}-${refreshKey}`}
                className="space-y-3"
              >
                {displayed.map((tender, i) => (
                  <TenderCard key={tender.id} tender={tender} index={i} />
                ))}
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="flex flex-col items-center justify-center py-24 space-y-4"
              >
                <div className="w-16 h-16 rounded-2xl border border-white/[0.08] bg-white/[0.03]
                                flex items-center justify-center">
                  <SearchX size={28} className="text-white/20" />
                </div>
                <p className="text-[15px] text-white/40 font-medium">
                  Brak przetargów spełniających kryteria
                </p>
                <button type="button"
                  onClick={() => {
                    handleSearchChange('');
                    setActiveFilter('all');
                  }}
                  className="px-4 py-2 rounded-xl border border-[#10b981]/30 bg-[#10b981]/10
                             text-[13px] font-medium text-[#10b981]
                             hover:bg-[#10b981]/20 transition-colors duration-150"
                >
                  Resetuj filtry
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        )}

        {/* ── Pagination ─────────────────────────────────────────────────── */}
        {!loading && totalPages > 1 && (
          <div className="flex items-center justify-between gap-4 pt-2">
            <button
              type="button"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-white/10
                         bg-white/[0.04] text-sm text-white/60 font-medium
                         hover:bg-white/[0.08] hover:text-white
                         disabled:opacity-30 disabled:cursor-not-allowed
                         transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150"
            >
              <ChevronLeft size={14} />
              Poprzednia
            </button>

            <span className="text-[13px] text-white/40 tabular-nums">
              {page + 1} / {totalPages}
            </span>

            <button
              type="button"
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-white/10
                         bg-white/[0.04] text-sm text-white/60 font-medium
                         hover:bg-white/[0.08] hover:text-white
                         disabled:opacity-30 disabled:cursor-not-allowed
                         transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150"
            >
              Następna
              <ChevronRight size={14} />
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
