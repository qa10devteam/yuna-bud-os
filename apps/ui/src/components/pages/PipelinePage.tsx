'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Plus, LayoutGrid, CalendarDays, Search, X, TrendingUp,
  Loader2, DollarSign, Target, Activity, Inbox,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';
import { GlassCard } from '@/components/ui/GlassCard';
import { MetricCard } from '@/components/ui/MetricCard';
import { Button } from '@/components/ui/Button';
import { PageShell } from '@/components/PageShell';
import type { Tender } from '@/types';
import { PageTransition } from '@/components/ui/PageTransition';

// ── Types ─────────────────────────────────────────────────────────────────────

interface TenderItem {
  id: string;
  title: string;
  buyer: string | null;
  cpv: string[] | null;
  value_pln: number | null;
  match_score: number | null;
  pipeline_status: string;
  deadline_at: string | null;
  published_at?: string | null;
}

// Backend shape from GET /api/v2/tenders
interface BackendTenderItem {
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

interface PipelineKPI {
  active: number;
  pipeline_value: number;
  win_rate_mtd: number;
}

// ── Column config — matches required pipeline_status values ──────────────────

const COLUMNS = [
  { key: 'scouting',  label: 'Rozpoznanie',  color: '#94A3B8', ring: 'rgba(148,163,184,0.35)' },
  { key: 'qualified', label: 'Zakwalif.',    color: '#3B82F6', ring: 'rgba(59,130,246,0.35)' },
  { key: 'offer',     label: 'Oferta',       color: '#EAB308', ring: 'rgba(234,179,8,0.35)' },
  { key: 'won',       label: 'Wygrany ✓',    color: '#22C55E', ring: 'rgba(34,197,94,0.35)' },
  { key: 'lost',      label: 'Przegrany ✗',  color: '#EF4444', ring: 'rgba(239,68,68,0.35)' },
] as const;

const COL_COLOR_MAP: Record<string, string> = Object.fromEntries(
  COLUMNS.map(c => [c.key, c.color])
);

// ── Map backend shape → TenderItem ───────────────────────────────────────────

function mapBackendTender(t: BackendTenderItem): TenderItem {
  return {
    id:              String(t.id),
    title:           t.title ?? '',
    buyer:           t.org_name ?? null,
    cpv:             t.cpv_code ? [t.cpv_code] : null,
    value_pln:       t.value_max ?? t.value_min ?? null,
    match_score:     t.go_score ?? t.match_score ?? null,
    pipeline_status: t.pipeline_status ?? 'scouting',
    deadline_at:     t.deadline ?? null,
  };
}

// ── Formatters ────────────────────────────────────────────────────────────────

function fmtPLN(v: number | null | undefined): string {
  if (v == null) return '—';
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1).replace('.0', '') + ' M zł';
  if (v >= 1_000) return (v / 1_000).toFixed(0) + ' tys. zł';
  return v.toFixed(0) + ' zł';
}

function daysUntil(d: string | null): number | null {
  if (!d) return null;
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86_400_000);
}

// ── Score badge (SVG circle) ──────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return null;
  const pct = Math.round(score > 1 ? score : score * 100);
  const color = pct >= 80 ? '#22C55E' : pct >= 60 ? '#EAB308' : '#EF4444';
  const r = 10, cx = 12, cy = 12;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" className="shrink-0">
      <circle cx={cx} cy={cy} r={r} stroke="#1E293B" strokeWidth="2.5" fill="none" />
      <circle
        cx={cx} cy={cy} r={r} stroke={color} strokeWidth="2.5" fill="none"
        strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
      />
      <text x={cx} y={cy + 3.5} textAnchor="middle" fontSize="6.5" fontWeight="700" fill={color}>
        {pct}
      </text>
    </svg>
  );
}

// ── Kanban Card ───────────────────────────────────────────────────────────────

