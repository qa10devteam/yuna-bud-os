'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  RefreshCw, ChevronDown, X, ExternalLink, MapPin, Calendar,
  Building2, Tag, Zap, TrendingUp, AlertCircle, CheckCircle2,
  Clock, FileText, BarChart3, ArrowUpDown, Filter, Target,
  DollarSign, Activity, Users, ChevronRight, RotateCw,
  Download, Loader2, FolderOpen,
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { GlassCard } from '@/components/ui/GlassCard';
import { PolandHeatmap } from '@/components/PolandHeatmap';
import { showToast } from '@/components/Toast';
import { useAuthFetch } from '@/lib/api-v2';
import { useStore } from '@/store/useStore';

// ─── Types ────────────────────────────────────────────────────────────────────

interface TenderItem {
  id: string;
  title: string;
  buyer: string | null;
  cpv: string[];
  voivodeship: string | null;
  value_pln: number | null;
  deadline_at: string | null;
  status: string;
  match_score: number | null;
  match_reason: string | null;
  source: string | null;
  external_id: string | null;
  published_at: string | null;
  url: string | null;
  raw?: Record<string, unknown>;
}

interface TenderFeedResponse {
  items: TenderItem[];
  total: number;
  cursor: string | null;
}

interface IntelKPI {
  n_tenders: number;
  n_with_value: number;
  total_value_mln: number;
  avg_value: number;
  avg_competition: number;
  n_buyers: number;
  n_contractors: number;
}

interface IntelSummaryResponse {
  kpi: IntelKPI;
  top_cpv: Array<{ cpv2: string; n: number }>;
  top_province: Array<{ province: string; n: number }>;
  filters: Record<string, unknown>;
}

interface SeasonalityRow {
  month: string;
  n_tenders: number;
  avg_value: number;
  total_value: number;
  avg_competition: number;
}

interface EstimateItem {
  id: string;
  variant: string;
  total_net_pln: number;
  lines: Array<{ name: string; amount: number; unit: string; unit_price: number; total: number }>;
  params: Record<string, unknown>;
}

