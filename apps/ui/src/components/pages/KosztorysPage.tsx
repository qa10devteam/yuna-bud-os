'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine,
} from 'recharts';
import {
  Calculator, Search, Plus, Trash2, Download, FileSpreadsheet, FileText,
  ChevronRight, X, Loader2, Zap, TrendingUp, AlertCircle, Edit2, Save,
  RotateCcw, SlidersHorizontal, Info, PanelRightOpen, PanelRightClose,
  BookOpen, CheckCircle2, Package, Database, Columns2,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';
import { GlassCard } from '@/components/ui/GlassCard';

// ── Types ──────────────────────────────────────────────────────────────────────

interface TenderItem {
  id: string;
  title: string;
  buyer: string;
  cpv: string[];
  value_pln: number | string | null;
}

interface KosztorysItem {
  id: string;
  description: string;
  unit: string;
  quantity: number;
  unit_price: number;
}

interface PredictResult {
  benchmark: number;
  ai_estimate: number;
  confidence_interval: { low95: number; high95: number };
  method: string;
  similar_projects: Array<{ title?: string; value?: number }>;
}

interface SekoItem {
  id: string;
  symbol: string;
  opis: string;
  jm: string;
  cena: number;
  chapter_name?: string;
  katalog_code?: string;
  release_nr?: string;
}

interface EditState {
  itemId: string;
  field: 'description' | 'unit' | 'quantity' | 'unit_price';
  value: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmtPLN(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(Number(n))) return '—';
  return Number(n).toLocaleString('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 });
}

function fmtNum(n: number): string {
  return n.toLocaleString('pl-PL', { maximumFractionDigits: 2 });
}

const OVERHEAD_PCT = 0.23;

// ── Method badge colors ────────────────────────────────────────────────────────
function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    benchmark: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    ai: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    ml: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    default: 'bg-earth-700/50 text-earth-400 border-earth-600/40',
  };
  const cls = colors[method?.toLowerCase()] ?? colors.default;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      <Zap className="w-3 h-3" />
      {method ?? 'unknown'}
    </span>
  );
}

// ── Skeleton loaders ───────────────────────────────────────────────────────────
function SkeletonRow() {
  return (
    <tr className="animate-pulse border-b border-earth-800/40">
      {[40, 180, 50, 70, 80, 80, 32].map((w, i) => (
        <td key={i} className="px-3 py-2.5">
          <div className="h-3 bg-earth-800 rounded" style={{ width: w }} />
        </td>
      ))}
    </tr>
  );
}

