'use client';

import { useState, useMemo } from 'react';
import { motion } from 'motion/react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import {
  TrendingUp, TrendingDown, Minus, Search, Filter,
  BarChart3, Users, Building2, Zap, RefreshCw, Award,
} from 'lucide-react';
import { PageShell } from '@/components/PageShell';
import { SkeletonCard } from '@/components/SkeletonCard';
import {
  useIntelSummary, useIntelTrends, useCompetitorsTop, useBuyersTop,
  useInflation, useFTS, useWinRates, useTopBuyersCpv, useSeasonality,
  fmtMln, fmtPct, PROVINCE_MAP, CPV_LABELS,
  type TrendRow, type ContractorTop, type BuyerTop,
  type WinRateRow, type TopBuyerCpvRow, type SeasonalityRow,
} from '@/lib/api-v2';

// ── Palette ───────────────────────────────────────────────────────────────────
const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#84cc16', '#f97316'];

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KPICard({ label, value, sub, icon: Icon, trend, color = '#10b981' }: {
  label: string; value: string; sub?: string;
  icon: React.ElementType; trend?: 'up' | 'down' | 'stable'; color?: string;
}) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-earth-900 border border-earth-700 rounded-xl p-5 flex flex-col gap-3"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs text-earth-400 uppercase tracking-widest font-medium">{label}</span>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: color + '22' }}>
          <Icon size={16} style={{ color }} />
        </div>
      </div>
      <div>
        <div className="text-2xl font-bold text-earth-50">{value}</div>
        {sub && (
          <div className="flex items-center gap-1 mt-1">
            {trend && <TrendIcon size={12} style={{ color: trend === 'up' ? '#10b981' : trend === 'down' ? '#ef4444' : '#71717a' }} />}
            <span className="text-xs text-earth-400">{sub}</span>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ── Trend chart ───────────────────────────────────────────────────────────────
function TrendChart({ data, loading }: { data: TrendRow[]; loading: boolean }) {
  const aggregated = useMemo(() => {
    const map = new Map<string, { quarter: string; n_tenders: number; total_value_mln: number; avg_offers: number; count: number }>();
    for (const row of data) {
      const q = row.quarter.slice(0, 7);
      const label = formatQuarter(q);
      const ex = map.get(label) || { quarter: label, n_tenders: 0, total_value_mln: 0, avg_offers: 0, count: 0 };
      ex.n_tenders += row.n_tenders;
      ex.total_value_mln += row.total_value / 1_000_000;
      ex.avg_offers += row.avg_competition;
      ex.count += 1;
      map.set(label, ex);
    }
    return Array.from(map.values())
      .map(r => ({ ...r, avg_offers: r.count > 0 ? +(r.avg_offers / r.count).toFixed(1) : 0 }))
      .sort((a, b) => a.quarter.localeCompare(b.quarter));
  }, [data]);

  if (loading) return <div className="h-48 animate-pulse bg-earth-800 rounded-xl" />;
  if (!aggregated.length) return <div className="h-48 flex items-center justify-center text-earth-500 text-sm">Brak danych</div>;

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={aggregated} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis dataKey="quarter" tick={{ fill: '#71717a', fontSize: 11 }} />
        <YAxis tick={{ fill: '#71717a', fontSize: 11 }} />
        <Tooltip
          contentStyle={{ background: '#1a1712', border: '1px solid #3f3f46', borderRadius: 8 }}
          labelStyle={{ color: '#f5f0eb' }}
          formatter={(v: number, name: string) => [
            name === 'total_value_mln' ? fmtMln(v) : v,
            name === 'n_tenders' ? 'Przetargi' : name === 'total_value_mln' ? 'Wartość' : 'Śr. ofert',
          ]}
        />
        <Area type="monotone" dataKey="n_tenders" stroke="#10b981" fill="url(#trendGrad)" strokeWidth={2} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Competitors table ─────────────────────────────────────────────────────────
function CompetitorsTable({ data, loading }: { data: ContractorTop[]; loading: boolean }) {
  if (loading) return <div className="h-48 animate-pulse bg-earth-800 rounded-xl" />;
  if (!data.length) return <div className="p-6 text-center text-earth-500 text-sm">Brak danych dla wybranego CPV</div>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-earth-700">
            {['#', 'Firma', 'Wygrane', 'Win rate', 'Wartość'].map(h => (
              <th key={h} className="text-left py-2 px-3 text-earth-400 font-medium text-xs uppercase tracking-wide">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 10).map((c, i) => (
            <motion.tr
              key={`${c.nip}-${i}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.03 }}
              className="border-b border-earth-800 hover:bg-earth-800/50 transition-colors"
            >
              <td className="py-2 px-3 text-earth-500 font-mono text-xs">{i + 1}</td>
              <td className="py-2 px-3">
                <div className="font-medium text-earth-100 truncate max-w-[200px]">{c.contractor_name || c.nip}</div>
                <div className="text-xs text-earth-500 font-mono">{c.nip}</div>
              </td>
              <td className="py-2 px-3 text-earth-200 font-mono">{c.wins}</td>
              <td className="py-2 px-3">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-16 bg-earth-700 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.min(100, c.win_rate_pct)}%` }} />
                  </div>
                  <span className="text-earth-300 text-xs">{c.win_rate_pct.toFixed(0)}%</span>
                </div>
              </td>
              <td className="py-2 px-3 text-emerald-400 font-mono text-xs">{fmtMln(c.total_value / 1_000_000)}</td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Buyers chart ──────────────────────────────────────────────────────────────
function BuyersChart({ data, loading }: { data: BuyerTop[]; loading: boolean }) {
  if (loading) return <div className="h-48 animate-pulse bg-earth-800 rounded-xl" />;
  const top8 = data.slice(0, 8).map(b => ({
    name: (b.buyer_name || b.buyer_nip).replace(/Gmina|Miasto|Urząd/gi, '').trim().slice(0, 28),
    value: +(b.total_value / 1_000_000).toFixed(1),
    tenders: b.n_tenders,
  }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={top8} layout="vertical" margin={{ top: 0, right: 16, left: 4, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
        <XAxis type="number" tick={{ fill: '#71717a', fontSize: 10 }} />
        <YAxis type="category" dataKey="name" width={140} tick={{ fill: '#a1a1aa', fontSize: 10 }} />
        <Tooltip
          contentStyle={{ background: '#1a1712', border: '1px solid #3f3f46', borderRadius: 8 }}
          formatter={(v: number) => [fmtMln(v), 'Wartość']}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {top8.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.85} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Inflation sparkline ───────────────────────────────────────────────────────
function InflationChart({ loading, data }: { loading: boolean; data: Array<{ quarter_label: string; avg_price: number; yoy_pct: number | null }> }) {
  if (loading) return <div className="h-32 animate-pulse bg-earth-800 rounded-xl" />;
  const recent = data.filter(d => d.yoy_pct != null).slice(-12);
  return (
    <ResponsiveContainer width="100%" height={130}>
      <AreaChart data={recent} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="inflGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis dataKey="quarter_label" tick={{ fill: '#71717a', fontSize: 10 }} />
        <YAxis tick={{ fill: '#71717a', fontSize: 10 }} unit="%" />
        <Tooltip
          contentStyle={{ background: '#1a1712', border: '1px solid #3f3f46', borderRadius: 8 }}
          formatter={(v: number) => [fmtPct(v), 'YoY']}
        />
        <Area type="monotone" dataKey="yoy_pct" stroke="#f59e0b" fill="url(#inflGrad)" strokeWidth={2} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── FTS search box ────────────────────────────────────────────────────────────
function FTSSearch() {
  const [q, setQ] = useState('');
  const { data, loading, total } = useFTS(q);

  return (
    <div>
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-earth-400" />
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Szukaj przetargów np. 'remont drogi', 'kanalizacja'…"
          className="w-full bg-earth-800 border border-earth-700 rounded-lg pl-9 pr-4 py-2.5 text-sm text-earth-100 placeholder-earth-500 focus:outline-none focus:border-emerald-500 transition-colors"
        />
        {loading && <RefreshCw size={12} className="absolute right-3 top-1/2 -translate-y-1/2 text-earth-400 animate-spin" />}
      </div>
      {q.length >= 3 && (
        <div className="mt-2">
          <div className="text-xs text-earth-500 mb-2">{total} wyników dla &quot;{q}&quot;</div>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {data.map(r => (
              <div key={r.id} className="p-3 bg-earth-800 rounded-lg border border-earth-700 hover:border-earth-600 transition-colors">
                <div className="text-sm text-earth-100 line-clamp-1">{r.title}</div>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs text-earth-500">{r.buyer || r.buyer_nip}</span>
                  {r.estimated_value && <span className="text-xs text-emerald-400">{fmtMln(r.estimated_value / 1_000_000)}</span>}
                  {r.date && <span className="text-xs text-earth-600">{r.date.slice(0, 10)}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatQuarter(q: string): string {
  // "2025-10" → "Q4'25"
  const [year, month] = q.split('-');
  const qNum = Math.ceil(parseInt(month) / 3);
  return `Q${qNum}'${year.slice(2)}`;
}

/** Format raw PLN value as "X mln" or "X tys." */
function fmtPln(v: number | null | undefined): string {
  if (v == null) return '—';
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)} mln`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)} tys.`;
  return `${Math.round(v)} zł`;
}

// ── Seasonality chart ─────────────────────────────────────────────────────────
const MONTH_LABELS = ['Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru'];

function SeasonalityChart({ data, loading }: { data: SeasonalityRow[]; loading: boolean }) {
  if (loading) return <div className="h-52 animate-pulse bg-earth-800 rounded-xl" />;
  if (!data.length) return <div className="h-52 flex items-center justify-center text-earth-500 text-sm">Brak danych</div>;

  const chartData = data.map(r => ({
    month: MONTH_LABELS[(r.month - 1) % 12],
    przetargi: r.n_tenders,
    wartość: +(r.total_value / 1_000_000).toFixed(1),
    konkurencja: r.avg_competition,
  }));

  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis dataKey="month" tick={{ fill: '#71717a', fontSize: 11 }} />
          <YAxis tick={{ fill: '#71717a', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: '#1a1712', border: '1px solid #3f3f46', borderRadius: 8 }}
            labelStyle={{ color: '#f5f0eb' }}
            formatter={(v: number, name: string) => [
              name === 'wartość' ? fmtMln(v) : v,
              name === 'przetargi' ? 'Przetargi' : name === 'wartość' ? 'Wartość (mln)' : 'Śr. ofert',
            ]}
          />
          <Bar dataKey="przetargi" fill="#10b981" fillOpacity={0.8} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="grid grid-cols-3 gap-3">
        {(() => {
          const peak = data.reduce((m, r) => r.n_tenders > m.n_tenders ? r : m, data[0]);
          const slow = data.reduce((m, r) => r.n_tenders < m.n_tenders ? r : m, data[0]);
          const avgComp = (data.reduce((s, r) => s + r.avg_competition, 0) / data.length).toFixed(1);
          return [
            { label: 'Szczyt aktywności', value: MONTH_LABELS[(peak.month - 1) % 12], sub: `${peak.n_tenders.toLocaleString('pl-PL')} przetargów` },
            { label: 'Najspokojniejszy', value: MONTH_LABELS[(slow.month - 1) % 12], sub: `${slow.n_tenders.toLocaleString('pl-PL')} przetargów` },
            { label: 'Śr. konkurencja', value: avgComp, sub: 'ofert / przetarg' },
          ].map(({ label, value, sub }) => (
            <div key={label} className="p-3 bg-earth-800 rounded-lg">
              <div className="text-xs text-earth-500">{label}</div>
              <div className="text-lg font-bold text-earth-100 mt-1">{value}</div>
              <div className="text-xs text-earth-600 mt-0.5">{sub}</div>
            </div>
          ));
        })()}
      </div>
    </div>
  );
}

// ── Win-rates table ───────────────────────────────────────────────────────────
function WinRatesTable({ data, loading }: { data: WinRateRow[]; loading: boolean }) {
  if (loading) return <div className="h-48 animate-pulse bg-earth-800 rounded-xl" />;
  if (!data.length) return (
    <div className="p-6 text-center text-earth-500 text-sm">
      Brak danych — wpisz prefiks CPV i kliknij Szukaj
    </div>
  );
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-earth-700">
            {['#', 'Wykonawca', 'Wygrane', 'Śr. wartość', 'Kody CPV'].map(h => (
              <th key={h} className="text-left py-2 px-3 text-earth-400 font-medium text-xs uppercase tracking-wide">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((r, i) => (
            <motion.tr
              key={`${r.contractor_name}-${i}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.025 }}
              className="border-b border-earth-800 hover:bg-earth-800/50 transition-colors"
            >
              <td className="py-2 px-3 text-earth-500 font-mono text-xs">{i + 1}</td>
              <td className="py-2 px-3">
                <div className="font-medium text-earth-100 truncate max-w-[220px]">{r.contractor_name}</div>
              </td>
              <td className="py-2 px-3">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 rounded-full bg-emerald-500/20 overflow-hidden" style={{ width: 48 }}>
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${Math.min(100, (r.wins / (data[0]?.wins || 1)) * 100)}%` }}
                    />
                  </div>
                  <span className="text-emerald-400 font-mono text-xs font-semibold">{r.wins}</span>
                </div>
              </td>
              <td className="py-2 px-3 text-earth-300 font-mono text-xs">{fmtPln(r.avg_value_pln)}</td>
              <td className="py-2 px-3">
                <div className="flex flex-wrap gap-1">
                  {r.cpvs.slice(0, 4).map(c => (
                    <span key={c} className="px-1.5 py-0.5 bg-earth-800 border border-earth-700 rounded text-[10px] text-earth-400 font-mono">
                      {c.slice(0, 8)}
                    </span>
                  ))}
                  {r.cpvs.length > 4 && (
                    <span className="text-[10px] text-earth-600">+{r.cpvs.length - 4}</span>
                  )}
                </div>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Top buyers CPV table ──────────────────────────────────────────────────────
function TopBuyersCpvTable({ data, loading }: { data: TopBuyerCpvRow[]; loading: boolean }) {
  if (loading) return <div className="h-40 animate-pulse bg-earth-800 rounded-xl" />;
  if (!data.length) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-earth-700">
            {['#', 'Zamawiający', 'Przetargi', 'Śr. wartość'].map(h => (
              <th key={h} className="text-left py-2 px-3 text-earth-400 font-medium text-xs uppercase tracking-wide">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((r, i) => (
            <motion.tr
              key={`${r.buyer}-${i}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.02 }}
              className="border-b border-earth-800 hover:bg-earth-800/50 transition-colors"
            >
              <td className="py-2 px-3 text-earth-500 font-mono text-xs">{i + 1}</td>
              <td className="py-2 px-3">
                <div className="font-medium text-earth-100 truncate max-w-[260px]">{r.buyer}</div>
              </td>
              <td className="py-2 px-3 text-blue-400 font-mono text-xs font-semibold">{r.tenders}</td>
              <td className="py-2 px-3 text-earth-300 font-mono text-xs">{fmtPln(r.avg_value_pln)}</td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Wygrane (Win-rates) panel ─────────────────────────────────────────────────
function WygranePanel({ defaultCpv }: { defaultCpv: string }) {
  const [input, setInput] = useState(defaultCpv || '45');
  const [search, setSearch] = useState(defaultCpv || '45');

  const { data: winRates, loading: wrLoading, total: wrTotal } = useWinRates(search);
  const { data: topBuyers, loading: tbLoading, total: tbTotal } = useTopBuyersCpv(search);

  const handleSearch = () => {
    const val = input.trim();
    if (val.length >= 2) setSearch(val);
  };

  return (
    <div className="space-y-6">
      {/* Search bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Award size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-earth-400" />
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Prefiks CPV np. 45, 4523, 45233000"
            className="w-full bg-earth-800 border border-earth-700 rounded-lg pl-9 pr-4 py-2.5 text-sm text-earth-100 placeholder-earth-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>
        <button
          onClick={handleSearch}
          className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5"
        >
          <Search size={13} />
          Szukaj
        </button>
      </div>

      {/* Contractors section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="text-sm font-semibold text-earth-100">Top wykonawcy</h4>
            <p className="text-xs text-earth-500 mt-0.5">
              CPV {search} • {wrTotal} wykonawców • historical_tenders
            </p>
          </div>
          {(wrLoading) && <RefreshCw size={13} className="text-earth-400 animate-spin" />}
        </div>
        <WinRatesTable data={winRates} loading={wrLoading} />
      </div>

      {/* Buyers section */}
      {(topBuyers.length > 0 || tbLoading) && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h4 className="text-sm font-semibold text-earth-100">Top zamawiający</h4>
              <p className="text-xs text-earth-500 mt-0.5">
                CPV {search} • {tbTotal} zamawiających
              </p>
            </div>
            {tbLoading && <RefreshCw size={13} className="text-earth-400 animate-spin" />}
          </div>
          <TopBuyersCpvTable data={topBuyers} loading={tbLoading} />
        </div>
      )}
    </div>
  );
}

// ── CPV filter pills ──────────────────────────────────────────────────────────
const CPV_PILLS = [
  { value: '', label: 'Wszystkie' },
  { value: '45', label: 'Budowlane' },
  { value: '4523', label: 'Drogi' },
  { value: '4521', label: 'Obiekty' },
  { value: '4524', label: 'Sieci' },
  { value: '454', label: 'Wykończenie' },
];

const PROVINCE_PILLS = [
  { value: '', label: 'Cała PL' },
  { value: 'PL14', label: 'Mazowsze' },
  { value: 'PL24', label: 'Śląsk' },
  { value: 'PL12', label: 'Małopolska' },
  { value: 'PL22', label: 'Pomorze' },
  { value: 'PL04', label: 'Kuj-Pom' },
];

// ── Main page ─────────────────────────────────────────────────────────────────
export function MarketIntelPage() {
  const [cpv, setCpv] = useState('45');
  const [province, setProvince] = useState('');
  const [tab, setTab] = useState<'trends' | 'competitors' | 'buyers' | 'inflation' | 'wygrane' | 'seasonality'>('trends');

  const { data: summary, loading: sumLoading } = useIntelSummary(cpv || undefined);
  const { data: trends, loading: trendsLoading } = useIntelTrends(cpv || undefined, 8, province || undefined);
  const { data: competitors, loading: compLoading } = useCompetitorsTop(cpv || undefined, province || undefined);
  const { data: buyers, loading: buyersLoading } = useBuyersTop(cpv || undefined, province || undefined);
  const { data: inflation, loading: inflLoading } = useInflation(undefined, 'R');
  const { data: seasonality, loading: seasLoading } = useSeasonality(cpv || undefined);

  const trendIcon = summary?.quarterly_trend === 'up' ? TrendingUp : summary?.quarterly_trend === 'down' ? TrendingDown : Minus;
  const _ = trendIcon; // suppress unused

  return (
    <PageShell
      title="Analityka Rynkowa"
      subtitle="Dane z 1.4M przetargów BZP 2024–2025 • Intercenbud ICB"
      actions={
        <div className="flex items-center gap-2 text-xs text-earth-500">
          <Zap size={12} className="text-emerald-500" />
          Live — sub-10ms
        </div>
      }
    >
      <div className="space-y-6">

        {/* ── Filters ──────────────────────────────────────────────────────── */}
        <div className="flex flex-wrap gap-4">
          <div>
            <div className="text-xs text-earth-500 mb-1.5 uppercase tracking-wide">CPV</div>
            <div className="flex flex-wrap gap-1.5">
              {CPV_PILLS.map(p => (
                <button
                  key={p.value}
                  onClick={() => setCpv(p.value)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                    cpv === p.value
                      ? 'bg-emerald-500 text-white'
                      : 'bg-earth-800 text-earth-400 hover:text-earth-200 border border-earth-700'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs text-earth-500 mb-1.5 uppercase tracking-wide">Region</div>
            <div className="flex flex-wrap gap-1.5">
              {PROVINCE_PILLS.map(p => (
                <button
                  key={p.value}
                  onClick={() => setProvince(p.value)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                    province === p.value
                      ? 'bg-blue-500 text-white'
                      : 'bg-earth-800 text-earth-400 hover:text-earth-200 border border-earth-700'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── KPI cards ────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {sumLoading ? (
            Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
          ) : summary ? (
            <>
              <KPICard
                label="Łączna liczba"
                value={summary.kpi.n_tenders.toLocaleString('pl-PL')}
                sub={summary.last_quarter ? `Ostatni kwartał: ${formatQuarter(summary.last_quarter.slice(0, 7))}` : 'Dane historyczne'}
                icon={BarChart3}
                trend={summary.quarterly_trend ?? 'stable'}
                color="#10b981"
              />
              <KPICard
                label="Wartość rynku"
                value={fmtMln(summary.kpi.total_value_mln)}
                sub={`Śr. ${fmtMln(summary.kpi.avg_value / 1_000_000)} / przetarg`}
                icon={TrendingUp}
                color="#3b82f6"
              />
              <KPICard
                label="Śr. oferty"
                value={summary.kpi.avg_competition.toFixed(1)}
                sub="ofert na przetarg"
                icon={Users}
                color="#8b5cf6"
              />
              <KPICard
                label="Top region"
                value={summary.top_province.length > 0 ? (PROVINCE_MAP[summary.top_province[0].province] || summary.top_province[0].province) : '—'}
                sub={cpv ? (CPV_LABELS[cpv] || `CPV ${cpv}`) : 'Wszystkie CPV'}
                icon={Building2}
                color="#f59e0b"
              />
            </>
          ) : (
            <div className="col-span-4 text-center text-earth-500 py-8">Brak danych — sprawdź autentykację</div>
          )}
        </div>

        {/* ── FTS Search ───────────────────────────────────────────────────── */}
        <div className="bg-earth-900 border border-earth-700 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Search size={16} className="text-emerald-400" />
            <span className="text-sm font-semibold text-earth-100">Szukaj w bazie przetargów</span>
            <span className="text-xs text-earth-500 ml-auto">Full-text search • 1.4M rekordów</span>
          </div>
          <FTSSearch />
        </div>

        {/* ── Tabs ─────────────────────────────────────────────────────────── */}
        <div>
          <div className="flex gap-1 mb-4 bg-earth-900 rounded-lg p-1 w-fit border border-earth-700">
            {[
              { key: 'trends', label: 'Trendy', icon: TrendingUp },
              { key: 'competitors', label: 'Konkurenci', icon: Users },
              { key: 'buyers', label: 'Zamawiający', icon: Building2 },
              { key: 'inflation', label: 'Inflacja ICB', icon: Filter },
              { key: 'seasonality', label: 'Sezonowość', icon: BarChart3 },
              { key: 'wygrane', label: 'Wygrane', icon: Award },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setTab(key as typeof tab)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  tab === key
                    ? 'bg-earth-700 text-earth-50'
                    : 'text-earth-400 hover:text-earth-200'
                }`}
              >
                <Icon size={14} />
                {label}
              </button>
            ))}
          </div>

          <div className="bg-earth-900 border border-earth-700 rounded-xl p-5">
            {tab === 'trends' && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-semibold text-earth-100">Trendy kwartal — liczba przetargów</h3>
                    <p className="text-xs text-earth-500 mt-0.5">Ostatnie 8 kwartałów • mv_market_trend</p>
                  </div>
                </div>
                <TrendChart data={trends} loading={trendsLoading} />
                {!trendsLoading && trends.length > 0 && (
                  <div className="mt-4 grid grid-cols-3 gap-3">
                    {[
                      { label: 'Łącznie przetargów', value: trends.reduce((s, r) => s + r.n_tenders, 0).toLocaleString('pl-PL') },
                      { label: 'Łączna wartość', value: fmtMln(trends.reduce((s, r) => s + r.total_value / 1_000_000, 0)) },
                      { label: 'Śr. ofert/przetarg', value: (trends.reduce((s, r) => s + r.avg_competition, 0) / Math.max(1, trends.length)).toFixed(1) },
                    ].map(({ label, value }) => (
                      <div key={label} className="p-3 bg-earth-800 rounded-lg">
                        <div className="text-xs text-earth-500">{label}</div>
                        <div className="text-lg font-bold text-earth-100 mt-1">{value}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {tab === 'competitors' && (
              <div>
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-earth-100">Top wykonawcy wg liczby wygranych</h3>
                  <p className="text-xs text-earth-500 mt-0.5">mv_contractor_ranking • tylko budownictwo</p>
                </div>
                <CompetitorsTable data={competitors} loading={compLoading} />
              </div>
            )}

            {tab === 'buyers' && (
              <div>
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-earth-100">Top zamawiający wg wartości zamówień</h3>
                  <p className="text-xs text-earth-500 mt-0.5">mv_buyer_ranking • mln PLN</p>
                </div>
                <BuyersChart data={buyers} loading={buyersLoading} />
              </div>
            )}

            {tab === 'inflation' && (
              <div>
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-earth-100">Inflacja cen robocizny ICB (R) — YoY %</h3>
                  <p className="text-xs text-earth-500 mt-0.5">Dane Intercenbud 2008–2026 • robocizna</p>
                </div>
                <InflationChart data={inflation} loading={inflLoading} />
                {!inflLoading && inflation.length > 0 && (
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    {(() => {
                      const last = inflation.filter(d => d.yoy_pct != null).at(-1);
                      const max = inflation.reduce((m, d) => (d.avg_price > (m?.avg_price || 0) ? d : m), inflation[0]);
                      return [
                        { label: 'Ostatni YoY', value: last ? fmtPct(last.yoy_pct) : '—', sub: last?.quarter_label },
                        { label: 'Najwyższa cena', value: max ? `${max.avg_price.toFixed(2)} zł/h` : '—', sub: max?.quarter_label },
                      ].map(({ label, value, sub }) => (
                        <div key={label} className="p-3 bg-earth-800 rounded-lg">
                          <div className="text-xs text-earth-500">{label}</div>
                          <div className="text-lg font-bold text-amber-400 mt-1">{value}</div>
                          <div className="text-xs text-earth-600 mt-0.5">{sub}</div>
                        </div>
                      ));
                    })()}
                  </div>
                )}
              </div>
            )}

            {tab === 'seasonality' && (
              <div>
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-earth-100">Sezonowość przetargów — aktywność miesięczna</h3>
                  <p className="text-xs text-earth-500 mt-0.5">
                    Liczba i wartość przetargów wg miesiąca • {cpv ? `CPV ${cpv}` : 'Wszystkie CPV'} • dane BZP 2024–2025
                  </p>
                </div>
                <SeasonalityChart data={seasonality} loading={seasLoading} />
              </div>
            )}

            {tab === 'wygrane' && (
              <div>
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-earth-100">Historyczne wygrane per CPV</h3>
                  <p className="text-xs text-earth-500 mt-0.5">
                    Kto wygrał przetargi w danej kategorii CPV • 1.4M rekordów BZP 2024–2025
                  </p>
                </div>
                <WygranePanel defaultCpv={cpv} />
              </div>
            )}
          </div>
        </div>

      </div>
    </PageShell>
  );
}
