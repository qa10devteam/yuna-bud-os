'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine,
  LineChart, Line, CartesianGrid, Legend,
} from 'recharts';
import {
  Calculator, Search, Plus, Trash2, Download, FileSpreadsheet, FileText,
  ChevronRight, X, Loader2, Zap, TrendingUp, AlertCircle, Edit2, Save,
  RotateCcw, SlidersHorizontal, Info, PanelRightOpen, PanelRightClose,
  BookOpen, CheckCircle2, Package, Database, Columns2, FileDown,
  BarChart2, Target, Shield, RefreshCw, Wrench, ChevronDown, ChevronUp, AlertTriangle,
  Upload, Bot,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';

// ── Types ──────────────────────────────────────────────────────────────────────

interface TenderItem {
  id: string;
  title: string;
  buyer: string;
  cpv: string[];
  value_pln: number | string | null;
}

/** Pozycja kosztorysu — pełny model R/M/S */
interface KPozycja {
  id?: string;
  lp: number;
  kst_code: string;
  opis: string;
  jednostka: string;
  ilosc: number;
  r_jcena: number;
  m_jcena: number;
  s_jcena: number;
  jcena_netto: number;
  wartosc_netto: number;
  r_total?: number;
  m_total?: number;
  s_total?: number;
  ko_total?: number;
  z_total?: number;
  kz_total?: number;
  is_anomaly?: boolean;
  icb_r_id?: number | null;
  icb_m_id?: number | null;
  icb_s_id?: number | null;
}

/** Narzuty kosztorysu */
interface Narzuty {
  ko_r_pct: number;
  ko_s_pct: number;
  z_pct: number;
  kz_pct: number;
  vat_pct: number;
}

interface KosztorysHeader {
  id: string;
  nazwa: string;
  inwestor?: string;
  obiekt?: string;
  typ: string;
  status: string;
  suma_netto: number;
  suma_brutto: number;
  suma_r: number;
  suma_m: number;
  suma_s: number;
  benchmark_percentile?: number;
  win_probability?: number;
  anomaly_score?: number;
  narzuty?: Narzuty;
}

interface IcbItem {
  id: number;
  symbol?: string;
  nazwa: string;
  jednostka: string;
  cena_netto: number;
  typ_rms: 'R' | 'M' | 'S';
  category?: string;
}

interface BenchmarkData {
  n_tenders: number;
  avg_value: number;
  median_value: number;
  p25_value: number;
  p75_value: number;
  our_percentile?: number;
}

interface IntelligenceResult {
  benchmark_percentile?: number;
  win_probability?: number;
  sweet_spot?: number;
  anomaly_score?: number;
  anomalies?: number;
  total_checked?: number;
  material_risk?: Array<{ category: string; risk_score: number; change_yoy_pct: number }>;
}

interface PriceIndex {
  quarter: string;
  R: number;
  M: number;
  S: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmtPLN(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(Number(n))) return '—';
  return Number(n).toLocaleString('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 });
}

function fmtNum(n: number, dec = 2): string {
  const v = n ?? 0;
  return v.toLocaleString('pl-PL', { maximumFractionDigits: dec });
}

function pct(a: number, total: number): string {
  if (!total) return '0%';
  return (((a ?? 0) / total) * 100).toFixed(1) + '%';
}

const DEFAULT_NARZUTY: Narzuty = { ko_r_pct: 70, ko_s_pct: 30, z_pct: 12.5, kz_pct: 7.1, vat_pct: 23 };

// ── Badge helpers ──────────────────────────────────────────────────────────────

function WinBadge({ p }: { p: number }) {
  const cls = p > 0.6 ? 'bg-accent-success/15 text-green-400 border-green-500/30'
    : p > 0.35 ? 'bg-accent-warning/15 text-amber-400 border-amber-500/30'
    : 'bg-accent-danger/15 text-red-400 border-red-500/30';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${cls}`}>
      <Target className="w-3 h-3" />
      P(wygrania) {(p * 100).toFixed(1)}%
    </span>
  );
}

function PercentileBadge({ p }: { p: number }) {
  const cls = p < 50 ? 'bg-accent-success/15 text-green-400 border-green-500/30'
    : p < 75 ? 'bg-accent-warning/15 text-amber-400 border-amber-500/30'
    : 'bg-accent-danger/15 text-red-400 border-red-500/30';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${cls}`}>
      <BarChart2 className="w-3 h-3" />
      Percentyl {p.toFixed(0)}%
    </span>
  );
}

function AnomalyBadge({ score }: { score: number }) {
  const cls = score < 0.1 ? 'bg-accent-success/15 text-green-400 border-green-500/30'
    : score < 0.25 ? 'bg-accent-warning/15 text-amber-400 border-amber-500/30'
    : 'bg-accent-danger/15 text-red-400 border-red-500/30';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${cls}`}>
      <Shield className="w-3 h-3" />
      Anomalie {(score * 100).toFixed(0)}%
    </span>
  );
}

// ── ICB Search Sidebar ─────────────────────────────────────────────────────────

function IcbSidebar({
  onSelect,
  onClose,
}: {
  onSelect: (item: IcbItem, field: 'R' | 'M' | 'S') => void;
  onClose: () => void;
}) {
  const authFetch = useAuthFetch();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<IcbItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [selectedType, setSelectedType] = useState<'all' | 'R' | 'M' | 'S'>('all');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) { setResults([]); setNotFound(false); return; }
    setLoading(true);
    setNotFound(false);
    try {
      const typ = selectedType === 'all' ? '' : `&typ_rms=${selectedType}`;
      const data = await authFetch(`/api/v2/icb/suggest?q=${encodeURIComponent(q)}${typ}&limit=30`);
      const items: IcbItem[] = Array.isArray(data) ? data : (data as any)?.results ?? (data as any)?.items ?? [];
      setResults(items);
      setNotFound(items.length === 0);
    } catch {
      setNotFound(true);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [authFetch, selectedType]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(query), 350);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, doSearch]);

  const RMS_COLORS: Record<string, string> = {
    R: 'text-accent-info bg-accent-info/10 border-accent-info/20',
    M: 'text-accent-primary bg-accent-primary/10 border-accent-primary/20',
    S: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 24 }}
      transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
      className="w-80 shrink-0 flex flex-col gap-0 bg-earth-900/70 border border-earth-800/60 rounded-token-xl overflow-hidden shadow-token-md"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-earth-800/60 bg-earth-900/80">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-400" />
          <span className="text-earth-200 text-sm font-semibold">ICB — Baza Cen</span>
          <span className="px-1.5 py-0.5 rounded-full bg-earth-800 text-earth-500 text-[10px]">784k pozycji</span>
        </div>
        <button onClick={onClose} className="btn-ghost w-6 h-6 !p-0 flex items-center justify-center">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Filtr R/M/S */}
      <div className="px-3 pt-2.5 pb-0 border-b border-earth-800/40">
        <div className="flex gap-1.5 mb-2">
          {(['all', 'R', 'M', 'S'] as const).map(t => (
            <button
              key={t}
              onClick={() => setSelectedType(t)}
              className={`px-2.5 py-1 rounded-token text-xs font-semibold transition-colors border ${
                selectedType === t
                  ? t === 'all' ? 'bg-earth-700 border-earth-600 text-earth-200'
                    : RMS_COLORS[t]
                  : 'bg-transparent border-earth-800 text-earth-600 hover:border-earth-700'
              }`}
            >
              {t === 'all' ? 'Wszystkie' : t === 'R' ? 'Robocizna' : t === 'M' ? 'Materiały' : 'Sprzęt'}
            </button>
          ))}
        </div>
        <div className="relative mb-2.5">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-earth-500 pointer-events-none" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Szukaj w bazie ICB…"
            className="input-base w-full pl-8 text-xs"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
          </div>
        )}
        {!loading && query.length < 2 && (
          <div className="px-4 py-6 text-center">
            <Database className="w-8 h-8 text-earth-700 mx-auto mb-2" />
            <p className="text-earth-600 text-xs">ICB · GUS · Sekocenbud</p>
            <p className="text-earth-700 text-xs mt-1">Q1 2008 → Q2 2026</p>
          </div>
        )}
        {!loading && notFound && (
          <div className="px-4 py-6 text-center">
            <p className="text-earth-500 text-xs">Brak wyników dla &ldquo;{query}&rdquo;</p>
          </div>
        )}
        {!loading && results.length > 0 && (
          <ul className="divide-y divide-earth-800/40">
            {results.map(item => (
              <li key={`${item.id}-${item.typ_rms}`} className="px-3 py-2.5 hover:bg-earth-800/30 transition-colors group">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-token border ${RMS_COLORS[item.typ_rms]}`}>
                        {item.typ_rms}
                      </span>
                      <span className="text-earth-600 text-xs font-mono truncate max-w-[80px]">{item.symbol}</span>
                    </div>
                    <p className="text-earth-300 text-xs leading-tight line-clamp-2">{item.nazwa}</p>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className="text-earth-500 text-xs">{item.jednostka}</span>
                      <span className="text-earth-700">·</span>
                      <span className="text-blue-400 text-xs font-bold font-mono">
                        {fmtNum(item.cena_netto)} zł
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1 shrink-0 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                    {(['R', 'M', 'S'] as const).map(f => (
                      <button
                        key={f}
                        onClick={() => onSelect(item, f)}
                        className={`px-1.5 py-0.5 rounded-token text-[10px] font-bold border transition-colors ${RMS_COLORS[f]}`}
                      >
                        → {f}
                      </button>
                    ))}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </motion.div>
  );
}