// ── Custom Recharts Tooltip ───────────────────────────────────────────────────
function PredictTooltip({ active, payload }: { active?: boolean; payload?: any[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-earth-900 border border-earth-700/60 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-earth-400 text-xs mb-0.5">{d.payload?.label}</p>
      <p className="text-earth-100 text-sm font-bold font-mono">{fmtPLN(d.value)}</p>
    </div>
  );
}

// ── Sekocenbud Sidebar ─────────────────────────────────────────────────────────
function SekocenbudSidebar({
  onPrefill,
  onClose,
}: {
  onPrefill: (item: SekoItem) => void;
  onClose: () => void;
}) {
  const authFetch = useAuthFetch();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SekoItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(
    async (q: string) => {
      if (q.length < 2) { setResults([]); setNotFound(false); return; }
      setLoading(true);
      setNotFound(false);
      try {
        // Try v2 first, fall back to v1
        let data: SekoItem[] = [];
        try {
          const res = await authFetch(`/api/v2/intelligence/sekocenbud?q=${encodeURIComponent(q)}&limit=20`);
          data = res?.items ?? res?.data ?? res ?? [];
        } catch {
          const res = await authFetch(`/api/v1/sekocenbud/search?q=${encodeURIComponent(q)}&limit=20`);
          data = res?.items ?? res?.data ?? res ?? [];
        }
        setResults(data);
        setNotFound(data.length === 0);
      } catch {
        setNotFound(true);
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [authFetch],
  );

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(query), 380);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, doSearch]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 24 }}
      transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
      className="w-72 shrink-0 flex flex-col gap-0 bg-earth-900/70 border border-earth-800/60 rounded-2xl overflow-hidden"
    >
      {/* Sidebar header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-earth-800/60 bg-earth-900/80">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-emerald-400" />
          <span className="text-earth-200 text-sm font-semibold">Sekocenbud</span>
        </div>
        <button
          onClick={onClose}
          className="w-6 h-6 rounded flex items-center justify-center text-earth-500 hover:text-earth-300 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Search */}
      <div className="px-3 py-3 border-b border-earth-800/40">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-earth-500 pointer-events-none" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Szukaj robót, materiałów…"
            className="w-full pl-8 pr-3 py-2 rounded-lg bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-xs focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition-colors"
          />
        </div>
        <p className="text-earth-600 text-xs mt-1.5 leading-tight">
          Baza SEKOCENBUD · 23&nbsp;725 pozycji
        </p>
      </div>

      {/* Results list */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
          </div>
        )}

        {!loading && query.length < 2 && (
          <div className="px-4 py-6 text-center">
            <Database className="w-8 h-8 text-earth-700 mx-auto mb-2" />
            <p className="text-earth-600 text-xs">Wpisz min. 2 znaki</p>
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
              <li key={item.id} className="px-3 py-2.5 hover:bg-earth-800/30 transition-colors group">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-earth-300 text-xs leading-tight line-clamp-2">{item.opis}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-earth-600 text-xs font-mono">{item.symbol}</span>
                      <span className="text-earth-700">·</span>
                      <span className="text-earth-500 text-xs">{item.jm}</span>
                      <span className="text-earth-700">·</span>
                      <span className="text-emerald-400 text-xs font-bold font-mono">
                        {fmtNum(item.cena)} zł
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => onPrefill(item)}
                    className="shrink-0 px-2 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium hover:bg-emerald-500/20 transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                  >
                    Dodaj
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Compare Modal — warianty A/B/C side-by-side
// ═══════════════════════════════════════════════════════════════════════════════

interface CompareVariant {
  tenderId: string;
  label: string;
  items: KosztorysItem[];
  loading: boolean;
  error: string | null;
}

const VARIANT_LABELS = ['Wariant A', 'Wariant B', 'Wariant C'];
const VARIANT_COLORS = ['text-emerald-400', 'text-blue-400', 'text-amber-400'];
const VARIANT_BG     = ['bg-emerald-500/10 border-emerald-500/20', 'bg-blue-500/10 border-blue-500/20', 'bg-amber-500/10 border-amber-500/20'];

function CompareModal({
  tenders,
  compareIds,
  onClose,
  authFetch,
}: {
  tenders: TenderItem[];
  compareIds: string[];
  onClose: () => void;
  authFetch: (url: string, opts?: RequestInit) => Promise<unknown>;
}) {
  const [variants, setVariants] = useState<CompareVariant[]>(() =>
    compareIds.slice(0, 3).map((id, i) => ({
      tenderId: id,
      label: VARIANT_LABELS[i] ?? ('Wariant ' + (i + 1)),
      items: [],
      loading: true,
      error: null,
    }))
  );

  useEffect(() => {
    compareIds.slice(0, 3).forEach((id, i) => {
      authFetch('/api/v1/kosztorys/' + id)
        .then((d: unknown) => {
          const data = d as { items?: KosztorysItem[] };
          setVariants(prev => {
            const next = [...prev];
            next[i] = { ...next[i], items: data?.items ?? [], loading: false };
            return next;
          });
        })
        .catch((e: unknown) => {
          setVariants(prev => {
            const next = [...prev];
            next[i] = { ...next[i], loading: false, error: (e as Error).message };
            return next;
          });
        });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function variantTotal(v: CompareVariant): number {
    return v.items.reduce((s, item) => s + item.quantity * item.unit_price, 0);
  }

  const totals = variants.map(variantTotal);
  const baseTotal = totals[0] ?? 0;

  function diffPct(t: number): string {
    if (baseTotal === 0) return '—';
    const pct = ((t - baseTotal) / baseTotal) * 100;
    return (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%';
  }

  // All unique descriptions across all variants (for aligned rows)
  const allDescs = Array.from(
    new Set(variants.flatMap(v => v.items.map(i => i.description)))
  );

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ scale: 0.96, y: 12, opacity: 0 }}
        animate={{ scale: 1, y: 0, opacity: 1 }}
        exit={{ scale: 0.96, y: 12, opacity: 0 }}
        transition={{ type: 'spring', damping: 28, stiffness: 300 }}
        className="bg-earth-950 border border-earth-800/60 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-earth-800/60 shrink-0">
          <div className="flex items-center gap-2.5">
            <Columns2 className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-earth-100">Porównanie wariantów kosztorysu</h3>
            <span className="px-2 py-0.5 rounded-full bg-earth-800 text-earth-500 text-xs">
              {variants.length} warianty
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-earth-500 hover:text-earth-200 hover:bg-earth-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Variant headers */}
        <div className="grid shrink-0" style={{ gridTemplateColumns: '200px ' + variants.map(() => '1fr').join(' ') }}>
          <div className="px-4 py-3 border-b border-r border-earth-800/40 bg-earth-900/30" />
          {variants.map((v, i) => {
            const tender = tenders.find(t => t.id === v.tenderId);
            return (
              <div
                key={v.tenderId}
                className="px-4 py-3 border-b border-r border-earth-800/40 bg-earth-900/30 last:border-r-0"
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`text-xs font-bold uppercase tracking-wide ${VARIANT_COLORS[i]}`}>
                    {v.label}
                  </span>
                  {i === 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-earth-800 text-earth-500 text-[10px]">bazowy</span>
                  )}
                </div>
                {tender && (
                  <p className="text-xs text-earth-400 line-clamp-2 leading-snug">{tender.title}</p>
                )}
              </div>
            );
          })}
        </div>

        {/* Table body */}
        <div className="flex-1 overflow-y-auto">
          {/* Loading state */}
          {variants.some(v => v.loading) && (
            <div className="flex items-center justify-center py-12 gap-2 text-earth-500 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              Ładowanie danych wariantów…
            </div>
          )}

          {/* Rows */}
          {!variants.some(v => v.loading) && allDescs.length === 0 && (
            <div className="py-12 text-center">
              <Package className="w-8 h-8 text-earth-700 mx-auto mb-2" />
              <p className="text-earth-500 text-sm">Brak pozycji kosztorysowych w wybranych wariantach</p>
            </div>
          )}

          {!variants.some(v => v.loading) && allDescs.length > 0 && (
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10">
                <tr className="bg-earth-900/80 backdrop-blur-sm">
                  <th className="text-left px-4 py-2.5 text-earth-500 font-medium border-b border-r border-earth-800/40 w-[200px]">
                    Pozycja
                  </th>
                  {variants.map((v, i) => (
                    <th
                      key={v.tenderId}
                      className="text-right px-4 py-2.5 border-b border-r border-earth-800/40 last:border-r-0"
                      colSpan={3}
                    >
                      <span className={`font-semibold ${VARIANT_COLORS[i]}`}>{v.label}</span>
                    </th>
                  ))}
                </tr>
                <tr className="bg-earth-900/60">
                  <th className="px-4 py-1.5 border-b border-r border-earth-800/40" />
                  {variants.map(v => (
                    <th key={v.tenderId + 'sub'} className="border-b border-r border-earth-800/40 last:border-r-0" colSpan={3}>
                      <div className="grid grid-cols-3 text-right">
                        <span className="px-2 py-1 text-earth-600 font-normal">Ilość</span>
                        <span className="px-2 py-1 text-earth-600 font-normal">Cena jdn.</span>
                        <span className="px-2 py-1 text-earth-600 font-normal">Wartość</span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {allDescs.map((desc, rowIdx) => (
                  <tr
                    key={desc}
                    className={rowIdx % 2 === 0 ? 'bg-earth-950' : 'bg-earth-900/30'}
                  >
                    <td className="px-4 py-2 border-r border-earth-800/30 text-earth-300 max-w-[200px]">
                      <span className="line-clamp-2 leading-snug">{desc}</span>
                    </td>
                    {variants.map(v => {
                      const item = v.items.find(it => it.description === desc);
                      return (
                        <td key={v.tenderId + desc} className="border-r border-earth-800/30 last:border-r-0" colSpan={3}>
                          {item ? (
                            <div className="grid grid-cols-3 text-right">
                              <span className="px-2 py-2 text-earth-400 tabular-nums">
                                {fmtNum(item.quantity)}{' '}{item.unit}
                              </span>
                              <span className="px-2 py-2 text-earth-400 tabular-nums">
                                {fmtPLN(item.unit_price)}
                              </span>
                              <span className="px-2 py-2 text-earth-200 font-medium tabular-nums">
                                {fmtPLN(item.quantity * item.unit_price)}
                              </span>
                            </div>
                          ) : (
                            <div className="grid grid-cols-3 text-right">
                              {[0, 1, 2].map(k => (
                                <span key={k} className="px-2 py-2 text-earth-700">—</span>
                              ))}
                            </div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer — sumy i różnica % */}
        {!variants.some(v => v.loading) && (
          <div className="shrink-0 border-t border-earth-800/60 px-4 py-4 bg-earth-900/40">
            <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(' + variants.length + ', 1fr)' }}>
              {variants.map((v, i) => {
                const total = totals[i] ?? 0;
                const diff = diffPct(total);
                const isBase = i === 0;
                return (
                  <div
                    key={v.tenderId}
                    className={'rounded-xl border px-4 py-3 ' + VARIANT_BG[i]}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-bold uppercase tracking-wide ${VARIANT_COLORS[i]}`}>
                        {v.label}
                      </span>
                      {!isBase && (
                        <span className={
                          'text-xs font-semibold tabular-nums ' +
                          (total > baseTotal ? 'text-red-400' : total < baseTotal ? 'text-emerald-400' : 'text-earth-500')
                        }>
                          {diff}
                        </span>
                      )}
                      {isBase && (
                        <span className="text-[10px] text-earth-600">baza</span>
                      )}
                    </div>
                    <p className="text-lg font-black text-earth-100 tabular-nums">
                      {fmtPLN(total)}
                    </p>
                    <p className="text-[10px] text-earth-600 mt-0.5">
                      {v.items.length} {v.items.length === 1 ? 'pozycja' : v.items.length < 5 ? 'pozycje' : 'pozycji'}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main component
// ═══════════════════════════════════════════════════════════════════════════════

export function KosztorysPage() {
  const { accessToken } = useStore();
  const authFetch = useAuthFetch();

  // ── Tender selector state ──────────────────────────────────────────────────
  const [tenderId, setTenderId] = useState<string | null>(null);
  const [tenderLabel, setTenderLabel] = useState<string>('');
  const [tenderCpv, setTenderCpv] = useState<string>('');
  const [tenderValuePln, setTenderValuePln] = useState<number>(0);
  const [tenders, setTenders] = useState<TenderItem[]>([]);
  const [tenderSearch, setTenderSearch] = useState('');
  const [tenderDropdown, setTenderDropdown] = useState(false);
  const [tendersLoading, setTendersLoading] = useState(false);
  const tenderInputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // ── Kosztorys state ────────────────────────────────────────────────────────
  const [items, setItems] = useState<KosztorysItem[]>([]);
  const [kosztLoading, setKosztLoading] = useState(false);

  // ── Inline edit ────────────────────────────────────────────────────────────
  const [editing, setEditing] = useState<EditState | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  // ── Add row form ───────────────────────────────────────────────────────────
  const [addDesc, setAddDesc] = useState('');
  const [addUnit, setAddUnit] = useState('');
  const [addQty, setAddQty] = useState('');
  const [addPrice, setAddPrice] = useState('');
  const [addLoading, setAddLoading] = useState(false);

  // ── AI Predict state ───────────────────────────────────────────────────────
  const [showPredict, setShowPredict] = useState(false);
  const [cpvInput, setCpvInput] = useState('');
  const [valueInput, setValueInput] = useState('');
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictResult, setPredictResult] = useState<PredictResult | null>(null);

  // ── Sekocenbud sidebar ─────────────────────────────────────────────────────
  const [showSeko, setShowSeko] = useState(false);

  // ── Export state ───────────────────────────────────────────────────────────
  const [exportLoading, setExportLoading] = useState<string | null>(null);

  // ── Compare variants state ──────────────────────────────────────────────────
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  // In-memory ring buffer: ostatnie 3 otwarte tender IDs (do porównania A/B/C)
  const recentTenderIdsRef = useRef<string[]>([]);

  // ── Computed totals ────────────────────────────────────────────────────────
  const totalNet = items.reduce((s, i) => s + i.quantity * i.unit_price, 0);
  const totalGross = totalNet * (1 + OVERHEAD_PCT);

  // ── Load tenders ───────────────────────────────────────────────────────────
  useEffect(() => {
    setTendersLoading(true);
    authFetch('/api/v1/tenders?limit=50')
      .then((d: { items: TenderItem[] }) => setTenders(d.items ?? []))
      .catch(() => {})
      .finally(() => setTendersLoading(false));
  }, [authFetch]);

  // ── Load kosztorys items when tender changes ───────────────────────────────
  useEffect(() => {
    if (!tenderId) { setItems([]); return; }
    setKosztLoading(true);
    authFetch(`/api/v1/kosztorys/${tenderId}`)
      .then((d: { items: KosztorysItem[]; total?: number }) => setItems(d.items ?? []))
      .catch(e => showToast('error', `Błąd ładowania kosztorysu: ${e.message}`))
      .finally(() => setKosztLoading(false));
  }, [tenderId, authFetch]);

  // ── Click-outside handler for tender dropdown ──────────────────────────────
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        tenderInputRef.current &&
        !tenderInputRef.current.contains(e.target as Node)
      ) {
        setTenderDropdown(false);
      }
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  // ── Select tender ──────────────────────────────────────────────────────────
  const selectTender = useCallback((t: TenderItem) => {
    setTenderId(t.id);
    setTenderLabel(t.title);
    setTenderCpv(t.cpv?.[0]?.slice(0, 8) ?? '');
    setTenderValuePln(typeof t.value_pln === 'number' ? t.value_pln : parseFloat(String(t.value_pln ?? 0)) || 0);
    setTenderSearch('');
    setTenderDropdown(false);
    // Pre-fill predict with tender's CPV+value
    if (t.cpv?.[0]) setCpvInput(t.cpv[0].slice(0, 8));
    if (t.value_pln) setValueInput(String(typeof t.value_pln === 'number' ? Math.round(t.value_pln) : parseFloat(String(t.value_pln)) || 0));
    setPredictResult(null);
    // Track in recent ring buffer (max 3, no duplicates)
    recentTenderIdsRef.current = [
      t.id,
      ...recentTenderIdsRef.current.filter(id => id !== t.id),
    ].slice(0, 3);
  }, []);

  const clearTender = useCallback(() => {
    setTenderId(null);
    setTenderLabel('');
    setTenderCpv('');
    setTenderValuePln(0);
    setItems([]);
    setPredictResult(null);
  }, []);

  // ── Filter tenders by search ───────────────────────────────────────────────
  const filteredTenders = tenders.filter(t =>
    !tenderSearch || t.title.toLowerCase().includes(tenderSearch.toLowerCase()) ||
    t.buyer?.toLowerCase().includes(tenderSearch.toLowerCase()),
  );

  // ── Run AI prediction ──────────────────────────────────────────────────────
  const runPredict = useCallback(async () => {
    if (!cpvInput || !valueInput) {
      showToast('warning', 'Podaj kod CPV i wartość');
      return;
    }
    setPredictLoading(true);
    try {
      const res = await authFetch(
        `/api/v2/estimates/predict?cpv=${encodeURIComponent(cpvInput)}&value=${encodeURIComponent(valueInput)}`,
      );
      setPredictResult(res as PredictResult);
    } catch (e: any) {
      showToast('error', `Błąd predykcji: ${e.message}`);
    } finally {
      setPredictLoading(false);
    }
  }, [cpvInput, valueInput, authFetch]);

  // ── Add kosztorys item ─────────────────────────────────────────────────────
  const addItem = useCallback(async () => {
    if (!tenderId) { showToast('warning', 'Wybierz przetarg'); return; }
    if (!addDesc || !addUnit || !addQty || !addPrice) {
      showToast('warning', 'Wypełnij wszystkie pola');
      return;
    }
    const qty = parseFloat(addQty);
    const price = parseFloat(addPrice);
    if (isNaN(qty) || isNaN(price) || qty <= 0 || price < 0) {
      showToast('warning', 'Nieprawidłowe wartości liczbowe');
      return;
    }
    setAddLoading(true);
    try {
      const newItem = await authFetch(`/api/v1/kosztorys/${tenderId}`, {
        method: 'POST',
        body: JSON.stringify({ description: addDesc, unit: addUnit, quantity: qty, unit_price: price }),
      });
      setItems(prev => [...prev, newItem as KosztorysItem]);
      setAddDesc(''); setAddUnit(''); setAddQty(''); setAddPrice('');
      showToast('success', 'Pozycja dodana');
    } catch (e: any) {
      showToast('error', `Błąd dodawania: ${e.message}`);
    } finally {
      setAddLoading(false);
    }
  }, [tenderId, addDesc, addUnit, addQty, addPrice, authFetch]);

  // ── Prefill from Sekocenbud ────────────────────────────────────────────────
  const prefillFromSeko = useCallback((item: SekoItem) => {
    setAddDesc(item.opis);
    setAddUnit(item.jm);
    setAddPrice(String(item.cena));
    showToast('info', `Wczytano: ${item.symbol}`);
  }, []);

  // ── Inline edit ────────────────────────────────────────────────────────────
  const startEdit = useCallback((itemId: string, field: EditState['field'], current: string) => {
    setEditing({ itemId, field, value: current });
  }, []);

  const commitEdit = useCallback(async () => {
    if (!editing || !tenderId) { setEditing(null); return; }
    const { itemId, field, value } = editing;
    const target = items.find(i => i.id === itemId);
    if (!target) { setEditing(null); return; }

    // Build update payload
    const update: Partial<KosztorysItem> = { ...target };
    if (field === 'description') update.description = value;
    else if (field === 'unit') update.unit = value;
    else if (field === 'quantity') update.quantity = parseFloat(value) || target.quantity;
    else if (field === 'unit_price') update.unit_price = parseFloat(value) || target.unit_price;

    setEditing(null);
    setSavingId(itemId);
    try {
      const updated = await authFetch(`/api/v1/kosztorys/${tenderId}/${itemId}`, {
        method: 'PATCH',
        body: JSON.stringify(update),
      });
      setItems(prev => prev.map(i => i.id === itemId ? (updated as KosztorysItem) : i));
    } catch (e: any) {
      showToast('error', `Błąd zapisu: ${e.message}`);
      // Revert
      setItems(prev => [...prev]);
    } finally {
      setSavingId(null);
    }
  }, [editing, tenderId, items, authFetch]);

  // ── Delete item ────────────────────────────────────────────────────────────
  const deleteItem = useCallback(async (itemId: string) => {
    if (!tenderId) return;
    setSavingId(itemId);
    try {
      await authFetch(`/api/v1/kosztorys/${tenderId}/${itemId}`, { method: 'DELETE' });
      setItems(prev => prev.filter(i => i.id !== itemId));
      showToast('success', 'Pozycja usunięta');
    } catch (e: any) {
      showToast('error', `Błąd usuwania: ${e.message}`);
    } finally {
      setSavingId(null);
    }
  }, [tenderId, authFetch]);

  // ── Export handlers ────────────────────────────────────────────────────────
  const exportATH = useCallback(async () => {
    if (!tenderId) return;
    setExportLoading('ath');
    try {
      const res = await fetch(`/api/v1/kosztorys/${tenderId}/export/ath`, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `kosztorys_${tenderId}.ath`; a.click();
      URL.revokeObjectURL(url);
      showToast('success', 'Eksport ATH gotowy');
    } catch (e: any) {
      showToast('error', `Błąd eksportu ATH: ${e.message}`);
    } finally {
      setExportLoading(null);
    }
  }, [tenderId, accessToken]);

  const exportFile = useCallback(async (format: 'xlsx' | 'docx') => {
    if (!tenderId) return;
    setExportLoading(format);
    try {
      const res = await fetch(`/api/v1/estimates/${tenderId}/export/${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `kosztorys_${tenderId}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('success', `Eksport ${format.toUpperCase()} gotowy`);
    } catch (e: any) {
      showToast('error', `Błąd eksportu ${format.toUpperCase()}: ${e.message}`);
    } finally {
      setExportLoading(null);
    }
  }, [tenderId, accessToken]);

  // ── Build predict chart data ───────────────────────────────────────────────
  const predictChartData = predictResult
    ? [
        { label: 'CI dolny 95%', value: predictResult.confidence_interval.low95, color: '#6b7280' },
        { label: 'Benchmark', value: predictResult.benchmark, color: '#10b981' },
        { label: 'AI Estymacja', value: predictResult.ai_estimate, color: '#34d399' },
        { label: 'CI górny 95%', value: predictResult.confidence_interval.high95, color: '#6b7280' },
      ]
    : [];

  // ── Handle compare: zbierz ostatnie 3 IDs + bieżący ──────────────────────
  function handleOpenCompare() {
    // Bieżący na pierwszym miejscu, potem ostatnio oglądane
    const ids = tenderId
      ? [tenderId, ...recentTenderIdsRef.current.filter(id => id !== tenderId)]
      : [...recentTenderIdsRef.current];
    // Fallback: pierwsze 3 z listy tenders
    const fallback = tenders.slice(0, 3).map(t => t.id);
    const merged = Array.from(new Set([...ids, ...fallback])).slice(0, 3);
    if (merged.length < 2) {
      showToast('warning', 'Otwórz co najmniej 2 kosztorysy aby porównać warianty');
      return;
    }
    setCompareIds(merged);
    setCompareOpen(true);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════════════════════════════════════

  return (
    <div className="flex flex-col h-full overflow-hidden bg-earth-950">
      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="px-6 pt-5 pb-4 border-b border-earth-800/60 shrink-0">
        <div className="flex items-center gap-1.5 text-xs text-earth-600 mb-1">
          <span className="text-earth-500 font-medium">Terra.OS</span>
          <ChevronRight className="w-3 h-3" />
          <span className="text-earth-300 font-semibold">Smart Estimator</span>
        </div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-earth-100 flex items-center gap-2">
              <Calculator className="w-5 h-5 text-emerald-400 shrink-0" />
              Kosztorys / Smart Estimator
            </h1>
            <p className="text-earth-500 text-xs mt-0.5">
              Wycena przetargu · Baza Sekocenbud · AI Predict
            </p>
          </div>
          {/* Header action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Porównaj warianty A/B/C */}
            <button
              onClick={handleOpenCompare}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl border bg-earth-800/50 border-earth-700/50 text-earth-400 hover:text-earth-200 hover:border-earth-600 transition-colors text-xs font-medium"
              title="Porównaj warianty A/B/C"
            >
              <Columns2 className="w-3.5 h-3.5" />
              Porównaj
            </button>
            {/* Toggle Seko sidebar */}
            <button
              onClick={() => setShowSeko(v => !v)}
              className={'flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs font-medium transition-colors ' + (
                showSeko
                  ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                  : 'bg-earth-800/50 border-earth-700/50 text-earth-400 hover:text-earth-200'
              )}
            >
              {showSeko ? <PanelRightClose className="w-3.5 h-3.5" /> : <PanelRightOpen className="w-3.5 h-3.5" />}
              Sekocenbud
            </button>
          </div>
        </div>
      </div>

      {/* ── Body ──────────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden flex gap-0">

        {/* ── Main column ─────────────────────────────────────────────────── */}
        <div className="flex-1 min-w-0 overflow-y-auto px-6 py-5 flex flex-col gap-5">

          {/* ── 1. Tender selector ────────────────────────────────────────── */}
          <GlassCard className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Search className="w-4 h-4 text-emerald-400" />
              <span className="text-earth-200 text-sm font-semibold">Wybierz przetarg</span>
              {tenderId && (
                <span className="ml-auto px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Wybrany
                </span>
              )}
            </div>

            {tenderId ? (
              /* Selected tender chip */
              <div className="flex items-center gap-3 p-3 rounded-xl bg-earth-800/50 border border-earth-700/40">
                <div className="min-w-0 flex-1">
                  <p className="text-earth-200 text-sm font-medium line-clamp-1">{tenderLabel}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {tenderCpv && (
                      <span className="text-emerald-400 text-xs font-mono">CPV {tenderCpv}</span>
                    )}
                    {tenderValuePln > 0 && (
                      <>
                        <span className="text-earth-700">·</span>
                        <span className="text-earth-400 text-xs font-mono">{fmtPLN(tenderValuePln)}</span>
                      </>
                    )}
                  </div>
                </div>
                <button
                  onClick={clearTender}
                  className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-earth-500 hover:text-earth-300 hover:bg-earth-700/50 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              /* Tender search dropdown */
              <div className="relative">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-500 pointer-events-none" />
                  <input
                    ref={tenderInputRef}
                    value={tenderSearch}
                    onChange={e => { setTenderSearch(e.target.value); setTenderDropdown(true); }}
                    onFocus={() => setTenderDropdown(true)}
                    placeholder="Szukaj przetargu po tytule lub zamawiającym…"
                    className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-sm focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition-colors"
                  />
                  {tendersLoading && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-500 animate-spin" />
                  )}
                </div>

                <AnimatePresence>
                  {tenderDropdown && (
                    <motion.div
                      ref={dropdownRef}
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      transition={{ duration: 0.15 }}
                      className="absolute z-30 left-0 right-0 top-full mt-1.5 bg-earth-900 border border-earth-700/60 rounded-xl shadow-2xl overflow-hidden max-h-64 overflow-y-auto"
                    >
                      {filteredTenders.length === 0 ? (
                        <div className="px-4 py-4 text-center text-earth-500 text-sm">
                          Brak wyników
                        </div>
                      ) : (
                        <ul className="divide-y divide-earth-800/50">
                          {filteredTenders.slice(0, 30).map(t => (
                            <li key={t.id}>
                              <button
                                onClick={() => selectTender(t)}
                                className="w-full text-left px-4 py-3 hover:bg-earth-800/50 transition-colors"
                              >
                                <p className="text-earth-200 text-sm line-clamp-1">{t.title}</p>
                                <div className="flex items-center gap-2 mt-0.5">
                                  <span className="text-earth-500 text-xs truncate max-w-[200px]">{t.buyer}</span>
                                  {t.cpv?.[0] && (
                                    <>
                                      <span className="text-earth-700">·</span>
                                      <span className="text-emerald-500 text-xs font-mono">{t.cpv[0].slice(0, 8)}</span>
                                    </>
                                  )}
                                  {t.value_pln ? (
                                    <>
                                      <span className="text-earth-700">·</span>
                                      <span className="text-earth-400 text-xs font-mono">
                                        {fmtPLN(typeof t.value_pln === 'number' ? t.value_pln : parseFloat(String(t.value_pln)))}
                                      </span>
                                    </>
                                  ) : null}
                                </div>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </GlassCard>

          {/* ── 2. AI Predict panel ────────────────────────────────────────── */}
          <GlassCard className="overflow-hidden">
            {/* Header / toggle */}
            <button
              onClick={() => setShowPredict(v => !v)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-earth-800/20 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-purple-400" />
                <span className="text-earth-200 text-sm font-semibold">AI Predykcja wartości</span>
                {predictResult && (
                  <span className="px-2 py-0.5 rounded-full bg-purple-500/15 border border-purple-500/25 text-purple-400 text-xs font-medium">
                    Wynik gotowy
                  </span>
                )}
              </div>
              <motion.div
                animate={{ rotate: showPredict ? 180 : 0 }}
                transition={{ duration: 0.2 }}
              >
                <SlidersHorizontal className="w-4 h-4 text-earth-500" />
              </motion.div>
            </button>

            <AnimatePresence>
              {showPredict && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
                  className="overflow-hidden"
                >
                  <div className="px-4 pb-4 border-t border-earth-800/40">
                    {/* Inputs */}
                    <div className="flex gap-3 mt-4 flex-wrap">
                      <div className="flex-1 min-w-[140px]">
                        <label className="block text-earth-500 text-xs mb-1.5">Kod CPV</label>
                        <input
                          value={cpvInput}
                          onChange={e => setCpvInput(e.target.value)}
                          placeholder="np. 45000000"
                          className="w-full px-3 py-2 rounded-lg bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-sm font-mono focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-colors"
                        />
                      </div>
                      <div className="flex-1 min-w-[140px]">
                        <label className="block text-earth-500 text-xs mb-1.5">Wartość (PLN)</label>
                        <input
                          value={valueInput}
                          onChange={e => setValueInput(e.target.value)}
                          placeholder="np. 1000000"
                          type="number"
                          className="w-full px-3 py-2 rounded-lg bg-earth-800/60 border border-earth-700/50 text-earth-200 placeholder-earth-600 text-sm font-mono focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-colors"
                        />
                      </div>
                      <div className="flex items-end">
                        <button
                          onClick={runPredict}
                          disabled={predictLoading}
                          className="px-4 py-2 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-400 text-sm font-medium hover:bg-purple-500/25 transition-colors disabled:opacity-50 flex items-center gap-2"
                        >
                          {predictLoading
                            ? <Loader2 className="w-4 h-4 animate-spin" />
                            : <Zap className="w-4 h-4" />}
                          Prognozuj
                        </button>
                      </div>
                    </div>

                    {/* Results */}
                    <AnimatePresence>
                      {predictResult && (
                        <motion.div
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 8 }}
                          transition={{ duration: 0.2 }}
                          className="mt-4"
                        >
                          {/* KPI cards */}
                          <div className="grid grid-cols-3 gap-3 mb-4">
                            <div className="p-3 rounded-xl bg-earth-800/40 border border-earth-700/40">
                              <p className="text-earth-500 text-xs mb-1">Benchmark</p>
                              <p className="text-earth-100 text-lg font-bold font-mono tabular-nums">
                                {fmtPLN(predictResult.benchmark)}
                              </p>
                            </div>
                            <div className="p-3 rounded-xl bg-purple-500/8 border border-purple-500/20">
                              <p className="text-purple-400 text-xs mb-1 flex items-center gap-1">
                                <Zap className="w-3 h-3" /> AI Estymacja
                              </p>
                              <p className="text-purple-300 text-lg font-bold font-mono tabular-nums">
                                {fmtPLN(predictResult.ai_estimate)}
                              </p>
                            </div>
                            <div className="p-3 rounded-xl bg-earth-800/40 border border-earth-700/40">
                              <p className="text-earth-500 text-xs mb-1 flex items-center gap-1">
                                <Info className="w-3 h-3" /> Metoda
                              </p>
                              <MethodBadge method={predictResult.method} />
                            </div>
                          </div>

                          {/* Confidence interval row */}
                          <div className="flex items-center gap-3 p-3 rounded-xl bg-earth-800/30 border border-earth-700/30 mb-4 text-xs">
                            <TrendingUp className="w-3.5 h-3.5 text-earth-500 shrink-0" />
                            <span className="text-earth-500">Przedział ufności 95%:</span>
                            <span className="font-mono text-earth-300">
                              {fmtPLN(predictResult.confidence_interval.low95)}
                            </span>
                            <span className="text-earth-700">—</span>
                            <span className="font-mono text-earth-300">
                              {fmtPLN(predictResult.confidence_interval.high95)}
                            </span>
                          </div>

                          {/* Bar chart */}
                          <div className="h-40 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart
                                data={predictChartData}
                                margin={{ top: 4, right: 8, left: 0, bottom: 4 }}
                                barSize={32}
                              >
                                <XAxis
                                  dataKey="label"
                                  tick={{ fill: '#6b7280', fontSize: 10 }}
                                  axisLine={false}
                                  tickLine={false}
                                />
                                <YAxis
                                  tick={{ fill: '#6b7280', fontSize: 10 }}
                                  axisLine={false}
                                  tickLine={false}
                                  tickFormatter={v =>
                                    v >= 1_000_000
                                      ? `${(v / 1_000_000).toFixed(1)} mln`
                                      : v >= 1_000
                                      ? `${(v / 1_000).toFixed(0)} tys.`
                                      : String(v)
                                  }
                                  width={64}
                                />
                                <Tooltip content={<PredictTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                                <ReferenceLine
                                  y={predictResult.ai_estimate}
                                  stroke="#a78bfa"
                                  strokeDasharray="4 3"
                                  strokeWidth={1}
                                />
                                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                                  {predictChartData.map((entry, i) => (
                                    <Cell key={i} fill={entry.color} />
                                  ))}
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </GlassCard>

          {/* ── 3. Kosztorys table ─────────────────────────────────────────── */}
          <div className="bg-earth-900/60 border border-earth-800/60 rounded-2xl overflow-hidden">
            {/* Table header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-earth-800/60">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-emerald-400" />
                <span className="text-earth-200 text-sm font-semibold">Pozycje kosztorysu</span>
                {items.length > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full bg-earth-700/60 text-earth-400 text-xs font-mono">
                    {items.length}
                  </span>
                )}
              </div>
              {!tenderId && (
                <span className="flex items-center gap-1.5 text-earth-600 text-xs">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Wybierz przetarg
                </span>
              )}
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-earth-800/50 bg-earth-900/40">
                    <th className="px-3 py-2.5 text-left text-earth-600 text-xs font-semibold w-10">Lp.</th>
                    <th className="px-3 py-2.5 text-left text-earth-600 text-xs font-semibold">Opis / Robota</th>
                    <th className="px-3 py-2.5 text-left text-earth-600 text-xs font-semibold w-16">J.m.</th>
                    <th className="px-3 py-2.5 text-right text-earth-600 text-xs font-semibold w-20">Ilość</th>
                    <th className="px-3 py-2.5 text-right text-earth-600 text-xs font-semibold w-24">Cena j.m.</th>
                    <th className="px-3 py-2.5 text-right text-earth-600 text-xs font-semibold w-28">Wartość</th>
                    <th className="px-3 py-2.5 w-8" />
                  </tr>
                </thead>
                <tbody>
                  {kosztLoading && (
                    <>
                      <SkeletonRow /><SkeletonRow /><SkeletonRow />
                    </>
                  )}

                  {!kosztLoading && items.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-4 py-10 text-center">
                        <div className="flex flex-col items-center gap-2">
                          <Package className="w-8 h-8 text-earth-700" />
                          <p className="text-earth-500 text-sm">
                            {tenderId ? 'Dodaj pierwszą pozycję kosztorysu' : 'Wybierz przetarg, aby zarządzać kosztorysem'}
                          </p>
                        </div>
                      </td>
                    </tr>
                  )}

                  {!kosztLoading && items.map((item, idx) => {
                    const wartosc = item.quantity * item.unit_price;
                    const isSaving = savingId === item.id;

                    const EditCell = ({
                      field,
                      value,
                      align = 'left',
                      mono = false,
                    }: {
                      field: EditState['field'];
                      value: string;
                      align?: 'left' | 'right';
                      mono?: boolean;
                    }) => {
                      const isEditing = editing?.itemId === item.id && editing.field === field;
                      if (isEditing) {
                        return (
                          <td className={`px-1 py-1 ${align === 'right' ? 'text-right' : ''}`}>
                            <input
                              autoFocus
                              value={editing.value}
                              onChange={e => setEditing(prev => prev ? { ...prev, value: e.target.value } : null)}
                              onBlur={commitEdit}
                              onKeyDown={e => {
                                if (e.key === 'Enter') commitEdit();
                                if (e.key === 'Escape') setEditing(null);
                              }}
                              className={`w-full px-2 py-1 rounded-md bg-earth-800 border border-emerald-500/50 text-earth-100 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500/30 ${mono ? 'font-mono' : ''} ${align === 'right' ? 'text-right' : ''}`}
                            />
                          </td>
                        );
                      }
                      return (
                        <td
                          className={`px-3 py-2.5 cursor-text group/cell ${align === 'right' ? 'text-right' : ''}`}
                          onClick={() => !isSaving && startEdit(item.id, field, value)}
                        >
                          <span className={`text-earth-300 text-xs ${mono ? 'font-mono tabular-nums' : ''} group-hover/cell:text-earth-100 transition-colors`}>
                            {value}
                          </span>
                          {!isSaving && (
                            <Edit2 className="w-2.5 h-2.5 text-earth-700 inline ml-1 opacity-0 group-hover/cell:opacity-100 transition-opacity" />
                          )}
                        </td>
                      );
                    };

                    return (
                      <tr
                        key={item.id}
                        className={`border-b border-earth-800/40 group hover:bg-earth-800/20 transition-colors ${isSaving ? 'opacity-60' : ''}`}
                      >
                        <td className="px-3 py-2.5 text-earth-600 text-xs font-mono tabular-nums">{idx + 1}</td>
                        <EditCell field="description" value={item.description} />
                        <EditCell field="unit" value={item.unit} />
                        <EditCell field="quantity" value={fmtNum(item.quantity)} align="right" mono />
                        <EditCell field="unit_price" value={fmtNum(item.unit_price)} align="right" mono />
                        <td className="px-3 py-2.5 text-right">
                          <span className="text-earth-200 text-xs font-bold font-mono tabular-nums">
                            {fmtPLN(wartosc)}
                          </span>
                        </td>
                        <td className="px-2 py-2.5 text-center">
                          {isSaving ? (
                            <Loader2 className="w-3.5 h-3.5 text-earth-500 animate-spin mx-auto" />
                          ) : (
                            <button
                              onClick={() => deleteItem(item.id)}
                              className="w-6 h-6 rounded flex items-center justify-center text-earth-700 hover:text-red-400 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-all"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}

                  {/* ── Add row form ─────────────────────────────────────── */}
                  {tenderId && (
                    <tr className="border-b border-earth-800/30 bg-earth-900/20">
                      <td className="px-3 py-2">
                        <Plus className="w-3.5 h-3.5 text-earth-600" />
                      </td>
                      <td className="px-1.5 py-2">
                        <input
                          value={addDesc}
                          onChange={e => setAddDesc(e.target.value)}
                          placeholder="Opis roboty / pozycji…"
                          className="w-full px-2.5 py-1.5 rounded-lg bg-earth-800/60 border border-earth-700/40 text-earth-200 placeholder-earth-700 text-xs focus:outline-none focus:border-emerald-500/40 transition-colors"
                        />
                      </td>
                      <td className="px-1.5 py-2">
                        <input
                          value={addUnit}
                          onChange={e => setAddUnit(e.target.value)}
                          placeholder="m²"
                          className="w-full px-2.5 py-1.5 rounded-lg bg-earth-800/60 border border-earth-700/40 text-earth-200 placeholder-earth-700 text-xs font-mono focus:outline-none focus:border-emerald-500/40 transition-colors"
                        />
                      </td>
                      <td className="px-1.5 py-2">
                        <input
                          value={addQty}
                          onChange={e => setAddQty(e.target.value)}
                          placeholder="0"
                          type="number"
                          className="w-full px-2.5 py-1.5 rounded-lg bg-earth-800/60 border border-earth-700/40 text-earth-200 placeholder-earth-700 text-xs font-mono text-right focus:outline-none focus:border-emerald-500/40 transition-colors"
                        />
                      </td>
                      <td className="px-1.5 py-2">
                        <input
                          value={addPrice}
                          onChange={e => setAddPrice(e.target.value)}
                          placeholder="0.00"
                          type="number"
                          className="w-full px-2.5 py-1.5 rounded-lg bg-earth-800/60 border border-earth-700/40 text-earth-200 placeholder-earth-700 text-xs font-mono text-right focus:outline-none focus:border-emerald-500/40 transition-colors"
                        />
                      </td>
                      <td className="px-3 py-2 text-right">
                        {addQty && addPrice ? (
                          <span className="text-earth-500 text-xs font-mono tabular-nums">
                            {fmtPLN((parseFloat(addQty) || 0) * (parseFloat(addPrice) || 0))}
                          </span>
                        ) : (
                          <span className="text-earth-700 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-2 py-2 text-center">
                        <button
                          onClick={addItem}
                          disabled={addLoading || !addDesc || !addUnit || !addQty || !addPrice}
                          className="w-7 h-7 rounded-lg flex items-center justify-center bg-emerald-500/15 border border-emerald-500/25 text-emerald-400 hover:bg-emerald-500/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          title="Dodaj pozycję"
                        >
                          {addLoading
                            ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            : <Save className="w-3.5 h-3.5" />}
                        </button>
                      </td>
                    </tr>
                  )}

                  {/* ── Total row ───────────────────────────────────────── */}
                  {items.length > 0 && (
                    <tr className="bg-earth-800/30 border-t-2 border-earth-700/60">
                      <td colSpan={5} className="px-3 py-3 text-right">
                        <span className="text-earth-400 text-xs font-semibold uppercase tracking-wide">
                          Razem netto
                        </span>
                      </td>
                      <td className="px-3 py-3 text-right">
                        <span className="text-earth-100 text-base font-bold font-mono tabular-nums">
                          {fmtPLN(totalNet)}
                        </span>
                      </td>
                      <td />
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── 4. Export buttons + summary bar ──────────────────────────── */}
          {tenderId && (
            <div className="flex flex-col gap-3">
              {/* Export buttons */}
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-earth-500 text-xs font-medium">Eksport:</span>
                <button
                  onClick={exportATH}
                  disabled={exportLoading === 'ath'}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-earth-800/60 border border-earth-700/50 text-earth-300 text-xs font-medium hover:bg-earth-700/60 hover:text-earth-100 transition-colors disabled:opacity-50"
                >
                  {exportLoading === 'ath'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <Download className="w-3.5 h-3.5" />}
                  ATH
                </button>
                <button
                  onClick={() => exportFile('xlsx')}
                  disabled={exportLoading === 'xlsx'}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-600/10 border border-green-600/20 text-green-400 text-xs font-medium hover:bg-green-600/20 transition-colors disabled:opacity-50"
                >
                  {exportLoading === 'xlsx'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <FileSpreadsheet className="w-3.5 h-3.5" />}
                  XLSX
                </button>
                <button
                  onClick={() => exportFile('docx')}
                  disabled={exportLoading === 'docx'}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600/10 border border-blue-600/20 text-blue-400 text-xs font-medium hover:bg-blue-600/20 transition-colors disabled:opacity-50"
                >
                  {exportLoading === 'docx'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <FileText className="w-3.5 h-3.5" />}
                  DOCX
                </button>
                <button
                  onClick={() => {
                    setItems([]);
                    setAddDesc(''); setAddUnit(''); setAddQty(''); setAddPrice('');
                    setPredictResult(null);
                    if (tenderId) {
                      setKosztLoading(true);
                      authFetch(`/api/v1/kosztorys/${tenderId}`)
                        .then((d: { items: KosztorysItem[] }) => setItems(d.items ?? []))
                        .catch(() => {})
                        .finally(() => setKosztLoading(false));
                    }
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-earth-800/40 border border-earth-700/30 text-earth-500 text-xs font-medium hover:text-earth-300 transition-colors ml-auto"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Odśwież
                </button>
              </div>

              {/* Summary bar */}
              {items.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.22 }}
                  className="p-4 rounded-2xl bg-earth-900/70 border border-emerald-500/20 flex items-center gap-6 flex-wrap"
                >
                  {/* Net */}
                  <div>
                    <p className="text-earth-500 text-xs mb-0.5">Razem NETTO</p>
                    <p className="text-earth-100 text-xl font-bold font-mono tabular-nums">
                      {fmtPLN(totalNet)}
                    </p>
                  </div>

                  <div className="text-earth-700 text-xl font-light">+</div>

                  {/* Overhead */}
                  <div>
                    <p className="text-earth-500 text-xs mb-0.5">Narzut ({(OVERHEAD_PCT * 100).toFixed(0)}%)</p>
                    <p className="text-earth-400 text-xl font-bold font-mono tabular-nums">
                      {fmtPLN(totalNet * OVERHEAD_PCT)}
                    </p>
                  </div>

                  <div className="text-earth-700 text-xl font-light">=</div>

                  {/* Gross */}
                  <div className="flex-1 min-w-[200px]">
                    <p className="text-emerald-400 text-xs mb-0.5 font-medium">Szacunek BRUTTO (z narzutem)</p>
                    <p className="text-emerald-400 text-2xl font-bold font-mono tabular-nums">
                      {fmtPLN(totalGross)}
                    </p>
                  </div>

                  {/* Comparison with tender value */}
                  {tenderValuePln > 0 && (
                    <div className="shrink-0">
                      <p className="text-earth-500 text-xs mb-0.5">vs. wartość przetargu</p>
                      <div className={`flex items-center gap-1.5 ${totalGross <= tenderValuePln ? 'text-emerald-400' : 'text-red-400'}`}>
                        <TrendingUp className="w-4 h-4" />
                        <span className="text-sm font-bold font-mono tabular-nums">
                          {totalGross <= tenderValuePln ? '' : '+'}
                          {fmtPLN(totalGross - tenderValuePln)}
                        </span>
                        <span className="text-xs">
                          ({totalGross <= tenderValuePln ? '' : '+'}
                          {tenderValuePln > 0 ? (((totalGross - tenderValuePln) / tenderValuePln) * 100).toFixed(1) : 0}%)
                        </span>
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
            </div>
          )}
        </div>

        {/* ── Sekocenbud Sidebar ───────────────────────────────────────────── */}
        <AnimatePresence>
          {showSeko && (
            <div className="py-5 pr-6 shrink-0">
              <SekocenbudSidebar
                onPrefill={prefillFromSeko}
                onClose={() => setShowSeko(false)}
              />
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Compare Modal (Portal-like AnimatePresence) ──────────────────── */}
      <AnimatePresence>
        {compareOpen && compareIds.length >= 2 && (
          <CompareModal
            tenders={tenders}
            compareIds={compareIds}
            onClose={() => setCompareOpen(false)}
            authFetch={authFetch}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
