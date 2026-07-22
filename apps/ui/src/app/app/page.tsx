'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { useStore } from '@/store/useStore';
import { Activity, Brain, Target, Calculator, type LucideIcon } from 'lucide-react';

// ── Helpers ────────────────────────────────────────────────────────────────────

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 18) return 'Dzień dobry';
  return 'Dobry wieczór';
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function statusToOcena(status: string): 'go' | 'nogo' | 'warn' {
  if (status === 'decided_go' || status === 'won') return 'go';
  if (status === 'decided_nogo' || status === 'lost' || status === 'archived') return 'nogo';
  return 'warn';
}

function ocenaLabel(o: 'go' | 'nogo' | 'warn'): string {
  if (o === 'go')   return 'GO';
  if (o === 'nogo') return 'NO-GO';
  return 'UWAGA';
}

function ocenaBadgeStyle(o: 'go' | 'nogo' | 'warn'): { background: string; color: string } {
  if (o === 'go')   return { background: 'rgba(16,185,129,0.15)', color: '#10b981' };
  if (o === 'nogo') return { background: 'rgba(239,68,68,0.15)',  color: '#ef4444' };
  return { background: 'rgba(234,179,8,0.15)', color: '#eab308' };
}

const MONTH_PL = ['Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru'];
function monthLabel(m: string): string {
  const parts = m.split('-');
  const monthIdx = parts[1] ? parseInt(parts[1], 10) - 1 : -1;
  return MONTH_PL[monthIdx] ?? m;
}

// ── Skeleton ───────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse bg-[#0f0f1a] rounded ${className ?? ''}`} />;
}

// ── Activity chart (Canvas 2D — no recharts) ───────────────────────────────────

function ActivityChart({ data, labels }: { data: number[]; labels?: string[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const chartData = data.length > 0 ? data : [0, 0, 0, 0, 0, 0, 0];
    const chartLabels = labels ?? chartData.map((_, i) => String(i + 1));

    const dpr      = window.devicePixelRatio || 1;
    const W        = canvas.offsetWidth;
    const H        = canvas.offsetHeight;
    canvas.width   = W * dpr;
    canvas.height  = H * dpr;
    ctx.scale(dpr, dpr);

    const labelH = 18;
    const max    = Math.max(...chartData, 1); // avoid div-by-zero
    const n      = chartData.length;
    const chartH = H - labelH - 4;
    const slotW  = W / n;
    const barW   = Math.floor(slotW * 0.55);

    ctx.clearRect(0, 0, W, H);

    chartData.forEach((val, i) => {
      const barH   = Math.round((val / max) * chartH);
      const x      = i * slotW + (slotW - barW) / 2;
      const y      = chartH - barH;
      const isMax  = val === max;
      const r      = Math.min(4, barW / 2, barH > 1 ? barH / 2 : 0.5);

      if (isMax) {
        ctx.fillStyle = '#10b981';
      } else {
        ctx.fillStyle = 'rgba(16,185,129,0.35)';
      }

      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + barW - r, y);
      ctx.quadraticCurveTo(x + barW, y, x + barW, y + r);
      ctx.lineTo(x + barW, chartH);
      ctx.lineTo(x, chartH);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
      ctx.closePath();
      ctx.fill();

      const lbl = chartLabels[i] ?? String(i + 1);
      ctx.fillStyle    = 'rgba(100,116,139,0.8)';
      ctx.font         = `${Math.round(10 * dpr) / dpr}px ui-sans-serif, system-ui, sans-serif`;
      ctx.textAlign    = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(lbl, x + barW / 2, chartH + 5);
    });

    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth   = 1;
    ctx.beginPath();
    ctx.moveTo(0, chartH);
    ctx.lineTo(W, chartH);
    ctx.stroke();
  }, [data, labels]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full"
      style={{ height: '96px', display: 'block' }}
    />
  );
}

// ── API response types ─────────────────────────────────────────────────────────

interface DashboardStats {
  total_tenders: number;
  new_today: number;
  high_score_count: number;
  pipeline_value: number;
  avg_score: number | null;
  weekly_activity: Array<{ day: string; count: number }>;
}

interface PipelineKPI {
  active_count: number;
  pipeline_value: number;
  win_rate_mtd: number | null;
  avg_deal_size: number | null;
  new_today: number;
}

interface AnalyticsDashboard {
  pipeline_value: number;
  active_bids: number;
  win_rate: number;
  win_rate_pct: number;
  total_won: number;
  total_lost: number;
  avg_margin: number | null;
}

interface WinRateTrendItem {
  month: string;
  won: number;
  lost: number;
  total: number;
  win_rate: number;
}

interface WinRateTrend {
  trend: WinRateTrendItem[];
  months: number;
}