interface IngestResult {
  agent_run_id: string;
  fetched: number;
  created: number;
  updated: number;
  dropped: number;
  errors: number;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const VOIVODESHIPS = [
  'dolnośląskie', 'kujawsko-pomorskie', 'lubelskie', 'lubuskie',
  'łódzkie', 'małopolskie', 'mazowieckie', 'opolskie',
  'podkarpackie', 'podlaskie', 'pomorskie', 'śląskie',
  'świętokrzyskie', 'warmińsko-mazurskie', 'wielkopolskie', 'zachodniopomorskie',
];

const STATUS_OPTS = [
  { value: '', label: 'Wszystkie statusy' },
  { value: 'new', label: 'Nowy' },
  { value: 'matched', label: 'Dopasowany' },
  { value: 'watching', label: 'Obserwowany' },
  { value: 'analyzing', label: 'W analizie' },
  { value: 'estimated', label: 'Wyceniony' },
  { value: 'decided_go', label: 'GO ✓' },
  { value: 'decided_nogo', label: 'NO-GO ✗' },
  { value: 'archived', label: 'Archiwum' },
];

const SORT_OPTS = [
  { value: 'match_score', label: 'Score dopasowania' },
  { value: 'deadline', label: 'Deadline' },
  { value: 'value', label: 'Wartość' },
  { value: 'published', label: 'Data publikacji' },
];

const CHART_COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtPLN(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(2).replace('.', ',') + ' M zł';
  if (v >= 1_000) return Math.round(v / 1_000).toLocaleString('pl-PL') + ' tys. zł';
  return Math.round(v).toLocaleString('pl-PL') + ' zł';
}

function fmtDate(s: string | null | undefined): string {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function daysUntil(s: string | null): number | null {
  if (!s) return null;
  return Math.ceil((new Date(s).getTime() - Date.now()) / 86_400_000);
}

function scoreColor(score: number): { text: string; bg: string; bar: string } {
  if (score >= 0.8) return { text: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30', bar: '#10b981' };
  if (score >= 0.5) return { text: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30', bar: '#f59e0b' };
  return { text: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30', bar: '#ef4444' };
}

function fmtMln(v: number): string {
  if (v >= 1000) return (v / 1000).toFixed(1) + ' mld';
  if (v >= 1) return v.toFixed(1) + ' M';
  return (v * 1000).toFixed(0) + ' tys.';
}

// ─── MatchScoreBar ────────────────────────────────────────────────────────────

function MatchScoreBar({ score, compact = false }: { score: number | null; compact?: boolean }) {
  if (score === null) return <span className="text-xs text-earth-600">—</span>;
  const pct = Math.round(score * 100);
  const { text, bar } = scoreColor(score);
  if (compact) {
    return (
      <div className="flex items-center gap-1.5">
        <div className="h-1 w-16 bg-earth-800 rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: bar }} />
        </div>
        <span className={`text-xs font-bold tabular-nums ${text}`}>{pct}%</span>
      </div>
    );
  }
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-earth-500">Dopasowanie</span>
        <span className={`text-sm font-bold tabular-nums ${text}`}>{pct}%</span>
      </div>
      <div className="h-2 w-full bg-earth-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="h-full rounded-full"
          style={{ backgroundColor: bar }}
        />
      </div>
    </div>
  );
}

// ─── KPI Strip ────────────────────────────────────────────────────────────────

function KPIStrip({ kpi, loading }: { kpi: IntelKPI | null; loading: boolean }) {
  const items = kpi
    ? [
        { label: 'Przetargi', value: kpi.n_tenders.toLocaleString('pl-PL'), icon: FileText, color: '#10b981' },
        { label: 'Łączna wartość', value: fmtMln(kpi.total_value_mln), icon: DollarSign, color: '#3b82f6' },
        { label: 'Śr. wartość', value: fmtPLN(kpi.avg_value), icon: TrendingUp, color: '#f59e0b' },
        { label: 'Śr. konkurencja', value: kpi.avg_competition?.toFixed(1) ?? '—', icon: Users, color: '#8b5cf6' },
        { label: 'Zamawiający', value: kpi.n_buyers.toLocaleString('pl-PL'), icon: Building2, color: '#06b6d4' },
      ]
    : [];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {loading
        ? Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-earth-800/50 rounded-xl animate-pulse" />
          ))
        : items.map(({ label, value, icon: Icon, color }) => (
            <GlassCard key={label} className="px-4 py-3 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: color + '22' }}>
                <Icon size={15} style={{ color }} />
              </div>
              <div className="min-w-0">
                <div className="text-[10px] text-earth-500 uppercase tracking-wide truncate">{label}</div>
                <div className="text-sm font-bold text-earth-100 tabular-nums">{value}</div>
              </div>
            </GlassCard>
          ))}
    </div>
  );
}

// ─── Seasonality chart (mini) ─────────────────────────────────────────────────

function SeasonalityMini({ data }: { data: SeasonalityRow[] }) {
  if (!data.length) return null;
  const last12 = data.slice(-12);
  return (
    <ResponsiveContainer width="100%" height={60}>
      <AreaChart data={last12} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="szGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="n_tenders" stroke="#10b981" fill="url(#szGrad)" strokeWidth={1.5} dot={false} />
        <Tooltip
          contentStyle={{ background: '#1a1a14', border: '1px solid #3f3f46', borderRadius: 6, fontSize: 11 }}
          formatter={(v: number) => [v, 'Przetargi']}
          labelFormatter={(l: string) => l}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ─── TenderCard ───────────────────────────────────────────────────────────────

function TenderCard({
  tender,
  selected,
  onClick,
}: {
  tender: TenderItem;
  selected: boolean;
  onClick: () => void;
}) {
  const days = daysUntil(tender.deadline_at);
  const score = tender.match_score ?? 0;
  const { bg } = scoreColor(score);
  const urgent = days !== null && days >= 0 && days <= 3;
  const expired = days !== null && days < 0;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      onClick={onClick}
      className={`relative rounded-xl border cursor-pointer transition-all duration-150 p-4 space-y-3 ${
        selected
          ? 'border-emerald-500/50 bg-emerald-500/5 shadow-lg shadow-emerald-500/5'
          : 'border-earth-800/60 bg-earth-900/50 hover:border-earth-700/80 hover:bg-earth-800/40'
      }`}
    >
      {/* Score accent stripe */}
      <div
        className="absolute left-0 top-3 bottom-3 w-0.5 rounded-full"
        style={{ backgroundColor: scoreColor(score).bar }}
      />

      {/* Top row */}
      <div className="flex items-start justify-between gap-2 pl-2">
        <p className="text-sm font-medium text-earth-100 line-clamp-2 leading-snug flex-1">{tender.title}</p>
        <MatchScoreBar score={tender.match_score} compact />
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pl-2 text-xs text-earth-500">
        {tender.buyer && (
          <span className="flex items-center gap-1 truncate max-w-[180px]">
            <Building2 size={11} className="shrink-0" />
            {tender.buyer}
          </span>
        )}
        {tender.voivodeship && (
          <span className="flex items-center gap-1">
            <MapPin size={11} className="shrink-0" />
            {tender.voivodeship}
          </span>
        )}
        {tender.value_pln && (
          <span className="flex items-center gap-1 text-earth-300 font-mono">
            <DollarSign size={11} className="shrink-0" />
            {fmtPLN(tender.value_pln)}
          </span>
        )}
        {tender.deadline_at && (
          <span className={`flex items-center gap-1 ${urgent ? 'text-red-400' : expired ? 'text-earth-600' : ''}`}>
            <Calendar size={11} className="shrink-0" />
            {fmtDate(tender.deadline_at)}
            {days !== null && !expired && days <= 14 && (
              <span className={`font-bold ${urgent ? 'text-red-400' : 'text-amber-500'}`}>({days}d)</span>
            )}
            {expired && <span className="text-earth-600 italic">(minął)</span>}
          </span>
        )}
      </div>

      {/* Match reason + CPV */}
      <div className="flex flex-wrap items-center gap-1.5 pl-2">
        {tender.match_reason && (
          <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border font-medium ${bg}`}>
            <Target size={9} />
            {tender.match_reason.split(';')[0]?.trim()}
          </span>
        )}
        {tender.cpv[0] && (
          <span className="text-[10px] text-earth-600 font-mono bg-earth-800/60 px-1.5 py-0.5 rounded">
            {tender.cpv[0]}
          </span>
        )}
        {tender.status && tender.status !== 'new' && (
          <span className="text-[10px] text-earth-500 bg-earth-800 px-1.5 py-0.5 rounded">{tender.status}</span>
        )}
      </div>
    </motion.div>
  );
}

// ─── EstimatesTab ─────────────────────────────────────────────────────────────

function EstimatesTab({
  tenderId,
  authFetch,
}: {
  tenderId: string;
  authFetch: (url: string, opts?: RequestInit) => Promise<unknown>;
}) {
  const [estimates, setEstimates] = useState<EstimateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const raw = await authFetch(`/api/v2/estimates?tender_id=${tenderId}`) as unknown;
      if (Array.isArray(raw)) {
        setEstimates(raw as EstimateItem[]);
      } else if (raw && typeof raw === 'object' && 'items' in raw) {
        setEstimates((raw as { items: EstimateItem[] }).items ?? []);
      } else {
        setEstimates([]);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [tenderId, authFetch]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate() {
    setCreating(true);
    try {
      await authFetch(`/api/v1/tenders/${tenderId}/estimate`, { method: 'POST' });
      showToast('success', 'Kosztorys utworzony — otwierasz w module Kosztorys');
      await load();
    } catch (e: unknown) {
      showToast('error', 'Błąd tworzenia kosztorysu: ' + (e as Error).message);
    } finally {
      setCreating(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-3 py-4">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="h-20 bg-earth-800/50 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4 py-2">
      <button
        onClick={handleCreate}
        disabled={creating}
        className="flex items-center gap-2 px-4 py-2.5 bg-emerald-500 text-earth-950 rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {creating ? (
          <RefreshCw size={14} className="animate-spin" />
        ) : (
          <BarChart3 size={14} />
        )}
        Utwórz kosztorys
      </button>

      {estimates.length === 0 ? (
        <div className="py-8 text-center">
          <BarChart3 size={28} className="text-earth-700 mx-auto mb-2" />
          <p className="text-earth-500 text-sm">Brak kosztorysów</p>
          <p className="text-earth-700 text-xs mt-1">Kliknij powyżej aby wygenerować pierwszy</p>
        </div>
      ) : (
        <div className="space-y-3">
          {estimates.map((est) => (
            <GlassCard key={est.id} className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-earth-300 uppercase tracking-wide">
                  {est.variant || 'Wariant podstawowy'}
                </span>
                <span className="text-sm font-bold text-emerald-400 tabular-nums">
                  {fmtPLN(est.total_net_pln)}
                </span>
              </div>
              {est.lines && est.lines.length > 0 && (
                <div className="space-y-1 pt-1 border-t border-earth-800/60">
                  {est.lines.slice(0, 4).map((line, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <span className="text-earth-400 truncate max-w-[200px]">{line.name}</span>
                      <span className="text-earth-300 tabular-nums">{fmtPLN(line.total)}</span>
                    </div>
                  ))}
                  {est.lines.length > 4 && (
                    <p className="text-[10px] text-earth-600">+{est.lines.length - 4} pozycji…</p>
                  )}
                </div>
              )}
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Detail Panel ─────────────────────────────────────────────────────────────

// ─── DocumentsTab ─────────────────────────────────────────────────────────────

interface BzpDocument {
  id: string;
  doc_type: string;
  filename: string;
  download_url: string;
  notice_id: string;
  fetched_at: string | null;
}

const DOC_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  SWZ: { label: 'SWZ', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
  FORM: { label: 'Formularz', color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' },
  CONTRACT: { label: 'Umowa', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' },
  DECLARATION: { label: 'Oświadczenie', color: 'text-purple-400 bg-purple-500/10 border-purple-500/30' },
  LIST: { label: 'Wykaz', color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30' },
  TECHNICAL: { label: 'Dokumentacja', color: 'text-rose-400 bg-rose-500/10 border-rose-500/30' },
  AMENDMENT: { label: 'Zmiana', color: 'text-orange-400 bg-orange-500/10 border-orange-500/30' },
  OTHER: { label: 'Inny', color: 'text-earth-400 bg-earth-700/30 border-earth-600/30' },
};

function DocumentsTab({ tenderId, authFetch }: { tenderId: string; authFetch: (url: string, opts?: RequestInit) => Promise<unknown> }) {
  const [docs, setDocs] = useState<BzpDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [fetchTriggered, setFetchTriggered] = useState(false);

  const loadDocs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await authFetch(`/api/v1/bzp/documents/${tenderId}`) as { documents: BzpDocument[]; total: number };
      setDocs(data.documents ?? []);
    } catch { /* ignore */ }
    setLoading(false);
  }, [tenderId, authFetch]);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleFetch = async () => {
    setFetching(true);
    setFetchTriggered(true);
    try {
      await authFetch(`/api/v1/bzp/documents/${tenderId}/fetch`, { method: 'POST' });
      // Poll for results after background fetch
      setTimeout(() => loadDocs(), 3000);
      setTimeout(() => { loadDocs(); setFetching(false); }, 8000);
    } catch {
      setFetching(false);
    }
  };

  const handleDownload = (doc: BzpDocument) => {
    window.open(doc.download_url, '_blank');
  };

  if (loading && docs.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-earth-500">
        <Loader2 size={20} className="animate-spin mr-2" />
        Ładowanie dokumentów...
      </div>
    );
  }

  return (
    <div className="space-y-4 pt-4">
      {/* Fetch button */}
      <button
        onClick={handleFetch}
        disabled={fetching}
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-emerald-600/20 border border-emerald-500/30 text-sm font-medium text-emerald-300 hover:bg-emerald-600/30 hover:border-emerald-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {fetching ? (
          <>
            <Loader2 size={14} className="animate-spin" />
            Pobieram z BZP...
          </>
        ) : (
          <>
            <Download size={14} />
            {docs.length > 0 ? 'Odśwież dokumenty' : 'Pobierz dokumenty SWZ'}
          </>
        )}
      </button>

      {fetchTriggered && docs.length === 0 && !fetching && (
        <p className="text-xs text-earth-500 text-center">
          Dokumenty pobierają się w tle. Odśwież za chwilę.
        </p>
      )}

      {/* Document list */}
      {docs.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] text-earth-600 uppercase tracking-wide flex items-center gap-1.5">
            <FolderOpen size={10} />
            {docs.length} dokumentów
          </p>
          {docs.map(doc => {
            const typeInfo = DOC_TYPE_LABELS[doc.doc_type] || DOC_TYPE_LABELS.OTHER;
            const ext = doc.filename.split('.').pop()?.toUpperCase() ?? '';
            return (
              <button
                key={doc.id}
                onClick={() => handleDownload(doc)}
                className="w-full flex items-start gap-3 p-3 rounded-lg bg-earth-900/50 border border-earth-800/60 hover:border-earth-700/80 hover:bg-earth-800/40 transition-all text-left group"
              >
                <div className="shrink-0 mt-0.5">
                  <FileText size={14} className="text-earth-500 group-hover:text-earth-300 transition-colors" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-earth-200 font-medium truncate group-hover:text-earth-50 transition-colors">
                    {doc.filename}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border font-medium ${typeInfo.color}`}>
                      {typeInfo.label}
                    </span>
                    <span className="text-[9px] text-earth-600 font-mono">{ext}</span>
                  </div>
                </div>
                <Download size={12} className="shrink-0 text-earth-600 group-hover:text-emerald-400 transition-colors mt-1" />
              </button>
            );
          })}
        </div>
      )}

      {docs.length === 0 && !fetchTriggered && (
        <div className="text-center py-8 text-earth-600">
          <FolderOpen size={32} className="mx-auto mb-3 opacity-40" />
          <p className="text-xs">Brak pobranych dokumentów</p>
          <p className="text-[10px] mt-1 text-earth-700">Kliknij przycisk powyżej aby pobrać SWZ z BZP</p>
        </div>
      )}
    </div>
  );
}