function KanbanCard({
  tender, colColor, onDragStart, onDragEnd, onClick,
}: {
  tender: TenderItem;
  colColor: string;
  onDragStart: (e: React.DragEvent<HTMLDivElement>, t: TenderItem) => void;
  onDragEnd: () => void;
  onClick: (t: TenderItem) => void;
}) {
  const days = daysUntil(tender.deadline_at);
  const isUrgent = days !== null && days >= 0 && days <= 7;
  const cpvTag = tender.cpv?.[0]?.slice(0, 8) ?? null;

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, tender)}
      onDragEnd={onDragEnd}
      onClick={() => onClick(tender)}
      className={[
        'rounded-xl bg-slate-800/80 border border-slate-700/50 p-3 cursor-grab active:cursor-grabbing relative',
        'hover:border-emerald-500/30 transition-colors duration-150 group select-none',
        isUrgent ? 'border-l-2 border-l-red-500/60' : '',
      ].join(' ')}
    >
      {/* Title (2 lines max) */}
      <p className="text-slate-100 text-xs font-medium leading-snug line-clamp-2 pr-8">
        {tender.title}
      </p>

      {/* Buyer */}
      <p className="text-slate-500 text-[10px] mt-1 truncate">{tender.buyer ?? '—'}</p>

      {/* CPV / type badge */}
      {cpvTag && (
        <div className="mt-1.5">
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-400 font-mono">
            {cpvTag}
          </span>
        </div>
      )}

      {/* Value */}
      <p className="text-slate-200 text-[11px] font-semibold font-mono tabular-nums mt-2">
        {fmtPLN(tender.value_pln)}
      </p>

      {/* Bottom row: deadline + score */}
      <div className="flex items-center justify-between mt-1.5 gap-1">
        <div className="flex-1 min-w-0">
          {days !== null && days >= 0 && (
            <span className={[
              'text-xs text-slate-400',
              days <= 3 ? 'text-red-400' : days <= 7 ? 'text-amber-400' : '',
            ].join(' ')}>
              {days <= 3 ? '⚠ ' : ''}{days}d
            </span>
          )}
          {days !== null && days < 0 && (
            <span className="text-xs text-red-400 font-mono">{Math.abs(days)}d po term.</span>
          )}
        </div>
        <ScoreBadge score={tender.match_score} />
      </div>
    </div>
  );
}

// ── Kanban Column ─────────────────────────────────────────────────────────────

function KanbanColumn({
  col, tenders, loading, isDragOver,
  onDrop, onDragOver, onDragEnter, onDragLeave,
  onCardClick, onCardDragStart, onCardDragEnd,
}: {
  col: typeof COLUMNS[number];
  tenders: TenderItem[];
  loading: boolean;
  isDragOver: boolean;
  onDrop: (e: React.DragEvent<HTMLDivElement>, key: string) => void;
  onDragOver: (e: React.DragEvent<HTMLDivElement>) => void;
  onDragEnter: (e: React.DragEvent<HTMLDivElement>, key: string) => void;
  onDragLeave: (e: React.DragEvent<HTMLDivElement>) => void;
  onCardClick: (t: TenderItem) => void;
  onCardDragStart: (e: React.DragEvent<HTMLDivElement>, t: TenderItem) => void;
  onCardDragEnd: () => void;
}) {
  const totalVal = tenders.reduce((s, t) => s + (t.value_pln ?? 0), 0);
  // Dynamic colors are intentionally inline — col.color and col.ring are runtime values
  const colStyle: React.CSSProperties = isDragOver
    ? { boxShadow: `0 0 0 2px ${col.ring}, inset 0 0 20px ${col.ring}` }
    : {};

  return (
    <div
      onDrop={(e) => onDrop(e, col.key)}
      onDragOver={onDragOver}
      onDragEnter={(e) => onDragEnter(e, col.key)}
      onDragLeave={onDragLeave}
      style={colStyle}
      className={[
        'flex flex-col w-[220px] shrink-0 rounded-2xl border transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150',
        'bg-ink-900/20',
        isDragOver ? 'scale-[1.01]' : '',
      ].join(' ')}
    >
      {/* Header — dynamic col.color stays inline */}
      <div
        className="px-3 py-2.5 rounded-t-2xl shrink-0"
        style={{ borderBottom: `1px solid ${col.color}22`, backgroundColor: col.color + '12' }}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide" style={{ color: col.color }}>
            <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: col.color }} />
            {col.label}
          </span>
          <span
            className="text-xs font-bold px-2 py-0.5 rounded-full tabular-nums"
            style={{ color: col.color, backgroundColor: col.color + '25' }}
          >
            {tenders.length}
          </span>
        </div>
        {totalVal > 0 && (
          <p className="text-[11px] text-slate-600 mt-0.5 font-mono">{fmtPLN(totalVal)}</p>
        )}
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2 min-h-[120px]" style={{ maxHeight: 'calc(100dvh - 280px)' }}>
        {loading ? (
          [0, 1].map(i => (
            <div key={i} className="p-3 rounded-2xl bg-ink-900/60 border border-ink-800/50 animate-pulse-soft">
              <div className="h-3 bg-ink-800 rounded w-full mb-1.5" />
              <div className="h-3 bg-ink-800 rounded w-3/4 mb-3" />
              <div className="h-2 bg-ink-800 rounded w-1/2" />
            </div>
          ))
        ) : tenders.length === 0 ? (
          <div className="py-8 flex flex-col items-center justify-center">
            <Inbox className="w-5 h-5 text-slate-700 mb-1.5" />
            <p className="text-slate-600 text-xs">Pusto</p>
          </div>
        ) : (
          tenders.map(t => (
            <KanbanCard
              key={t.id}
              tender={t}
              colColor={col.color}
              onDragStart={onCardDragStart}
              onDragEnd={onCardDragEnd}
              onClick={onCardClick}
            />
          ))
        )}
      </div>
    </div>
  );
}