interface TenderItem {
  id: string;
  title: string;
  buyer: string | null;
  status: string;
  deadline_at: string | null;
  created_at: string;
}

interface TendersResponse {
  items: TenderItem[];
  total: number;
}

// ── Metric card definition ─────────────────────────────────────────────────────

interface MetricCard {
  label: string;
  value: string | null;   // null → show skeleton
  trend: string | null;
  trendPositive: boolean;
  Icon: LucideIcon;
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const user        = useStore((s) => s.user);
  const accessToken = useStore((s) => s.accessToken);
  const router      = useRouter();
  const isAuth      = !!(user && accessToken);

  const [statsData,     setStatsData]     = useState<DashboardStats | null>(null);
  const [kpiData,       setKpiData]       = useState<PipelineKPI | null>(null);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsDashboard | null>(null);
  const [trendData,     setTrendData]     = useState<WinRateTrend | null>(null);
  const [tendersData,   setTendersData]   = useState<TendersResponse | null>(null);

  const [statsLoading,     setStatsLoading]     = useState(true);
  const [kpiLoading,       setKpiLoading]       = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [trendLoading,     setTrendLoading]     = useState(true);
  const [tendersLoading,   setTendersLoading]   = useState(true);

  useEffect(() => {
    if (!isAuth) router.replace('/login');
  }, [isAuth, router]);

  // ── Silent background GET — no toast on error, just returns null ──────────────
  const silentGet = useCallback(
    async <T,>(url: string): Promise<T | null> => {
      try {
        const res = await fetch(url, {
          headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        });
        if (!res.ok) return null;
        return (await res.json()) as T;
      } catch {
        return null;
      }
    },
    [accessToken],
  );

  useEffect(() => {
    silentGet<DashboardStats>('/api/v2/dashboard/stats')
      .then((d) => { if (d) setStatsData(d); })
      .finally(() => setStatsLoading(false));
  }, [silentGet]);

  useEffect(() => {
    silentGet<PipelineKPI>('/api/v2/dashboard/pipeline-kpi')
      .then((d) => { if (d) setKpiData(d); })
      .finally(() => setKpiLoading(false));
  }, [silentGet]);

  useEffect(() => {
    silentGet<AnalyticsDashboard>('/api/v2/analytics/dashboard')
      .then((d) => { if (d) setAnalyticsData(d); })
      .finally(() => setAnalyticsLoading(false));
  }, [silentGet]);

  useEffect(() => {
    silentGet<WinRateTrend>('/api/v2/analytics/win-rate-trend?months=7')
      .then((d) => { if (d) setTrendData(d); })
      .finally(() => setTrendLoading(false));
  }, [silentGet]);

  useEffect(() => {
    silentGet<TendersResponse>('/api/v2/tenders?limit=5&sort=created_at')
      .then((d) => { if (d) setTendersData(d); })
      .finally(() => setTendersLoading(false));
  }, [silentGet]);

  if (!isAuth) return null;

  const greeting = getGreeting();

  // ── Derived metric cards ───────────────────────────────────────────────────

  const metricCards: MetricCard[] = [
    {
      label: 'Aktywne przetargi',
      value: kpiLoading ? null : String(kpiData?.active_count ?? 0),
      trend: null,
      trendPositive: true,
      Icon: Activity,
    },
    {
      label: 'Nowe dziś',
      value: statsLoading ? null : String(statsData?.new_today ?? 0),
      trend: null,
      trendPositive: true,
      Icon: Brain,
    },
    {
      label: 'Win rate',
      value: analyticsLoading ? null : `${analyticsData?.win_rate_pct ?? 0}%`,
      trend: null,
      trendPositive: true,
      Icon: Target,
    },
    {
      label: 'Wartość pipeline',
      value: kpiLoading
        ? null
        : kpiData?.pipeline_value
          ? `${(kpiData.pipeline_value / 1_000_000).toFixed(1)} M`
          : '0',
      trend: null,
      trendPositive: false,
      Icon: Calculator,
    },
  ];

  // ── Chart data from win-rate trend ─────────────────────────────────────────

  const trendItems: WinRateTrendItem[] = trendData?.trend ?? [];
  const chartData: number[]   = trendItems.map(t => Math.round(t.win_rate * 100));
  const chartLabels: string[] = trendItems.map(t => monthLabel(t.month));

  // ── Tenders list ───────────────────────────────────────────────────────────

  const tenders: TenderItem[] = tendersData?.items ?? [];