// ─── DetailPanel ──────────────────────────────────────────────────────────────

function DetailPanel({
  tender,
  onClose,
  authFetch,
}: {
  tender: TenderItem;
  onClose: () => void;
  authFetch: (url: string, opts?: RequestInit) => Promise<unknown>;
}) {
  const [tab, setTab] = useState<'details' | 'estimate' | 'documents'>('details');
  const score = tender.match_score ?? 0;
  const pct = Math.round(score * 100);
  const { text: scoreText, bar: scoreBar, bg: scoreBg } = scoreColor(score);
  const days = daysUntil(tender.deadline_at);
  const reasonParts = tender.match_reason?.split(';').map(s => s.trim()).filter(Boolean) ?? [];

  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', damping: 28, stiffness: 260 }}
      className="flex flex-col h-full bg-earth-950 border-l border-earth-800/60 overflow-hidden"
    >
      {/* Panel header */}
      <div className="flex items-start gap-3 p-5 border-b border-earth-800/60 shrink-0">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-earth-500 mb-1 flex items-center gap-1.5">
            <Activity size={11} />
            {tender.source ?? 'BZP'}
            {tender.external_id && (
              <span className="font-mono text-earth-600">{tender.external_id}</span>
            )}
          </p>
          <h3 className="text-sm font-semibold text-earth-100 leading-snug line-clamp-3">
            {tender.title}
          </h3>
        </div>
        <button
          onClick={onClose}
          className="shrink-0 mt-0.5 p-1.5 rounded-lg text-earth-500 hover:text-earth-200 hover:bg-earth-800 transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* Score hero */}
      <div className={`mx-5 mt-4 p-4 rounded-xl border ${scoreBg}`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-earth-400 flex items-center gap-1.5">
            <Target size={12} />
            Score dopasowania
          </span>
          <span className={`text-2xl font-black tabular-nums ${scoreText}`}>{pct}%</span>
        </div>
        <div className="h-2 w-full bg-earth-900 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.7, ease: 'easeOut', delay: 0.1 }}
            className="h-full rounded-full"
            style={{ backgroundColor: scoreBar }}
          />
        </div>
        {reasonParts.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {reasonParts.map((r, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-earth-900/60 border border-earth-700/60 text-earth-400"
              >
                <CheckCircle2 size={9} className="text-emerald-500" />
                {r}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mx-5 mt-4 bg-earth-900 rounded-lg p-1 border border-earth-800 shrink-0">
        {([
          { key: 'details', label: 'Szczegóły', icon: FileText },
          { key: 'documents', label: 'Dokumenty', icon: Download },
          { key: 'estimate', label: 'Kosztorys', icon: BarChart3 },
        ] as const).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-medium transition-all ${
              tab === key
                ? 'bg-earth-700 text-earth-50 shadow-sm'
                : 'text-earth-500 hover:text-earth-300'
            }`}
          >
            <Icon size={12} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-5 pb-6">
        <AnimatePresence mode="wait">
          {tab === 'details' ? (
            <motion.div
              key="details"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              className="space-y-4 pt-4"
            >
              {/* Key fields */}
              <GlassCard className="divide-y divide-earth-800/60">
                {[
                  { icon: Building2, label: 'Zamawiający', value: tender.buyer ?? '—' },
                  { icon: MapPin, label: 'Region', value: tender.voivodeship ?? '—' },
                  {
                    icon: DollarSign,
                    label: 'Wartość',
                    value: fmtPLN(tender.value_pln),
                    accent: true,
                  },
                  {
                    icon: Calendar,
                    label: 'Termin składania',
                    value: fmtDate(tender.deadline_at) + (days !== null && days >= 0 ? ` (${days}d)` : days !== null ? ' — minął' : ''),
                    warn: days !== null && days >= 0 && days <= 3,
                  },
                  { icon: Activity, label: 'Status', value: tender.status },
                  { icon: Tag, label: 'Źródło', value: tender.source ?? '—' },
                  {
                    icon: Calendar,
                    label: 'Opublikowano',
                    value: fmtDate(tender.published_at),
                  },
                ].map(({ icon: Icon, label, value, accent, warn }) => (
                  <div key={label} className="flex items-start gap-3 px-4 py-3">
                    <Icon size={14} className="text-earth-600 mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] text-earth-600 uppercase tracking-wide mb-0.5">{label}</p>
                      <p
                        className={`text-xs font-medium truncate ${
                          accent ? 'text-emerald-400' : warn ? 'text-red-400' : 'text-earth-200'
                        }`}
                      >
                        {value}
                      </p>
                    </div>
                  </div>
                ))}
              </GlassCard>

              {/* CPV codes */}
              {tender.cpv.length > 0 && (
                <div>
                  <p className="text-[10px] text-earth-600 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                    <Tag size={10} /> Kody CPV
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {tender.cpv.map(code => (
                      <span
                        key={code}
                        className="text-[11px] font-mono text-earth-400 bg-earth-800 px-2 py-0.5 rounded border border-earth-700/60"
                      >
                        {code}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* External link */}
              {tender.url && (
                <a
                  href={tender.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 w-full px-4 py-2.5 rounded-xl bg-earth-800/60 border border-earth-700/60 text-sm text-earth-300 hover:text-earth-100 hover:border-earth-600 transition-colors"
                >
                  <ExternalLink size={14} className="text-earth-500" />
                  Otwórz ogłoszenie
                  <ChevronRight size={14} className="ml-auto text-earth-600" />
                </a>
              )}
            </motion.div>
          ) : tab === 'estimate' ? (
            <motion.div
              key="estimate"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
            >
              <EstimatesTab tenderId={tender.id} authFetch={authFetch} />
            </motion.div>
          ) : (
            <motion.div
              key="documents"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
            >
              <DocumentsTab tenderId={tender.id} authFetch={authFetch} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ─── Main ZwiadPage ───────────────────────────────────────────────────────────

export function ZwiadPage() {
  const { accessToken } = useStore();
  const authFetch = useAuthFetch();

  // Feed state
  const [tenders, setTenders] = useState<TenderItem[]>([]);
  const [total, setTotal] = useState(0);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loadingFeed, setLoadingFeed] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [feedError, setFeedError] = useState<string | null>(null);

  // KPI / intel state
  const [kpi, setKpi] = useState<IntelKPI | null>(null);
  const [kpiLoading, setKpiLoading] = useState(true);
  const [seasonality, setSeasonality] = useState<SeasonalityRow[]>([]);

  // UI state
  const [selectedTender, setSelectedTenderLocal] = useState<TenderItem | null>(null);
  const [syncing, setSyncing] = useState(false);

  // ── Smart polling state ─────────────────────────────────────────────────────
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const POLL_INTERVAL = 30_000;

  // Filters
  const [filterStatus, setFilterStatus] = useState('');
  const [filterVoivodeship, setFilterVoivodeship] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [filterCpv, setFilterCpv] = useState('');
  const [filterMinValue, setFilterMinValue] = useState('');
  const [filterMaxValue, setFilterMaxValue] = useState('');
  const [sortBy, setSortBy] = useState('match_score');
  const [filtersExpanded, setFiltersExpanded] = useState(false);

  const feedEndRef = useRef<HTMLDivElement>(null);

  // ── Fetch KPI ───────────────────────────────────────────────────────────────

  const [topProvince, setTopProvince] = useState<Array<{ province: string; n: number }>>([]);
  const [topCpv, setTopCpv] = useState<Array<{ cpv2: string; n: number }>>([]);

  const fetchKPI = useCallback(async () => {
    setKpiLoading(true);
    try {
      const data = await authFetch('/api/v2/intelligence/summary') as IntelSummaryResponse;
      setKpi(data?.kpi ?? null);
      setTopProvince(data?.top_province?.slice(0, 6) ?? []);
      setTopCpv(data?.top_cpv?.slice(0, 5) ?? []);
    } catch {
      // non-critical
    } finally {
      setKpiLoading(false);
    }
  }, [authFetch]);

  const fetchSeasonality = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/intelligence/seasonality') as { data: SeasonalityRow[] };
      setSeasonality(data?.data ?? []);
    } catch {
      // non-critical
    }
  }, [authFetch]);

  // ── Fetch feed ──────────────────────────────────────────────────────────────

  const fetchFeed = useCallback(
    async (reset = true) => {
      if (reset) {
        setLoadingFeed(true);
        setFeedError(null);
      } else {
        setLoadingMore(true);
      }
      try {
        const params = new URLSearchParams({ limit: '20' });
        if (!reset && cursor) params.set('cursor', cursor);
        if (filterStatus) params.set('status', filterStatus);
        if (filterVoivodeship) params.set('voivodeship', filterVoivodeship);
        if (filterSource) params.set('source', filterSource);
        if (filterCpv) params.set('cpv', filterCpv);
        if (filterMinValue) params.set('min_value', filterMinValue);
        if (filterMaxValue) params.set('max_value', filterMaxValue);
        if (sortBy) params.set('sort', sortBy);

        const data = (await authFetch(`/api/v1/tenders?${params}`)) as TenderFeedResponse;
        const items = data?.items ?? [];

        if (reset) {
          setTenders(items);
        } else {
          setTenders(prev => [...prev, ...items]);
        }
        setTotal(data?.total ?? 0);
        setCursor(data?.cursor ?? null);
        setLastRefreshed(new Date());
      } catch (e: unknown) {
        setFeedError((e as Error).message);
      } finally {
        setLoadingFeed(false);
        setLoadingMore(false);
      }
    },
    [authFetch, cursor, filterStatus, filterVoivodeship, filterSource, filterCpv, filterMinValue, filterMaxValue, sortBy],
  );

  // Initial load
  useEffect(() => {
    fetchFeed(true);
    fetchKPI();
    fetchSeasonality();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus, filterVoivodeship, filterSource, filterCpv, filterMinValue, filterMaxValue, sortBy, accessToken]);

  // ── Auto-refresh polling (every 30s) ───────────────────────────────────────
  useEffect(() => {
    const id = setInterval(() => {
      fetchFeed(true);
    }, POLL_INTERVAL);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [POLL_INTERVAL, filterStatus, filterVoivodeship, filterSource, filterCpv, filterMinValue, filterMaxValue, sortBy, accessToken]);

  // ── Ingest run ──────────────────────────────────────────────────────────────

  async function handleIngest() {
    setSyncing(true);
    try {
      const result = (await authFetch('/api/v1/ingest/run?offline=false&days_back=14', { method: 'POST' })) as IngestResult;
      showToast(
        'success',
        `Pobrano ${result.fetched ?? 0} • Nowe: ${result.created ?? 0} • Zaktualizowane: ${result.updated ?? 0}`,
      );
      setTimeout(() => {
        fetchFeed(true);
        fetchKPI();
      }, 1500);
    } catch (e: unknown) {
      showToast('error', 'Błąd pobierania: ' + (e as Error).message);
    } finally {
      setSyncing(false);
    }
  }

  // ── Computed ─────────────────────────────────────────────────────────────────

  const hasMore = cursor !== null && tenders.length < total;

  // ── Last-refreshed label ────────────────────────────────────────────────────
  function fmtLastRefreshed(d: Date | null): string {
    if (!d) return '';
    const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diffSec < 60) return 'przed chwilą';
    const diffMin = Math.floor(diffSec / 60);
    return diffMin === 1 ? '1 min temu' : diffMin + ' min temu';
  }
  const isRecent = lastRefreshed !== null && (Date.now() - lastRefreshed.getTime()) < 60_000;

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full overflow-hidden bg-earth-950">

      {/* ── Top bar ─────────────────────────────────────────────────────────── */}
      <div className="shrink-0 px-6 py-4 border-b border-earth-800/60 space-y-4">
        {/* Header row */}
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-earth-100 flex items-center gap-2">
              <Zap size={18} className="text-emerald-400" />
              Tender Intelligence Hub
            </h2>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-xs text-earth-500">
                {loadingFeed ? 'Ładowanie…' : `${total.toLocaleString('pl-PL')} przetargów w bazie`}
                {seasonality.length > 0 && (
                  <span className="ml-2 text-earth-700">• Sezonowość aktywna</span>
                )}
              </p>
              {lastRefreshed && (
                <span className="flex items-center gap-1.5 text-xs text-earth-600">
                  <span className="text-earth-700">·</span>
                  {/* Pulse dot — zielony gdy odświeżono < 60s temu */}
                  <motion.div
                    animate={isRecent ? { opacity: [1, 0.3, 1] } : { opacity: 0.4 }}
                    transition={isRecent ? { repeat: Infinity, duration: 2 } : {}}
                    className="w-2 h-2 rounded-full bg-emerald-500"
                  />
                  <span>odświeżono {fmtLastRefreshed(lastRefreshed)}</span>
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Manual refresh z RotateCw + spin */}
            <button
              onClick={() => fetchFeed(true)}
              disabled={loadingFeed}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-earth-800 border border-earth-700/50 text-earth-400 hover:text-earth-200 hover:border-earth-600 transition-colors disabled:opacity-40 text-xs font-medium"
              title="Odśwież teraz"
            >
              <RotateCw size={13} className={loadingFeed ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">Odśwież</span>
            </button>
            <button
              onClick={handleIngest}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-earth-950 rounded-xl text-sm font-semibold hover:bg-emerald-400 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {syncing ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Activity size={14} />
              )}
              Pobierz nowe
            </button>
          </div>
        </div>

        {/* KPI strip */}
        <KPIStrip kpi={kpi} loading={kpiLoading} />

        {/* Seasonality mini chart */}
        {seasonality.length > 0 && (
          <div className="rounded-xl bg-earth-900/60 border border-earth-800/40 px-4 pt-2 pb-1">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-earth-600 uppercase tracking-wide">Sezonowość — ostatnie 12 miesięcy</span>
              <span className="text-[10px] text-earth-700 tabular-nums">
                max {Math.max(...seasonality.slice(-12).map(d => d.n_tenders))} / mies.
              </span>
            </div>
            <SeasonalityMini data={seasonality} />
          </div>
        )}

        {/* Top Provinces heatmap + Top CPV mini bar chart */}
        {(topProvince.length > 0 || topCpv.length > 0) && (
          <div className="grid grid-cols-2 gap-3">
            {topProvince.length > 0 && (
              <div className="rounded-xl bg-earth-900/60 border border-earth-800/40 px-4 pt-3 pb-2">
                <span className="text-[10px] text-earth-600 uppercase tracking-wide block mb-2">Mapa intensywności — województwa</span>
                <PolandHeatmap data={topProvince} />
              </div>
            )}
            {topCpv.length > 0 && (
              <div className="rounded-xl bg-earth-900/60 border border-earth-800/40 px-4 pt-3 pb-2">
                <span className="text-[10px] text-earth-600 uppercase tracking-wide block mb-2">Top kategorie CPV</span>
                <ResponsiveContainer width="100%" height={80}>
                  <BarChart data={topCpv} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <XAxis dataKey="cpv2" tick={{ fill: '#6b7280', fontSize: 9 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 6, fontSize: 11 }}
                      labelStyle={{ color: '#9ca3af' }}
                      formatter={(v: number) => [v.toLocaleString('pl-PL'), 'przetargi']}
                    />
                    <Bar dataKey="n" fill="#3b82f6" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Filters bar ─────────────────────────────────────────────────────── */}
      <div className="shrink-0 px-6 py-3 border-b border-earth-800/40 bg-earth-950/80">
        <div className="flex items-center gap-3 flex-wrap">
          {/* Source filter */}
          <div className="relative">
            <select
              value={filterSource}
              onChange={e => setFilterSource(e.target.value)}
              className="appearance-none bg-earth-800 border border-earth-700/60 rounded-xl pl-3 pr-8 py-2 text-xs text-earth-200 focus:outline-none focus:border-emerald-500/50 transition-colors cursor-pointer"
            >
              <option value="">Wszystkie źródła</option>
              <option value="bzp">BZP</option>
              <option value="ted">TED EU</option>
              <option value="bip">BIP</option>
            </select>
            <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-earth-500 pointer-events-none" />
          </div>

          {/* Status filter */}
          <div className="relative">
            <select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              className="appearance-none bg-earth-800 border border-earth-700/60 rounded-xl pl-3 pr-8 py-2 text-xs text-earth-200 focus:outline-none focus:border-emerald-500/50 transition-colors cursor-pointer"
            >
              {STATUS_OPTS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-earth-500 pointer-events-none" />
          </div>

          {/* Voivodeship filter */}
          <div className="relative">
            <select
              value={filterVoivodeship}
              onChange={e => setFilterVoivodeship(e.target.value)}
              className="appearance-none bg-earth-800 border border-earth-700/60 rounded-xl pl-3 pr-8 py-2 text-xs text-earth-200 focus:outline-none focus:border-emerald-500/50 transition-colors cursor-pointer"
            >
              <option value="">Wszystkie regiony</option>
              {VOIVODESHIPS.map(v => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
            <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-earth-500 pointer-events-none" />
          </div>

          {/* Sort */}
          <div className="relative flex items-center gap-1.5">
            <ArrowUpDown size={12} className="text-earth-600" />
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="appearance-none bg-earth-800 border border-earth-700/60 rounded-xl pl-2 pr-7 py-2 text-xs text-earth-200 focus:outline-none focus:border-emerald-500/50 transition-colors cursor-pointer"
            >
              {SORT_OPTS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 text-earth-500 pointer-events-none" />
          </div>

          {/* Filters toggle */}
          <button
            onClick={() => setFiltersExpanded(f => !f)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs transition-colors ${
              filtersExpanded
                ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
                : 'bg-earth-800 border border-earth-700/60 text-earth-500 hover:text-earth-200'
            }`}
          >
            <Filter size={12} />
            Więcej
          </button>

          {/* Active filter chips */}
          {filterSource && (
            <span className="flex items-center gap-1 text-[11px] bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 px-2 py-1 rounded-full">
              {filterSource.toUpperCase()}
              <button onClick={() => setFilterSource('')} className="hover:text-white">
                <X size={10} />
              </button>
            </span>
          )}
          {filterStatus && (
            <span className="flex items-center gap-1 text-[11px] bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-2 py-1 rounded-full">
              Status: {STATUS_OPTS.find(s => s.value === filterStatus)?.label}
              <button onClick={() => setFilterStatus('')} className="hover:text-white">
                <X size={10} />
              </button>
            </span>
          )}
          {filterVoivodeship && (
            <span className="flex items-center gap-1 text-[11px] bg-blue-500/10 border border-blue-500/30 text-blue-400 px-2 py-1 rounded-full">
              {filterVoivodeship}
              <button onClick={() => setFilterVoivodeship('')} className="hover:text-white">
                <X size={10} />
              </button>
            </span>
          )}
          {filterCpv && (
            <span className="flex items-center gap-1 text-[11px] bg-purple-500/10 border border-purple-500/30 text-purple-400 px-2 py-1 rounded-full">
              CPV: {filterCpv}
              <button onClick={() => setFilterCpv('')} className="hover:text-white">
                <X size={10} />
              </button>
            </span>
          )}
          {(filterMinValue || filterMaxValue) && (
            <span className="flex items-center gap-1 text-[11px] bg-amber-500/10 border border-amber-500/30 text-amber-400 px-2 py-1 rounded-full">
              {filterMinValue ? fmtPLN(Number(filterMinValue)) : '0'} - {filterMaxValue ? fmtPLN(Number(filterMaxValue)) : '∞'}
              <button onClick={() => { setFilterMinValue(''); setFilterMaxValue(''); }} className="hover:text-white">
                <X size={10} />
              </button>
            </span>
          )}
        </div>

        {/* Expanded filters row */}
        <AnimatePresence>
          {filtersExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="flex items-center gap-3 flex-wrap pt-3 mt-3 border-t border-earth-800/40">
                {/* CPV input */}
                <div className="flex items-center gap-1.5">
                  <Tag size={12} className="text-earth-600" />
                  <input
                    type="text"
                    value={filterCpv}
                    onChange={e => setFilterCpv(e.target.value)}
                    placeholder="CPV (np. 45 lub 45233142)"
                    className="bg-earth-800 border border-earth-700/60 rounded-xl px-3 py-2 text-xs text-earth-200 placeholder:text-earth-600 focus:outline-none focus:border-emerald-500/50 w-48 transition-colors"
                  />
                </div>

                {/* Value range */}
                <div className="flex items-center gap-1.5">
                  <DollarSign size={12} className="text-earth-600" />
                  <input
                    type="number"
                    value={filterMinValue}
                    onChange={e => setFilterMinValue(e.target.value)}
                    placeholder="Min PLN"
                    className="bg-earth-800 border border-earth-700/60 rounded-xl px-3 py-2 text-xs text-earth-200 placeholder:text-earth-600 focus:outline-none focus:border-emerald-500/50 w-28 transition-colors tabular-nums"
                  />
                  <span className="text-earth-600 text-xs">-</span>
                  <input
                    type="number"
                    value={filterMaxValue}
                    onChange={e => setFilterMaxValue(e.target.value)}
                    placeholder="Max PLN"
                    className="bg-earth-800 border border-earth-700/60 rounded-xl px-3 py-2 text-xs text-earth-200 placeholder:text-earth-600 focus:outline-none focus:border-emerald-500/50 w-28 transition-colors tabular-nums"
                  />
                </div>

                {/* Clear all */}
                <button
                  onClick={() => {
                    setFilterStatus('');
                    setFilterVoivodeship('');
                    setFilterSource('');
                    setFilterCpv('');
                    setFilterMinValue('');
                    setFilterMaxValue('');
                    setSortBy('match_score');
                  }}
                  className="flex items-center gap-1 px-3 py-2 rounded-xl text-xs text-earth-500 hover:text-red-400 bg-earth-800 border border-earth-700/60 hover:border-red-500/30 transition-colors"
                >
                  <X size={11} />
                  Wyczyść filtry
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Body: Feed + Detail Panel ────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Feed — left ~60% */}
        <div
          className={`flex flex-col overflow-hidden transition-all duration-300 ${
            selectedTender ? 'w-[58%]' : 'flex-1'
          }`}
        >
          <div className="flex-1 overflow-y-auto">
            {feedError ? (
              <div className="m-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start gap-3">
                <AlertCircle size={16} className="shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Błąd ładowania przetargów</p>
                  <p className="text-red-500 text-xs mt-1">{feedError}</p>
                  <button
                    onClick={() => fetchFeed(true)}
                    className="mt-2 underline text-xs hover:text-red-300"
                  >
                    Spróbuj ponownie
                  </button>
                </div>
              </div>
            ) : loadingFeed ? (
              <div className="p-4 space-y-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="h-28 rounded-xl bg-earth-800/40 animate-pulse" />
                ))}
              </div>
            ) : tenders.length === 0 ? (
              /* Empty state */
              <div className="flex flex-col items-center justify-center h-full py-20 px-6 text-center">
                <div className="w-16 h-16 rounded-2xl bg-earth-800/60 border border-earth-700/60 flex items-center justify-center mb-4">
                  <RefreshCw size={28} className="text-earth-600" />
                </div>
                <h3 className="text-earth-200 font-semibold mb-2">Brak przetargów</h3>
                <p className="text-earth-500 text-sm max-w-sm mb-1">
                  {filterStatus || filterVoivodeship || filterSource || filterCpv || filterMinValue || filterMaxValue
                    ? 'Zmień filtry aby zobaczyć więcej wyników'
                    : 'Baza przetargów jest pusta. Pobierz pierwsze przetargi z BZP.'}
                </p>
                {!filterStatus && !filterVoivodeship && !filterSource && !filterCpv && !filterMinValue && !filterMaxValue && (
                  <button
                    onClick={handleIngest}
                    disabled={syncing}
                    className="mt-4 flex items-center gap-2 px-5 py-2.5 bg-emerald-500 text-earth-950 rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-colors disabled:opacity-50"
                  >
                    {syncing ? <RefreshCw size={14} className="animate-spin" /> : <Activity size={14} />}
                    Pobierz pierwsze przetargi
                  </button>
                )}
              </div>
            ) : (
              <div className="p-4 space-y-2.5">
                <AnimatePresence mode="popLayout">
                  {tenders.map(tender => (
                    <TenderCard
                      key={tender.id}
                      tender={tender}
                      selected={selectedTender?.id === tender.id}
                      onClick={() =>
                        setSelectedTenderLocal(prev => (prev?.id === tender.id ? null : tender))
                      }
                    />
                  ))}
                </AnimatePresence>

                {/* Load more */}
                <div ref={feedEndRef} className="pt-2 pb-4">
                  {hasMore ? (
                    <button
                      onClick={() => fetchFeed(false)}
                      disabled={loadingMore}
                      className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-earth-800 text-earth-500 hover:text-earth-200 hover:border-earth-700 text-sm transition-colors disabled:opacity-40"
                    >
                      {loadingMore ? (
                        <RefreshCw size={14} className="animate-spin" />
                      ) : (
                        <ChevronDown size={14} />
                      )}
                      {loadingMore
                        ? 'Ładowanie…'
                        : `Załaduj więcej (${total - tenders.length} pozostało)`}
                    </button>
                  ) : tenders.length > 0 ? (
                    <p className="text-center text-[11px] text-earth-700 py-2">
                      Wszystkie {total} przetargów załadowane
                    </p>
                  ) : null}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Detail Panel — right ~40%, slide-in */}
        <AnimatePresence>
          {selectedTender ? (
            <div className="w-[42%] shrink-0 h-full">
              <DetailPanel
                key={selectedTender.id}
                tender={selectedTender}
                onClose={() => setSelectedTenderLocal(null)}
                authFetch={authFetch}
              />
            </div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}
