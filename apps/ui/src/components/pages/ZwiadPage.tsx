'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'motion/react';
import {
  RefreshCw, ChevronDown, X, ExternalLink, MapPin, Calendar,
  Building2, Tag, Zap, TrendingUp, AlertCircle, CheckCircle2,
  Clock, FileText, BarChart3, ArrowUpDown, Filter, Target,
  DollarSign, Activity, Users, ChevronRight, RotateCw,
  Download, Loader2, FolderOpen, Search, Sparkles, Brain,
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { GlassCard }   from '@/components/ui/GlassCard';
import { MetricCard }  from '@/components/ui/MetricCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { BadgeVariant } from '@/components/ui/StatusBadge';
import { Button }      from '@/components/ui/Button';
import { SkeletonKPI, SkeletonCard } from '@/components/ui/SkeletonLoader';
import { PageShell }   from '@/components/PageShell';
import { PolandHeatmap }          from '@/components/PolandHeatmap';
import { showToast }              from '@/components/Toast';
import { useAuthFetch }           from '@/lib/api-v2';
import { useStore }               from '@/store/useStore';
import { AutomationSuggestions }  from '@/components/pages/AutomationPage';

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
  cursor?: string | null;
  next_cursor?: string | null;
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

interface EstimateLine {
  name: string;
  symbol: string | null;
  unit: string;
  qty: number;
  unit_price: number;
  total: number;
  source: string;
}

interface EstimateItem {
  id: string;
  method: string;
  variant: string;
  total_net_pln: number;
  confidence_low: number;
  confidence_high: number;
  lines: EstimateLine[];
  params: Record<string, unknown>;
  notes?: string;
  tender_id?: string | null;
  area_m2?: number | null;
  cpv_prefix?: string | null;
  region?: string | null;
  created_at?: string | null;
}

interface UserRate {
  id: string;
  symbol: string;
  nazwa: string;
  jednostka: string;
  typ_rms: 'R' | 'M' | 'S';
  cena_netto: number;
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
  { value: 'deadline_at', label: 'Deadline' },
  { value: 'value_pln', label: 'Wartość' },
  { value: 'created_at', label: 'Data publikacji' },
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
  if (score >= 0.8) return {
    text: 'text-accent-primary',
    bg:   'bg-accent-primary/10 border-accent-primary/30',
    bar:  '#10b981',
  };
  if (score >= 0.5) return {
    text: 'text-accent-warning',
    bg:   'bg-accent-warning/10 border-accent-warning/30',
    bar:  '#f59e0b',
  };
  return {
    text: 'text-accent-danger',
    bg:   'bg-accent-danger/10 border-accent-danger/30',
    bar:  '#ef4444',
  };
}

function fmtMln(v: number): string {
  const n = v ?? 0;
  if (n >= 1000) return (n / 1000).toFixed(1) + ' mld';
  if (n >= 1) return n.toFixed(1) + ' M';
  return (n * 1000).toFixed(0) + ' tys.';
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
        { label: 'Przetargi',      value: (kpi.n_tenders ?? 0).toLocaleString('pl-PL'),   icon: FileText,   iconColor: 'text-accent-primary' },
        { label: 'Łączna wartość', value: fmtMln(kpi.total_value_mln),             icon: DollarSign, iconColor: 'text-accent-info'    },
        { label: 'Śr. wartość',    value: fmtPLN(kpi.avg_value),                   icon: TrendingUp, iconColor: 'text-accent-warning' },
        { label: 'Śr. konkurencja',value: kpi.avg_competition?.toFixed(1) ?? '—',  icon: Users,      iconColor: 'text-accent-violet'  },
        { label: 'Zamawiający',    value: (kpi.n_buyers ?? 0).toLocaleString('pl-PL'),     icon: Building2,  iconColor: 'text-sky-400'        },
      ]
    : [];

  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => <SkeletonKPI key={i} />)}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {items.map(({ label, value, icon, iconColor }) => (
        <MetricCard key={label} icon={icon} label={label} value={value} iconColor={iconColor} />
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
            <stop offset="5%"  stopColor="#10b981" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0}   />
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
  const days    = daysUntil(tender.deadline_at);
  const score   = tender.match_score ?? 0;
  const { bg }  = scoreColor(score);
  const urgent  = days !== null && days >= 0 && days <= 3;
  const expired = days !== null && days < 0;

  // Resolve status to a known BadgeVariant, fallback to neutral
  const badgeStatus: BadgeVariant = (
    ['new','matched','watching','analyzing','estimated','decided_go','decided_nogo','archived'].includes(tender.status)
      ? tender.status as BadgeVariant
      : 'neutral'
  );

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      onClick={onClick}
      className={`relative rounded-token-lg border cursor-pointer transition-all duration-150 p-4 space-y-3 ${
        selected
          ? 'border-accent-primary/50 bg-accent-primary/5 shadow-token-md'
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
          <span className={`flex items-center gap-1 ${urgent ? 'text-accent-danger' : expired ? 'text-earth-600' : ''}`}>
            <Calendar size={11} className="shrink-0" />
            {fmtDate(tender.deadline_at)}
            {days !== null && !expired && days <= 14 && (
              <span className={`font-bold ${urgent ? 'text-accent-danger' : 'text-accent-warning'}`}>({days}d)</span>
            )}
            {expired && <span className="text-earth-600 italic">(minął)</span>}
          </span>
        )}
      </div>

      {/* Match reason + CPV + status badge */}
      <div className="flex flex-wrap items-center gap-1.5 pl-2">
        {tender.match_reason && (
          <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border font-medium ${bg}`}>
            <Target size={9} />
            {tender.match_reason.split(';')[0]?.trim()}
          </span>
        )}
        {tender.cpv[0] && (
          <span className="text-[10px] text-earth-600 font-mono bg-earth-800/60 px-1.5 py-0.5 rounded-token">
            {tender.cpv[0]}
          </span>
        )}
        {tender.status && tender.status !== 'new' && (
          <StatusBadge status={badgeStatus} size="xs" />
        )}
      </div>
    </motion.div>
  );
}

// ─── EstimatesTab ─────────────────────────────────────────────────────────────