  return (
    <div className="px-6 py-8 max-w-6xl mx-auto">

      {/* ── Greeting ── */}
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-8"
      >
        <h1
          className="text-2xl font-bold text-slate-100"
          style={{ fontFamily: 'var(--font-space)' }}
        >
          {greeting},{' '}
          <span style={{ color: '#10b981' }}>
            {user?.name?.split(' ')[0] ?? 'Witaj'}
          </span>
          .
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Oto co dzieje się w Twoich przetargach.
        </p>
      </motion.div>

      {/* ── Breadcrumb ── */}
      <div className="flex items-center gap-1.5 mb-4" style={{ fontSize: '11px' }}>
        <span style={{ color: '#475569' }}>BudOS</span>
        <span style={{ color: '#334155' }}>/</span>
        <span style={{ color: '#94a3b8' }}>Dashboard</span>
      </div>

      {/* ── Metric cards ── */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {metricCards.map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.35 }}
            className="rounded-2xl p-5 flex flex-col gap-3"
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            {/* icon + label row */}
            <div className="flex items-center justify-between">
              <span style={{ fontSize: '11px', color: '#64748b', letterSpacing: '0.04em' }}>
                {card.label}
              </span>
              <card.Icon size={14} style={{ color: '#334155' }} />
            </div>

            {/* value or skeleton */}
            {card.value === null ? (
              <Skeleton className="h-9 w-16" />
            ) : (
              <span
                className="text-3xl font-bold"
                style={{ color: '#e8edf5', fontFamily: 'var(--font-space)', lineHeight: 1 }}
              >
                {card.value}
              </span>
            )}

            {/* trend */}
            {card.trend !== null && (
              <span
                className="text-[11px] font-medium"
                style={{ color: card.trendPositive ? '#10b981' : '#ef4444' }}
              >
                {card.trendPositive ? '↑' : '↓'} {card.trend} vs poprzedni okres
              </span>
            )}
          </motion.div>
        ))}
      </div>

      {/* ── Przetargi table ── */}
      <motion.section
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25, duration: 0.4 }}
        className="rounded-2xl border border-white/[0.07] overflow-hidden mb-6"
        style={{ background: 'rgba(255,255,255,0.03)', backdropFilter: 'blur(16px)' }}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
          <h2
            className="text-sm font-semibold text-slate-200"
            style={{ fontFamily: 'var(--font-space)' }}
          >
            Najnowsze przetargi
          </h2>
        </div>

        {/* Table header */}
        <div
          className="grid px-5 py-2 text-[10px] font-semibold uppercase tracking-widest text-slate-600 border-b border-white/[0.05]"
          style={{ gridTemplateColumns: '1fr 1fr auto auto' }}
        >
          <span>Tytuł</span>
          <span>Zamawiający</span>
          <span className="text-right pr-6">Termin</span>
          <span>Ocena</span>
        </div>

        {/* Table rows */}
        <div className="divide-y divide-white/[0.04]">
          {tendersLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="px-5 py-4">
                <Skeleton className="h-4 w-full" />
              </div>
            ))
          ) : tenders.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-slate-600">
              Brak przetargów
            </div>
          ) : (
            tenders.map((p, i) => {
              const ocena = statusToOcena(p.status);
              return (
                <motion.div
                  key={p.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.05 }}
                  className="grid items-center gap-4 px-5 cursor-pointer transition-colors"
                  style={{
                    gridTemplateColumns: '1fr 1fr auto auto',
                    paddingTop: '16px',
                    paddingBottom: '16px',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background = '';
                  }}
                >
                  <span className="text-sm text-slate-200 font-medium truncate">{p.title}</span>
                  <span className="text-xs text-slate-500 truncate">{p.buyer ?? '—'}</span>
                  <span className="text-[11px] font-mono text-slate-600 shrink-0">
                    {p.deadline_at ? formatDate(p.deadline_at) : '—'}
                  </span>
                  <span
                    style={{
                      ...ocenaBadgeStyle(ocena),
                      fontSize: '10px',
                      fontWeight: 600,
                      letterSpacing: '0.06em',
                      padding: '3px 8px',
                      borderRadius: '6px',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {ocenaLabel(ocena)}
                  </span>
                </motion.div>
              );
            })
          )}
        </div>
      </motion.section>

      {/* ── Activity chart ── */}
      <motion.section
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.32, duration: 0.4 }}
        className="rounded-2xl border border-white/[0.07] overflow-hidden"
        style={{ background: 'rgba(255,255,255,0.03)', backdropFilter: 'blur(16px)' }}
      >
        <div className="px-5 py-4 border-b border-white/[0.06]">
          <h2
            className="text-sm font-semibold text-slate-200"
            style={{ fontFamily: 'var(--font-space)' }}
          >
            Win rate — ostatnie 7 miesięcy
          </h2>
          <p className="text-[11px] text-slate-600 mt-0.5">
            Procent wygranych przetargów per miesiąc
          </p>
        </div>
        <div className="px-4 pt-4 pb-3">
          {trendLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : (
            <ActivityChart data={chartData} labels={chartLabels} />
          )}
        </div>
      </motion.section>

    </div>
  );
}
