'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  BarChart2, Search, Grid3X3, TrendingUp, MapPin, Activity, HardHat,
  Loader2, AlertCircle, RefreshCw, ChevronUp, ChevronDown, X,
  Database, Package, Percent, ArrowUpRight, ArrowDownRight,
  Play, Info, Minus, ZapOff, Zap, LayoutDashboard, SlidersHorizontal,
  Map, BarChart, Sigma, Hammer,
} from 'lucide-react';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';

// ── Types ──────────────────────────────────────────────────────────────────────

interface DashboardData {
  total_records: number;
  unique_symbols: number;
  categories_count: number;
  yoy_inflation_pct: number;
  narzuty: { branza: string; ko_pct: number; z_pct: number; kz_pct: number }[];
  regional_coefficients: { voivodeship: string; coefficient: number }[];
  latest_quarter_by_type: { R?: string; M?: string; S?: string };
}

interface SearchResult {
  nazwa: string;
  symbol: string;
  cena_netto: number;
  qoq_change_pct: number | null;
  kategoria: string;
  jednostka: string;
}

interface SearchResponse {
  quarter: string;
  count: number;
  results: SearchResult[];
}

interface CategoryItem {
  nazwa: string;
  count: number;
  avg_price: number;
  unique_symbols: number;
}

interface CategoriesResponse {
  categories: CategoryItem[];
}

interface CategoryDetailTrend {
  period: string;
  avg_price: number;
}

interface CategoryDetailItem {
  nazwa: string;
  symbol: string;
  cena_netto: number;
  jednostka: string;
}

interface CategoryDetail {
  category: string;
  trend: CategoryDetailTrend[];
  top_expensive: CategoryDetailItem[];
  most_volatile: CategoryDetailItem[];
}

interface ForecastRow {
  period: string;
  predicted_price: number;
  lower_bound: number;
  upper_bound: number;
  mape_pct: number;
}

interface ForecastResponse {
  category: string;
  typ_rms: string;
  forecasts: ForecastRow[];
}

interface RegionCompareDatum {
  voivodeship: string;
  adjusted_price: number;
  coefficient: number;
  diff_vs_national_pct: number;
}

interface RegionCompareResponse {
  category: string;
  national_avg: number;
  regions: RegionCompareDatum[];
}

interface VolatilityRow {
  category: string;
  typ_rms: string;
  mean_price: number;
  cv: number;
  risk_level: 'low' | 'medium' | 'high';
}

interface VolatilityResponse {
  rows: VolatilityRow[];
}

interface RobociznaRegion {
  voivodeship: string;
  stawka_r: number;
  coefficient: number;
  breakdown: Record<string, number>;
}

interface RobociznaResponse {
  national_avg_r: number;
  regions: RobociznaRegion[];
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const fmtPLN = (v: number | null | undefined) => {
  if (v == null) return '—';
  return v.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' zł';
};

const fmtPct = (v: number | null | undefined) => {
  if (v == null) return '—';
  return (v > 0 ? '+' : '') + v.toFixed(2) + '%';
};

const fmtM = (v: number) => {
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(3) + ' M';
  if (v >= 1_000) return (v / 1_000).toFixed(1) + ' k';
  return v.toLocaleString('pl-PL');
};

const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'szukaj', label: 'Szukaj', icon: Search },
  { id: 'kategorie', label: 'Kategorie', icon: Grid3X3 },
  { id: 'prognoza', label: 'Prognoza', icon: TrendingUp },
  { id: 'regiony', label: 'Regiony', icon: MapPin },
  { id: 'zmiennosc', label: 'Zmienność', icon: Activity },
  { id: 'robocizna', label: 'Robocizna', icon: HardHat },
] as const;

type TabId = typeof TABS[number]['id'];

// ── Spinner ────────────────────────────────────────────────────────────────────

function Spinner({ size = 24 }: { size?: number }) {
  return (
    <Loader2
      className="animate-spin text-accent-info"
      style={{ width: size, height: size }}
    />
  );
}

// ── Error box ──────────────────────────────────────────────────────────────────

function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-earth-400">
      <AlertCircle className="text-accent-danger" size={32} />
      <p className="text-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1 text-xs text-accent-info hover:text-accent-info/80 transition-colors"
        >
          <RefreshCw size={12} /> Spróbuj ponownie
        </button>
      )}
    </div>
  );
}

// ── SVG Bar Chart (horizontal) ─────────────────────────────────────────────────

