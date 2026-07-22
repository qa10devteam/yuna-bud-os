'use client';

/**
 * MarketDashboardPage — S6
 * Rynek: BZP · TED UE · GUS Budownictwo
 *
 * Layout:
 *  Row 0 — 6 KPI cards (real data z bazy)
 *  Row 1 — BZP trend tygodniowy 26 tyg (AreaChart full-width)
 *  Row 2 — TED podział notice_type (Pie) | TED Top CPV (HorizontalBar)
 *  Row 3 — GUS produkcja top-5 woj (MultiLine) | GUS wynagrodzenia (AreaChart)
 *  Row 4 — BZP top CPV (HorizontalBar) | BZP mapa województw (PolandHeatmap)
 *  Row 5 — Pre-tender sygnały miesięcznie (BarChart full-width)
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  AreaChart, Area,
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell,
  XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  Activity, TrendingUp, BarChart3, Globe2, Zap,
  Building2, RefreshCw, AlertCircle, ChevronRight,
  ArrowUpRight, Clock,
} from 'lucide-react';
import { GlassCard }         from '@/components/ui/GlassCard';
import { MetricCard }        from '@/components/ui/MetricCard';
import { PageShell }         from '@/components/PageShell';
import { PolandHeatmap }     from '@/components/PolandHeatmap';
import { SkeletonKPI }       from '@/components/ui/SkeletonLoader';
import { useAuthFetch }      from '@/lib/api-v2';

// ─── Design tokens (dopasowane do earth palette) ─────────────────────────────

const T = {
  emerald:  '#10b981',   // em
  blue:     '#3b82f6',   // indigo
  violet:   '#8b5cf6',   // violet
  amber:    '#f59e0b',   // warn
  red:      '#ef4444',   // nogo
  cyan:     '#06b6d4',
  surface:  '#1c1a16',   // ink-800
  border:   'rgba(74,66,55,0.5)',   // ink-700/50
  muted:    '#6b5e50',   // slate-500
  text2:    '#c4b5a0',   // slate-300
} as const;

// Tooltip style — pasuje do ink-900 tła
const TOOLTIP_STYLE = {
  backgroundColor: '#0f0d0a',
  border: `1px solid ${T.border}`,
  borderRadius: 8,
  color: T.text2,
  fontSize: 12,
  padding: '8px 12px',
} as const;

const TICK = { fill: T.muted, fontSize: 11 } as const;
const GRID = { stroke: 'rgba(255,255,255,0.04)', strokeDasharray: '3 3' as string } as const;

// Kolory województw dla multi-line
const PROVINCE_COLORS: Record<string, string> = {
  MAZOWIECKIE:   T.blue,
  ŚLĄSKIE:       T.amber,
  MAŁOPOLSKIE:   T.emerald,
  DOLNOŚLĄSKIE:  T.violet,
  WIELKOPOLSKIE: T.cyan,
};

const PIE_COLORS = [T.blue, T.emerald, T.amber, T.violet, T.red, T.cyan];

// Mapowanie NUTS2 kod → pełna nazwa (dla heatmapy)
const NUTS2_MAP: Record<string, string> = {
  PL02: 'DOLNOŚLĄSKIE',
  PL04: 'KUJ.-POMOR.',
  PL06: 'LUBELSKIE',
  PL08: 'LUBUSKIE',
  PL10: 'ŁÓDZKIE',
  PL12: 'MAZOWIECKIE',
  PL14: 'MAŁOPOLSKIE',
  PL16: 'OPOLSKIE',
  PL18: 'PODKARPACKIE',
  PL20: 'PODLASKIE',
  PL22: 'POMORSKIE',
  PL24: 'ŚLĄSKIE',
  PL26: 'ŚWIĘTOKRZYSKIE',
  PL28: 'WARM.-MAZ.',
  PL30: 'WIELKOPOLSKIE',
  PL32: 'ZACHODNIOPOM.',
  // fallback dla surowych nazw
  'śląskie': 'ŚLĄSKIE',
};

// Mapowanie NUTS2 → kod używany przez PolandHeatmap
const NUTS2_TO_HEATMAP: Record<string, string> = {
  PL02: 'PL34', PL04: 'PL14', PL06: 'PL23',
  PL08: 'PL31', PL10: 'PL11', PL12: 'PL12',
  PL14: 'PL21', PL16: 'PL41', PL18: 'PL24',
  PL20: 'PL61', PL22: 'PL63', PL24: 'PL22',
  PL26: 'PL62', PL28: 'PL51', PL30: 'PL32',
  PL32: 'PL33', 'śląskie': 'PL22',
};

// CPV prefix → czytelna nazwa
const CPV_PREFIX_LABELS: Record<string, string> = {
  '45': 'Roboty budowlane',
  '71': 'Usługi inżyn.',
  '72': 'IT',
  '48': 'Oprogramowanie',
  '50': 'Naprawy/utrzym.',
  '79': 'Usługi biznesowe',
  '85': 'Zdrowie',
  '90': 'Sanit./środowisko',
  '34': 'Transport',
  '55': 'Gastronomia',
  '60': 'Transport publ.',
  '66': 'Finanse',
  '73': 'B+R',
  '76': 'Górnictwo',
  '80': 'Edukacja',
};

// ─── Typy danych ─────────────────────────────────────────────────────────────

interface KPI {
  bzp_30d:            number;
  unique_contractors: number;
  avg_value_k:        number;
  total_value_bln:    number;
  ted_30d:            number;
  pretender_30d:      number;
  gus_production_mln: number;
}

interface BzpWeekly    { week: string;   count: number }
interface TedType      { type: string;   count: number }
interface TedCpv       { cpv: string;    count: number }
interface GusRow       { period: string; value: number; province: string }
interface GusWage      { period: string; value: number }
interface BzpCpv       { cpv: string;    count: number }
interface BzpVoiv      { province: string; n: number }
interface PretenderRow { month: string;  count: number }

interface MarketData {
  kpi:               KPI;
  bzp_weekly:        BzpWeekly[];
  ted_types:         TedType[];
  ted_cpv:           TedCpv[];
  gus_production:    GusRow[];
  gus_wages:         GusWage[];
  bzp_cpv:           BzpCpv[];
  bzp_voivodeship:   BzpVoiv[];
  pretender_monthly: PretenderRow[];
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ChartSkeleton({ height = 260 }: { height?: number }) {
  return (
    <div
      className="rounded-xl bg-ink-800/40 animate-pulse"
      style={{ height }}
    />
  );
}

interface ChartCardProps {
  title:    string;
  subtitle?: string;
  icon:     React.ElementType;
  children: React.ReactNode;
  loading:  boolean;
  height?:  number;
  badge?:   React.ReactNode;
}

function ChartCard({
  title, subtitle, icon: Icon, children, loading, height = 260, badge,
}: ChartCardProps) {
  return (
    <GlassCard className="p-5 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-ink-700/60 to-ink-800/80 flex items-center justify-center">
            <Icon className="w-4 h-4 text-em" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 leading-tight">{title}</h3>
            {subtitle && (
              <p className="text-[11px] text-slate-500 mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
        {badge}
      </div>
      {/* Chart */}
      {loading ? <ChartSkeleton height={height} /> : children}
    </GlassCard>
  );
}