// ── Timeline SVG View ─────────────────────────────────────────────────────────

function TimelineView({ tenders }: { tenders: TenderItem[] }) {
  const DAYS = 60;
  const ROW_H = 34;
  const LABEL_W = 180;
  const CHART_W = 820;
  const TOTAL_W = LABEL_W + CHART_W;
  const today = Date.now();
  const end = today + DAYS * 86_400_000;

  const withDeadline = tenders
    .filter(t => t.deadline_at)
    .sort((a, b) => new Date(a.deadline_at!).getTime() - new Date(b.deadline_at!).getTime())
    .slice(0, 35);

  const HEADER_H = 46;
  const HEIGHT = HEADER_H + withDeadline.length * ROW_H + 10;

  const dateX = (ms: number) => LABEL_W + ((ms - today) / (end - today)) * CHART_W;

  const ticks: { x: number; label: string }[] = [];
  for (let d = 0; d <= DAYS; d += 7) {
    const ms = today + d * 86_400_000;
    ticks.push({
      x: LABEL_W + (d / DAYS) * CHART_W,
      label: new Date(ms).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit' }),
    });
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-ink-800/60 bg-ink-950">
      <svg width={TOTAL_W} height={HEIGHT} viewBox={`0 0 ${TOTAL_W} ${HEIGHT}`}>
        {/* Background */}
        <rect width={TOTAL_W} height={HEIGHT} fill="#0A0906" />
        {/* Alternate row bg */}
        {withDeadline.map((_, i) => i % 2 === 0 && (
          <rect key={i} x={0} y={HEADER_H + i * ROW_H} width={TOTAL_W} height={ROW_H} fill="#0D0B08" />
        ))}
        {/* Tick lines */}
        {ticks.map((tick, i) => (
          <g key={i}>
            <line x1={tick.x} y1={HEADER_H} x2={tick.x} y2={HEIGHT} stroke="#1E2A38" strokeWidth="1" />
            <text x={tick.x + 3} y={HEADER_H - 8} fontSize="10" fill="#475569" fontFamily="monospace">{tick.label}</text>
          </g>
        ))}
        {/* Chart area border */}
        <rect x={LABEL_W} y={HEADER_H} width={CHART_W} height={HEIGHT - HEADER_H} fill="none" stroke="#1E2A38" strokeWidth="1" />

        {/* Today line */}
        <line x1={LABEL_W} y1={0} x2={LABEL_W} y2={HEIGHT} stroke="#EF4444" strokeWidth="1.5" strokeDasharray="5 3" />
        <text x={LABEL_W + 4} y={16} fontSize="10" fill="#EF4444" fontWeight="600">Dziś</text>

        {/* Tender rows */}
        {withDeadline.map((t, i) => {
          const y = HEADER_H + i * ROW_H;
          const deadlineMs = new Date(t.deadline_at!).getTime();
          const startMs = Math.max(today, today);
          const endMs = deadlineMs;
          const x1 = Math.max(LABEL_W, dateX(startMs));
          const x2 = Math.min(LABEL_W + CHART_W, dateX(endMs));
          const barW = Math.max(x2 - x1, 2);
          const color = COL_COLOR_MAP[t.pipeline_status?.toLowerCase()] ?? '#94A3B8';
          const overdue = deadlineMs < today;
          const pad = 6;

          return (
            <g key={t.id}>
              {/* Label */}
              <text x={4} y={y + ROW_H / 2 + 4} fontSize="10" fill="#94A3B8">
                {t.title.slice(0, 30)}{t.title.length > 30 ? '…' : ''}
              </text>
              {/* Bar */}
              {!overdue && endMs <= end && (
                <rect x={x1} y={y + pad} width={barW} height={ROW_H - pad * 2} rx="3"
                  fill={color + '40'} stroke={color} strokeWidth="1" />
              )}
              {overdue && (
                <rect x={LABEL_W + CHART_W - 40} y={y + pad} width={40} height={ROW_H - pad * 2} rx="3"
                  fill="#EF444450" stroke="#EF4444" strokeWidth="1" />
              )}
              {/* Deadline dot */}
              {!overdue && endMs <= end && (
                <circle cx={x2} cy={y + ROW_H / 2} r="3.5" fill={color} />
              )}
              {/* Value */}
              {t.value_pln != null && !overdue && endMs <= end && x2 + 50 < LABEL_W + CHART_W && (
                <text x={x2 + 7} y={y + ROW_H / 2 + 4} fontSize="9" fill={color + 'AA'}>
                  {fmtPLN(t.value_pln)}
                </text>
              )}
            </g>
          );
        })}

        {withDeadline.length === 0 && (
          <text x={TOTAL_W / 2} y={HEIGHT / 2 + 6} textAnchor="middle" fontSize="13" fill="#475569">
            Brak przetargów z terminem składania
          </text>
        )}
      </svg>
    </div>
  );
}

