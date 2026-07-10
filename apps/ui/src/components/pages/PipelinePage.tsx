'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'motion/react';
import { AlertTriangle, TrendingUp, Filter } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';
import { TenderDetail } from '@/components/TenderDetail';
import { StatusBadge } from '@/components/ui/StatusBadge';

// dnd-kit
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// ── Types ──────────────────────────────────────────────────────────────────────
interface TenderItem {
  id: string;
  title: string;
  buyer: string | null;
  cpv: string[];
  voivodeship: string | null;
  value_pln: number | string | null;
  match_score: number | null;
  status: string;
  deadline_at: string | null;
  match_reason: string | null;
  source: string | null;
}

// ── Config ────────────────────────────────────────────────────────────────────
const PIPELINE_STAGES = [
  { key: 'new',          label: 'Monitoring',  desc: 'Świeżo z BZP',          color: '#60a5fa', borderColor: 'border-blue-500/30',   bg: 'bg-blue-500/8',    headerBg: 'bg-blue-500/15' },
  { key: 'matched',      label: 'Analiza',     desc: 'Pasuje do profilu',      color: '#a78bfa', borderColor: 'border-purple-500/30', bg: 'bg-purple-500/8',  headerBg: 'bg-purple-500/15' },
  { key: 'watching',     label: 'GO/NO-GO',    desc: 'W obserwacji',           color: '#38bdf8', borderColor: 'border-sky-500/30',    bg: 'bg-sky-500/8',     headerBg: 'bg-sky-500/15' },
  { key: 'analyzing',    label: 'Kosztorys',   desc: 'Dokumentacja pobrana',   color: '#fbbf24', borderColor: 'border-yellow-500/30', bg: 'bg-yellow-500/8',  headerBg: 'bg-yellow-500/15' },
  { key: 'estimated',    label: 'Weryfikacja', desc: 'Kosztorys gotowy',       color: '#34d399', borderColor: 'border-emerald-500/30',bg: 'bg-emerald-500/8', headerBg: 'bg-emerald-500/15' },
  { key: 'decided_go',   label: 'Złożenie',    desc: 'Oferta złożona',         color: '#10b981', borderColor: 'border-emerald-600/40',bg: 'bg-emerald-600/8', headerBg: 'bg-emerald-600/20' },
  { key: 'decided_nogo', label: 'Wynik',       desc: 'Rezygnacja / Wynik',     color: '#f87171', borderColor: 'border-red-500/30',    bg: 'bg-red-500/8',     headerBg: 'bg-red-500/15' },
];

function fmtPLN(v: number | string | null | undefined) {
  if (v === null || v === undefined) return '—';
  const n = typeof v === 'string' ? parseFloat(v) : v;
  if (isNaN(n)) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + ' M zł';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + ' tys. zł';
  return n.toFixed(0) + ' zł';
}

function daysUntil(deadline: string | null): number | null {
  if (!deadline) return null;
  return Math.ceil((new Date(deadline).getTime() - Date.now()) / 86400000);
}

// ── Sortable card ─────────────────────────────────────────────────────────────
function SortableCard({ tender, color, onOpen }: { tender: TenderItem; color: string; onOpen: (t: TenderItem) => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: tender.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };
  const score = tender.match_score !== null ? Math.round(tender.match_score * 100) : null;
  const days = daysUntil(tender.deadline_at);
  const urgent = days !== null && days <= 7;

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        onClick={() => onOpen(tender)}
        className={"p-3 rounded-xl bg-earth-900/60 border border-earth-800/50 hover:border-earth-700/70 hover:bg-earth-900 transition-all duration-200 cursor-pointer group" + (urgent ? " border-l-2 border-l-red-400/60" : "")}
      >
        <p className="text-earth-200 text-xs font-medium line-clamp-2 leading-snug group-hover:text-earth-100">{tender.title}</p>
        <p className="text-earth-600 text-xs mt-1.5 truncate">{tender.buyer ?? '—'}</p>
        <div className="flex items-center justify-between mt-2">
          <span className="text-earth-400 text-xs font-mono">{fmtPLN(tender.value_pln)}</span>
          {score !== null && (
            <span className="text-xs font-bold px-1.5 py-0.5 rounded" style={{ color, backgroundColor: color + '20' }}>
              {score}%
            </span>
          )}
        </div>
        {days !== null && (
          <p className={"text-[10px] mt-1 font-mono " + (days <= 3 ? "text-red-400" : days <= 7 ? "text-yellow-400" : "text-earth-600")}>
            {days < 0 ? "po terminie" : days === 0 ? "dziś" : days + "d"}
          </p>
        )}
      </motion.div>
    </div>
  );
}