// ── Narzuty Editor ─────────────────────────────────────────────────────────────

function NarzutyEditor({
  narzuty,
  onChange,
  onClose,
}: {
  narzuty: Narzuty;
  onChange: (n: Narzuty) => void;
  onClose: () => void;
}) {
  const [local, setLocal] = useState<Narzuty>({ ...narzuty });

  function field(key: keyof Narzuty, label: string, desc: string) {
    return (
      <div>
        <label className="label-base">{label}</label>
        <p className="text-earth-700 text-[10px] mb-1">{desc}</p>
        <div className="relative">
          <input
            type="number" min={0} max={200} step={0.1}
            value={local[key]}
            onChange={e => setLocal(prev => ({ ...prev, [key]: parseFloat(e.target.value) || 0 }))}
            className="input-base w-full pr-8 tabular-nums"
          />
          <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-earth-600 text-xs">%</span>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.97 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-earth-950 border border-earth-800/60 rounded-token-xl shadow-token-lg w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-blue-400" />
            <h3 className="text-earth-100 text-sm font-bold">Narzuty kosztorysu</h3>
          </div>
          <button onClick={onClose} className="btn-ghost !p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-5">
          {field('ko_r_pct', 'Ko/R', 'Koszty pośrednie od robocizny')}
          {field('ko_s_pct', 'Ko/S', 'Koszty pośrednie od sprzętu')}
          {field('z_pct', 'Zysk (Z)', 'Zysk od całości kosztów')}
          {field('kz_pct', 'Kz', 'Koszty zakupu materiałów')}
          {field('vat_pct', 'VAT', 'Stawka podatku')}
        </div>

        <div className="bg-earth-900/60 rounded-token px-3 py-2.5 mb-5 text-xs text-earth-500">
          <span className="font-mono text-earth-400">CJ = R + M + S + Ko·(R·ko_r + S·ko_s) + Kz·M + Z·(R+M+S+Ko+Kz)</span>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => setLocal({ ...DEFAULT_NARZUTY })}
            className="btn-secondary px-4 py-2 text-xs"
          >
            Domyślne
          </button>
          <button
            onClick={() => { onChange(local); onClose(); }}
            className="btn-primary flex-1 text-xs"
          >
            Zastosuj
          </button>
        </div>
      </div>
    </motion.div>
  );
}

// ── Intelligence Panel ─────────────────────────────────────────────────────────