// Badge "live" z pulsującą kropką
function LiveBadge() {
  return (
    <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-em/10 border border-em/20">
      <span className="w-1.5 h-1.5 rounded-full bg-em animate-pulse" />
      <span className="text-[10px] font-medium text-em">LIVE</span>
    </span>
  );
}

// Custom Tooltip z ink-900 tłem
function ChartTooltipContent({
  active, payload, label, formatter,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
  formatter?: (v: number, name: string) => [string, string];
}) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-xl border border-ink-700/50 shadow-xl"
      style={TOOLTIP_STYLE}
    >
      {label && <p className="text-slate-400 text-[11px] mb-1">{label}</p>}
      {payload.map((p, i) => {
        const [val, name] = formatter ? formatter(p.value, p.name) : [p.value.toString(), p.name];
        return (
          <div key={i} className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: p.color }} />
            <span className="text-slate-300 text-xs">{name}:</span>
            <span className="text-slate-100 text-xs font-semibold tabular-nums">{val}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Transformacje danych ─────────────────────────────────────────────────────

/** GUS production → pivot per year z województwami jako kolumny */
function buildGusProductionData(rows: GusRow[]): Array<Record<string, string | number>> {
  const byYear: Record<string, Record<string, number>> = {};
  for (const r of rows) {
    if (!byYear[r.period]) byYear[r.period] = { period: parseInt(r.period, 10) };
    byYear[r.period][r.province] = r.value;
  }
  return Object.values(byYear).sort((a, b) => (a.period as number) - (b.period as number));
}

/** Normalizuj woj. BZP (NUTS2 kody PL) → format dla PolandHeatmap */
function buildHeatmapData(rows: BzpVoiv[]): Array<{ province: string; n: number }> {
  return rows.map((r) => ({
    province: NUTS2_TO_HEATMAP[r.province] ?? r.province,
    n: r.n,
  }));
}

/** Formatuj CPV 2-cyfrowy → "45 Roboty budowlane" */
function cpvLabel(code: string): string {
  const prefix = code.toString().padStart(2, '0');
  const name = CPV_PREFIX_LABELS[prefix];
  return name ? `${prefix} — ${name}` : `CPV ${prefix}`;
}

/** Mapuj notice_type na polską nazwę */
function tedTypeLabel(type: string): string {
  const map: Record<string, string> = {
    contract_notice: 'Ogłoszenie o zamówieniu',
    award_notice:    'Ogłoszenie o udzieleniu',
    prior_info:      'Wstępne ogłoszenie',
  };
  return map[type] ?? type;
}

// ─── KPI Row ─────────────────────────────────────────────────────────────────

function KPIRow({ kpi, loading }: { kpi?: KPI; loading: boolean }) {
  const cards = [
    {
      icon: Activity,
      label: 'BZP wyniki (30 dni)',
      value: kpi ? kpi.bzp_30d.toLocaleString('pl') : '—',
      iconColor: 'text-em',
    },
    {
      icon: Building2,
      label: 'Unikalnych wykonawców',
      value: kpi ? kpi.unique_contractors.toLocaleString('pl') : '—',
      iconColor: 'text-indigo',
    },
    {
      icon: TrendingUp,
      label: 'Śr. wartość (tys. PLN)',
      value: kpi ? `${kpi.avg_value_k.toFixed(0)} k` : '—',
      iconColor: 'text-warn',
    },
    {
      icon: BarChart3,
      label: 'Łączna wartość BZP (mld)',
      value: kpi ? `${kpi.total_value_bln} mld` : '—',
      iconColor: 'text-violet',
    },
    {
      icon: Globe2,
      label: 'TED UE (30 dni)',
      value: kpi ? kpi.ted_30d.toLocaleString('pl') : '—',
      iconColor: 'text-cyan-400',
    },
    {
      icon: Zap,
      label: 'Pre-tender sygnały (30 dni)',
      value: kpi ? kpi.pretender_30d.toLocaleString('pl') : '—',
      iconColor: 'text-nogo',
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
      {cards.map((c, i) =>
        loading ? (
          <SkeletonKPI key={i} />
        ) : (
          <motion.div
            key={c.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.3, ease: 'easeOut' }}
          >
            <MetricCard
              icon={c.icon}
              label={c.label}
              value={c.value}
              iconColor={c.iconColor}
            />
          </motion.div>
        ),
      )}
    </div>
  );
}

// ─── Główna strona ────────────────────────────────────────────────────────────

export function MarketDashboardPage() {
  const authFetch = useAuthFetch();

  const [data,       setData]       = useState<MarketData | null>(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null);

  // ── Fetch ──────────────────────────────────────────────────────────────────

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    let cancelled = false;

    (authFetch('/api/v2/dashboard/market-charts') as Promise<Response>)
      .then(async (res) => {
        if (cancelled) return;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json() as MarketData;
        setData(json);
        setRefreshedAt(new Date());
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [authFetch]);

  useEffect(() => {
    const cleanup = fetchData();
    return cleanup;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Derived data ──────────────────────────────────────────────────────────

  const gusProductionData = useMemo(
    () => data?.gus_production ? buildGusProductionData(data.gus_production) : [],
    [data?.gus_production],
  );

  const provinces = useMemo(
    () => [...new Set((data?.gus_production ?? []).map((r) => r.province))],
    [data?.gus_production],
  );

  const heatmapData = useMemo(
    () => data?.bzp_voivodeship ? buildHeatmapData(data.bzp_voivodeship) : [],
    [data?.bzp_voivodeship],
  );

  const bzpCpvLabelled = useMemo(
    () => (data?.bzp_cpv ?? []).map((r) => ({ ...r, label: r.cpv })),
    [data?.bzp_cpv],
  );

  const tedCpvLabelled = useMemo(
    () => (data?.ted_cpv ?? []).map((r) => ({ ...r, label: cpvLabel(r.cpv) })),
    [data?.ted_cpv],
  );

  const tedTypesLabelled = useMemo(
    () => (data?.ted_types ?? []).map((r) => ({ ...r, label: tedTypeLabel(r.type) })),
    [data?.ted_types],
  );

  // ── Render ────────────────────────────────────────────────────────────────

  const actions = (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-slate-600 flex items-center gap-1">
        <Clock className="w-3 h-3" />
        {refreshedAt ? refreshedAt.toLocaleTimeString('pl', { hour: '2-digit', minute: '2-digit' }) : '--:--'}
      </span>
      <button type="button"
        onClick={fetchData}
        disabled={loading}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-ink-800 border border-ink-700/50 text-slate-300 hover:text-slate-100 hover:bg-ink-700 transition-colors text-xs disabled:opacity-50"
      >
        <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
        Odśwież
      </button>
    </div>
  );

  return (
    <PageShell
      title="Rynek"
      subtitle="Dane BZP · TED UE · GUS Budownictwo — źródło: baza YUNA"
      actions={actions}
    >
      {/* ── Error banner ─────────────────────────────────────────────────── */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-3 px-4 py-3 rounded-xl bg-nogo/10 border border-nogo/30 text-nogo text-sm mb-2"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>Błąd ładowania danych: {error}</span>
            <button type="button"
              onClick={fetchData}
              className="ml-auto text-xs underline hover:no-underline"
            >
              Spróbuj ponownie
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Row 0: KPI ───────────────────────────────────────────────────── */}
      <KPIRow kpi={data?.kpi} loading={loading} />

      {/* ── Row 1: BZP trend tygodniowy (full-width) ─────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35, duration: 0.4 }}
      >
        <ChartCard
          title="BZP — Aktywność rynku (ostatnie 26 tygodni)"
          subtitle={data ? `Łącznie ${data.bzp_weekly.reduce((s, r) => s + r.count, 0).toLocaleString('pl')} ogłoszeń o udzieleniu` : undefined}
          icon={Activity}
          loading={loading}
          height={220}
          badge={<LiveBadge />}
        >
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart
              data={data?.bzp_weekly ?? []}
              margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
            >
              <defs>
                <linearGradient id="bzpWeekGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={T.emerald} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={T.emerald} stopOpacity={0}    />
                </linearGradient>
              </defs>
              <CartesianGrid {...GRID} />
              <XAxis
                dataKey="week"
                tickFormatter={(v: string) => v.slice(5)}   // MM-DD
                tick={TICK}
                tickLine={false}
                axisLine={false}
                interval={3}
              />
              <YAxis tick={TICK} tickLine={false} axisLine={false} />
              <Tooltip
                content={
                  <ChartTooltipContent
                    formatter={(v) => [v.toLocaleString('pl'), 'Ogłoszeń']}
                  />
                }
                labelFormatter={(v: string) => `Tydzień: ${v}`}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke={T.emerald}
                strokeWidth={2}
                fill="url(#bzpWeekGrad)"
                dot={false}
                activeDot={{ r: 4, fill: T.emerald, strokeWidth: 0 }}
                name="Ogłoszeń"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </motion.div>

      {/* ── Row 2: TED Pie + TED CPV ──────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45, duration: 0.4 }}
        className="grid grid-cols-1 lg:grid-cols-2 gap-4"
      >
        {/* TED Pie */}
        <ChartCard
          title="TED UE — Typy ogłoszeń"
          subtitle={data ? `${data.ted_types.reduce((s, r) => s + r.count, 0).toLocaleString('pl')} ogłoszeń PL w TED (30 dni)` : undefined}
          icon={Globe2}
          loading={loading}
          height={260}
        >
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={tedTypesLabelled}
                dataKey="count"
                nameKey="label"
                cx="50%"
                cy="47%"
                outerRadius={85}
                innerRadius={40}
                paddingAngle={3}
                label={({ label, percent }: { label: string; percent: number }) =>
                  percent > 0.05 ? `${(percent * 100).toFixed(0)}%` : ''
                }
                labelLine={false}
              >
                {tedTypesLabelled.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} stroke="transparent" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v: number) => [v.toLocaleString('pl'), 'Ogłoszeń']}
              />
              <Legend
                formatter={(value: string) => (
                  <span style={{ color: T.text2, fontSize: 11 }}>{value}</span>
                )}
                iconSize={8}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* TED Top CPV */}
        <ChartCard
          title="TED UE — Top kategorii CPV (umowy)"
          subtitle="Dominujące branże w zamówieniach UE z Polski"
          icon={BarChart3}
          loading={loading}
          height={260}
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              layout="vertical"
              data={tedCpvLabelled}
              margin={{ top: 4, right: 16, left: 4, bottom: 0 }}
            >
              <CartesianGrid {...GRID} horizontal={false} />
              <XAxis type="number" tick={TICK} tickLine={false} axisLine={false} />
              <YAxis
                type="category"
                dataKey="label"
                tick={{ ...TICK, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={120}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v: number) => [v.toLocaleString('pl'), 'Ogłoszeń']}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} name="Ogłoszeń">
                {tedCpvLabelled.map((_, i) => (
                  <Cell
                    key={i}
                    fill={T.blue}
                    fillOpacity={1 - i * 0.07}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </motion.div>

      {/* ── Row 3: GUS Produkcja + GUS Wynagrodzenia ─────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.55, duration: 0.4 }}
        className="grid grid-cols-1 lg:grid-cols-2 gap-4"
      >
        {/* GUS MultiLine */}
        <ChartCard
          title="GUS — Produkcja budowlano-montażowa"
          subtitle="Top 5 województw, 2015–2025 (wartość w mln PLN)"
          icon={TrendingUp}
          loading={loading}
          height={260}
        >
          <ResponsiveContainer width="100%" height={260}>
            <LineChart
              data={gusProductionData}
              margin={{ top: 4, right: 16, left: -10, bottom: 0 }}
            >
              <CartesianGrid {...GRID} />
              <XAxis dataKey="period" tick={TICK} tickLine={false} axisLine={false} />
              <YAxis
                tick={TICK}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `${(v / 1_000_000).toFixed(0)}M`}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v: number, name: string) => [
                  `${(v as number / 1_000_000).toFixed(1)} M PLN`,
                  name,
                ]}
              />
              <Legend
                iconSize={8}
                formatter={(v: string) => (
                  <span style={{ color: T.text2, fontSize: 10 }}>{v}</span>
                )}
              />
              {provinces.map((prov) => (
                <Line
                  key={prov}
                  type="monotone"
                  dataKey={prov as string}
                  stroke={PROVINCE_COLORS[prov] ?? T.blue}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 3 }}
                  name={prov as string}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* GUS Wynagrodzenia */}
        <ChartCard
          title="GUS — Wynagrodzenia w budownictwie"
          subtitle="Średnia krajowa PLN/rok, 2011–2015"
          icon={TrendingUp}
          loading={loading}
          height={260}
        >
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart
              data={data?.gus_wages ?? []}
              margin={{ top: 4, right: 8, left: -10, bottom: 0 }}
            >
              <defs>
                <linearGradient id="wagesGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={T.violet} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={T.violet} stopOpacity={0}   />
                </linearGradient>
              </defs>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="period" tick={TICK} tickLine={false} axisLine={false} />
              <YAxis
                tick={TICK}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v: number) => [`${v.toLocaleString('pl')} PLN/rok`, 'Wynagrodzenie']}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={T.violet}
                strokeWidth={2}
                fill="url(#wagesGrad)"
                dot={{ fill: T.violet, r: 4, strokeWidth: 0 }}
                activeDot={{ r: 5 }}
                name="Wynagrodzenie"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </motion.div>

      {/* ── Row 4: BZP CPV + Mapa województw ────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.65, duration: 0.4 }}
        className="grid grid-cols-1 lg:grid-cols-2 gap-4"
      >
        {/* BZP Top CPV HorizontalBar */}
        <ChartCard
          title="BZP — Top 10 CPV (wyniki 180 dni)"
          subtitle="Najczęstsze kody CPV w ogłoszeniach o udzieleniu"
          icon={BarChart3}
          loading={loading}
          height={280}
        >
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              layout="vertical"
              data={bzpCpvLabelled}
              margin={{ top: 4, right: 16, left: 4, bottom: 0 }}
            >
              <CartesianGrid {...GRID} horizontal={false} />
              <XAxis type="number" tick={TICK} tickLine={false} axisLine={false} />
              <YAxis
                type="category"
                dataKey="label"
                tick={{ ...TICK, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={78}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v: number) => [v.toLocaleString('pl'), 'Wyników BZP']}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} name="Wyniki BZP">
                {bzpCpvLabelled.map((_, i) => (
                  <Cell
                    key={i}
                    fill={T.emerald}
                    fillOpacity={1 - i * 0.07}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Mapa województw */}
        <ChartCard
          title="BZP — Rozkład geograficzny"
          subtitle="Liczba ogłoszeń wg województwa (180 dni)"
          icon={Building2}
          loading={loading}
          height={280}
        >
          {loading ? (
            <ChartSkeleton height={280} />
          ) : heatmapData.length > 0 ? (
            <PolandHeatmap data={heatmapData} />
          ) : (
            <div className="flex items-center justify-center h-[280px] text-slate-600 text-sm">
              Brak danych geograficznych
            </div>
          )}
        </ChartCard>
      </motion.div>

      {/* ── Row 5: Pre-tender sygnały (full-width) ───────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.75, duration: 0.4 }}
      >
        <ChartCard
          title="Pre-tender — Sygnały planowanych zamówień"
          subtitle={data ? `${data.pretender_monthly.reduce((s, r) => s + r.count, 0).toLocaleString('pl')} sygnałów · wyprzedzenie 4–8 tyg. przed ogłoszeniem` : undefined}
          icon={Zap}
          loading={loading}
          height={200}
          badge={
            <span className="px-2 py-0.5 rounded-full bg-warn/10 border border-warn/20 text-[10px] font-medium text-warn">
              PRO
            </span>
          }
        >
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={data?.pretender_monthly ?? []}
              margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
            >
              <defs>
                <linearGradient id="pretenderGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"  stopColor={T.amber} stopOpacity={0.9} />
                  <stop offset="100%" stopColor={T.amber} stopOpacity={0.4} />
                </linearGradient>
              </defs>
              <CartesianGrid {...GRID} />
              <XAxis
                dataKey="month"
                tickFormatter={(v: string) => v.slice(5)}
                tick={TICK}
                tickLine={false}
                axisLine={false}
              />
              <YAxis tick={TICK} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v: number) => [v.toLocaleString('pl'), 'Sygnałów']}
              />
              <Bar
                dataKey="count"
                fill="url(#pretenderGrad)"
                radius={[4, 4, 0, 0]}
                name="Sygnały"
                maxBarSize={48}
              />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </motion.div>

      {/* ── Footnote ─────────────────────────────────────────────────────── */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.9 }}
        className="text-[11px] text-slate-700 flex items-center gap-1.5 pt-1"
      >
        <ChevronRight className="w-3 h-3" />
        Dane: BZP (ezamówienia.gov.pl) · TED (ted.europa.eu) · GUS BDL — aktualizacja co 15 min / 6h / 24h
      </motion.p>
    </PageShell>
  );
}