// ── Drag overlay card ─────────────────────────────────────────────────────────
function DragCard({ tender }: { tender: TenderItem }) {
  const score = tender.match_score !== null ? Math.round(tender.match_score * 100) : null;
  return (
    <div className="p-3 rounded-xl bg-earth-800 border border-earth-600 shadow-2xl opacity-95 w-60">
      <p className="text-earth-100 text-xs font-medium line-clamp-2">{tender.title}</p>
      <div className="flex items-center justify-between mt-2">
        <span className="text-earth-400 text-xs font-mono">{fmtPLN(tender.value_pln)}</span>
        {score !== null && <span className="text-xs font-bold text-accent-primary">{score}%</span>}
      </div>
    </div>
  );
}

// ── Skeleton card ─────────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="p-3 rounded-xl bg-earth-900/60 border border-earth-800/50 animate-pulse">
      <div className="h-3 bg-earth-800 rounded w-full mb-1.5" />
      <div className="h-3 bg-earth-800 rounded w-3/4 mb-3" />
      <div className="h-2.5 bg-earth-800 rounded w-1/2" />
    </div>
  );
}

// ── Droppable column ──────────────────────────────────────────────────────────
function DroppableColumn({
  stage, tenders, loading, onOpen,
}: {
  stage: typeof PIPELINE_STAGES[number];
  tenders: TenderItem[];
  loading: boolean;
  onOpen: (t: TenderItem) => void;
}) {
  return (
    <div className={"flex flex-col w-64 rounded-2xl border " + stage.borderColor + " " + stage.bg + " overflow-hidden"}>
      <div className={"px-3 py-2.5 " + stage.headerBg + " border-b " + stage.borderColor + " shrink-0"}>
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold" style={{ color: stage.color }}>{stage.label}</span>
          <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ color: stage.color, backgroundColor: stage.color + '25' }}>
            {tenders.length}
          </span>
        </div>
        <p className="text-earth-600 text-xs mt-0.5">{stage.desc}</p>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        <SortableContext items={tenders.map(t => t.id)} strategy={verticalListSortingStrategy}>
          {loading
            ? Array.from({ length: 2 }).map((_, i) => <SkeletonCard key={i} />)
            : tenders.length === 0
              ? (
                <div className="py-6 text-center">
                  <TrendingUp className="w-5 h-5 text-earth-800 mx-auto mb-1" />
                  <p className="text-earth-700 text-xs">Brak przetargów</p>
                </div>
              )
              : tenders.map(t => <SortableCard key={t.id} tender={t} color={stage.color} onOpen={onOpen} />)
          }
        </SortableContext>
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export function PipelinePage() {
  const { accessToken } = useStore();
  const [tendersByStage, setTendersByStage] = useState<Record<string, TenderItem[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalValue, setTotalValue] = useState(0);
  const [urgentOnly, setUrgentOnly] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedTender, setSelectedTender] = useState<TenderItem | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const authFetch = useAuthFetch();

  const fetchTenders = useCallback(async () => {
    try {
      const data = await authFetch('/api/v1/tenders?limit=100');
      const items: TenderItem[] = data.items ?? [];
      const byStage: Record<string, TenderItem[]> = {};
      for (const st of PIPELINE_STAGES) byStage[st.key] = [];
      for (const t of items) {
        if (byStage[t.status] !== undefined) byStage[t.status].push(t);
      }
      const tv = items.reduce((s, t) => {
        const n = t.value_pln !== null ? parseFloat(String(t.value_pln)) : 0;
        return s + (isNaN(n) ? 0 : n);
      }, 0);
      setTendersByStage(byStage);
      setTotalValue(tv);
      setLoading(false);
    } catch (e: unknown) {
      setError((e as Error).message);
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => { fetchTenders(); }, [fetchTenders]);

  function findTenderById(id: string): TenderItem | null {
    for (const tenders of Object.values(tendersByStage)) {
      const t = tenders.find(x => x.id === id);
      if (t) return t;
    }
    return null;
  }

  function findStageForTender(id: string): string | null {
    for (const [stage, tenders] of Object.entries(tendersByStage)) {
      if (tenders.find(t => t.id === id)) return stage;
    }
    return null;
  }

  function handleDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }

  async function handleDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    setActiveId(null);
    if (!over) return;
    const tenderId = String(active.id);
    const overId = String(over.id);
    const fromStage = findStageForTender(tenderId);
    // Check if over is a stage key or a tender id
    const toStage = PIPELINE_STAGES.find(s => s.key === overId)?.key ?? findStageForTender(overId);
    if (!fromStage || !toStage || fromStage === toStage) return;

    // Optimistic update
    setTendersByStage(prev => {
      const tender = prev[fromStage].find(t => t.id === tenderId);
      if (!tender) return prev;
      return {
        ...prev,
        [fromStage]: prev[fromStage].filter(t => t.id !== tenderId),
        [toStage]: [...prev[toStage], { ...tender, status: toStage }],
      };
    });

    try {
      await authFetch('/api/v1/tenders/' + tenderId, {
        method: 'PATCH',
        body: JSON.stringify({ status: toStage }),
      });
      showToast('success', 'Status przetargu zaktualizowany');
    } catch {
      showToast('error', 'Błąd aktualizacji statusu');
      fetchTenders();
    }
  }

  const activeTotal = Object.values(tendersByStage).reduce((s, arr) => s + arr.length, 0);
  const goCount = tendersByStage['decided_go']?.length ?? 0;
  const conversionRate = activeTotal > 0 ? ((goCount / activeTotal) * 100).toFixed(0) : '0';

  const displayedByStage = urgentOnly
    ? Object.fromEntries(Object.entries(tendersByStage).map(([k, v]) => [k, v.filter(t => {
        const d = daysUntil(t.deadline_at);
        return d !== null && d <= 7;
      })]))
    : tendersByStage;

  if (error) return (
    <div className="m-6 p-4 rounded-xl bg-accent-danger/10 border border-accent-danger/20 text-accent-danger text-sm flex gap-2">
      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />{error}
    </div>
  );

  const activeTender = activeId ? findTenderById(activeId) : null;

  return (
    <>
      <div className="flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-earth-800/60 flex items-center justify-between shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-earth-100">Pipeline przetargów</h2>
            <p className="text-earth-500 text-xs mt-0.5">Przeciągnij karty między kolumnami</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setUrgentOnly(u => !u)}
              className={"flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors " + (urgentOnly ? "bg-red-500/20 text-red-400" : "bg-earth-800 text-earth-400 hover:text-earth-200")}
            >
              <Filter className="w-3.5 h-3.5" /> Pilne
            </button>
            <div className="text-center">
              <p className="text-xl font-bold text-earth-100 tabular-nums">{activeTotal}</p>
              <p className="text-earth-600 text-xs">Aktywnych</p>
            </div>
            <div className="w-px h-8 bg-earth-800" />
            <div className="text-center">
              <p className="text-xl font-bold text-accent-primary tabular-nums">{fmtPLN(totalValue)}</p>
              <p className="text-earth-600 text-xs">Łączna wartość</p>
            </div>
            <div className="w-px h-8 bg-earth-800" />
            <div className="text-center">
              <p className="text-xl font-bold text-accent-info tabular-nums">{conversionRate}%</p>
              <p className="text-earth-600 text-xs">Konwersja</p>
            </div>
          </div>
        </div>

        {/* Kanban */}
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          <div className="flex-1 overflow-x-auto overflow-y-hidden">
            <div className="flex gap-3 p-4 h-full min-w-max">
              {PIPELINE_STAGES.map(stage => (
                <DroppableColumn
                  key={stage.key}
                  stage={stage}
                  tenders={displayedByStage[stage.key] ?? []}
                  loading={loading}
                  onOpen={setSelectedTender}
                />
              ))}
            </div>
          </div>
          <DragOverlay>
            {activeTender ? <DragCard tender={activeTender} /> : null}
          </DragOverlay>
        </DndContext>
      </div>

      <TenderDetail tender={selectedTender} onClose={() => setSelectedTender(null)} />
    </>
  );
}