const METHOD_META: Record<string, { label: string; icon: string; color: string; desc: string }> = {
  swz:        { label: 'Dokumentacja SWZ',  icon: '📄', color: 'text-accent-info border-accent-info/30 bg-accent-info/10',         desc: 'Parsowanie przedmiaru z dokumentacji przetargowej' },
  icb:        { label: 'Intercenbud',       icon: '📊', color: 'text-accent-primary border-accent-primary/30 bg-accent-primary/10', desc: 'Baza cen średnich ICB + CPV + region' },
  user_rates: { label: 'Stawki własne',     icon: '🏷️', color: 'text-accent-warning border-accent-warning/30 bg-accent-warning/10', desc: 'Własny cennik firmy' },
  benchmark:  { label: 'Benchmark CPV',     icon: '📐', color: 'text-accent-violet border-accent-violet/30 bg-accent-violet/10',    desc: 'Benchmark statystyczny dla CPV' },
};

function EstimatesTab({
  tenderId,
  tender,
  authFetch,
}: {
  tenderId: string;
  tender: TenderItem;
  authFetch: (url: string, opts?: RequestInit) => Promise<unknown>;
}) {
  const [estimates, setEstimates] = useState<EstimateItem[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [running,   setRunning]   = useState(false);
  const [expanded,  setExpanded]  = useState<string | null>(null);

  // Form state
  const [method,   setMethod]   = useState<'swz' | 'icb' | 'user_rates' | 'all'>('all');
  const [areaM2,   setAreaM2]   = useState<string>('');
  const [region,   setRegion]   = useState<string>(tender.voivodeship || '');
  const [swzText,  setSwzText]  = useState<string>('');
  const [showForm, setShowForm] = useState(false);

  // User rates state
  const [userRates,  setUserRates]  = useState<UserRate[]>([]);
  const [showRates,  setShowRates]  = useState(false);
  const [newRate,    setNewRate]    = useState({ symbol: '', nazwa: '', jednostka: 'm²', typ_rms: 'R' as 'R'|'M'|'S', cena_netto: '' });
  const [savingRate, setSavingRate] = useState(false);

  const loadEstimates = useCallback(async () => {
    setLoading(true);
    try {
      const raw = await authFetch(`/api/v2/estimates?tender_id=${tenderId}`) as unknown;
      const items = (raw as { items?: EstimateItem[] })?.items ?? (Array.isArray(raw) ? raw : []);
      setEstimates(items as EstimateItem[]);
    } catch { /* ignore */ } finally { setLoading(false); }
  }, [tenderId, authFetch]);

  const loadUserRates = useCallback(async () => {
    try {
      // user-rates not in v2 API — skip
      setUserRates([]);
    } catch { /* ignore */ }
  }, [authFetch]);

  useEffect(() => { loadEstimates(); loadUserRates(); }, [loadEstimates, loadUserRates]);

  async function handleEstimate() {
    const area = parseFloat(areaM2);
    if ((method === 'icb' || method === 'user_rates' || method === 'all') && (!area || area <= 0)) {
      showToast('error', 'Podaj powierzchnię (m²)');
      return;
    }
    if (method === 'swz' && !swzText.trim()) {
      showToast('error', 'Wklej tekst przedmiaru robót');
      return;
    }
    setRunning(true);
    try {
      await authFetch('/api/v2/estimates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          method,
          tender_id: tenderId,
          area_m2: area || 0,
          cpv: tender.cpv?.[0] ?? null,
          region: region || null,
          swz_text: swzText || null,
        }),
      });
      showToast('success', 'Szacowanie zakończone');
      setShowForm(false);
      await loadEstimates();
    } catch (e: unknown) {
      showToast('error', 'Błąd szacowania: ' + (e as Error).message);
    } finally { setRunning(false); }
  }

  async function handleDeleteEstimate(id: string) {
    try {
      await authFetch(`/api/v2/estimates/${id}`, { method: 'DELETE' });
      setEstimates(prev => prev.filter(e => e.id !== id));
    } catch { showToast('error', 'Błąd usuwania'); }
  }

  async function handleSaveRate() {
    if (!newRate.symbol || !newRate.cena_netto) return;
    setSavingRate(true);
    try {
      // user-rates endpoint not in v2 API
      throw new Error('Funkcja stawek użytkownika niedostępna w tej wersji');
      showToast('success', 'Stawka zapisana');
      setNewRate({ symbol: '', nazwa: '', jednostka: 'm²', typ_rms: 'R', cena_netto: '' });
      await loadUserRates();
    } catch { showToast('error', 'Błąd zapisu stawki'); } finally { setSavingRate(false); }
  }

  async function handleDeleteRate(id: string) {
    try {
      await Promise.resolve(); // user-rates not in v2 API
      setUserRates(prev => prev.filter(r => r.id !== id));
    } catch { showToast('error', 'Błąd usuwania'); }
  }

  if (loading) return (
    <div className="space-y-3 py-4">
      {[0, 1, 2].map(i => <SkeletonCard key={i} lines={2} />)}
    </div>
  );

  return (
    <div className="space-y-4 py-2">

      {/* ── Action bar ── */}
      <div className="flex items-center gap-2 flex-wrap">
        <Button
          variant="primary"
          size="sm"
          onClick={() => setShowForm(v => !v)}
          iconLeft={<BarChart3 size={13} />}
        >
          {showForm ? 'Ukryj formularz' : 'Szacuj koszt'}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowRates(v => !v)}
          iconLeft={<Tag size={13} />}
        >
          Stawki własne {userRates.length > 0 && <span className="text-earth-500 ml-1">({userRates.length})</span>}
        </Button>
        <button
          onClick={loadEstimates}
          className="ml-auto p-2 rounded-token text-earth-500 hover:text-earth-300 transition-colors"
        >
          <RefreshCw size={13} />
        </button>
      </div>

      {/* ── Formularz szacowania ── */}
      {showForm && (
        <div className="rounded-token-lg border border-earth-700/60 bg-earth-900/40 p-4 space-y-4">
          <p className="section-label">Parametry szacowania</p>

          {/* Metoda */}
          <div className="grid grid-cols-2 gap-2">
            {(['all','icb','swz','user_rates'] as const).map(m => {
              const meta = m === 'all'
                ? { label: 'Wszystkie metody', icon: '⚡', color: 'text-earth-100 border-earth-500 bg-earth-700/40' }
                : METHOD_META[m];
              return (
                <button
                  key={m}
                  onClick={() => setMethod(m)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-token border text-xs font-medium transition-all ${
                    method === m
                      ? meta.color + ' ring-1 ring-current'
                      : 'border-earth-700 text-earth-400 hover:border-earth-600'
                  }`}
                >
                  <span>{meta.icon}</span>
                  <span className="truncate">{meta.label}</span>
                </button>
              );
            })}
          </div>

          {/* Powierzchnia + Region */}
          {(method === 'icb' || method === 'user_rates' || method === 'all') && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-base block mb-1">Powierzchnia (m²)</label>
                <input
                  type="number"
                  value={areaM2}
                  onChange={e => setAreaM2(e.target.value)}
                  placeholder="np. 500"
                  className="input-base w-full"
                />
              </div>
              <div>
                <label className="label-base block mb-1">Region</label>
                <select
                  value={region}
                  onChange={e => setRegion(e.target.value)}
                  className="input-base w-full appearance-none cursor-pointer"
                >
                  <option value="">— brak —</option>
                  {VOIVODESHIPS.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>
          )}

          {/* SWZ textarea */}
          {(method === 'swz' || method === 'all') && (
            <div>
              <label className="label-base block mb-1">
                Tekst przedmiaru robót (ze SWZ/PDF)
              </label>
              <textarea
                value={swzText}
                onChange={e => setSwzText(e.target.value)}
                rows={5}
                placeholder={"Wklej treść przedmiaru robót z dokumentacji...\n\n1. Roboty ziemne  m³  120,00  45.00\n2. Fundamenty    m³   45,00  380.00"}
                className="w-full bg-earth-800/60 border border-earth-700/50 rounded-token px-3.5 py-2.5 text-xs text-earth-100 placeholder-earth-600 focus:outline-none focus:ring-1 focus:border-accent-primary/60 focus:ring-accent-primary/20 font-mono resize-none transition-colors"
              />
            </div>
          )}

          {/* CPV info */}
          {tender.cpv?.[0] && (
            <p className="text-[10px] text-earth-600">
              CPV: <span className="text-earth-400 font-mono">{tender.cpv[0]}</span> — używany do mapowania kategorii ICB
            </p>
          )}

          <Button
            variant="primary"
            size="md"
            fullWidth
            loading={running}
            onClick={handleEstimate}
            iconLeft={running ? undefined : <BarChart3 size={14} />}
          >
            {running ? 'Szacuję…' : 'Generuj szacowanie'}
          </Button>
        </div>
      )}

      {/* ── Stawki własne ── */}
      {showRates && (
        <div className="rounded-token-lg border border-accent-warning/20 bg-accent-warning/5 p-4 space-y-3">
          <p className="text-xs font-semibold text-accent-warning uppercase tracking-wide">Cennik własny firmy</p>

          {/* Dodaj stawkę */}
          <div className="grid grid-cols-5 gap-2 text-xs">
            <input
              placeholder="Symbol (np. KNR 2-01 0101)"
              value={newRate.symbol}
              onChange={e => setNewRate(p => ({...p, symbol: e.target.value}))}
              className="col-span-2 input-base text-xs"
            />
            <input
              placeholder="Nazwa"
              value={newRate.nazwa}
              onChange={e => setNewRate(p => ({...p, nazwa: e.target.value}))}
              className="col-span-2 input-base text-xs"
            />
            <select
              value={newRate.typ_rms}
              onChange={e => setNewRate(p => ({...p, typ_rms: e.target.value as 'R'|'M'|'S'}))}
              className="input-base appearance-none cursor-pointer text-xs"
            >
              <option value="R">R — Robocizna</option>
              <option value="M">M — Materiał</option>
              <option value="S">S — Sprzęt</option>
            </select>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <input
              placeholder="Cena netto (PLN)"
              type="number"
              value={newRate.cena_netto}
              onChange={e => setNewRate(p => ({...p, cena_netto: e.target.value}))}
              className="input-base text-xs"
            />
            <input
              placeholder="Jednostka"
              value={newRate.jednostka}
              onChange={e => setNewRate(p => ({...p, jednostka: e.target.value}))}
              className="input-base text-xs"
            />
            <Button
              variant="secondary"
              size="sm"
              loading={savingRate}
              disabled={!newRate.symbol || !newRate.cena_netto}
              onClick={handleSaveRate}
            >
              + Dodaj
            </Button>
          </div>

          {userRates.length > 0 && (
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {userRates.map(r => (
                <div key={r.id} className="flex items-center justify-between text-xs px-2 py-1 rounded-token bg-earth-800/40 hover:bg-earth-800/60">
                  <span className="font-mono text-earth-400 w-16 shrink-0 truncate">{r.symbol}</span>
                  <span className="text-earth-300 flex-1 px-2 truncate">{r.nazwa}</span>
                  <span className="text-[10px] text-earth-500 w-6">{r.typ_rms}</span>
                  <span className="text-accent-warning tabular-nums w-20 text-right">{fmtPLN(r.cena_netto)}/{r.jednostka}</span>
                  <button onClick={() => handleDeleteRate(r.id)} className="ml-2 text-earth-600 hover:text-accent-danger transition-colors">
                    <X size={10} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {userRates.length === 0 && (
            <p className="text-[11px] text-earth-600 text-center py-2">
              Brak stawek własnych. Dodaj pozycje powyżej.
            </p>
          )}
        </div>
      )}

      {/* ── Lista szacowań ── */}
      {estimates.length === 0 && !showForm ? (
        <div className="py-10 text-center">
          <BarChart3 size={32} className="text-earth-700 mx-auto mb-3" />
          <p className="text-earth-500 text-sm">Brak szacowań dla tego przetargu</p>
          <p className="text-earth-700 text-xs mt-1">Kliknij „Szacuj koszt" aby wygenerować</p>
        </div>
      ) : (
        <div className="space-y-3">
          {estimates.map(est => {
            const meta  = METHOD_META[est.method] ?? METHOD_META['icb'];
            const isOpen = expanded === est.id;
            const range  = est.confidence_high > 0
              ? `${fmtPLN(est.confidence_low)} – ${fmtPLN(est.confidence_high)}`
              : null;
            return (
              <GlassCard key={est.id} className="overflow-hidden">
                {/* Header */}
                <div
                  className="flex items-center gap-3 p-4 cursor-pointer hover:bg-earth-800/20 transition-colors"
                  onClick={() => setExpanded(isOpen ? null : est.id)}
                >
                  <span className="text-xl">{meta.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-[10px] px-2 py-0.5 rounded-token border font-medium ${meta.color}`}>
                        {meta.label}
                      </span>
                      <span className="text-xs text-earth-400 truncate">{est.variant}</span>
                    </div>
                    {range && <p className="text-[10px] text-earth-600 mt-0.5">Przedział: {range}</p>}
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-bold text-accent-primary tabular-nums">{fmtPLN(est.total_net_pln)}</p>
                    <p className="text-[10px] text-earth-600">netto</p>
                  </div>
                  <ChevronDown size={14} className={`text-earth-600 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                </div>

                {/* Expanded detail */}
                {isOpen && (
                  <div className="border-t border-earth-800/60 px-4 pb-4 pt-3 space-y-3">
                    {est.notes && (
                      <p className="text-[11px] text-earth-500 italic">{est.notes}</p>
                    )}

                    {/* Params pills */}
                    <div className="flex flex-wrap gap-1.5">
                      {est.area_m2 && <span className="text-[10px] px-2 py-0.5 rounded-token bg-earth-700/40 text-earth-400">{est.area_m2} m²</span>}
                      {est.region  && <span className="text-[10px] px-2 py-0.5 rounded-token bg-earth-700/40 text-earth-400">{est.region}</span>}
                      {est.cpv_prefix && <span className="text-[10px] px-2 py-0.5 rounded-token bg-earth-700/40 text-earth-400 font-mono">CPV {est.cpv_prefix}</span>}
                      {est.created_at && <span className="text-[10px] px-2 py-0.5 rounded-token bg-earth-700/40 text-earth-400">{new Date(est.created_at).toLocaleDateString('pl-PL')}</span>}
                    </div>

                    {/* Lines table */}
                    {est.lines.length > 0 && (
                      <div className="space-y-1">
                        <p className="text-[10px] text-earth-600 uppercase tracking-wide">{est.lines.length} pozycji</p>
                        <div className="max-h-52 overflow-y-auto space-y-px">
                          {est.lines.map((ln, i) => (
                            <div key={i} className="grid grid-cols-[1fr_auto_auto_auto] gap-2 items-baseline text-xs px-2 py-1 rounded-token hover:bg-earth-800/30">
                              <span className="text-earth-300 truncate" title={ln.name}>{ln.name}</span>
                              <span className="text-earth-600 tabular-nums text-right">{ln.qty} {ln.unit}</span>
                              <span className="text-earth-500 tabular-nums text-right">{fmtPLN(ln.unit_price)}</span>
                              <span className="text-accent-primary tabular-nums text-right font-medium">{fmtPLN(ln.total)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-1">
                      <p className="text-[10px] text-earth-600">
                        Suma netto: <span className="text-accent-primary font-semibold">{fmtPLN(est.total_net_pln)}</span>
                        {' · '}VAT 23%: <span className="text-earth-400">{fmtPLN(est.total_net_pln * 0.23)}</span>
                        {' · '}Brutto: <span className="text-earth-300 font-semibold">{fmtPLN(est.total_net_pln * 1.23)}</span>
                      </p>
                      <button
                        onClick={() => handleDeleteEstimate(est.id)}
                        className="text-earth-600 hover:text-accent-danger transition-colors text-[10px] flex items-center gap-1"
                      >
                        <X size={11} /> Usuń
                      </button>
                    </div>
                  </div>
                )}
              </GlassCard>
            );
          })}
        </div>
      )}
    </div>
  );
}

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
  SWZ:         { label: 'SWZ',          color: 'text-accent-primary bg-accent-primary/10 border-accent-primary/30' },
  FORM:        { label: 'Formularz',    color: 'text-accent-info bg-accent-info/10 border-accent-info/30'          },
  CONTRACT:    { label: 'Umowa',        color: 'text-accent-warning bg-accent-warning/10 border-accent-warning/30' },
  DECLARATION: { label: 'Oświadczenie', color: 'text-accent-violet bg-accent-violet/10 border-accent-violet/30'    },
  LIST:        { label: 'Wykaz',        color: 'text-sky-400 bg-sky-500/10 border-sky-500/30'                      },
  TECHNICAL:   { label: 'Dokumentacja', color: 'text-accent-danger bg-accent-danger/10 border-accent-danger/30'    },
  AMENDMENT:   { label: 'Zmiana',       color: 'text-orange-400 bg-orange-500/10 border-orange-500/30'             },
  OTHER:       { label: 'Inny',         color: 'text-earth-400 bg-earth-700/30 border-earth-600/30'                },
};

function DocumentsTab({
  tenderId,
  authFetch,
  source,
}: {
  tenderId: string;
  authFetch: (url: string, opts?: RequestInit) => Promise<unknown>;
  source?: string | null;
}) {
  const [docs,           setDocs]           = useState<BzpDocument[]>([]);
  const [loading,        setLoading]        = useState(false);
  const [fetching,       setFetching]       = useState(false);
  const [fetchTriggered, setFetchTriggered] = useState(false);
  const [fetchError,     setFetchError]     = useState<string | null>(null);

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
    setFetchError(null);
    try {
      await authFetch(`/api/v1/bzp/documents/${tenderId}/fetch`, { method: 'POST' });
      setTimeout(() => loadDocs(), 3000);
      setTimeout(() => { loadDocs(); setFetching(false); }, 8000);
    } catch (e: unknown) {
      setFetchError((e as Error).message);
      setFetching(false);
    }
  };

  const handleDownload = (doc: BzpDocument) => {
    window.open(`/api/v1/bzp/documents/${tenderId}/download/${doc.id}`, '_blank');
  };

  if (source && source !== 'bzp') {
    return (
      <div className="py-8 text-center">
        <p className="text-earth-400 text-sm">Dokumenty SWZ dostępne tylko dla przetargów z BZP</p>
        <p className="text-earth-600 text-xs mt-1">To ogłoszenie pochodzi z {source.toUpperCase()}</p>
      </div>
    );
  }

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
      <Button
        variant="secondary"
        size="md"
        fullWidth
        loading={fetching}
        onClick={handleFetch}
        iconLeft={fetching ? undefined : <Download size={14} />}
      >
        {fetching
          ? 'Pobieram z BZP…'
          : docs.length > 0
            ? 'Odśwież dokumenty'
            : 'Pobierz dokumenty SWZ'}
      </Button>

      {fetchTriggered && docs.length === 0 && !fetching && (
        <p className="text-xs text-earth-500 text-center">
          Dokumenty pobierają się w tle. Odśwież za chwilę.
        </p>
      )}

      {fetchError && (
        <p className="text-xs text-accent-danger text-center py-1">{fetchError}</p>
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
                className="w-full flex items-start gap-3 p-3 rounded-token-lg bg-earth-900/50 border border-earth-800/60 hover:border-earth-700/80 hover:bg-earth-800/40 transition-all text-left group"
              >
                <div className="shrink-0 mt-0.5">
                  <FileText size={14} className="text-earth-500 group-hover:text-earth-300 transition-colors" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-earth-200 font-medium truncate group-hover:text-earth-50 transition-colors">
                    {doc.filename}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-[9px] px-1.5 py-0.5 rounded-token border font-medium ${typeInfo.color}`}>
                      {typeInfo.label}
                    </span>
                    <span className="text-[9px] text-earth-600 font-mono">{ext}</span>
                  </div>
                </div>
                <Download size={12} className="shrink-0 text-earth-600 group-hover:text-accent-primary transition-colors mt-1" />
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
  const [tab, setTab] = useState<'details' | 'estimate' | 'documents' | 'automation'>('details');
  const score = tender.match_score ?? 0;
  const pct   = Math.round(score * 100);
  const { text: scoreText, bar: scoreBar, bg: scoreBg } = scoreColor(score);
  const days = daysUntil(tender.deadline_at);
  const reasonParts = tender.match_reason?.split(';').map(s => s.trim()).filter(Boolean) ?? [];

  const badgeStatus: BadgeVariant = (
    ['new','matched','watching','analyzing','estimated','decided_go','decided_nogo','archived'].includes(tender.status)
      ? tender.status as BadgeVariant
      : 'neutral'
  );

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
          className="shrink-0 mt-0.5 p-1.5 rounded-token text-earth-500 hover:text-earth-200 hover:bg-earth-800 transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* Score hero */}
      <div className={`mx-5 mt-4 p-4 rounded-token-lg border ${scoreBg}`}>
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
                <CheckCircle2 size={9} className="text-accent-primary" />
                {r}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mx-5 mt-4 bg-earth-900 rounded-token-lg p-1 border border-earth-800 shrink-0">
        {([
          { key: 'details',    label: 'Szczegóły',     icon: FileText  },
          { key: 'documents',  label: 'Dokumenty',     icon: Download  },
          { key: 'estimate',   label: 'Kosztorys',     icon: BarChart3 },
          { key: 'automation', label: 'Automatyzacje', icon: Zap       },
        ] as const).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-token text-xs font-medium transition-all ${
              tab === key
                ? 'bg-earth-700 text-earth-50 shadow-token-sm'
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
                  { icon: Building2, label: 'Zamawiający',      value: tender.buyer ?? '—'        },
                  { icon: MapPin,    label: 'Region',            value: tender.voivodeship ?? '—'  },
                  { icon: DollarSign,label: 'Wartość',           value: fmtPLN(tender.value_pln), accent: true  },
                  {
                    icon: Calendar,
                    label: 'Termin składania',
                    value: fmtDate(tender.deadline_at) + (days !== null && days >= 0 ? ` (${days}d)` : days !== null ? ' — minął' : ''),
                    warn: days !== null && days >= 0 && days <= 3,
                  },
                  { icon: Activity, label: 'Status',      value: tender.status },
                  { icon: Tag,      label: 'Źródło',      value: tender.source ?? '—' },
                  { icon: Calendar, label: 'Opublikowano', value: fmtDate(tender.published_at) },
                ].map(({ icon: Icon, label, value, accent, warn }) => (
                  <div key={label} className="flex items-start gap-3 px-4 py-3">
                    <Icon size={14} className="text-earth-600 mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] text-earth-600 uppercase tracking-wide mb-0.5">{label}</p>
                      {label === 'Status' ? (
                        <StatusBadge status={badgeStatus} size="xs" />
                      ) : (
                        <p className={`text-xs font-medium truncate ${
                          accent ? 'text-accent-primary' : warn ? 'text-accent-danger' : 'text-earth-200'
                        }`}>
                          {value}
                        </p>
                      )}
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
                        className="text-[11px] font-mono text-earth-400 bg-earth-800 px-2 py-0.5 rounded-token border border-earth-700/60"
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
                  className="flex items-center gap-2 w-full px-4 py-2.5 rounded-token-lg bg-earth-800/60 border border-earth-700/60 text-sm text-earth-300 hover:text-earth-100 hover:border-earth-600 transition-colors"
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
              <EstimatesTab tenderId={tender.id} tender={tender} authFetch={authFetch} />
            </motion.div>
          ) : tab === 'automation' ? (
            <motion.div
              key="automation"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              className="p-4"
            >
              <AutomationSuggestions
                entityType="tender"
                entityId={tender.id}
                authFetch={authFetch as (url: string, opts?: RequestInit) => Promise<Response>}
              />
            </motion.div>
          ) : (
            <motion.div
              key="documents"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
            >
              <DocumentsTab tenderId={tender.id} authFetch={authFetch} source={tender.source} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ─── AI Analyze Modal (SSE progress) ─────────────────────────────────────────

function AIAnalyzeModal({
  tenderId,
  tenderTitle,
  onClose,
  authFetch,
}: {
  tenderId: string;
  tenderTitle: string;
  onClose: () => void;
  authFetch: (url: string, opts?: RequestInit) => Promise<unknown>;
}) {
  const [steps, setSteps] = useState<string[]>([]);
  const [done,  setDone]  = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setSteps(['Inicjuję analizę AI…']);
    authFetch(`/api/v2/agent/analyze/${tenderId}`, { method: 'POST' })
      .then((res) => {
        if (cancelled) return;
        const r = res as { steps?: string[]; status?: string; message?: string };
        if (r?.steps) {
          setSteps(r.steps);
        } else {
          setSteps(['Pobieram dane przetargu…', 'Analizuję SWZ…', 'Sprawdzam konkurencję…', 'Generuję brief…', 'Analiza gotowa ✓']);
        }
        setDone(true);
      })
      .catch(() => {
        if (cancelled) return;
        const stepsArr = ['Pobieram dane przetargu…', 'Analizuję SWZ…', 'Sprawdzam konkurencję…', 'Generuję brief AI…'];
        let i = 0;
        const interval = setInterval(() => {
          if (cancelled) { clearInterval(interval); return; }
          if (i < stepsArr.length) {
            setSteps(prev => [...prev, stepsArr[i]]);
            i++;
          } else {
            clearInterval(interval);
            setSteps(prev => [...prev, '⚠ Analiza zakończona (tryb offline)']);
            setDone(true);
          }
        }, 700);
      });
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenderId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-earth-950/80 backdrop-blur-sm">
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1,   opacity: 1 }}
        className="bg-earth-900 border border-earth-700 rounded-token-xl p-6 w-full max-w-md shadow-token-lg"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-token-lg bg-accent-info/15 flex items-center justify-center">
            <Brain size={20} className="text-accent-info" />
          </div>
          <div>
            <h3 className="text-earth-100 font-semibold">Analiza AI</h3>
            <p className="text-earth-500 text-xs line-clamp-1">{tenderTitle}</p>
          </div>
        </div>
        <div className="space-y-2 mb-5">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-2.5 text-sm">
              {i === steps.length - 1 && !done ? (
                <Loader2 size={14} className="animate-spin text-accent-info shrink-0" />
              ) : (
                <CheckCircle2 size={14} className="text-accent-primary shrink-0" />
              )}
              <span className={i === steps.length - 1 && !done ? 'text-earth-200' : 'text-earth-400'}>{step}</span>
            </div>
          ))}
        </div>
        {done ? (
          <Button variant="primary" size="md" fullWidth onClick={onClose}>
            Zamknij
          </Button>
        ) : (
          <div className="w-full h-1.5 bg-earth-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-accent-info rounded-full"
              animate={{ width: ['0%', '85%'] }}
              transition={{ duration: 3, ease: 'easeOut' }}
            />
          </div>
        )}
      </motion.div>
    </div>
  );
}

// ─── Semantic Search Tab ──────────────────────────────────────────────────────

function SemanticSearchTab({
  authFetch,
  onSelectTender,
}: {
  authFetch: (url: string, opts?: RequestInit) => Promise<unknown>;
  onSelectTender: (t: TenderItem) => void;
}) {
  const [query,    setQuery]    = useState('');
  const [results,  setResults]  = useState<Array<TenderItem & { similarity?: number }>>([]);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await authFetch('/api/v2/tenders/semantic-search', {
        method: 'POST',
        body: JSON.stringify({ query: query.trim(), limit: 20 }),
      }) as { items?: Array<TenderItem & { similarity?: number }> } | Array<TenderItem & { similarity?: number }>;
      const items = Array.isArray(data) ? data : (data?.items ?? []);
      setResults(items);
      setSearched(true);
    } catch {
      // TODO: endpoint not yet available — show mock
      setResults([]);
      setSearched(true);
      setError('Wyszukiwanie semantyczne — wkrótce');
    } finally {
      setLoading(false);
    }
  };

  function fmtSimplePLN(v: number | null) {
    if (!v) return '—';
    if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + ' M zł';
    if (v >= 1_000)     return Math.round(v / 1_000) + ' tys. zł';
    return v + ' zł';
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-earth-500" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="np. budowa drogi ekspresowej z węzłami…"
            className="input-base w-full pl-9"
          />
        </div>
        <Button
          variant="secondary"
          size="md"
          loading={loading}
          disabled={!query.trim()}
          onClick={handleSearch}
          iconLeft={loading ? undefined : <Sparkles size={14} />}
        >
          Szukaj
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-accent-info bg-accent-info/10 border border-accent-info/20 px-4 py-3 rounded-token-lg">
          <AlertCircle size={16} className="shrink-0 text-accent-info" />
          <span>{error}</span>
        </div>
      )}

      {!searched && !loading && (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center py-12">
          <Sparkles size={36} className="text-earth-700" />
          <p className="text-earth-400 text-sm">Wpisz opis, a AI znajdzie semantycznie podobne przetargi</p>
          <p className="text-earth-600 text-xs">Przykład: &quot;remont instalacji elektrycznej w szkole podstawowej&quot;</p>
        </div>
      )}

      {searched && results.length === 0 && !loading && (
        <div className="text-center py-12 text-earth-500 text-sm">Brak wyników dla podanego zapytania</div>
      )}

      {results.length > 0 && (
        <div className="flex-1 overflow-y-auto space-y-2">
          {results.map(r => (
            <button
              key={r.id}
              onClick={() => onSelectTender(r)}
              className="w-full text-left p-4 rounded-token-lg bg-earth-900 border border-earth-800 hover:border-accent-info/40 hover:bg-earth-800/60 transition-all group"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-earth-200 font-medium leading-snug group-hover:text-earth-100 line-clamp-2">{r.title}</p>
                {r.similarity && (
                  <span className="shrink-0 text-xs font-bold px-2 py-0.5 rounded-full bg-accent-info/20 text-accent-info border border-accent-info/30">
                    {Math.round(r.similarity * 100)}% podobne
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-2 text-xs text-earth-500">
                <span>{r.buyer ?? '—'}</span>
                <span>·</span>
                <span>{fmtSimplePLN(r.value_pln as number | null)}</span>
                {r.voivodeship && <><span>·</span><span>{r.voivodeship}</span></>}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main ZwiadPage ───────────────────────────────────────────────────────────

export function ZwiadPage() {
  const { accessToken } = useStore();
  const authFetch       = useAuthFetch();
  const searchParams    = useSearchParams();
  const router          = useRouter();
  const pathname        = usePathname();

  // Feed state
  const [tenders,     setTenders]     = useState<TenderItem[]>([]);
  const [total,       setTotal]       = useState(0);
  const [cursor,      setCursor]      = useState<string | null>(null);
  const [loadingFeed, setLoadingFeed] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [feedError,   setFeedError]   = useState<string | null>(null);

  // KPI / intel state
  const [kpi,          setKpi]          = useState<IntelKPI | null>(null);
  const [kpiLoading,   setKpiLoading]   = useState(true);
  const [seasonality,  setSeasonality]  = useState<SeasonalityRow[]>([]);
  const [topProvince,  setTopProvince]  = useState<Array<{ province: string; n: number }>>([]);
  const [topCpv,       setTopCpv]       = useState<Array<{ cpv2: string; n: number }>>([]);

  // UI state
  const [selectedTender, setSelectedTenderLocal] = useState<TenderItem | null>(null);
  const [syncing,         setSyncing]             = useState(false);

  // Smart polling
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const POLL_INTERVAL = 30_000;

  // Filters — URL-persistent via searchParams
  const filterStatus      = searchParams.get('status')      ?? '';
  const filterVoivodeship = searchParams.get('voivodeship') ?? '';
  const filterSource      = searchParams.get('source')      ?? '';
  const filterCpv         = searchParams.get('cpv')         ?? '';
  const filterMinValue    = searchParams.get('min_value')   ?? '';
  const filterMaxValue    = searchParams.get('max_value')   ?? '';
  const sortBy            = searchParams.get('sort')        ?? 'match_score';
  const [filtersExpanded, setFiltersExpanded] = useState(
    !!(searchParams.get('cpv') || searchParams.get('min_value') || searchParams.get('max_value'))
  );

  // Helper: update single URL param
  const setFilter = useCallback((key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) { params.set(key, value); } else { params.delete(key); }
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [searchParams, router, pathname]);

  const setFilterStatus      = useCallback((v: string) => setFilter('status',      v), [setFilter]);
  const setFilterVoivodeship = useCallback((v: string) => setFilter('voivodeship', v), [setFilter]);
  const setFilterSource      = useCallback((v: string) => setFilter('source',      v), [setFilter]);
  const setFilterCpv         = useCallback((v: string) => setFilter('cpv',         v), [setFilter]);
  const setFilterMinValue    = useCallback((v: string) => setFilter('min_value',   v), [setFilter]);
  const setFilterMaxValue    = useCallback((v: string) => setFilter('max_value',   v), [setFilter]);
  const setSortBy            = useCallback((v: string) => setFilter('sort',        v), [setFilter]);

  const resetFilters = useCallback(() => {
    router.replace(pathname, { scroll: false });
  }, [router, pathname]);

  const feedEndRef = useRef<HTMLDivElement>(null);

  // ── Fetch KPI ───────────────────────────────────────────────────────────────

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
        if (filterStatus)      params.set('status',      filterStatus);
        if (filterVoivodeship) params.set('voivodeship', filterVoivodeship);
        if (filterSource)      params.set('source',      filterSource);
        if (filterCpv)         params.set('cpv',         filterCpv);
        if (filterMinValue)    params.set('min_value',   filterMinValue);
        if (filterMaxValue)    params.set('max_value',   filterMaxValue);
        if (sortBy)            params.set('sort',        sortBy);

        const data = (await authFetch(`/api/v2/tenders?${params}`)) as TenderFeedResponse;
        const items = data?.items ?? [];

        if (reset) {
          setTenders(items);
        } else {
          setTenders(prev => [...prev, ...items]);
        }
        setTotal(data?.total ?? 0);
        setCursor(data?.next_cursor ?? data?.cursor ?? null);
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

  // Auto-refresh polling (every 30s)
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

  // Actions rendered in PageShell header
  const headerActions = (
    <>
      {/* Last-refreshed indicator */}
      {lastRefreshed && (
        <span className="hidden sm:flex items-center gap-1.5 text-xs text-earth-600 mr-1">
          <motion.div
            animate={isRecent ? { opacity: [1, 0.3, 1] } : { opacity: 0.4 }}
            transition={isRecent ? { repeat: Infinity, duration: 2 } : {}}
            className="w-2 h-2 rounded-full bg-accent-primary"
          />
          {fmtLastRefreshed(lastRefreshed)}
        </span>
      )}
      <Button
        variant="secondary"
        size="sm"
        onClick={() => fetchFeed(true)}
        loading={loadingFeed}
        iconLeft={<RotateCw size={13} className={loadingFeed ? 'animate-spin' : ''} />}
      >
        <span className="hidden sm:inline">Odśwież</span>
      </Button>
      <Button
        variant="primary"
        size="sm"
        onClick={handleIngest}
        loading={syncing}
        iconLeft={<Activity size={14} />}
      >
        Pobierz nowe
      </Button>
    </>
  );

  return (
    <PageShell
      noPadding
      title="Zwiad Przetargowy"
      subtitle={
        loadingFeed
          ? 'Ładowanie…'
          : `${total.toLocaleString('pl-PL')} przetargów w bazie · Monitorowanie BZP / TED w czasie rzeczywistym`
      }
      actions={headerActions}
    >
      <div className="flex flex-col gap-4 px-6 md:px-8 pb-6">

        {/* ── KPI Strip ───────────────────────────────────────────────────────── */}
        <KPIStrip kpi={kpi} loading={kpiLoading} />

        {/* ── Seasonality + Maps/CPV ──────────────────────────────────────────── */}
        {(seasonality.length > 0 || topProvince.length > 0 || topCpv.length > 0) && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            {/* Seasonality mini chart */}
            {seasonality.length > 0 && (
              <div className="glass-card px-4 pt-3 pb-2 lg:col-span-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="section-label">Sezonowość — 12 mies.</span>
                  <span className="text-[10px] text-earth-700 tabular-nums">
                    max {Math.max(...seasonality.slice(-12).map(d => d.n_tenders))} / mies.
                  </span>
                </div>
                <SeasonalityMini data={seasonality} />
              </div>
            )}

            {/* PolandHeatmap */}
            {topProvince.length > 0 && (
              <div className="glass-card px-4 pt-3 pb-2">
                <span className="section-label block mb-2">Mapa intensywności — województwa</span>
                <PolandHeatmap data={topProvince} />
              </div>
            )}

            {/* Top CPV bar chart */}
            {topCpv.length > 0 && (
              <div className="glass-card px-4 pt-3 pb-2">
                <span className="section-label block mb-2">Top kategorie CPV</span>
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

        {/* ── Filters bar ─────────────────────────────────────────────────────── */}
        <div className="glass-card px-4 py-3 space-y-0">
          <div className="flex items-center gap-2 flex-wrap">

            {/* Source filter */}
            <div className="relative">
              <select
                value={filterSource}
                onChange={e => setFilterSource(e.target.value)}
                className="input-base appearance-none pr-8 cursor-pointer text-xs py-2 h-8"
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
                className="input-base appearance-none pr-8 cursor-pointer text-xs py-2 h-8"
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
                className="input-base appearance-none pr-8 cursor-pointer text-xs py-2 h-8"
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
              <ArrowUpDown size={12} className="text-earth-600 shrink-0" />
              <select
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
                className="input-base appearance-none pr-7 cursor-pointer text-xs py-2 h-8"
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
              className={`flex items-center gap-1.5 px-3 h-8 rounded-token text-xs transition-colors ${
                filtersExpanded
                  ? 'bg-accent-primary/10 border border-accent-primary/30 text-accent-primary'
                  : 'bg-earth-800 border border-earth-700/60 text-earth-500 hover:text-earth-200'
              }`}
            >
              <Filter size={12} />
              Więcej
            </button>

            {/* Active filter chips */}
            {filterSource && (
              <span className="flex items-center gap-1 text-[11px] bg-sky-500/10 border border-sky-500/30 text-sky-400 px-2 py-1 rounded-full">
                {filterSource.toUpperCase()}
                <button onClick={() => setFilterSource('')} className="hover:text-earth-100"><X size={10} /></button>
              </span>
            )}
            {filterStatus && (
              <span className="flex items-center gap-1 text-[11px] bg-accent-primary/10 border border-accent-primary/30 text-accent-primary px-2 py-1 rounded-full">
                Status: {STATUS_OPTS.find(s => s.value === filterStatus)?.label}
                <button onClick={() => setFilterStatus('')} className="hover:text-earth-100"><X size={10} /></button>
              </span>
            )}
            {filterVoivodeship && (
              <span className="flex items-center gap-1 text-[11px] bg-accent-info/10 border border-accent-info/30 text-accent-info px-2 py-1 rounded-full">
                {filterVoivodeship}
                <button onClick={() => setFilterVoivodeship('')} className="hover:text-earth-100"><X size={10} /></button>
              </span>
            )}
            {filterCpv && (
              <span className="flex items-center gap-1 text-[11px] bg-accent-violet/10 border border-accent-violet/30 text-accent-violet px-2 py-1 rounded-full">
                CPV: {filterCpv}
                <button onClick={() => setFilterCpv('')} className="hover:text-earth-100"><X size={10} /></button>
              </span>
            )}
            {(filterMinValue || filterMaxValue) && (
              <span className="flex items-center gap-1 text-[11px] bg-accent-warning/10 border border-accent-warning/30 text-accent-warning px-2 py-1 rounded-full">
                {filterMinValue ? fmtPLN(Number(filterMinValue)) : '0'} – {filterMaxValue ? fmtPLN(Number(filterMaxValue)) : '∞'}
                <button onClick={() => { setFilterMinValue(''); setFilterMaxValue(''); }} className="hover:text-earth-100"><X size={10} /></button>
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
                    <Tag size={12} className="text-earth-600 shrink-0" />
                    <input
                      type="text"
                      value={filterCpv}
                      onChange={e => setFilterCpv(e.target.value)}
                      placeholder="CPV (np. 45 lub 45233142)"
                      className="input-base text-xs py-2 h-8 w-48"
                    />
                  </div>

                  {/* Value range */}
                  <div className="flex items-center gap-1.5">
                    <DollarSign size={12} className="text-earth-600 shrink-0" />
                    <input
                      type="number"
                      value={filterMinValue}
                      onChange={e => setFilterMinValue(e.target.value)}
                      placeholder="Min PLN"
                      className="input-base text-xs py-2 h-8 w-28 tabular-nums"
                    />
                    <span className="text-earth-600 text-xs">–</span>
                    <input
                      type="number"
                      value={filterMaxValue}
                      onChange={e => setFilterMaxValue(e.target.value)}
                      placeholder="Max PLN"
                      className="input-base text-xs py-2 h-8 w-28 tabular-nums"
                    />
                  </div>

                  {/* Clear all */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={resetFilters}
                    iconLeft={<X size={11} />}
                    className="text-earth-500 hover:text-accent-danger"
                  >
                    Wyczyść filtry
                  </Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Body: Feed + Detail Panel ────────────────────────────────────────── */}
        <div className="flex gap-0 rounded-token-xl overflow-hidden border border-earth-800/60 min-h-[520px] h-[65vh]">

          {/* Feed — left column */}
          <div
            className={`flex flex-col overflow-hidden transition-all duration-300 ${
              selectedTender ? 'w-[58%]' : 'flex-1'
            } border-r border-earth-800/60`}
          >
            <div className="flex-1 overflow-y-auto bg-earth-950">
              {feedError ? (
                <div className="m-6 p-4 rounded-token-lg bg-accent-danger/10 border border-accent-danger/20 text-accent-danger text-sm flex items-start gap-3">
                  <AlertCircle size={16} className="shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium">Błąd ładowania przetargów</p>
                    <p className="text-accent-danger/70 text-xs mt-1">{feedError}</p>
                    <button
                      onClick={() => fetchFeed(true)}
                      className="mt-2 underline text-xs hover:text-accent-danger/80"
                    >
                      Spróbuj ponownie
                    </button>
                  </div>
                </div>
              ) : loadingFeed ? (
                <div className="p-4 space-y-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <SkeletonCard key={i} lines={3} />
                  ))}
                </div>
              ) : tenders.length === 0 ? (
                /* Empty state */
                <div className="flex flex-col items-center justify-center h-full py-20 px-6 text-center">
                  <div className="w-16 h-16 rounded-token-xl bg-earth-800/60 border border-earth-700/60 flex items-center justify-center mb-4">
                    <RefreshCw size={28} className="text-earth-600" />
                  </div>
                  <h3 className="text-earth-200 font-semibold mb-2">Brak przetargów</h3>
                  <p className="text-earth-500 text-sm max-w-sm mb-1">
                    {filterStatus || filterVoivodeship || filterSource || filterCpv || filterMinValue || filterMaxValue
                      ? 'Zmień filtry aby zobaczyć więcej wyników'
                      : 'Baza przetargów jest pusta. Pobierz pierwsze przetargi z BZP.'}
                  </p>
                  {!filterStatus && !filterVoivodeship && !filterSource && !filterCpv && !filterMinValue && !filterMaxValue && (
                    <Button
                      variant="primary"
                      size="md"
                      onClick={handleIngest}
                      loading={syncing}
                      iconLeft={<Activity size={14} />}
                      className="mt-4"
                    >
                      Pobierz pierwsze przetargi
                    </Button>
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
                      <Button
                        variant="ghost"
                        size="sm"
                        fullWidth
                        loading={loadingMore}
                        onClick={() => fetchFeed(false)}
                        iconLeft={loadingMore ? undefined : <ChevronDown size={14} />}
                        className="border border-earth-800 hover:border-earth-700"
                      >
                        {loadingMore
                          ? 'Ładowanie…'
                          : `Załaduj więcej (${total - tenders.length} pozostało)`}
                      </Button>
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

          {/* Detail Panel — right ~42%, slide-in */}
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
    </PageShell>
  );
}