function IntelligencePanel({
  kosztorysId,
  tender,
  sumaNet,
  authFetch,
}: {
  kosztorysId?: string;
  tender?: TenderItem | null;
  sumaNet: number;
  authFetch: ReturnType<typeof useAuthFetch>;
}) {
  const [intel, setIntel] = useState<IntelligenceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [priceIndex, setPriceIndex] = useState<PriceIndex[]>([]);
  const [benchmark, setBenchmark] = useState<BenchmarkData | null>(null);
  const [expanded, setExpanded] = useState(true);

  const runIntelligence = useCallback(async () => {
    if (!sumaNet && !kosztorysId) return;
    setLoading(true);
    try {
      // Benchmark per CPV
      const cpv = tender?.cpv?.[0];
      if (cpv) {
        const cpv5 = cpv.replace(/[^0-9]/g, '').slice(0, 5);
        try {
          const bm = await authFetch(`/api/v2/intelligence/benchmark?cpv5=${cpv5}&nuts2_code=PL`);
          setBenchmark(bm as BenchmarkData);
        } catch { /* ok */ }
      }

      // Price index trend
      try {
        const idx = await authFetch('/api/v2/intelligence/prices/index?years=3');
        setPriceIndex((idx as { data?: PriceIndex[] })?.data ?? []);
      } catch { /* ok */ }

      // Intelligence per kosztorys
      if (kosztorysId) {
        try {
          const res = await authFetch(`/api/v2/analytics/cost-estimate`);
          setIntel(res as IntelligenceResult);
        } catch { /* ok */ }
      } else if (sumaNet && cpv) {
        // Quick win probability estimate
        try {
          const wp = await authFetch('/api/v2/intelligence/win-probability', {
            method: 'POST',
            body: JSON.stringify({ our_price: sumaNet, cpv5: tender?.cpv?.[0]?.replace(/[^0-9]/g, '').slice(0, 5) }),
          });
          setIntel({ win_probability: (wp as { win_probability?: number })?.win_probability });
        } catch { /* ok */ }
      }
    } finally {
      setLoading(false);
    }
  }, [authFetch, kosztorysId, tender, sumaNet]);

  useEffect(() => {
    if (sumaNet > 0) runIntelligence();
  }, [sumaNet, runIntelligence]);

  return (
    <GlassCard className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-accent-violet" />
          <span className="text-earth-200 text-sm font-semibold">Intelligence</span>
        </div>
        <div className="flex items-center gap-2">
          {loading && <Loader2 className="w-3.5 h-3.5 text-accent-violet animate-spin" />}
          <button onClick={() => setExpanded(e => !e)} className="btn-ghost !p-1">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            {/* Badges */}
            {intel && (
              <div className="flex flex-wrap gap-2 mb-3">
                {intel.win_probability !== undefined && <WinBadge p={intel.win_probability} />}
                {intel.benchmark_percentile !== undefined && <PercentileBadge p={intel.benchmark_percentile} />}
                {intel.anomaly_score !== undefined && <AnomalyBadge score={intel.anomaly_score} />}
              </div>
            )}

            {/* Benchmark bar */}
            {benchmark && sumaNet > 0 && (
              <div className="mb-3">
                <div className="flex items-center justify-between text-xs text-earth-500 mb-1">
                  <span>Pozycja na rynku (CPV {tender?.cpv?.[0]})</span>
                  <span className="text-earth-400 tabular-nums">{fmtPLN(sumaNet)}</span>
                </div>
                <div className="relative h-5 bg-earth-800/60 rounded-full overflow-hidden">
                  {/* P25–P75 range */}
                  <div
                    className="absolute top-0 h-full bg-accent-info/20"
                    style={{
                      left: `${Math.min(100, (benchmark.p25_value / (benchmark.p75_value * 1.5)) * 100)}%`,
                      width: `${Math.min(100, ((benchmark.p75_value - benchmark.p25_value) / (benchmark.p75_value * 1.5)) * 100)}%`,
                    }}
                  />
                  {/* Median line */}
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-accent-info/60"
                    style={{ left: `${Math.min(100, (benchmark.median_value / (benchmark.p75_value * 1.5)) * 100)}%` }}
                  />
                  {/* Our price needle */}
                  <div
                    className="absolute top-0 bottom-0 w-1 bg-accent-primary rounded-full"
                    style={{ left: `${Math.min(98, (sumaNet / (benchmark.p75_value * 1.5)) * 100)}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-earth-700 mt-0.5">
                  <span>min {fmtPLN(benchmark.p25_value)}</span>
                  <span>med {fmtPLN(benchmark.median_value)}</span>
                  <span>max {fmtPLN(benchmark.p75_value)}</span>
                </div>
              </div>
            )}

            {/* Price index chart */}
            {priceIndex.length > 0 && (
              <div>
                <p className="text-earth-600 text-xs mb-1.5">Indeks cen ICB (R/M/S) — trend</p>
                <ResponsiveContainer width="100%" height={80}>
                  <LineChart data={priceIndex.slice(-8)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
                    <XAxis dataKey="quarter" tick={{ fill: '#555', fontSize: 9 }} tickLine={false} />
                    <YAxis tick={{ fill: '#555', fontSize: 9 }} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                    <Tooltip
                      contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: 8, fontSize: 10 }}
                      labelStyle={{ color: '#888' }}
                    />
                    <Line type="monotone" dataKey="R" stroke="#60a5fa" dot={false} strokeWidth={1.5} name="Robocizna" />
                    <Line type="monotone" dataKey="M" stroke="#10b981" dot={false} strokeWidth={1.5} name="Materiały" />
                    <Line type="monotone" dataKey="S" stroke="#fbbf24" dot={false} strokeWidth={1.5} name="Sprzęt" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Material risk */}
            {intel?.material_risk && intel.material_risk.length > 0 && (
              <div className="mt-3">
                <p className="text-earth-600 text-xs mb-1.5">Ryzyko cen materiałów</p>
                <div className="space-y-1">
                  {intel.material_risk.slice(0, 3).map(r => (
                    <div key={r.category} className="flex items-center justify-between">
                      <span className="text-earth-500 text-xs truncate max-w-[140px]">{r.category}</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs tabular-nums ${r.change_yoy_pct > 5 ? 'text-red-400' : r.change_yoy_pct < -2 ? 'text-accent-primary' : 'text-earth-400'}`}>
                          {r.change_yoy_pct > 0 ? '+' : ''}{(r.change_yoy_pct ?? 0).toFixed(1)}%
                        </span>
                        <div className="w-12 h-1.5 bg-earth-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${r.risk_score > 0.6 ? 'bg-accent-danger' : r.risk_score > 0.3 ? 'bg-amber-400' : 'bg-accent-primary'}`}
                            style={{ width: `${r.risk_score * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!intel && !loading && !benchmark && (
              <p className="text-earth-700 text-xs text-center py-2">
                Dodaj pozycje i wybierz przetarg aby aktywować intelligence
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
}

// ── Pozycja Row ────────────────────────────────────────────────────────────────

function PozycjaRow({
  poz,
  onDelete,
  onEdit,
}: {
  poz: KPozycja;
  onDelete: () => void;
  onEdit: (field: keyof KPozycja, value: number | string) => void;
}) {
  const [editField, setEditField] = useState<keyof KPozycja | null>(null);
  const [editValue, setEditValue] = useState('');

  function startEdit(field: keyof KPozycja, val: number | string) {
    setEditField(field);
    setEditValue(String(val));
  }

  function commitEdit() {
    if (editField && editValue !== '') {
      const numeric = ['ilosc', 'r_jcena', 'm_jcena', 's_jcena'];
      const val = numeric.includes(editField as string) ? parseFloat(editValue) || 0 : editValue;
      onEdit(editField, val);
    }
    setEditField(null);
  }

  function cell(field: keyof KPozycja, display: string, numeric = true) {
    if (editField === field) {
      return (
        <td className="px-2 py-1.5">
          <input
            autoFocus
            type={numeric ? 'number' : 'text'}
            value={editValue}
            onChange={e => setEditValue(e.target.value)}
            onBlur={commitEdit}
            onKeyDown={e => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditField(null); }}
            className="w-full px-2 py-0.5 rounded-token bg-earth-800 border border-blue-500/40 text-earth-200 text-xs focus:outline-none tabular-nums"
            style={{ minWidth: 60 }}
          />
        </td>
      );
    }
    return (
      <td
        className="px-2 py-1.5 text-right text-earth-400 text-xs tabular-nums cursor-pointer hover:text-earth-200 hover:bg-earth-800/30 rounded-token transition-colors"
        onClick={() => startEdit(field, poz[field] as number | string)}
      >
        {display}
      </td>
    );
  }

  return (
    <tr className={`border-b border-earth-800/30 hover:bg-earth-900/40 transition-colors group ${poz.is_anomaly ? 'bg-accent-danger/5' : ''}`}>
      <td className="px-2 py-1.5 text-earth-700 text-xs w-8">{poz.lp}</td>
      <td className="px-2 py-1.5 text-earth-600 text-xs font-mono w-28 truncate">{poz.kst_code || '—'}</td>
      <td
        className="px-2 py-1.5 text-earth-300 text-xs cursor-pointer hover:text-earth-100 transition-colors"
        onClick={() => startEdit('opis', poz.opis)}
      >
        {editField === 'opis' ? (
          <input
            autoFocus
            type="text"
            value={editValue}
            onChange={e => setEditValue(e.target.value)}
            onBlur={commitEdit}
            onKeyDown={e => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditField(null); }}
            className="w-full px-2 py-0.5 rounded-token bg-earth-800 border border-blue-500/40 text-earth-200 text-xs focus:outline-none"
          />
        ) : (
          <span className={poz.is_anomaly ? 'text-red-300' : ''}>
            {poz.is_anomaly && (
              <span className="inline-flex items-center mr-1.5" title="Anomalia cenowa - wartość odbiega od bazy rynkowej">
                <span className="w-2 h-2 rounded-full bg-accent-danger animate-pulse-soft inline-block" />
              </span>
            )}
            {poz.opis}
          </span>
        )}
      </td>
      <td className="px-2 py-1.5 text-earth-600 text-xs w-12 text-center">{poz.jednostka}</td>
      {cell('ilosc', fmtNum(poz.ilosc, 2))}
      {cell('r_jcena', fmtNum(poz.r_jcena, 2))}
      {cell('m_jcena', fmtNum(poz.m_jcena, 2))}
      {cell('s_jcena', fmtNum(poz.s_jcena, 2))}
      <td className="px-2 py-1.5 text-right text-earth-300 text-xs tabular-nums font-semibold w-24">
        {fmtNum(poz.jcena_netto, 4)}
      </td>
      <td className={`px-2 py-1.5 text-right text-xs tabular-nums font-bold w-28 ${poz.is_anomaly ? 'text-red-400' : 'text-blue-300'}`}>
        {fmtPLN(poz.wartosc_netto)}
      </td>
      <td className="px-2 py-1.5 w-8">
        <button
          onClick={onDelete}
          className="opacity-0 group-hover:opacity-100 w-5 h-5 rounded-token flex items-center justify-center text-earth-700 hover:text-red-400 transition-all"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </td>
    </tr>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main component
// ═══════════════════════════════════════════════════════════════════════════════

export function KosztorysPage() {
  const { accessToken } = useStore();
  const authFetch = useAuthFetch();

  // ── Tender selector ────────────────────────────────────────────────────────
  const [tender, setTender] = useState<TenderItem | null>(null);
  const [tenders, setTenders] = useState<TenderItem[]>([]);
  const [tenderSearch, setTenderSearch] = useState('');
  const [tenderDropdown, setTenderDropdown] = useState(false);
  const [tendersLoading, setTendersLoading] = useState(false);
  const tenderInputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // ── Kosztorys v2 state ─────────────────────────────────────────────────────
  const [kosztorysId, setKosztorysId] = useState<string | null>(null);
  const [pozycje, setPozycje] = useState<KPozycja[]>([]);
  const [kosztLoading, setKosztLoading] = useState(false);
  const [narzuty, setNarzuty] = useState<Narzuty>({ ...DEFAULT_NARZUTY });
  const [showNarzuty, setShowNarzuty] = useState(false);

  // ── Tabs ───────────────────────────────────────────────────────────────────
  const [activeKTab, setActiveKTab] = useState<'pozycje' | 'ryzyko' | 'prognoza'>('pozycje');
  const [anomalyData, setAnomalyData] = useState<{count: number; anomalies: Array<{id: string; opis: string; kst_code?: string; is_anomaly: boolean}>} | null>(null);
  const [anomalyLoading, setAnomalyLoading] = useState(false);
  const [alertsData, setAlertsData] = useState<Array<{id: string; symbol: string; change_pct: number; severity: string; current_price: number; baseline_price: number}>>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);

  // ── Prognoza tab ───────────────────────────────────────────────────────────
  type ForecastPoint = { period: string; avg_price: number | null; is_forecast?: boolean };
  const [forecastData, setForecastData] = useState<ForecastPoint[]>([]);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastHorizon, setForecastHorizon] = useState(4);
  const [forecastCategory, setForecastCategory] = useState('murarstwo');
  const [forecastError, setForecastError] = useState<string | null>(null);

  const runForecast = useCallback(async () => {
    setForecastLoading(true);
    setForecastError(null);
    try {
      const params = new URLSearchParams({
        category: forecastCategory,
        typ_rms: 'M',
        horizon: String(forecastHorizon),
      });
      const res = await authFetch(`/api/v1/intelligence/prices/forecast?${params}`);
      const d = res as { quarters?: ForecastPoint[]; history?: ForecastPoint[] };
      setForecastData(d.quarters ?? d.history ?? []);
    } catch (e) {
      setForecastError('Błąd ładowania prognozy');
    } finally {
      setForecastLoading(false);
    }
  }, [authFetch, forecastCategory, forecastHorizon]);

  // ── Add row form ───────────────────────────────────────────────────────────
  const [addKst, setAddKst] = useState('');
  const [addOpis, setAddOpis] = useState('');
  const [addJm, setAddJm] = useState('m2');
  const [addIlosc, setAddIlosc] = useState('');
  const [addR, setAddR] = useState('');
  const [addM, setAddM] = useState('');
  const [addS, setAddS] = useState('');
  const [addLoading, setAddLoading] = useState(false);

  // ── Sidebar ────────────────────────────────────────────────────────────────
  const [showIcb, setShowIcb] = useState(false);

  // ── Export ─────────────────────────────────────────────────────────────────
  const [exportLoading, setExportLoading] = useState<string | null>(null);

  // ── Recalc ─────────────────────────────────────────────────────────────────
  const [recalcLoading, setRecalcLoading] = useState(false);

  // ── ATH Import ─────────────────────────────────────────────────────────────
  const athFileInputRef = useRef<HTMLInputElement>(null);
  const [athImportLoading, setAthImportLoading] = useState(false);

  // ── AI Wycena ──────────────────────────────────────────────────────────────
  const [aiWycenaLoading, setAiWycenaLoading] = useState(false);

  // ── Computed sums ──────────────────────────────────────────────────────────
  const sumaR     = pozycje.reduce((s, p) => s + (p.r_total ?? 0), 0);
  const sumaM     = pozycje.reduce((s, p) => s + (p.m_total ?? 0), 0);
  const sumaS     = pozycje.reduce((s, p) => s + (p.s_total ?? 0), 0);
  const sumaKo    = pozycje.reduce((s, p) => s + (p.ko_total ?? 0), 0);
  const sumaZ     = pozycje.reduce((s, p) => s + (p.z_total ?? 0), 0);
  const sumaKz    = pozycje.reduce((s, p) => s + (p.kz_total ?? 0), 0);
  const sumaNetto = pozycje.reduce((s, p) => s + p.wartosc_netto, 0);
  const sumaVat   = sumaNetto * narzuty.vat_pct / 100;
  const sumaBrutto = sumaNetto + sumaVat;

  // ── Load tenders ───────────────────────────────────────────────────────────
  useEffect(() => {
    setTendersLoading(true);
    authFetch('/api/v2/tenders?limit=100')
      .then((d: unknown) => setTenders((d as { items: TenderItem[] }).items ?? []))
      .catch(() => {})
      .finally(() => setTendersLoading(false));
  }, [authFetch]);

  // ── Load / create kosztorys when tender changes ────────────────────────────
  useEffect(() => {
    if (!tender) { setPozycje([]); setKosztorysId(null); return; }
    const controller = new AbortController();
    setKosztLoading(true);
    // Spróbuj v2 najpierw
    authFetch(`/api/v2/estimates?tender_id=${tender.id}&limit=5`)
      .then((d: unknown) => {
        const list = (d as { items?: KosztorysHeader[] }).items ?? [];
        if (list.length > 0) {
          const k = list[0];
          setKosztorysId(k.id);
          if (k.narzuty) setNarzuty(k.narzuty as Narzuty);
          return loadPozycje(k.id);
        } else {
          // Utwórz nowy kosztorys v2
          return authFetch('/api/v2/estimates', {
            method: 'POST',
            body: JSON.stringify({
              nazwa: tender.title.slice(0, 120),
              tender_id: tender.id,
              ...narzuty,
            }),
          }).then((k: unknown) => {
            const kid = (k as KosztorysHeader).id;
            setKosztorysId(kid);
            setPozycje([]);
          });
        }
      })
      .catch(() => {
        // Fallback to v1
        authFetch(`/api/v2/estimates?tender_id=${tender.id}`)
          .then((d: unknown) => {
            const items = (d as { items?: { id: string; description: string; unit: string; quantity: number; unit_price: number }[] }).items ?? [];
            // Convert v1 items to KPozycja (uproszczone)
            const poz: KPozycja[] = items.map((it, idx) => ({
              id: it.id,
              lp: idx + 1,
              kst_code: '',
              opis: it.description,
              jednostka: it.unit,
              ilosc: it.quantity,
              r_jcena: 0,
              m_jcena: it.unit_price,
              s_jcena: 0,
              jcena_netto: it.unit_price,
              wartosc_netto: it.quantity * it.unit_price,
            }));
            setPozycje(poz);
          })
          .catch(() => {});
      })
      .finally(() => { if (!controller.signal.aborted) setKosztLoading(false); });
    return () => controller.abort();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tender?.id]);

  async function loadPozycje(kid: string) {
    // GET /api/v2/estimates/{id} returns full estimate with lines[]
    const d = await authFetch(`/api/v2/estimates/${kid}`);
    const raw = (d as { lines?: Array<Record<string, unknown>> }).lines ?? [];
    // Map backend fields → KPozycja (backend: description/unit/labor_pln → opis/jednostka/r_jcena)
    const items: KPozycja[] = raw.map((it, idx) => {
      const r = (it.labor_pln as number) ?? 0;
      const m = (it.material_pln as number) ?? 0;
      const s = (it.equipment_pln as number) ?? 0;
      const jcena = (it.unit_price as number) ?? (r + m + s);
      const ilosc = (it.quantity as number) ?? 1;
      const narzuty_local = narzuty;
      const ko = r * narzuty_local.ko_r_pct / 100 + s * narzuty_local.ko_s_pct / 100;
      const kz = m * narzuty_local.kz_pct / 100;
      const z  = (r + m + s + ko + kz) * narzuty_local.z_pct / 100;
      return {
        id: it.id as string,
        lp: idx + 1,
        kst_code: (it.kst_code as string) ?? '',
        opis: (it.description as string) ?? '',
        jednostka: (it.unit as string) ?? 'szt',
        ilosc,
        r_jcena: r, m_jcena: m, s_jcena: s,
        jcena_netto: (it.line_total_pln as number) ? ((it.line_total_pln as number) / ilosc) : jcena,
        wartosc_netto: (it.line_total_pln as number) ?? (jcena * ilosc),
        r_total: r * ilosc,
        m_total: m * ilosc,
        s_total: s * ilosc,
        ko_total: ko * ilosc,
        z_total: z * ilosc,
        kz_total: kz * ilosc,
      };
    });
    setPozycje(items);
  }

  // ── Add pozycja ────────────────────────────────────────────────────────────
  async function addPozycja() {
    if (!addOpis.trim()) { showToast('error', 'Podaj opis pozycji'); return; }
    const r_jcena = parseFloat(addR) || 0;
    const m_jcena = parseFloat(addM) || 0;
    const s_jcena = parseFloat(addS) || 0;
    const ilosc   = parseFloat(addIlosc) || 1;

    if (kosztorysId) {
      setAddLoading(true);
      try {
        // Backend uses PATCH /lines with description/unit/labor_pln/material_pln/equipment_pln
        await authFetch(`/api/v2/estimates/${kosztorysId}/lines`, {
          method: 'PATCH',
          body: JSON.stringify([{
            description: addOpis,
            unit: addJm,
            quantity: ilosc,
            unit_price: r_jcena + m_jcena + s_jcena,
            labor_pln: r_jcena,
            material_pln: m_jcena,
            equipment_pln: s_jcena,
          }]),
        });
        await loadPozycje(kosztorysId);
      } catch (e) {
        showToast('error', (e as Error).message);
      } finally {
        setAddLoading(false);
      }
    } else {
      // Lokalne dodanie (bez API)
      const ko = r_jcena * narzuty.ko_r_pct / 100 + s_jcena * narzuty.ko_s_pct / 100;
      const kz = m_jcena * narzuty.kz_pct / 100;
      const z  = (r_jcena + m_jcena + s_jcena + ko + kz) * narzuty.z_pct / 100;
      const cj = r_jcena + m_jcena + s_jcena + ko + kz + z;
      const newPoz: KPozycja = {
        id: `local-${Date.now()}`,
        lp: (pozycje.at(-1)?.lp ?? 0) + 1,
        kst_code: addKst,
        opis: addOpis,
        jednostka: addJm,
        ilosc,
        r_jcena, m_jcena, s_jcena,
        jcena_netto: Math.round(cj * 10000) / 10000,
        wartosc_netto: Math.round(cj * ilosc * 100) / 100,
        r_total: r_jcena * ilosc,
        m_total: m_jcena * ilosc,
        s_total: s_jcena * ilosc,
        ko_total: ko * ilosc,
        z_total: z * ilosc,
        kz_total: kz * ilosc,
      };
      setPozycje(prev => [...prev, newPoz]);
    }

    setAddKst(''); setAddOpis(''); setAddJm('m2'); setAddIlosc(''); setAddR(''); setAddM(''); setAddS('');
  }

  // ── Delete pozycja ─────────────────────────────────────────────────────────
  async function deletePozycja(poz: KPozycja) {
    if (kosztorysId && poz.id && !poz.id.startsWith('local-')) {
      try {
        await authFetch(`/api/v2/estimates/${kosztorysId}/lines/${poz.id}`, { method: 'DELETE' });
      } catch { /* ok */ }
    }
    setPozycje(prev => prev.filter(p => p.id !== poz.id).map((p, i) => ({ ...p, lp: i + 1 })));
  }

  // ── Edit pozycja (local) ───────────────────────────────────────────────────
  function editPozycja(poz: KPozycja, field: keyof KPozycja, value: number | string) {
    setPozycje(prev => prev.map(p => {
      if (p.id !== poz.id) return p;
      const updated = { ...p, [field]: value };
      // Przelicz CJ
      const { r_jcena, m_jcena, s_jcena, ilosc } = updated;
      const ko = r_jcena * narzuty.ko_r_pct / 100 + s_jcena * narzuty.ko_s_pct / 100;
      const kz = m_jcena * narzuty.kz_pct / 100;
      const z  = (r_jcena + m_jcena + s_jcena + ko + kz) * narzuty.z_pct / 100;
      const cj = r_jcena + m_jcena + s_jcena + ko + kz + z;
      return {
        ...updated,
        jcena_netto: Math.round(cj * 10000) / 10000,
        wartosc_netto: Math.round(cj * ilosc * 100) / 100,
        r_total: r_jcena * ilosc,
        m_total: m_jcena * ilosc,
        s_total: s_jcena * ilosc,
        ko_total: ko * ilosc,
        z_total: z * ilosc,
        kz_total: kz * ilosc,
      };
    }));
  }

  // ── ICB prefill ────────────────────────────────────────────────────────────
  function icbSelect(item: IcbItem, field: 'R' | 'M' | 'S') {
    if (field === 'R') { setAddR(String(item.cena_netto)); if (!addOpis) setAddOpis(item.nazwa); }
    if (field === 'M') { setAddM(String(item.cena_netto)); if (!addOpis) setAddOpis(item.nazwa); }
    if (field === 'S') { setAddS(String(item.cena_netto)); if (!addOpis) setAddOpis(item.nazwa); }
    if (!addJm) setAddJm(item.jednostka);
    showToast('success', `ICB ${field}: ${item.nazwa.slice(0, 40)} → ${fmtNum(item.cena_netto)} zł/${item.jednostka}`);
  }

  // ── Recalc from API ────────────────────────────────────────────────────────
  async function recalc() {
    if (!kosztorysId) {
      // Przelicz lokalnie z narzutami
      setPozycje(prev => prev.map(p => {
        const ko = p.r_jcena * narzuty.ko_r_pct / 100 + p.s_jcena * narzuty.ko_s_pct / 100;
        const kz = p.m_jcena * narzuty.kz_pct / 100;
        const z  = (p.r_jcena + p.m_jcena + p.s_jcena + ko + kz) * narzuty.z_pct / 100;
        const cj = p.r_jcena + p.m_jcena + p.s_jcena + ko + kz + z;
        return {
          ...p,
          jcena_netto: Math.round(cj * 10000) / 10000,
          wartosc_netto: Math.round(cj * p.ilosc * 100) / 100,
          ko_total: ko * p.ilosc,
          kz_total: kz * p.ilosc,
          z_total: z * p.ilosc,
        };
      }));
      showToast('success', 'Przeliczono lokalnie');
      return;
    }
    setRecalcLoading(true);
    try {
      // PUT /api/v2/estimates/{id} — overhead_pct/profit_pct/params dla narzutów
      await authFetch(`/api/v2/estimates/${kosztorysId}`, {
        method: 'PUT',
        body: JSON.stringify({
          overhead_pct: narzuty.ko_r_pct,
          profit_pct: narzuty.z_pct,
          params: { ko_r_pct: narzuty.ko_r_pct, ko_s_pct: narzuty.ko_s_pct, kz_pct: narzuty.kz_pct, z_pct: narzuty.z_pct },
        }),
      });
      // recalc not available in v2 — skip
      // await authFetch(`/api/v2/estimates/${kosztorysId}/recalc`, { method: 'POST' });
      await loadPozycje(kosztorysId);
      showToast('success', 'Przeliczono kosztorys');
    } catch (e) {
      showToast('error', (e as Error).message);
    } finally {
      setRecalcLoading(false);
    }
  }

  // ── Risk / Intelligence ────────────────────────────────────────────────────
  async function runAnomaly() {
    if (!kosztorysId) return;
    setAnomalyLoading(true);
    try {
      // anomalies endpoint not in v2 API — no-op
      setAnomalyData(null);
    } catch (e) {
      showToast('error', (e as Error).message);
    } finally {
      setAnomalyLoading(false);
    }
  }

  async function loadAlerts() {
    setAlertsLoading(true);
    try {
      const res = await authFetch('/api/v2/market/materials');
      const data = await (res as unknown as Response).json();
      setAlertsData(Array.isArray(data) ? data : data.alerts ?? []);
    } catch {
      setAlertsData([]);
    } finally {
      setAlertsLoading(false);
    }
  }

  // ── Export ─────────────────────────────────────────────────────────────────
  async function exportFile(format: 'pdf' | 'ath' | 'xlsx') {
    if (!kosztorysId && format !== 'xlsx') {
      showToast('error', 'Zapisz kosztorys przed eksportem');
      return;
    }
    setExportLoading(format);
    try {
      if (format === 'pdf' && kosztorysId) {
        const blob = await fetch(`/api/v1/estimates/${kosztorysId}/export/docx`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        }).then(r => r.blob());
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = `kosztorys_${kosztorysId.slice(0, 8)}.pdf`;
        a.click(); URL.revokeObjectURL(url);
      } else if (format === 'ath' && kosztorysId) {
        const blob = await fetch(`/api/v1/estimates/${kosztorysId}/export/xlsx`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        }).then(r => r.blob());
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = `kosztorys_${kosztorysId.slice(0, 8)}.ath`;
        a.click(); URL.revokeObjectURL(url);
      } else if (format === 'xlsx') {
        // Export local as CSV (xlsx fallback)
        const csv = ['Lp,Kod,Opis,Jm,Ilość,R jcena,M jcena,S jcena,CJ netto,Wartość netto',
          ...pozycje.map(p =>
            `${p.lp},"${p.kst_code}","${p.opis}",${p.jednostka},${p.ilosc},${p.r_jcena},${p.m_jcena},${p.s_jcena},${(p.jcena_netto ?? 0).toFixed(4)},${(p.wartosc_netto ?? 0).toFixed(2)}`
          ),
          `,,,,,,,,Netto,${sumaNetto.toFixed(2)}`,
          `,,,,,,,,VAT ${narzuty.vat_pct}%,${sumaVat.toFixed(2)}`,
          `,,,,,,,,Brutto,${sumaBrutto.toFixed(2)}`,
        ].join('\n');
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = 'kosztorys.csv';
        a.click(); URL.revokeObjectURL(url);
      }
      showToast('success', `Eksport ${format.toUpperCase()} gotowy`);
    } catch (e) {
      showToast('error', (e as Error).message);
    } finally {
      setExportLoading(null);
    }
  }

  // ── Filtered tenders ───────────────────────────────────────────────────────
  const filteredTenders = tenders.filter(t =>
    !tenderSearch || t.title.toLowerCase().includes(tenderSearch.toLowerCase()) || t.buyer.toLowerCase().includes(tenderSearch.toLowerCase())
  );

  // ── ATH Import handler ─────────────────────────────────────────────────────
  async function handleAthImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !tender) return;
    setAthImportLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`/api/v1/kosztorys/${tender.id}/import/ath`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
        body: formData,
      });
      if (!res.ok) throw new Error(`Import failed: ${res.status}`);
      showToast('success', `Zaimportowano plik ATH: ${file.name}`);
      if (kosztorysId) await loadPozycje(kosztorysId);
    } catch (err) {
      showToast('error', (err as Error).message);
    } finally {
      setAthImportLoading(false);
      if (athFileInputRef.current) athFileInputRef.current.value = '';
    }
  }

  // ── AI Wycena handler ──────────────────────────────────────────────────────
  async function handleAiWycena() {
    if (!kosztorysId) {
      showToast('error', 'Brak aktywnego kosztorysu');
      return;
    }
    setAiWycenaLoading(true);
    try {
      await authFetch(`/api/v2/estimates/${kosztorysId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'Wycenij automatycznie wszystkie pozycje na podstawie rynkowych cen KNR' }),
      });
      showToast('success', 'AI Wycena zakończona pomyślnie');
      await loadPozycje(kosztorysId);
    } catch (err) {
      showToast('error', (err as Error).message);
    } finally {
      setAiWycenaLoading(false);
    }
  }

  // ── Header actions ─────────────────────────────────────────────────────────
  const headerActions = (
    <>
      <button
        onClick={() => setShowIcb(v => !v)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-token border text-xs font-medium transition-colors ${
          showIcb
            ? 'bg-accent-info/15 border-accent-info/30 text-accent-info'
            : 'btn-secondary'
        }`}
      >
        <Database className="w-3.5 h-3.5" />
        ICB
      </button>
      <button
        onClick={() => setShowNarzuty(true)}
        className="btn-secondary flex items-center gap-1.5 text-xs"
      >
        <SlidersHorizontal className="w-3.5 h-3.5" />
        Narzuty
      </button>
    </>
  );

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <PageShell
      title="Kosztorys"
      subtitle="Kalkulacja KNR z bazą cen ICB"
      actions={headerActions}
      noPadding={false}
    >
      <div className="flex gap-4 flex-1 min-h-0">
        {/* Main content */}
        <div className="flex-1 flex flex-col gap-4 min-w-0">
          {/* Tender selector */}
          <GlassCard className="p-4 shrink-0">
            <div className="flex items-center gap-3">
              <Search className="w-4 h-4 text-earth-500 shrink-0" />
              <div className="relative flex-1" ref={dropdownRef}>
                <input
                  ref={tenderInputRef}
                  value={tenderSearch || tender?.title || ''}
                  onChange={e => { setTenderSearch(e.target.value); setTenderDropdown(true); }}
                  onFocus={() => setTenderDropdown(true)}
                  onBlur={() => setTimeout(() => setTenderDropdown(false), 150)}
                  placeholder="Wybierz przetarg lub wpisz nazwę…"
                  className="input-base w-full"
                />
                {tendersLoading && (
                  <Loader2 className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-600 animate-spin" />
                )}
                {tenderDropdown && filteredTenders.length > 0 && (
                  <div className="absolute top-full left-0 right-0 z-40 mt-1 bg-earth-900 border border-earth-700/60 rounded-token-lg shadow-token-lg overflow-hidden max-h-60 overflow-y-auto">
                    {filteredTenders.slice(0, 20).map(t => (
                      <button
                        key={t.id}
                        className="w-full px-3 py-2.5 text-left hover:bg-earth-800/60 transition-colors border-b border-earth-800/30 last:border-0"
                        onClick={() => {
                          setTender(t);
                          setTenderSearch('');
                          setTenderDropdown(false);
                        }}
                      >
                        <p className="text-earth-200 text-xs font-medium line-clamp-1">{t.title}</p>
                        <p className="text-earth-600 text-xs mt-0.5">{t.buyer} · {fmtPLN(Number(t.value_pln))}</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {tender && (
                <button
                  onClick={() => { setTender(null); setTenderSearch(''); setPozycje([]); setKosztorysId(null); }}
                  className="btn-ghost shrink-0 !p-1"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            {tender && (
              <div className="flex items-center gap-4 mt-2 px-7">
                <span className="text-earth-600 text-xs">{tender.buyer}</span>
                {tender.cpv?.[0] && <span className="text-earth-700 text-xs font-mono">CPV {tender.cpv[0]}</span>}
                {tender.value_pln && <span className="text-earth-500 text-xs tabular-nums">{fmtPLN(Number(tender.value_pln))}</span>}
                {kosztorysId && <span className="text-accent-info/70 text-xs font-mono">v2:{kosztorysId.slice(0, 8)}</span>}
              </div>
            )}
          </GlassCard>

          {/* Add row form */}
          <GlassCard className="p-3 shrink-0">
            <div className="flex items-center gap-2 mb-2">
              <Plus className="w-3.5 h-3.5 text-accent-primary" />
              <span className="section-label">Nowa pozycja</span>
            </div>
            <div className="grid grid-cols-12 gap-2">
              <input value={addKst} onChange={e => setAddKst(e.target.value)} placeholder="KNR/kod"
                className="col-span-2 px-2 py-1.5 rounded-token bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-xs focus:outline-none focus:border-accent-primary/50 transition-colors" />
              <input value={addOpis} onChange={e => setAddOpis(e.target.value)} placeholder="Opis pozycji *"
                className="col-span-4 px-2 py-1.5 rounded-token bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-xs focus:outline-none focus:border-accent-primary/50 transition-colors" />
              <input value={addJm} onChange={e => setAddJm(e.target.value)} placeholder="Jm"
                className="col-span-1 px-2 py-1.5 rounded-token bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-xs focus:outline-none focus:border-accent-primary/50 transition-colors" />
              <input value={addIlosc} onChange={e => setAddIlosc(e.target.value)} type="number" placeholder="Ilość"
                className="col-span-1 px-2 py-1.5 rounded-token bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-xs focus:outline-none focus:border-accent-primary/50 transition-colors" />
              <input value={addR} onChange={e => setAddR(e.target.value)} type="number" placeholder="R zł"
                className="col-span-1 px-2 py-1.5 rounded-token bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-xs focus:outline-none focus:border-accent-primary/50 transition-colors" />
              <input value={addM} onChange={e => setAddM(e.target.value)} type="number" placeholder="M zł"
                className="col-span-1 px-2 py-1.5 rounded-token bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-xs focus:outline-none focus:border-accent-primary/50 transition-colors" />
              <input value={addS} onChange={e => setAddS(e.target.value)} type="number" placeholder="S zł"
                className="col-span-1 px-2 py-1.5 rounded-token bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-xs focus:outline-none focus:border-accent-primary/50 transition-colors" />
              <button
                onClick={addPozycja}
                disabled={addLoading || !addOpis.trim()}
                className="col-span-1 btn-primary flex items-center justify-center gap-1 !text-xs disabled:opacity-50"
              >
                {addLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              </button>
            </div>
          </GlassCard>

          {/* Pozycje / Risk / Prognoza tabs */}
          <GlassCard className="flex-1 overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-earth-800/40 shrink-0">
              <div className="flex items-center gap-1">
                {([
                  { key: 'pozycje', label: 'Pozycje', icon: <Calculator className="w-3.5 h-3.5" /> },
                  { key: 'ryzyko',  label: 'Ryzyko cen', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
                  { key: 'prognoza', label: 'Prognoza', icon: <TrendingUp className="w-3.5 h-3.5" /> },
                ] as const).map(t => (
                  <button
                    key={t.key}
                    onClick={() => {
                      setActiveKTab(t.key);
                      if (t.key === 'ryzyko' && alertsData.length === 0) loadAlerts();
                    }}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-token text-xs transition-colors ${
                      activeKTab === t.key
                        ? 'bg-earth-700/60 text-earth-200'
                        : 'text-earth-500 hover:text-earth-300 hover:bg-earth-800/40'
                    }`}
                  >
                    {t.icon}{t.label}
                    {t.key === 'pozycje' && <span className="px-1.5 py-0.5 rounded-full bg-earth-800 text-earth-500 text-xs">{pozycje.length}</span>}
                    {t.key === 'ryzyko' && alertsData.length > 0 && <span className="px-1.5 py-0.5 rounded-full bg-accent-danger/30 text-accent-danger text-xs">{alertsData.length}</span>}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={recalc}
                  disabled={recalcLoading}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-token bg-accent-info/10 border border-accent-info/20 text-accent-info text-xs hover:bg-accent-info/20 transition-colors disabled:opacity-50"
                >
                  {recalcLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                  Przelicz
                </button>
                <button
                  onClick={() => exportFile('pdf')}
                  disabled={exportLoading === 'pdf'}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-token bg-accent-danger/10 border border-accent-danger/20 text-accent-danger text-xs hover:bg-accent-danger/20 transition-colors disabled:opacity-50"
                >
                  {exportLoading === 'pdf' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileDown className="w-3.5 h-3.5" />}
                  PDF
                </button>
                <button
                  onClick={() => exportFile('ath')}
                  disabled={exportLoading === 'ath'}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-token bg-accent-violet/10 border border-accent-violet/20 text-accent-violet text-xs hover:bg-accent-violet/20 transition-colors disabled:opacity-50"
                >
                  {exportLoading === 'ath' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                  ATH
                </button>
                <button
                  onClick={() => exportFile('xlsx')}
                  disabled={exportLoading === 'xlsx'}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-token bg-accent-success/10 border border-accent-success/20 text-accent-success text-xs hover:bg-accent-success/20 transition-colors disabled:opacity-50"
                >
                  {exportLoading === 'xlsx' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
                  CSV
                </button>
                {/* Hidden file input for ATH import */}
                <input
                  ref={athFileInputRef}
                  type="file"
                  accept=".xml,.ath"
                  className="hidden"
                  onChange={handleAthImport}
                />
                <button
                  onClick={() => athFileInputRef.current?.click()}
                  disabled={athImportLoading || !tender}
                  title="Importuj plik ATH"
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-token bg-orange-600/10 border border-orange-600/20 text-orange-400 text-xs hover:bg-orange-600/20 transition-colors disabled:opacity-50"
                >
                  {athImportLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                  Import ATH
                </button>
                <button
                  onClick={handleAiWycena}
                  disabled={aiWycenaLoading || !kosztorysId}
                  title="Automatyczna wycena AI na podstawie cen KNR"
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-token bg-accent-violet/10 border border-accent-violet/20 text-accent-violet text-xs hover:bg-accent-violet/20 transition-colors disabled:opacity-50"
                >
                  {aiWycenaLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Bot className="w-3.5 h-3.5" />}
                  AI Wycena
                </button>
              </div>
            </div>

            {/* ── Tab content ──────────────────────────────────────────────── */}

            {/* TAB: Pozycje */}
            {activeKTab === 'pozycje' && (
            <div className="flex-1 overflow-auto">
              {kosztLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 text-earth-600 animate-spin" />
                </div>
              ) : pozycje.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <Calculator className="w-10 h-10 text-earth-800" />
                  <p className="text-earth-600 text-sm">Brak pozycji kosztorysowych</p>
                  <p className="text-earth-700 text-xs">Dodaj pozycje ręcznie lub zaimportuj z ICB/ATH</p>
                </div>
              ) : (
                <table className="w-full text-xs border-collapse">
                  <thead className="sticky top-0 z-10">
                    <tr className="bg-earth-900/90 backdrop-blur-sm border-b border-earth-800/60">
                      <th className="px-2 py-2 text-left text-earth-600 font-medium w-8">Lp</th>
                      <th className="px-2 py-2 text-left text-earth-600 font-medium w-28">Kod KNR</th>
                      <th className="px-2 py-2 text-left text-earth-600 font-medium">Opis</th>
                      <th className="px-2 py-2 text-center text-earth-600 font-medium w-12">Jm</th>
                      <th className="px-2 py-2 text-right text-earth-600 font-medium w-16">Ilość</th>
                      <th className="px-2 py-2 text-right text-blue-600 font-medium w-16">R jcena</th>
                      <th className="px-2 py-2 text-right text-accent-primary font-medium w-16">M jcena</th>
                      <th className="px-2 py-2 text-right text-amber-600 font-medium w-16">S jcena</th>
                      <th className="px-2 py-2 text-right text-earth-600 font-medium w-24">CJ netto</th>
                      <th className="px-2 py-2 text-right text-earth-400 font-medium w-28">Wartość</th>
                      <th className="w-8" />
                    </tr>
                  </thead>
                  <tbody>
                    {pozycje.map(poz => (
                      <PozycjaRow
                        key={poz.id ?? poz.lp}
                        poz={poz}
                        onDelete={() => deletePozycja(poz)}
                        onEdit={(field, value) => editPozycja(poz, field, value)}
                      />
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            )}

            {/* TAB: Ryzyko cen */}
            {activeKTab === 'ryzyko' && (
            <div className="flex-1 overflow-auto p-4 space-y-4">
              {/* Anomaly analysis */}
              <div className="rounded-token-lg border border-earth-800/60 bg-earth-900/40 p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    <span className="text-earth-300 text-sm font-semibold">Analiza anomalii cenowych</span>
                  </div>
                  <button
                    onClick={runAnomaly}
                    disabled={anomalyLoading || !kosztorysId}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-token bg-amber-600/10 border border-amber-600/20 text-amber-400 text-xs hover:bg-amber-600/20 transition-colors disabled:opacity-50"
                  >
                    {anomalyLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                    Analizuj
                  </button>
                </div>
                {anomalyData ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-token bg-earth-800/40 p-3 text-center">
                        <p className="text-earth-500 text-xs mb-1">Pozycje z anomaliami</p>
                        <p className={`text-lg font-bold tabular-nums ${anomalyData.count > 0 ? 'text-red-400' : 'text-accent-primary'}`}>
                          {anomalyData.count}
                        </p>
                      </div>
                      <div className="rounded-token bg-earth-800/40 p-3 text-center">
                        <p className="text-earth-500 text-xs mb-1">Łącznie pozycji</p>
                        <p className="text-lg font-bold tabular-nums text-earth-300">{pozycje.length}</p>
                      </div>
                    </div>
                    {anomalyData.anomalies.length > 0 && (
                      <div>
                        <p className="text-earth-500 text-xs mb-2">Pozycje z anomaliami cenowymi:</p>
                        <div className="space-y-1">
                          {anomalyData.anomalies.map(a => (
                            <div key={a.id} className="flex items-center gap-2 rounded-token bg-accent-danger/5 border border-accent-danger/20 px-3 py-2">
                              <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                              <span className="text-earth-300 text-xs flex-1 truncate">{a.opis}</span>
                              {a.kst_code && <span className="text-earth-600 text-xs ml-auto shrink-0">{a.kst_code}</span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {anomalyData.count === 0 && (
                      <p className="text-accent-primary text-xs text-center py-2">Brak anomalii cenowych w tym kosztorysie</p>
                    )}
                  </div>
                ) : (
                  <p className="text-earth-600 text-xs text-center py-4">
                    {!kosztorysId ? 'Wybierz kosztorys aby uruchomić analizę' : 'Kliknij „Analizuj" aby wykryć anomalie cenowe'}
                  </p>
                )}
              </div>

              {/* Material alerts */}
              <div className="rounded-token-lg border border-earth-800/60 bg-earth-900/40 p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Package className="w-4 h-4 text-blue-400" />
                    <span className="text-earth-300 text-sm font-semibold">Alerty cen materiałów</span>
                    {alertsData.length > 0 && (
                      <span className="px-1.5 py-0.5 rounded-full bg-accent-danger/30 text-accent-danger text-xs">{alertsData.length}</span>
                    )}
                  </div>
                  <button
                    onClick={loadAlerts}
                    disabled={alertsLoading}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-token bg-accent-info/10 border border-accent-info/20 text-accent-info text-xs hover:bg-accent-info/20 transition-colors disabled:opacity-50"
                  >
                    {alertsLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                    Odśwież
                  </button>
                </div>
                {alertsLoading ? (
                  <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 text-earth-600 animate-spin" /></div>
                ) : alertsData.length === 0 ? (
                  <p className="text-earth-600 text-xs text-center py-4">Brak aktywnych alertów cenowych</p>
                ) : (
                  <div className="space-y-1.5">
                    {alertsData.map(alert => (
                      <div key={alert.id} className={`flex items-center gap-3 rounded-token px-3 py-2.5 border ${
                        alert.severity === 'critical' ? 'bg-accent-danger/5 border-accent-danger/20' :
                        alert.severity === 'high' ? 'bg-orange-900/10 border-orange-800/30' :
                        'bg-amber-900/10 border-amber-800/30'
                      }`}>
                        <div className="flex-1 min-w-0">
                          <p className="text-earth-300 text-xs font-medium truncate">{alert.symbol}</p>
                          <p className="text-earth-500 text-xs">
                            {(alert.baseline_price ?? 0).toFixed(2)} → {(alert.current_price ?? 0).toFixed(2)} PLN
                          </p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className={`text-sm font-bold tabular-nums ${alert.change_pct > 0 ? 'text-red-400' : 'text-accent-primary'}`}>
                            {alert.change_pct > 0 ? '+' : ''}{(alert.change_pct ?? 0).toFixed(1)}%
                          </p>
                          <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                            alert.severity === 'critical' ? 'bg-accent-danger/30 text-accent-danger' :
                            alert.severity === 'high' ? 'bg-orange-900/60 text-orange-300' :
                            'bg-amber-900/60 text-amber-300'
                          }`}>{alert.severity}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            )}

            {/* TAB: Prognoza */}
            {activeKTab === 'prognoza' && (
            <div className="flex-1 overflow-auto p-4 space-y-4">
              {/* Kontrolki */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <label className="text-xs text-earth-500">Kategoria</label>
                  <select
                    value={forecastCategory}
                    onChange={e => setForecastCategory(e.target.value)}
                    className="text-xs bg-earth-800/60 border border-earth-700/60 rounded-token px-2 py-1.5 text-earth-200 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                  >
                    {['murarstwo','beton_cement','stal_konstrukcyjna','dach_pokrycia','drewno',
                      'kruszywa_ziemne','nawierzchnie','instalacje_wod_kan','ogrzewanie',
                      'wentylacja_klima','elektryka','izolacja_termo','malowanie',
                      'plytki_ceramiczne','stolarka','inne'].map(c => (
                      <option key={c} value={c}>{c.replace(/_/g,' ')}</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-earth-500">Horyzont</label>
                  <select
                    value={forecastHorizon}
                    onChange={e => setForecastHorizon(Number(e.target.value))}
                    className="text-xs bg-earth-800/60 border border-earth-700/60 rounded-token px-2 py-1.5 text-earth-200 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                  >
                    {[2,4,6,8,12].map(h => <option key={h} value={h}>{h} kw.</option>)}
                  </select>
                </div>
                <button
                  onClick={runForecast}
                  disabled={forecastLoading}
                  className="btn-primary flex items-center gap-1.5 !text-xs disabled:opacity-50"
                >
                  {forecastLoading
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <TrendingUp className="w-3.5 h-3.5" />
                  }
                  Generuj prognozę
                </button>
              </div>

              {/* Error */}
              {forecastError && (
                <div className="flex items-center gap-2 text-xs text-accent-danger bg-accent-danger/10 border border-accent-danger/30 rounded-token px-3 py-2">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  {forecastError}
                </div>
              )}

              {/* Wykres */}
              {forecastData.length > 0 ? (
                <div className="rounded-token-lg border border-earth-800/60 bg-earth-900/40 p-4">
                  <p className="text-xs text-earth-500 mb-3 font-medium">
                    Cena średnia [PLN/jm] — {forecastCategory.replace(/_/g,' ')} · historia + prognoza {forecastHorizon} kw.
                  </p>
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={forecastData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
                      <XAxis dataKey="period" tick={{ fontSize: 10, fill: '#6b6b6b' }} />
                      <YAxis tick={{ fontSize: 10, fill: '#6b6b6b' }} width={56}
                        tickFormatter={(v: number) => v >= 1000 ? `${(v/1000).toFixed(1)}k` : String(v)} />
                      <Tooltip
                        contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8, fontSize: 11 }}
                        formatter={(v: number | string, name: string): [string, string] => [
                          typeof v === 'number' ? `${v.toFixed(2)} PLN` : String(v),
                          name === 'avg_price' ? 'Historia' : name === 'forecast_price' ? 'Prognoza' : name,
                        ]}
                      />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      {/* Historia — linia ciągła */}
                      <Line
                        type="monotone"
                        dataKey="avg_price"
                        name="Historia"
                        stroke="#3b82f6" strokeWidth={2} dot={{ r: 2 }}
                        connectNulls
                      />
                      {/* Prognoza — linia przerywana */}
                      <Line
                        type="monotone"
                        dataKey="forecast_price"
                        name="Prognoza"
                        stroke="#60a5fa" strokeWidth={2} dot={{ r: 3 }}
                        strokeDasharray="6 3"
                        connectNulls
                      />
                    </LineChart>
                  </ResponsiveContainer>
                  {/* Legenda prognoza vs historia */}
                  <div className="flex gap-4 mt-2">
                    <div className="flex items-center gap-1.5 text-xs text-earth-500">
                      <span className="w-5 border-t-2 border-blue-500 inline-block" />
                      Historia
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-earth-500">
                      <span className="w-5 border-t-2 border-dashed border-blue-400 inline-block" />
                      Prognoza
                    </div>
                  </div>
                </div>
              ) : !forecastLoading && (
                <div className="rounded-token-lg border border-earth-800/60 bg-earth-900/40 p-8 flex flex-col items-center gap-3">
                  <TrendingUp className="w-10 h-10 text-earth-700" />
                  <p className="text-earth-400 text-sm font-medium">Wybierz kategorię i kliknij „Generuj prognozę"</p>
                  <p className="text-earth-600 text-xs text-center max-w-xs">
                    Regresja liniowa na ostatnich 12 kwartałach ICB (784k wierszy). Horyzont do 12 kwartałów.
                  </p>
                </div>
              )}
            </div>
            )}

            {/* Sumy */}
            {pozycje.length > 0 && (
              <div className="shrink-0 border-t border-earth-800/60 px-4 py-3 bg-earth-900/40">
                <div className="grid grid-cols-6 gap-3 text-xs">
                  <div>
                    <p className="text-blue-600 font-medium mb-0.5">Robocizna (R)</p>
                    <p className="text-earth-300 tabular-nums font-semibold">{fmtPLN(sumaR)}</p>
                    <p className="text-earth-700">{pct(sumaR, sumaNetto)}</p>
                  </div>
                  <div>
                    <p className="text-accent-primary font-medium mb-0.5">Materiały (M)</p>
                    <p className="text-earth-300 tabular-nums font-semibold">{fmtPLN(sumaM)}</p>
                    <p className="text-earth-700">{pct(sumaM, sumaNetto)}</p>
                  </div>
                  <div>
                    <p className="text-amber-600 font-medium mb-0.5">Sprzęt (S)</p>
                    <p className="text-earth-300 tabular-nums font-semibold">{fmtPLN(sumaS)}</p>
                    <p className="text-earth-700">{pct(sumaS, sumaNetto)}</p>
                  </div>
                  <div>
                    <p className="text-earth-600 font-medium mb-0.5">Ko + Z + Kz</p>
                    <p className="text-earth-300 tabular-nums font-semibold">{fmtPLN(sumaKo + sumaZ + sumaKz)}</p>
                    <p className="text-earth-700">{pct(sumaKo + sumaZ + sumaKz, sumaNetto)}</p>
                  </div>
                  <div>
                    <p className="text-earth-400 font-medium mb-0.5">NETTO</p>
                    <p className="text-earth-200 tabular-nums font-bold text-sm">{fmtPLN(sumaNetto)}</p>
                    <p className="text-earth-700">VAT {fmtPLN(sumaVat)}</p>
                  </div>
                  <div>
                    <p className="text-blue-400 font-semibold mb-0.5">BRUTTO</p>
                    <p className="text-blue-300 tabular-nums font-black text-base">{fmtPLN(sumaBrutto)}</p>
                    <p className="text-earth-700">VAT {narzuty.vat_pct}%</p>
                  </div>
                </div>
              </div>
            )}
          </GlassCard>
        </div>

        {/* Right panel */}
        <div className="w-72 shrink-0 flex flex-col gap-4">
          <AnimatePresence>
            {showIcb && (
              <IcbSidebar onSelect={icbSelect} onClose={() => setShowIcb(false)} />
            )}
          </AnimatePresence>

          {!showIcb && (
            <IntelligencePanel
              kosztorysId={kosztorysId ?? undefined}
              tender={tender}
              sumaNet={sumaNetto}
              authFetch={authFetch}
            />
          )}

          {/* Narzuty summary */}
          <GlassCard className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Wrench className="w-4 h-4 text-earth-500" />
                <span className="section-label">Narzuty</span>
              </div>
              <button onClick={() => setShowNarzuty(true)} className="btn-ghost !p-1">
                <Edit2 className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {([
                ['Ko/R', narzuty.ko_r_pct + '%'],
                ['Ko/S', narzuty.ko_s_pct + '%'],
                ['Z', narzuty.z_pct + '%'],
                ['Kz', narzuty.kz_pct + '%'],
                ['VAT', narzuty.vat_pct + '%'],
              ] as [string, string][]).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between bg-earth-800/30 rounded-token px-2.5 py-1.5">
                  <span className="text-earth-600 text-xs">{k}</span>
                  <span className="text-earth-300 text-xs font-bold tabular-nums">{v}</span>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* RMS chart */}
          {pozycje.length > 0 && (
            <GlassCard className="p-4">
              <p className="section-label mb-3">Struktura kosztów</p>
              <ResponsiveContainer width="100%" height={120}>
                <BarChart data={[
                  { name: 'R', value: sumaR, fill: '#60a5fa' },
                  { name: 'M', value: sumaM, fill: '#10b981' },
                  { name: 'S', value: sumaS, fill: '#fbbf24' },
                  { name: 'Ko', value: sumaKo, fill: '#8b5cf6' },
                  { name: 'Z+Kz', value: sumaZ + sumaKz, fill: '#f97316' },
                ]} barCategoryGap="20%">
                  <XAxis dataKey="name" tick={{ fill: '#555', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <YAxis tick={false} axisLine={false} />
                  <Tooltip
                    formatter={(v: number) => [fmtPLN(v), '']}
                    contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: 8, fontSize: 10 }}
                    labelStyle={{ color: '#888' }}
                  />
                  <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                    {[
                      { fill: '#60a5fa' }, { fill: '#10b981' }, { fill: '#fbbf24' },
                      { fill: '#8b5cf6' }, { fill: '#f97316' },
                    ].map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>
          )}
        </div>
      </div>

      {/* Modals */}
      <AnimatePresence>
        {showNarzuty && (
          <NarzutyEditor
            narzuty={narzuty}
            onChange={n => { setNarzuty(n); recalc(); }}
            onClose={() => setShowNarzuty(false)}
          />
        )}
      </AnimatePresence>
    </PageShell>
  );
}