// ── Add Modal ─────────────────────────────────────────────────────────────────

function AddModal({
  onClose, onAdd, authFetch,
}: {
  onClose: () => void;
  onAdd: (t: TenderItem) => void;
  authFetch: ReturnType<typeof useAuthFetch>;
}) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<TenderItem[]>([]);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 2) { setResults([]); return; }
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const data = await authFetch(`/api/v2/tenders?q=${encodeURIComponent(query)}&limit=10`);
        const items: BackendTenderItem[] = data?.items ?? [];
        setResults(items.map(mapBackendTender));
      } catch { setResults([]); } finally { setSearching(false); }
    }, 350);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, authFetch]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ duration: 0.2, ease: [0, 0, 0.2, 1] }}
        className="w-full max-w-lg"
      >
        <GlassCard className="p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-slate-100">Dodaj przetarg do pipeline</h3>
            <button type="button"
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded-xl hover:bg-ink-800 transition-colors"
            >
              <X className="w-4 h-4 text-slate-400" />
            </button>
          </div>

          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Szukaj przetargu po tytule lub zamawiającym…"
              className="input-base w-full pl-9 pr-4 py-2.5"
            />
            {searching && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 animate-spin" />}
          </div>

          {/* Results */}
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {results.length === 0 && query.length >= 2 && !searching && (
              <div className="py-8 text-center">
                <Search className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                <p className="text-slate-500 text-sm">Brak wyników dla &ldquo;{query}&rdquo;</p>
              </div>
            )}
            {query.length < 2 && (
              <p className="text-center text-slate-600 text-sm py-6">Wpisz co najmniej 2 znaki aby wyszukać</p>
            )}
            {results.map(t => (
              <button type="button"
                key={t.id}
                onClick={() => onAdd(t)}
                className="w-full text-left p-3 rounded-2xl bg-ink-800/40 hover:bg-ink-800/80 border border-ink-700/40 hover:border-em/40 transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150 group"
              >
                <p className="text-slate-100 text-sm font-medium line-clamp-1 group-hover:text-slate-100">{t.title}</p>
                <div className="flex items-center gap-2 mt-1">
                  <p className="text-slate-500 text-xs truncate flex-1">{t.buyer ?? '—'}</p>
                  <span className="text-slate-400 text-xs font-mono shrink-0">{fmtPLN(t.value_pln)}</span>
                </div>
              </button>
            ))}
          </div>
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function PipelinePage() {
  const { setSelectedTender, setCurrentModule } = useStore();
  const authFetch = useAuthFetch();

  // Initialise with empty columns — real data comes from API
  const emptyByStatus = (): Record<string, TenderItem[]> =>
    Object.fromEntries(COLUMNS.map(c => [c.key, []]));

  const [tendersByStatus, setTendersByStatus] = useState<Record<string, TenderItem[]>>(emptyByStatus);
  const [kpi, setKpi] = useState<PipelineKPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'kanban' | 'timeline'>('kanban');
  const [dragOverCol, setDragOverCol] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);

  // ── Fetch tenders ─────────────────────────────────────────────────────────
  const fetchTenders = useCallback(async () => {
    setLoading(true);
    try {
      const data = await authFetch('/api/v2/tenders?include_pipeline=true&limit=100');
      const rawItems: BackendTenderItem[] = data?.items ?? [];
      const items = rawItems.map(mapBackendTender);

      const byStatus: Record<string, TenderItem[]> = emptyByStatus();
      for (const t of items) {
        const key = (t.pipeline_status ?? '').toLowerCase() || 'scouting';
        if (byStatus[key] !== undefined) {
          byStatus[key].push({ ...t, pipeline_status: key });
        } else {
          // Unknown status falls into scouting
          byStatus['scouting'].push({ ...t, pipeline_status: 'scouting' });
        }
      }
      setTendersByStatus(byStatus);
    } catch {
      // On error keep current state, don't wipe
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  const fetchKpi = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/dashboard/pipeline-kpi');
      setKpi(data);
    } catch { /* non-critical */ }
  }, [authFetch]);

  useEffect(() => { fetchTenders(); fetchKpi(); }, [fetchTenders, fetchKpi]);

  // ── Drag handlers ─────────────────────────────────────────────────────────
  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, tender: TenderItem) => {
    e.dataTransfer.setData('tenderId', tender.id);
    e.dataTransfer.setData('fromStatus', (tender.pipeline_status ?? 'scouting').toLowerCase());
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnd = () => { setDragOverCol(null); };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>, colKey: string) => {
    e.preventDefault();
    setDragOverCol(colKey);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    const target = e.currentTarget as HTMLElement;
    if (!target.contains(e.relatedTarget as Node)) {
      // don't clear here — rely on dragEnd to avoid flicker
    }
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>, toStatus: string) => {
    e.preventDefault();
    setDragOverCol(null);
    const tenderId = e.dataTransfer.getData('tenderId');
    const fromStatus = e.dataTransfer.getData('fromStatus');
    if (!tenderId || fromStatus === toStatus) return;

    // Find tender
    const tender = (tendersByStatus[fromStatus] ?? []).find(t => t.id === tenderId);
    if (!tender) return;

    // Optimistic update — move card immediately
    setTendersByStatus(prev => ({
      ...prev,
      [fromStatus]: (prev[fromStatus] ?? []).filter(t => t.id !== tenderId),
      [toStatus]:   [...(prev[toStatus] ?? []), { ...tender, pipeline_status: toStatus }],
    }));

    try {
      await authFetch(`/api/v2/tenders/${tenderId}`, {
        method: 'PATCH',
        body: JSON.stringify({ pipeline_status: toStatus }),
      });
      const label = COLUMNS.find(c => c.key === toStatus)?.label ?? toStatus;
      showToast('success', `Przeniesiono → ${label}`);
    } catch {
      // Revert on error
      fetchTenders();
    }
  };

  // ── Add to pipeline ───────────────────────────────────────────────────────
  const handleAddTender = async (tender: TenderItem) => {
    try {
      await authFetch(`/api/v2/tenders/${tender.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ pipeline_status: 'scouting' }),
      });
      showToast('success', 'Dodano do pipeline jako Rozpoznanie');
      setShowAddModal(false);
      fetchTenders();
    } catch { /* toast handled */ }
  };

  // ── Card click → decyzja ──────────────────────────────────────────────────
  const handleCardClick = (tender: TenderItem) => {
    setSelectedTender(tender as unknown as Tender);
    setCurrentModule('decyzja');
  };

  // ── Derived stats ─────────────────────────────────────────────────────────
  const allFlat = Object.values(tendersByStatus).flat();
  const totalCount = allFlat.length;
  const totalValue = allFlat.reduce((s, t) => s + (t.value_pln ?? 0), 0);
  const wonCount = (tendersByStatus['won'] ?? []).length;
  const closedCount = wonCount + (tendersByStatus['lost'] ?? []).length;
  const winRate = closedCount > 0 ? Math.round((wonCount / closedCount) * 100) : null;

  // ── Actions bar ───────────────────────────────────────────────────────────
  const actions = (
    <div className="flex items-center gap-2 flex-wrap">
      {/* View toggle */}
      <div className="flex items-center rounded-md bg-ink-900 border border-ink-800/60 p-0.5">
        <Button
          variant={view === 'kanban' ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => setView('kanban')}
          iconLeft={<LayoutGrid className="w-3.5 h-3.5" />}
        >
          Kanban
        </Button>
        <Button
          variant={view === 'timeline' ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => setView('timeline')}
          iconLeft={<CalendarDays className="w-3.5 h-3.5" />}
        >
          Timeline
        </Button>
      </div>
      {/* Add button */}
      <Button
        variant="primary"
        size="sm"
        onClick={() => setShowAddModal(true)}
        iconLeft={<Plus className="w-3.5 h-3.5" />}
      >
        Dodaj
      </Button>
    </div>
  );

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <PageShell
      title="Lejek Ofertowy"
      subtitle={`${totalCount} przetargów · ${fmtPLN(totalValue)} łączna wartość`}
      actions={actions}
    >
      {/* ── KPI metrics ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        {kpi ? (
          <>
            <MetricCard
              icon={Activity}
              label="Aktywne przetargi"
              value={String(kpi.active)}
              iconColor="text-indigo"
              loading={loading}
            />
            <MetricCard
              icon={DollarSign}
              label="Wartość pipeline"
              value={fmtPLN(kpi.pipeline_value)}
              iconColor="text-orange-400"
              loading={loading}
            />
            <MetricCard
              icon={Target}
              label="Win Rate MTD"
              value={`${Math.round(kpi.win_rate_mtd * 100)}%`}
              iconColor="text-go"
              loading={loading}
            />
          </>
        ) : (
          <>
            <MetricCard
              icon={Activity}
              label="Aktywne przetargi"
              value={String(totalCount)}
              iconColor="text-indigo"
              loading={loading}
            />
            <MetricCard
              icon={DollarSign}
              label="Wartość pipeline"
              value={fmtPLN(totalValue)}
              iconColor="text-orange-400"
              loading={loading}
            />
            <MetricCard
              icon={Target}
              label="Win Rate"
              value={winRate !== null ? `${winRate}%` : '—'}
              iconColor={
                winRate !== null && winRate > 30
                  ? 'text-emerald-400'
                  : winRate !== null && winRate >= 20
                  ? 'text-amber-400'
                  : 'text-red-400'
              }
              loading={loading}
            />
          </>
        )}
      </div>

      {/* ── Kanban / Timeline ─────────────────────────────────────────── */}
      {view === 'kanban' ? (
        <div className="overflow-x-auto">
          <div className="flex gap-3 pb-4" style={{ minWidth: 'max-content' }}>
            {COLUMNS.map(col => (
              <KanbanColumn
                key={col.key}
                col={col}
                tenders={tendersByStatus[col.key] ?? []}
                loading={loading}
                isDragOver={dragOverCol === col.key}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onCardClick={handleCardClick}
                onCardDragStart={handleDragStart}
                onCardDragEnd={handleDragEnd}
              />
            ))}
          </div>
        </div>
      ) : (
        <div>
          <div className="mb-3">
            <h3 className="text-sm font-semibold text-slate-300">Harmonogram terminów — następne 60 dni</h3>
            <p className="text-xs text-slate-500 mt-0.5">Poziome paski = czas do deadline, kolor = status pipeline</p>
          </div>
          {/* Legend */}
          <div className="flex items-center gap-4 mb-4 flex-wrap">
            {COLUMNS.map(c => (
              <div key={c.key} className="flex items-center gap-1.5 text-xs text-slate-500">
                <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: c.color }} />
                {c.label}
              </div>
            ))}
          </div>
          <TimelineView tenders={allFlat} />
        </div>
      )}

      {/* ── Add Modal ─────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showAddModal && (
          <AddModal
            onClose={() => setShowAddModal(false)}
            onAdd={handleAddTender}
            authFetch={authFetch}
          />
        )}
      </AnimatePresence>
    </PageShell>
  );
}