function HBarChart({
  data,
  labelKey,
  valueKey,
  color = '#3B82F6',
  height = 280,
}: {
  data: Record<string, any>[];
  labelKey: string;
  valueKey: string;
  color?: string;
  height?: number;
}) {
  if (!data?.length) return null;
  const sorted = [...data].sort((a, b) => b[valueKey] - a[valueKey]);
  const max = Math.max(...sorted.map(d => d[valueKey]));
  const rowH = 24;
  const paddingLeft = 160;
  const paddingRight = 60;
  const paddingTop = 10;
  const svgH = sorted.length * rowH + paddingTop * 2;
  const svgW = 540;
  const barW = svgW - paddingLeft - paddingRight;

  return (
    <svg width="100%" viewBox={`0 0 ${svgW} ${svgH}`} style={{ maxHeight: height }}>
      {sorted.map((d, i) => {
        const y = paddingTop + i * rowH;
        const w = max > 0 ? (d[valueKey] / max) * barW : 0;
        return (
          <g key={i}>
            <text
              x={paddingLeft - 8}
              y={y + rowH / 2 + 4}
              textAnchor="end"
              fill="#9ca3af"
              fontSize={10}
            >
              {d[labelKey]}
            </text>
            <rect
              x={paddingLeft}
              y={y + 4}
              width={Math.max(w, 0)}
              height={rowH - 8}
              fill={color}
              opacity={0.75}
              rx={2}
            />
            <text
              x={paddingLeft + w + 5}
              y={y + rowH / 2 + 4}
              fill="#e5e7eb"
              fontSize={10}
            >
              {d[valueKey]?.toFixed(3)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ── SVG Line Chart ─────────────────────────────────────────────────────────────

function LineChartSVG({
  data,
  xKey,
  yKey,
  color = '#3B82F6',
  height = 180,
}: {
  data: Record<string, any>[];
  xKey: string;
  yKey: string;
  color?: string;
  height?: number;
}) {
  if (!data?.length) return null;
  const W = 480;
  const H = height;
  const pad = { top: 16, right: 20, bottom: 28, left: 56 };
  const innerW = W - pad.left - pad.right;
  const innerH = H - pad.top - pad.bottom;

  const vals = data.map(d => Number(d[yKey]) || 0);
  const minV = Math.min(...vals);
  const maxV = Math.max(...vals);
  const range = maxV - minV || 1;

  const toX = (i: number) => pad.left + (i / Math.max(data.length - 1, 1)) * innerW;
  const toY = (v: number) => pad.top + innerH - ((v - minV) / range) * innerH;

  const points = data.map((d, i) => `${toX(i)},${toY(Number(d[yKey]) || 0)}`).join(' ');

  // Label every Nth
  const step = Math.ceil(data.length / 6);

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ height }}>
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map(t => {
        const y = pad.top + innerH * (1 - t);
        const v = minV + range * t;
        return (
          <g key={t}>
            <line x1={pad.left} y1={y} x2={W - pad.right} y2={y} stroke="#374151" strokeDasharray="3,3" />
            <text x={pad.left - 6} y={y + 4} textAnchor="end" fill="#6b7280" fontSize={9}>
              {v.toFixed(0)}
            </text>
          </g>
        );
      })}
      {/* X labels */}
      {data.map((d, i) =>
        i % step === 0 ? (
          <text key={i} x={toX(i)} y={H - 4} textAnchor="middle" fill="#6b7280" fontSize={9}>
            {String(d[xKey]).slice(-5)}
          </text>
        ) : null
      )}
      {/* Line */}
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* Dots */}
      {data.map((d, i) => (
        <circle key={i} cx={toX(i)} cy={toY(Number(d[yKey]) || 0)} r={3} fill={color} />
      ))}
    </svg>
  );
}

// ── SVG Band (forecast) chart ──────────────────────────────────────────────────

function BandChartSVG({ data }: { data: ForecastRow[] }) {
  if (!data?.length) return null;
  const W = 560;
  const H = 220;
  const pad = { top: 20, right: 20, bottom: 32, left: 64 };
  const innerW = W - pad.left - pad.right;
  const innerH = H - pad.top - pad.bottom;

  const allVals = data.flatMap(d => [d.lower_bound, d.upper_bound, d.predicted_price]);
  const minV = Math.min(...allVals);
  const maxV = Math.max(...allVals);
  const range = maxV - minV || 1;

  const toX = (i: number) => pad.left + (i / Math.max(data.length - 1, 1)) * innerW;
  const toY = (v: number) => pad.top + innerH - ((v - minV) / range) * innerH;

  const upperPath = data.map((d, i) => `${i === 0 ? 'M' : 'L'}${toX(i)},${toY(d.upper_bound)}`).join(' ');
  const lowerPath = [...data].reverse().map((d, i, arr) => `${i === 0 ? 'M' : 'L'}${toX(arr.length - 1 - i)},${toY(d.lower_bound)}`).join(' ');
  const bandPath = upperPath + ' ' + lowerPath + ' Z';

  const linePts = data.map((d, i) => `${toX(i)},${toY(d.predicted_price)}`).join(' ');

  const step = Math.ceil(data.length / 6);

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ height: H }}>
      {/* Grid */}
      {[0, 0.25, 0.5, 0.75, 1].map(t => {
        const y = pad.top + innerH * (1 - t);
        const v = minV + range * t;
        return (
          <g key={t}>
            <line x1={pad.left} y1={y} x2={W - pad.right} y2={y} stroke="#374151" strokeDasharray="3,3" />
            <text x={pad.left - 6} y={y + 4} textAnchor="end" fill="#6b7280" fontSize={9}>
              {v.toFixed(0)}
            </text>
          </g>
        );
      })}
      {/* Band */}
      <path d={bandPath} fill="#3B82F6" opacity={0.15} />
      {/* Line */}
      <polyline points={linePts} fill="none" stroke="#3B82F6" strokeWidth={2} strokeLinejoin="round" />
      {/* X labels */}
      {data.map((d, i) =>
        i % step === 0 ? (
          <text key={i} x={toX(i)} y={H - 6} textAnchor="middle" fill="#6b7280" fontSize={9}>
            {d.period}
          </text>
        ) : null
      )}
      {/* Legend */}
      <rect x={pad.left} y={6} width={10} height={10} fill="#3B82F6" opacity={0.3} rx={1} />
      <text x={pad.left + 14} y={15} fill="#9ca3af" fontSize={9}>Przedział ufności</text>
      <line x1={pad.left + 110} y1={11} x2={pad.left + 130} y2={11} stroke="#3B82F6" strokeWidth={2} />
      <text x={pad.left + 134} y={15} fill="#9ca3af" fontSize={9}>Prognoza</text>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  TAB 1 — Dashboard
// ─────────────────────────────────────────────────────────────────────────────

function DashboardTab() {
  const authFetch = useAuthFetch();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch('/api/v2/icb/dashboard');
      setData(res as DashboardData);
    } catch (e: any) {
      setError(e.message || 'Błąd ładowania danych');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="flex justify-center py-20"><Spinner size={36} /></div>;
  if (error || !data) return <ErrorBox message={error || 'Brak danych'} onRetry={load} />;

  const inflation = data.yoy_inflation_pct;
  const inflColor = inflation < 0 ? 'text-accent-success' : 'text-accent-danger';

  const kpis = [
    {
      label: 'Rekordów ICB',
      value: fmtM(data.total_records),
      icon: <Database size={20} className="text-accent-info" />,
      sub: 'InterCenBud',
    },
    {
      label: 'Unikalnych symboli',
      value: data.unique_symbols?.toLocaleString('pl-PL'),
      icon: <Package size={20} className="text-accent-violet" />,
      sub: 'materiałów',
    },
    {
      label: 'Kategorii',
      value: data.categories_count?.toLocaleString('pl-PL'),
      icon: <Grid3X3 size={20} className="text-accent-warning" />,
      sub: 'grup materiałowych',
    },
    {
      label: 'Inflacja YoY',
      value: <span className={inflColor}>{fmtPct(inflation)}</span>,
      icon: inflation < 0
        ? <ArrowDownRight size={20} className="text-accent-success" />
        : <ArrowUpRight size={20} className="text-accent-danger" />,
      sub: 'rok do roku',
    },
  ];

  return (
    <div className="space-y-6">
      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((k, i) => (
          <motion.div
            key={k.label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <GlassCard className="p-5 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-earth-400 uppercase tracking-wider">{k.label}</span>
                {k.icon}
              </div>
              <div className="text-2xl font-bold text-earth-100">{k.value}</div>
              <div className="text-xs text-earth-500">{k.sub}</div>
            </GlassCard>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Narzuty table */}
        <GlassCard className="p-5">
          <h3 className="text-sm font-semibold text-earth-100 mb-4 flex items-center gap-2">
            <Percent size={16} className="text-accent-info" /> Narzuty branżowe
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-earth-800">
                  {['Branża', 'KO %', 'Z %', 'KZ %'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs text-earth-400 font-medium pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(data.narzuty || []).map((n, i) => (
                  <tr
                    key={i}
                    className="border-b border-earth-800/50 hover:bg-earth-900/40 transition-colors"
                  >
                    <td className="py-2 pr-4 text-earth-100 font-medium">{n.branza}</td>
                    <td className="py-2 pr-4 text-earth-300">{n.ko_pct?.toFixed(1)}%</td>
                    <td className="py-2 pr-4 text-earth-300">{n.z_pct?.toFixed(1)}%</td>
                    <td className="py-2 text-earth-300">{n.kz_pct?.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>

        {/* Regional coefficients bar chart */}
        <GlassCard className="p-5">
          <h3 className="text-sm font-semibold text-earth-100 mb-4 flex items-center gap-2">
            <MapPin size={16} className="text-accent-info" /> Współczynniki regionalne
          </h3>
          <HBarChart
            data={data.regional_coefficients || []}
            labelKey="voivodeship"
            valueKey="coefficient"
            height={320}
          />
        </GlassCard>
      </div>

      {/* Latest quarter by type */}
      {data.latest_quarter_by_type && (
        <GlassCard className="p-5">
          <h3 className="text-sm font-semibold text-earth-100 mb-4 flex items-center gap-2">
            <BarChart2 size={16} className="text-accent-info" /> Ostatnie kwartały wg typu
          </h3>
          <div className="grid grid-cols-3 gap-4">
            {(['R', 'M', 'S'] as const).map(t => (
              <div key={t} className="bg-earth-900/60 rounded-token p-4 border border-earth-800 text-center">
                <div className="text-2xl font-bold text-accent-info mb-1">{t}</div>
                <div className="text-xs text-earth-400 uppercase mb-2">
                  {t === 'R' ? 'Robocizna' : t === 'M' ? 'Materiały' : 'Sprzęt'}
                </div>
                <div className="text-sm font-semibold text-earth-100">
                  {data.latest_quarter_by_type[t] || '—'}
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  TAB 2 — Szukaj
// ─────────────────────────────────────────────────────────────────────────────

function SzukajTab() {
  const authFetch = useAuthFetch();
  const [query, setQuery] = useState('');
  const [inputVal, setInputVal] = useState('');
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await authFetch(`/api/v2/icb/search?q=${encodeURIComponent(q.trim())}`);
      setResult(res as SearchResponse);
    } catch (e: any) {
      setError(e.message || 'Błąd wyszukiwania');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  const handleSubmit = () => {
    setQuery(inputVal);
    doSearch(inputVal);
  };

  return (
    <div className="space-y-5">
      {/* Search bar */}
      <GlassCard className="p-5">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-earth-400" />
            <input
              type="text"
              value={inputVal}
              onChange={e => setInputVal(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="Szukaj materiału, symbolu lub kategorii…"
              className="w-full bg-earth-900/60 border border-earth-800 rounded-token pl-9 pr-4 py-2.5 text-sm text-earth-100 placeholder-earth-500 focus:outline-none focus:border-accent-info/60 focus:ring-1 focus:ring-accent-info/30 transition-all"
            />
          </div>
          <button
            onClick={handleSubmit}
            disabled={loading || !inputVal.trim()}
            className="flex items-center gap-2 px-5 py-2.5 btn-primary disabled:opacity-50 disabled:cursor-not-allowed rounded-token text-sm font-medium transition-colors"
          >
            {loading ? <Spinner size={14} /> : <Search size={14} />}
            Szukaj
          </button>
        </div>
      </GlassCard>

      {/* Results */}
      <AnimatePresence mode="wait">
        {loading && (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex justify-center py-12">
            <Spinner size={32} />
          </motion.div>
        )}
        {error && !loading && (
          <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <ErrorBox message={error} onRetry={() => doSearch(query)} />
          </motion.div>
        )}
        {result && !loading && (
          <motion.div key="result" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <GlassCard className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold text-earth-100">
                    Wyniki: <span className="text-accent-info">{result.count}</span>
                  </span>
                  {result.quarter && (
                    <span className="text-xs bg-earth-800 text-earth-300 px-2 py-0.5 rounded-full">
                      Kwartał: {result.quarter}
                    </span>
                  )}
                </div>
              </div>
              {result.results?.length === 0 ? (
                <div className="text-center py-10 text-earth-400 text-sm">
                  Brak wyników dla: <span className="text-earth-200 font-medium">"{query}"</span>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-earth-800">
                        {['Nazwa', 'Symbol', 'Cena netto', 'QoQ %', 'Kategoria', 'Jedn.'].map(h => (
                          <th key={h} className="pb-2 text-left text-xs text-earth-400 font-medium pr-4 whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.results.map((r, i) => (
                        <tr
                          key={i}
                          className="border-b border-earth-800/40 hover:bg-accent-info/5 transition-colors cursor-default"
                        >
                          <td className="py-2 pr-4 text-earth-100 max-w-[200px] truncate" title={r.nazwa}>{r.nazwa}</td>
                          <td className="py-2 pr-4 font-mono text-xs text-accent-info">{r.symbol}</td>
                          <td className="py-2 pr-4 text-earth-100 whitespace-nowrap font-medium">{fmtPLN(r.cena_netto)}</td>
                          <td className={`py-2 pr-4 whitespace-nowrap font-medium ${
                            r.qoq_change_pct == null ? 'text-earth-500' :
                            r.qoq_change_pct > 0 ? 'text-accent-danger' :
                            r.qoq_change_pct < 0 ? 'text-accent-success' : 'text-earth-400'
                          }`}>
                            {r.qoq_change_pct == null ? '—' : fmtPct(r.qoq_change_pct)}
                          </td>
                          <td className="py-2 pr-4 text-earth-300 text-xs max-w-[120px] truncate" title={r.kategoria}>{r.kategoria}</td>
                          <td className="py-2 text-earth-400 text-xs">{r.jednostka}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  TAB 3 — Kategorie
// ─────────────────────────────────────────────────────────────────────────────

function KategorieTab() {
  const authFetch = useAuthFetch();
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<CategoryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch('/api/v2/icb/categories') as CategoriesResponse;
      setCategories(res.categories || []);
    } catch (e: any) {
      setError(e.message || 'Błąd ładowania kategorii');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  const loadDetail = useCallback(async (cat: string) => {
    setSelected(cat);
    setDetail(null);
    setDetailLoading(true);
    try {
      const res = await authFetch(`/api/v2/icb/category/${encodeURIComponent(cat)}/detail`);
      setDetail(res as CategoryDetail);
    } catch (e: any) {
      showToast('error', 'Błąd ładowania szczegółów kategorii');
    } finally {
      setDetailLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { loadCategories(); }, [loadCategories]);

  if (loading) return <div className="flex justify-center py-20"><Spinner size={36} /></div>;
  if (error) return <ErrorBox message={error} onRetry={loadCategories} />;

  return (
    <div className="flex gap-5">
      {/* Category grid */}
      <div className={`grid gap-4 transition-all ${selected ? 'grid-cols-2 flex-1' : 'grid-cols-3 w-full'}`}
        style={{ gridAutoRows: 'min-content' }}>
        {categories.map((cat, i) => (
          <motion.div
            key={cat.nazwa}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: Math.min(i * 0.03, 0.5) }}
          >
            <div
              className="cursor-pointer"
              onClick={() => selected === cat.nazwa ? (setSelected(null), setDetail(null)) : loadDetail(cat.nazwa)}
            >
            <GlassCard
              className={`p-4 transition-all hover:border-accent-info/40 ${
                selected === cat.nazwa ? 'border-accent-info/60 bg-accent-info/10' : ''
              }`}
            >
              <div className="font-semibold text-earth-100 text-sm mb-2 line-clamp-2">{cat.nazwa}</div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <div className="text-earth-500">Rekordy</div>
                  <div className="text-earth-200 font-medium">{cat.count?.toLocaleString('pl-PL')}</div>
                </div>
                <div>
                  <div className="text-earth-500">Śr. cena</div>
                  <div className="text-earth-200 font-medium">{cat.avg_price?.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-earth-500">Symbole</div>
                  <div className="text-earth-200 font-medium">{cat.unique_symbols}</div>
                </div>
              </div>
            </GlassCard>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Side panel */}
      <AnimatePresence>
        {selected && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, x: 40, width: 0 }}
            animate={{ opacity: 1, x: 0, width: 380 }}
            exit={{ opacity: 0, x: 40, width: 0 }}
            className="flex-shrink-0 overflow-hidden"
            style={{ width: 380 }}
          >
            <GlassCard className="p-5 h-full">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-earth-100 line-clamp-1">{selected}</h3>
                <button
                  onClick={() => { setSelected(null); setDetail(null); }}
                  className="text-earth-400 hover:text-earth-200 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              {detailLoading && <div className="flex justify-center py-10"><Spinner /></div>}

              {detail && !detailLoading && (
                <div className="space-y-5 overflow-y-auto max-h-[70vh]">
                  {/* Trend chart */}
                  {detail.trend?.length > 0 && (
                    <div>
                      <div className="text-xs text-earth-400 uppercase tracking-wider mb-2">Trend cen</div>
                      <LineChartSVG
                        data={detail.trend}
                        xKey="period"
                        yKey="avg_price"
                        height={150}
                      />
                    </div>
                  )}

                  {/* Top expensive */}
                  {detail.top_expensive?.length > 0 && (
                    <div>
                      <div className="text-xs text-earth-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                        <ArrowUpRight size={12} className="text-accent-warning" /> Najdroższe
                      </div>
                      <div className="space-y-1">
                        {detail.top_expensive.slice(0, 5).map((item, i) => (
                          <div key={i} className="flex justify-between items-center text-xs p-2 bg-earth-900/40 rounded border border-earth-800/50">
                            <div>
                              <div className="text-earth-100 font-medium">{item.nazwa}</div>
                              <div className="text-earth-500 font-mono">{item.symbol}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-accent-warning font-semibold">{fmtPLN(item.cena_netto)}</div>
                              <div className="text-earth-500">{item.jednostka}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Most volatile */}
                  {detail.most_volatile?.length > 0 && (
                    <div>
                      <div className="text-xs text-earth-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                        <Activity size={12} className="text-accent-danger" /> Najbardziej zmienne
                      </div>
                      <div className="space-y-1">
                        {detail.most_volatile.slice(0, 5).map((item, i) => (
                          <div key={i} className="flex justify-between items-center text-xs p-2 bg-earth-900/40 rounded border border-earth-800/50">
                            <div>
                              <div className="text-earth-100 font-medium">{item.nazwa}</div>
                              <div className="text-earth-500 font-mono">{item.symbol}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-earth-200 font-semibold">{fmtPLN(item.cena_netto)}</div>
                              <div className="text-earth-500">{item.jednostka}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  TAB 4 — Prognoza
// ─────────────────────────────────────────────────────────────────────────────

function ProgNozaTab({ categories }: { categories: CategoryItem[] }) {
  const authFetch = useAuthFetch();
  const [selCat, setSelCat] = useState('');
  const [selTyp, setSelTyp] = useState<'M' | 'R' | 'S'>('M');
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadForecast = useCallback(async (cat: string, typ: string) => {
    if (!cat) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await authFetch(`/api/v2/icb/forecast?category=${encodeURIComponent(cat)}&typ_rms=${typ}`);
      setData(res as ForecastResponse);
    } catch (e: any) {
      setError(e.message || 'Błąd ładowania prognoz');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  const computeForecast = useCallback(async () => {
    if (!selCat) return;
    setComputing(true);
    try {
      await authFetch('/api/v2/icb/forecast/compute', {
        method: 'POST',
        body: JSON.stringify({ category: selCat, typ_rms: selTyp }),
      });
      showToast('success', 'Obliczanie prognoz uruchomione');
      await loadForecast(selCat, selTyp);
    } catch (e: any) {
      showToast('error', 'Błąd obliczania prognoz');
    } finally {
      setComputing(false);
    }
  }, [authFetch, selCat, selTyp, loadForecast]);

  const hasForecast = data && data.forecasts?.length > 0;

  return (
    <div className="space-y-5">
      {/* Controls */}
      <GlassCard className="p-5">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-earth-400 mb-1.5">Kategoria</label>
            <select
              value={selCat}
              onChange={e => setSelCat(e.target.value)}
              className="w-full bg-earth-900/60 border border-earth-800 rounded-token px-3 py-2.5 text-sm text-earth-100 focus:outline-none focus:border-accent-info/60"
            >
              <option value="">— wybierz kategorię —</option>
              {categories.map(c => (
                <option key={c.nazwa} value={c.nazwa}>{c.nazwa}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-earth-400 mb-1.5">Typ R/M/S</label>
            <select
              value={selTyp}
              onChange={e => setSelTyp(e.target.value as 'M' | 'R' | 'S')}
              className="bg-earth-900/60 border border-earth-800 rounded-token px-3 py-2.5 text-sm text-earth-100 focus:outline-none focus:border-accent-info/60"
            >
              <option value="M">M — Materiały</option>
              <option value="R">R — Robocizna</option>
              <option value="S">S — Sprzęt</option>
            </select>
          </div>
          <button
            onClick={() => loadForecast(selCat, selTyp)}
            disabled={!selCat || loading}
            className="flex items-center gap-2 px-5 py-2.5 btn-primary disabled:opacity-50 disabled:cursor-not-allowed rounded-token text-sm font-medium transition-colors"
          >
            {loading ? <Spinner size={14} /> : <TrendingUp size={14} />}
            Pobierz prognozy
          </button>
        </div>
      </GlassCard>

      <AnimatePresence mode="wait">
        {loading && (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex justify-center py-12">
            <Spinner size={32} />
          </motion.div>
        )}

        {!loading && data && !hasForecast && (
          <motion.div key="no-forecast" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <GlassCard className="p-10 text-center">
              <ZapOff size={40} className="text-earth-500 mx-auto mb-3" />
              <p className="text-earth-400 text-sm mb-5">
                Brak prognoz dla <strong className="text-earth-200">{selCat}</strong> / typ <strong className="text-earth-200">{selTyp}</strong>
              </p>
              <button
                onClick={computeForecast}
                disabled={computing}
                className="inline-flex items-center gap-2 px-6 py-3 bg-accent-info hover:bg-accent-info/80 disabled:opacity-60 rounded-token text-sm font-semibold text-white transition-colors"
              >
                {computing ? <Spinner size={16} /> : <Zap size={16} />}
                {computing ? 'Obliczanie…' : 'Oblicz prognozy'}
              </button>
            </GlassCard>
          </motion.div>
        )}

        {!loading && hasForecast && (
          <motion.div key="forecast" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
            {/* Band chart */}
            <GlassCard className="p-5">
              <h3 className="text-sm font-semibold text-earth-100 mb-4 flex items-center gap-2">
                <TrendingUp size={16} className="text-accent-info" />
                Prognoza: {data!.category} · typ {data!.typ_rms}
              </h3>
              <BandChartSVG data={data!.forecasts} />
            </GlassCard>

            {/* Table */}
            <GlassCard className="p-5">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-earth-800">
                      {['Okres', 'Prognoza', 'Dolny próg', 'Górny próg', 'MAPE %'].map(h => (
                        <th key={h} className="pb-2 text-left text-xs text-earth-400 font-medium pr-4">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data!.forecasts.map((row, i) => (
                      <tr key={i} className="border-b border-earth-800/40 hover:bg-accent-info/5 transition-colors">
                        <td className="py-2 pr-4 font-mono text-xs text-earth-300">{row.period}</td>
                        <td className="py-2 pr-4 font-medium text-earth-100">{fmtPLN(row.predicted_price)}</td>
                        <td className="py-2 pr-4 text-earth-400">{fmtPLN(row.lower_bound)}</td>
                        <td className="py-2 pr-4 text-earth-400">{fmtPLN(row.upper_bound)}</td>
                        <td className={`py-2 font-medium ${
                          row.mape_pct < 5 ? 'text-accent-success' : row.mape_pct < 15 ? 'text-accent-warning' : 'text-accent-danger'
                        }`}>{row.mape_pct?.toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {!loading && !data && !error && (
          <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="text-center py-16 text-earth-500 text-sm">
              Wybierz kategorię i typ, aby wyświetlić prognozy.
            </div>
          </motion.div>
        )}

        {error && !loading && (
          <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <ErrorBox message={error} onRetry={() => loadForecast(selCat, selTyp)} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  TAB 5 — Regiony
// ─────────────────────────────────────────────────────────────────────────────

function RegionyTab({ categories }: { categories: CategoryItem[] }) {
  const authFetch = useAuthFetch();
  const [selCat, setSelCat] = useState('');
  const [data, setData] = useState<RegionCompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (cat: string) => {
    if (!cat) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await authFetch(`/api/v2/icb/compare?category=${encodeURIComponent(cat)}`);
      setData(res as RegionCompareResponse);
    } catch (e: any) {
      setError(e.message || 'Błąd ładowania danych regionalnych');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  const maxPrice = data ? Math.max(...data.regions.map(r => r.adjusted_price)) : 1;

  return (
    <div className="space-y-5">
      <GlassCard className="p-5">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-xs text-earth-400 mb-1.5">Kategoria</label>
            <select
              value={selCat}
              onChange={e => { setSelCat(e.target.value); load(e.target.value); }}
              className="w-full bg-earth-900/60 border border-earth-800 rounded-token px-3 py-2.5 text-sm text-earth-100 focus:outline-none focus:border-accent-info/60"
            >
              <option value="">— wybierz kategorię —</option>
              {categories.map(c => (
                <option key={c.nazwa} value={c.nazwa}>{c.nazwa}</option>
              ))}
            </select>
          </div>
        </div>
      </GlassCard>

      <AnimatePresence mode="wait">
        {loading && (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex justify-center py-12">
            <Spinner size={32} />
          </motion.div>
        )}

        {error && !loading && (
          <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <ErrorBox message={error} onRetry={() => load(selCat)} />
          </motion.div>
        )}

        {data && !loading && (
          <motion.div key="data" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
            {/* National avg hero */}
            <GlassCard className="p-6 text-center border-accent-info/30">
              <div className="text-xs text-earth-400 uppercase tracking-widest mb-1">Średnia krajowa</div>
              <div className="text-4xl font-bold text-accent-info">{fmtPLN(data.national_avg)}</div>
              <div className="text-sm text-earth-400 mt-1">{data.category}</div>
            </GlassCard>

            {/* Regional bars */}
            <GlassCard className="p-5">
              <h3 className="text-sm font-semibold text-earth-100 mb-4 flex items-center gap-2">
                <Map size={16} className="text-accent-info" /> Porównanie regionalne
              </h3>
              <div className="space-y-2">
                {data.regions.map((r, i) => {
                  const barW = maxPrice > 0 ? (r.adjusted_price / maxPrice) * 100 : 0;
                  const diffColor = r.diff_vs_national_pct > 0 ? 'text-accent-danger' : r.diff_vs_national_pct < 0 ? 'text-accent-success' : 'text-earth-400';
                  return (
                    <motion.div
                      key={r.voivodeship}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="flex items-center gap-3"
                    >
                      <div className="w-36 text-xs text-earth-300 truncate shrink-0">{r.voivodeship}</div>
                      <div className="flex-1 bg-earth-900/60 rounded-full h-5 relative overflow-hidden">
                        <div
                          className="h-full rounded-full bg-accent-info/70 transition-all duration-500"
                          style={{ width: `${barW}%` }}
                        />
                        <span className="absolute inset-0 flex items-center px-2 text-xs text-earth-100">
                          {fmtPLN(r.adjusted_price)}
                        </span>
                      </div>
                      <div className="w-16 text-xs text-earth-400 text-right shrink-0">
                        k={r.coefficient?.toFixed(3)}
                      </div>
                      <div className={`w-16 text-xs text-right shrink-0 font-medium ${diffColor}`}>
                        {fmtPct(r.diff_vs_national_pct)}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {!data && !loading && !error && (
          <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="text-center py-16 text-earth-500 text-sm">
              Wybierz kategorię, aby porównać regiony.
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  TAB 6 — Zmienność
// ─────────────────────────────────────────────────────────────────────────────

type SortField = 'category' | 'typ_rms' | 'mean_price' | 'cv' | 'risk_level';

function ZmiennoscTab() {
  const authFetch = useAuthFetch();
  const [data, setData] = useState<VolatilityRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('cv');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch('/api/v2/icb/volatility-matrix') as VolatilityResponse;
      setData(res.rows || []);
    } catch (e: any) {
      setError(e.message || 'Błąd ładowania macierzy zmienności');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  const sorted = [...data].sort((a, b) => {
    const av = a[sortField] as any;
    const bv = b[sortField] as any;
    if (typeof av === 'number' && typeof bv === 'number') {
      return sortDir === 'asc' ? av - bv : bv - av;
    }
    return sortDir === 'asc' ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
  });

  const toggleSort = (f: SortField) => {
    if (sortField === f) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(f); setSortDir('desc'); }
  };

  const SortIcon = ({ f }: { f: SortField }) => {
    if (sortField !== f) return <Minus size={10} className="text-earth-600" />;
    return sortDir === 'asc' ? <ChevronUp size={10} className="text-accent-info" /> : <ChevronDown size={10} className="text-accent-info" />;
  };

  const riskBadge = (r: string) => {
    if (r === 'high') return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-accent-danger/20 text-accent-danger border border-accent-danger/30">Wysoki</span>;
    if (r === 'medium') return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-accent-warning/20 text-accent-warning border border-accent-warning/30">Średni</span>;
    return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-accent-success/20 text-accent-success border border-accent-success/30">Niski</span>;
  };

  if (loading) return <div className="flex justify-center py-20"><Spinner size={36} /></div>;
  if (error) return <ErrorBox message={error} onRetry={load} />;

  return (
    <GlassCard className="p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-earth-100 flex items-center gap-2">
          <Activity size={16} className="text-accent-info" /> Macierz zmienności
        </h3>
        <span className="text-xs text-earth-400">{sorted.length} pozycji</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-earth-800">
              {([
                ['category', 'Kategoria'],
                ['typ_rms', 'Typ'],
                ['mean_price', 'Śr. cena'],
                ['cv', 'CV %'],
                ['risk_level', 'Ryzyko'],
              ] as [SortField, string][]).map(([f, label]) => (
                <th
                  key={f}
                  onClick={() => toggleSort(f)}
                  className="pb-2 text-left text-xs text-earth-400 font-medium pr-4 cursor-pointer hover:text-earth-200 transition-colors select-none"
                >
                  <span className="inline-flex items-center gap-1">
                    {label} <SortIcon f={f} />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr key={i} className="border-b border-earth-800/40 hover:bg-accent-info/5 transition-colors">
                <td className="py-2 pr-4 text-earth-100 max-w-[200px] truncate" title={row.category}>{row.category}</td>
                <td className="py-2 pr-4">
                  <span className="font-mono text-xs px-1.5 py-0.5 bg-earth-800 rounded text-earth-300">{row.typ_rms}</span>
                </td>
                <td className="py-2 pr-4 text-earth-200 font-medium">{fmtPLN(row.mean_price)}</td>
                <td className={`py-2 pr-4 font-semibold ${
                  row.cv > 30 ? 'text-accent-danger' : row.cv > 15 ? 'text-accent-warning' : 'text-accent-success'
                }`}>{row.cv?.toFixed(2)}%</td>
                <td className="py-2">{riskBadge(row.risk_level)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </GlassCard>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  TAB 7 — Robocizna
// ─────────────────────────────────────────────────────────────────────────────

function RobociznaTab() {
  const authFetch = useAuthFetch();
  const [data, setData] = useState<RobociznaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch('/api/v2/icb/robocizna/map');
      setData(res as RobociznaResponse);
    } catch (e: any) {
      setError(e.message || 'Błąd ładowania danych robocizny');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="flex justify-center py-20"><Spinner size={36} /></div>;
  if (error || !data) return <ErrorBox message={error || 'Brak danych'} onRetry={load} />;

  // Collect all breakdown keys
  const bKeys = data.regions.length > 0
    ? Object.keys(data.regions[0].breakdown || {})
    : [];

  return (
    <div className="space-y-5">
      {/* Hero */}
      <GlassCard className="p-8 text-center border-accent-info/30">
        <div className="flex items-center justify-center gap-2 text-xs text-earth-400 uppercase tracking-widest mb-2">
          <HardHat size={14} className="text-accent-info" /> Robocizna — stawka krajowa R
        </div>
        <div className="text-5xl font-bold text-accent-info mb-1">
          {fmtPLN(data.national_avg_r)}
        </div>
        <div className="text-sm text-earth-400">normatywna stawka robocizny / r-g</div>
      </GlassCard>

      {/* Regional table */}
      <GlassCard className="p-5">
        <h3 className="text-sm font-semibold text-earth-100 mb-4 flex items-center gap-2">
          <Map size={16} className="text-accent-info" /> Stawki regionalne
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-earth-800">
                <th className="pb-2 text-left text-xs text-earth-400 font-medium pr-4 whitespace-nowrap">Województwo</th>
                <th className="pb-2 text-left text-xs text-earth-400 font-medium pr-4 whitespace-nowrap">Stawka R</th>
                <th className="pb-2 text-left text-xs text-earth-400 font-medium pr-4 whitespace-nowrap">Współcz.</th>
                {bKeys.map(k => (
                  <th key={k} className="pb-2 text-left text-xs text-earth-400 font-medium pr-4 whitespace-nowrap">{k}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.regions.map((r, i) => (
                <motion.tr
                  key={r.voivodeship}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.02 }}
                  className="border-b border-earth-800/40 hover:bg-accent-info/5 transition-colors"
                >
                  <td className="py-2 pr-4 text-earth-100 font-medium">{r.voivodeship}</td>
                  <td className="py-2 pr-4 text-accent-info font-semibold">{fmtPLN(r.stawka_r)}</td>
                  <td className="py-2 pr-4 text-earth-300 font-mono text-xs">{r.coefficient?.toFixed(3)}</td>
                  {bKeys.map(k => (
                    <td key={k} className="py-2 pr-4 text-earth-400 text-xs">
                      {r.breakdown?.[k] != null ? fmtPLN(r.breakdown[k]) : '—'}
                    </td>
                  ))}
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Main ICBPage
// ─────────────────────────────────────────────────────────────────────────────

export function ICBPage() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard');
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const authFetch = useAuthFetch();

  // Pre-load categories for tabs that need them
  useEffect(() => {
    authFetch('/api/v2/icb/categories')
      .then((res: any) => setCategories(res?.categories || []))
      .catch(() => {});
  }, [authFetch]);

  return (
    <PageShell
      title="Cennik ICB"
      subtitle="Baza cen robocizny, materiałów, sprzętu"
    >
      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-earth-900/60 border border-earth-800 rounded-token-lg p-1 overflow-x-auto">
        {TABS.map(tab => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-token text-xs font-medium whitespace-nowrap transition-all flex-shrink-0 ${
                active
                  ? 'bg-accent-info text-white shadow-token-md'
                  : 'text-earth-400 hover:text-earth-200 hover:bg-earth-800/60'
              }`}
            >
              <Icon size={13} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.15 }}
        >
          {activeTab === 'dashboard' && <DashboardTab />}
          {activeTab === 'szukaj' && <SzukajTab />}
          {activeTab === 'kategorie' && <KategorieTab />}
          {activeTab === 'prognoza' && <ProgNozaTab categories={categories} />}
          {activeTab === 'regiony' && <RegionyTab categories={categories} />}
          {activeTab === 'zmiennosc' && <ZmiennoscTab />}
          {activeTab === 'robocizna' && <RobociznaTab />}
        </motion.div>
      </AnimatePresence>
    </PageShell>
  );
}
