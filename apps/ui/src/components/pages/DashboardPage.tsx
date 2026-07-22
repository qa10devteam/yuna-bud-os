'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'motion/react';
import { useAuthFetch } from '@/lib/api-v2';
import type { Tender } from '@/types';
import { useStore } from '@/store/useStore';
import { PageTransition } from '@/components/ui/PageTransition';
import { GlassCard } from '@/components/ui/GlassCard';
import { MetricCard } from '@/components/ui/MetricCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Button } from '@/components/ui/Button';
import { PageShell } from '@/components/PageShell';
import { showToast } from '@/components/Toast';
import {
  Activity,
  TrendingUp,
  Target,
  FileText,
  ArrowRight,
  RefreshCw,
  Zap,
  CalendarDays,
  Building2,
  ChevronRight,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface DashboardKPI {
  active_tenders: number;
  pipeline_value: number;
  win_rate_mtd: number;
  avg_deal_size: number;
  new_today: number;
  total_value?: number;
}

interface DashboardTender {
  id: string;
  title: string;
  buyer: string;
  deadline: string;
  match_score: number;
  value: number;
}

interface AuditEntry {
  id: string;
  action_type: 'create' | 'update' | 'delete' | 'login';
  user_email: string;
  action: string;
  created_at: string;
}

interface DigestData {
  content: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Mock data
// ─────────────────────────────────────────────────────────────────────────────

const CHART_DATA = [3, 5, 4, 8, 6, 9, 8];
const CHART_LABELS = ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Ndz'];

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function formatPLN(value: number | null | undefined): string {
  return (value ?? 0).toLocaleString('pl-PL', {
    style: 'currency',
    currency: 'PLN',
    maximumFractionDigits: 0,
  });
}

function truncate(text: string, max: number): string {
  return text.length <= max ? text : text.slice(0, max) + '…';
}

function daysUntil(dateStr: string): number {
  const diff = new Date(dateStr).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function goDecision(score: number): { label: string; color: string; bg: string } {
  if (score >= 80) return { label: 'GO', color: '#10b981', bg: 'rgba(16,185,129,0.12)' };
  if (score >= 60) return { label: 'UWAGA', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' };
  return { label: 'NO-GO', color: '#ef4444', bg: 'rgba(239,68,68,0.12)' };
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Dzień dobry';
  if (h < 18) return 'Dzień dobry';
  return 'Dobry wieczór';
}

function relativeTime(dateStr: string): string {
  const diffMs  = Date.now() - new Date(dateStr).getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffH   = Math.floor(diffMin / 60);
  const diffD   = Math.floor(diffH / 24);

  if (diffMin < 1)  return 'teraz';
  if (diffMin < 60) return `${diffMin}m temu`;
  if (diffH < 24)   return `${diffH}h temu`;
  if (diffD === 1)  return 'wczoraj';
  if (diffD < 7)    return `${diffD}d temu`;
  return new Date(dateStr).toLocaleDateString('pl-PL');
}

// ─────────────────────────────────────────────────────────────────────────────
// Animated Counter Hook
// ─────────────────────────────────────────────────────────────────────────────

function useAnimatedCounter(target: number, duration = 1200): number {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    if (target === 0) {
      setCurrent(0);
      return;
    }
    const startTime = Date.now();
    const tick = () => {
      const elapsed  = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased    = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target, duration]);

  return current;
}

// ─────────────────────────────────────────────────────────────────────────────
// AIActivityChart — canvas line chart
// ─────────────────────────────────────────────────────────────────────────────

function AIActivityChart() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr    = window.devicePixelRatio || 1;
    const width  = canvas.offsetWidth;
    const height = canvas.offsetHeight;

    canvas.width  = width  * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const data    = CHART_DATA;
    const labels  = CHART_LABELS;
    const padL    = 36;
    const padR    = 16;
    const padT    = 16;
    const padB    = 32;
    const plotW   = width  - padL - padR;
    const plotH   = height - padT - padB;
    const maxVal  = Math.max(...data) + 1;
    const minVal  = 0;
    const range   = maxVal - minVal;

    const xOf = (i: number) => padL + (i / (data.length - 1)) * plotW;
    const yOf = (v: number) => padT + plotH - ((v - minVal) / range) * plotH;

    // ── grid lines ──────────────────────────────────────────────────────────
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth   = 1;
    const gridLines = 4;
    for (let g = 0; g <= gridLines; g++) {
      const y = padT + (g / gridLines) * plotH;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(padL + plotW, y);
      ctx.stroke();
    }

    // ── gradient fill ────────────────────────────────────────────────────────
    const grad = ctx.createLinearGradient(0, padT, 0, padT + plotH);
    grad.addColorStop(0,   'rgba(16,185,129,0.18)');
    grad.addColorStop(1,   'rgba(16,185,129,0)');

    ctx.beginPath();
    ctx.moveTo(xOf(0), yOf(data[0]));
    for (let i = 1; i < data.length; i++) {
      const cx  = (xOf(i - 1) + xOf(i)) / 2;
      ctx.bezierCurveTo(cx, yOf(data[i - 1]), cx, yOf(data[i]), xOf(i), yOf(data[i]));
    }
    ctx.lineTo(xOf(data.length - 1), padT + plotH);
    ctx.lineTo(xOf(0), padT + plotH);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // ── stroke line ──────────────────────────────────────────────────────────
    ctx.beginPath();
    ctx.moveTo(xOf(0), yOf(data[0]));
    for (let i = 1; i < data.length; i++) {
      const cx = (xOf(i - 1) + xOf(i)) / 2;
      ctx.bezierCurveTo(cx, yOf(data[i - 1]), cx, yOf(data[i]), xOf(i), yOf(data[i]));
    }
    ctx.strokeStyle    = '#10b981';
    ctx.lineWidth      = 2;
    ctx.lineJoin       = 'round';
    ctx.lineCap        = 'round';
    ctx.shadowColor    = 'rgba(16,185,129,0.4)';
    ctx.shadowBlur     = prefersReducedMotion ? 0 : 6;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // ── data point dots ──────────────────────────────────────────────────────
    for (let i = 0; i < data.length; i++) {
      const x = xOf(i);
      const y = yOf(data[i]);
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle   = '#10b981';
      ctx.shadowColor = 'rgba(16,185,129,0.6)';
      ctx.shadowBlur  = prefersReducedMotion ? 0 : 8;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    // ── x-axis labels ─────────────────────────────────────────────────────────
    ctx.fillStyle  = 'rgba(148,163,184,0.7)';
    ctx.font       = `${11 * dpr / dpr}px Inter, system-ui, sans-serif`;
    ctx.textAlign  = 'center';
    ctx.textBaseline = 'top';
    for (let i = 0; i < labels.length; i++) {
      ctx.fillText(labels[i], xOf(i), padT + plotH + 8);
    }

    // ── y-axis labels (last value) ─────────────────────────────────────────
    ctx.fillStyle    = 'rgba(148,163,184,0.5)';
    ctx.textAlign    = 'right';
    ctx.textBaseline = 'middle';
    for (let g = 0; g <= gridLines; g++) {
      const v = Math.round(minVal + ((gridLines - g) / gridLines) * range);
      const y = padT + (g / gridLines) * plotH;
      ctx.fillText(String(v), padL - 6, y);
    }
  }, [prefersReducedMotion]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      style={{ display: 'block' }}
    />
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TenderRow — single row in the recent tenders list
// ─────────────────────────────────────────────────────────────────────────────

interface TenderRowProps {
  tender: DashboardTender;
  index: number;
  onClick: () => void;
}

function TenderRow({ tender, index, onClick }: TenderRowProps) {
  const days     = daysUntil(tender.deadline);
  const decision = goDecision(tender.match_score);
  const deadline = new Date(tender.deadline).toLocaleDateString('pl-PL', {
    day: '2-digit',
    month: 'short',
  });

  return (
    <motion.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.35, delay: index * 0.07 }}
      onClick={onClick}
      className="group flex items-start gap-3 px-3 py-3 rounded-xl cursor-pointer transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200 hover:bg-white/[0.03]"
    >
      {/* Decision badge */}
      <div
        className="mt-0.5 shrink-0 px-2 py-0.5 rounded-md text-[10px] font-bold tracking-wide"
        style={{ color: decision.color, background: decision.bg }}
      >
        {decision.label}
      </div>

      {/* Title + buyer */}
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-slate-100 truncate leading-snug group-hover:text-emerald-400 transition-colors">
          {truncate(tender.title, 55)}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <Building2 className="w-3 h-3 text-slate-500 shrink-0" />
          <span className="text-[11px] text-slate-500 truncate">{tender.buyer}</span>
        </div>
      </div>

      {/* Deadline */}
      <div className="shrink-0 flex flex-col items-end gap-0.5">
        <div
          className="flex items-center gap-1 text-[11px] font-medium"
          style={{ color: days < 10 ? '#f87171' : days < 21 ? '#fbbf24' : '#94a3b8' }}
        >
          <CalendarDays className="w-3 h-3" />
          {deadline}
        </div>
        <span className="text-[10px] text-slate-600">{days}d</span>
      </div>

      <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-400 transition-colors mt-0.5 shrink-0" />
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// InlineMetricCard — glassmorphism metric card (Linear-tier)
// ─────────────────────────────────────────────────────────────────────────────

interface InlineMetricCardProps {
  icon: React.ElementType;
  label: string;
  value: string;
  trend: number;
  trendLabel?: string;
  delay?: number;
}

function InlineMetricCard({ icon: Icon, label, value, trend, trendLabel = 'vs. poprzedni tydzień', delay = 0 }: InlineMetricCardProps) {
  const isPositive = trend >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.22, 1, 0.36, 1] }}
      className="relative overflow-hidden rounded-2xl p-5 flex flex-col gap-4"
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.08)',
        backdropFilter: 'blur(12px)',
      }}
    >
      {/* subtle top-left glow */}
      <div
        className="pointer-events-none absolute -top-8 -left-8 w-24 h-24 rounded-full opacity-20"
        style={{ background: 'radial-gradient(circle, #10b981 0%, transparent 70%)' }}
      />

      {/* Header row */}
      <div className="flex items-center justify-between">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.2)' }}
        >
          <Icon className="w-4 h-4 text-emerald-400" />
        </div>

        {/* Trend badge */}
        <div
          className="flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[11px] font-semibold"
          style={{
            background: isPositive ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
            color: isPositive ? '#10b981' : '#ef4444',
          }}
        >
          <span>{isPositive ? '↑' : '↓'}</span>
          <span>{Math.abs(trend)}</span>
        </div>
      </div>

      {/* Value */}
      <div>
        <p
          className="font-bold text-white leading-none tracking-tight tabular-nums"
          style={{ fontSize: 32 }}
        >
          {value}
        </p>
        <p className="text-[13px] font-medium text-slate-300 mt-2 leading-snug">{label}</p>
        <p className="text-[11px] text-slate-500 mt-0.5">{trendLabel}</p>
      </div>
      {/* Bottom accent */}
      <div className="absolute bottom-0 left-0 right-0 h-[2px] rounded-b-2xl"
        style={{ background: 'linear-gradient(90deg, rgba(16,185,129,0.4) 0%, transparent 100%)' }} />
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main — DashboardPage
// ─────────────────────────────────────────────────────────────────────────────

export function DashboardPage() {
  const authFetch = useAuthFetch();
  const { setCurrentModule, setSelectedTender, user } = useStore();
  const displayName = user?.name?.split(' ')[0] ?? 'Demo';

  // ── State ──────────────────────────────────────────────────────────────────

  const [kpi,             setKpi]             = useState<DashboardKPI | null>(null);
  const [tenders,         setTenders]         = useState<DashboardTender[]>([]);
  const [auditLog,        setAuditLog]        = useState<AuditEntry[]>([]);
  const [auditError,      setAuditError]      = useState(false);
  const [digest,          setDigest]          = useState<string | null>(null);
  const [digestError,     setDigestError]     = useState(false);
  const [digestLoading,   setDigestLoading]   = useState(false);
  const [loading,         setLoading]         = useState(true);
  const [refreshingAudit, setRefreshingAudit] = useState(false);

  // ── Animated counters ──────────────────────────────────────────────────────

  const animActiveTenders  = useAnimatedCounter(kpi?.active_tenders  ?? 12);
  const animWinRate        = useAnimatedCounter(kpi?.win_rate_mtd    ?? 67);

  // ── Data Fetching ──────────────────────────────────────────────────────────

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/dashboard/stats') as DashboardKPI;
      setKpi(data);
    } catch (err) {
      try {
        const fallback = await authFetch('/api/v2/tenders/stats') as DashboardKPI;
        setKpi(fallback);
      } catch {
        console.error('Dashboard KPI fetch failed:', err);
      }
    }
  }, [authFetch]);

  const fetchTenders = useCallback(async () => {
    try {
      const data = await authFetch(
        '/api/v2/tenders?sort=match_score&limit=5&deadline_days=14',
      ) as DashboardTender[];
      setTenders(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Tenders fetch failed:', err);
    }
  }, [authFetch]);

  const fetchAuditLog = useCallback(async () => {
    try {
      setRefreshingAudit(true);
      const data = await authFetch('/api/v2/audit/recent?limit=15') as AuditEntry[];
      setAuditLog(Array.isArray(data) ? data : []);
      setAuditError(false);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 404) {
        setAuditError(true);
      } else {
        console.error('Audit fetch failed:', err);
        setAuditError(true);
      }
    } finally {
      setRefreshingAudit(false);
    }
  }, [authFetch]);

  const fetchDigest = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/dashboard/digest') as DigestData;
      if (data?.content) {
        setDigest(data.content);
        setDigestError(false);
      } else {
        setDigestError(true);
      }
    } catch {
      setDigestError(true);
    }
  }, [authFetch]);

  const generateDigest = useCallback(async () => {
    setDigestLoading(true);
    try {
      await authFetch('/api/v2/dashboard/digest/generate', { method: 'POST' });
      showToast('success', 'Digest jest generowany…');
      setTimeout(() => {
        fetchDigest();
        setDigestLoading(false);
      }, 2000);
    } catch {
      showToast('error', 'Nie udało się wygenerować digestu');
      setDigestLoading(false);
    }
  }, [authFetch, fetchDigest]);

  // ── Initial Load ───────────────────────────────────────────────────────────

  useEffect(() => {
    async function loadAll() {
      setLoading(true);
      await Promise.all([
        fetchDashboard(),
        fetchTenders(),
        fetchAuditLog(),
        fetchDigest(),
      ]);
      setLoading(false);
    }
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Auto-refresh audit co 60 s ─────────────────────────────────────────────

  useEffect(() => {
    const id = setInterval(fetchAuditLog, 60_000);
    return () => clearInterval(id);
  }, [fetchAuditLog]);

  // ── Computed ───────────────────────────────────────────────────────────────

  const handleRefreshAll = () => {
    fetchDashboard();
    fetchTenders();
    fetchAuditLog();
    fetchDigest();
    showToast('info', 'Odświeżam dane…');
  };

  const displayTenders = tenders;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <PageShell
      title="Dashboard"
      subtitle="Przegląd aktywności przetargowej"
      actions={
        <Button
          variant="secondary"
          size="sm"
          iconLeft={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
          onClick={handleRefreshAll}
        >
          Odśwież
        </Button>
      }
    >

      {/* ══════════════════════════════════════════════════════════════════════
          GREETING
          ══════════════════════════════════════════════════════════════════════ */}

      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="mb-8"
      >
        <h1
          className="font-bold text-white leading-tight tracking-tight"
          style={{ fontSize: 24 }}
        >
          {getGreeting()}, {displayName}.
        </h1>
        <p className="text-slate-400 mt-1 text-[14px]">
          Masz{' '}
          <span className="text-emerald-400 font-semibold">
            {animActiveTenders} aktywnych przetargów
          </span>{' '}
          i 3 kosztorysy do przeglądu. YU-NA jest gotowa.
        </p>
      </motion.div>

      {/* ══════════════════════════════════════════════════════════════════════
          ROW 1 — 4 × Metric Cards (Linear-tier glassmorphism)
          ══════════════════════════════════════════════════════════════════════ */}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <InlineMetricCard
          icon={Activity}
          label="Aktywne przetargi"
          value={String(animActiveTenders)}
          trend={3}
          trendLabel="nowe w tym tygodniu"
          delay={0}
        />
        <InlineMetricCard
          icon={Zap}
          label="Analiza AI dziś"
          value="8"
          trend={5}
          trendLabel="więcej niż wczoraj"
          delay={0.08}
        />
        <InlineMetricCard
          icon={Target}
          label="Średnie GO"
          value={`${animWinRate}%`}
          trend={4}
          trendLabel="+4pp wobec poprzedniego m-ca"
          delay={0.16}
        />
        <InlineMetricCard
          icon={FileText}
          label="Kosztorysy"
          value="3"
          trend={1}
          trendLabel="nowy w tym tygodniu"
          delay={0.24}
        />
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          ROW 2 — Chart 60% | Tender list 40%
          ══════════════════════════════════════════════════════════════════════ */}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-8">

        {/* ── LEFT: AI Activity Chart ── */}
        <motion.div
          className="lg:col-span-3"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
        >
          <div
            className="rounded-2xl p-6 h-full flex flex-col"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              backdropFilter: 'blur(12px)',
            }}
          >
            {/* Chart header */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-[14px] font-semibold text-slate-100">
                  Aktywność AI — ostatnie 7 dni
                </h2>
                <p className="text-[12px] text-slate-500 mt-0.5">
                  Liczba analiz przetargowych wykonanych przez YU-NA
                </p>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full"
                style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)' }}
              >
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[11px] text-emerald-400 font-medium">Na żywo</span>
              </div>
            </div>

            {/* Canvas */}
            <div className="flex-1 min-h-[160px]">
              <AIActivityChart />
            </div>

            {/* Legend */}
            <div className="flex items-center gap-4 mt-4 pt-4"
              style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
            >
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-0.5 rounded bg-emerald-400" />
                <span className="text-[11px] text-slate-500">Analizy AI</span>
              </div>
              <div className="flex items-center gap-1.5 ml-auto">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-[11px] text-emerald-400 font-medium">
                  Łącznie {CHART_DATA.reduce((a, b) => a + b, 0)} analiz w tygodniu
                </span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* ── RIGHT: Recent Tenders List ── */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.38, ease: [0.22, 1, 0.36, 1] }}
        >
          <div
            className="rounded-2xl p-5 h-full flex flex-col"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              backdropFilter: 'blur(12px)',
            }}
          >
            {/* Section header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <h2 className="text-[14px] font-semibold text-slate-100">
                  Ostatnie przetargi
                </h2>
              </div>
              <button type="button"
                onClick={() => setCurrentModule('zwiad')}
                className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-emerald-400 transition-colors"
              >
                Wszystkie
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            {/* List */}
            <div className="flex-1 flex flex-col gap-0.5 overflow-y-auto">
              <AnimatePresence mode="popLayout">
                {displayTenders.slice(0, 5).map((tender, i) => (
                  <TenderRow
                    key={tender.id}
                    tender={tender}
                    index={i}
                    onClick={() => {
                      setSelectedTender(tender as unknown as Tender);
                      setCurrentModule('decyzja');
                    }}
                  />
                ))}
              </AnimatePresence>
            </div>

            {/* Footer */}
            <div
              className="mt-4 pt-4 flex items-center justify-between"
              style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
            >
              <span className="text-[11px] text-slate-600">
                {displayTenders.length} przetargów aktywnych
              </span>
              <button type="button"
                onClick={() => setCurrentModule('zwiad')}
                className="text-[11px] text-emerald-400 hover:text-emerald-300 transition-colors font-medium"
              >
                Przeglądaj wszystkie →
              </button>
            </div>
          </div>
        </motion.div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          ROW 3 — AI Digest (secondary, collapsible)
          ══════════════════════════════════════════════════════════════════════ */}

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.5 }}
        className="mb-8"
      >
        <div
          className="rounded-2xl p-6"
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.07)',
            backdropFilter: 'blur(12px)',
          }}
        >
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, rgba(16,185,129,0.2) 0%, rgba(139,92,246,0.2) 100%)',
                  border: '1px solid rgba(16,185,129,0.2)',
                }}
              >
                <Zap className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <h2 className="text-[14px] font-semibold text-slate-100">AI Digest</h2>
                <p className="text-[11px] text-slate-500">
                  Inteligencja rynkowa YU-NA · aktualizacja dzienna
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              iconLeft={
                <RefreshCw
                  className={`w-3.5 h-3.5 ${digestLoading ? 'animate-spin' : ''}`}
                />
              }
              loading={digestLoading}
              onClick={generateDigest}
            >
              Generuj digest
            </Button>
          </div>

          {digestLoading ? (
            <div className="space-y-2.5">
              {[100, 80, 90, 70, 85].map((w, i) => (
                <div
                  key={i}
                  className="h-3 rounded-full animate-pulse"
                  style={{ width: `${w}%`, background: 'rgba(255,255,255,0.06)' }}
                />
              ))}
            </div>
          ) : digestError || !digest ? (
            <div
              className="rounded-xl px-5 py-6 flex flex-col items-center gap-2 text-center"
              style={{ background: 'rgba(255,255,255,0.02)', border: '1px dashed rgba(255,255,255,0.08)' }}
            >
              <Zap className="w-6 h-6 text-slate-600" />
              <p className="text-[13px] text-slate-400 font-medium">
                Digest zostanie wygenerowany dziś o 8:00
              </p>
              <p className="text-[12px] text-slate-600">
                Kliknij „Generuj digest" aby wygenerować teraz.
              </p>
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none text-slate-300 leading-relaxed">
              {digest.split('\n').map((line, i) => {
                if (line.startsWith('## '))
                  return <h2 key={i} className="text-base font-semibold text-slate-100 mt-4 mb-2">{line.slice(3)}</h2>;
                if (line.startsWith('# '))
                  return <h1 key={i} className="text-lg font-bold text-slate-100 mt-4 mb-2">{line.slice(2)}</h1>;
                const parts = line.split(/\*\*(.*?)\*\*/g);
                return (
                  <p key={i} className="text-[13px] text-slate-300 leading-relaxed mb-1.5">
                    {parts.map((part, j) =>
                      j % 2 === 1
                        ? <strong key={j} className="font-semibold text-slate-100">{part}</strong>
                        : <span key={j}>{part}</span>
                    )}
                  </p>
                );
              })}
            </div>
          )}
        </div>
      </motion.div>

      {/* ══════════════════════════════════════════════════════════════════════
          ROW 4 — Activity feed (conditional, secondary)
          ══════════════════════════════════════════════════════════════════════ */}

      {!auditError && auditLog.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="mb-8"
        >
          <div
            className="rounded-2xl p-6"
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[14px] font-semibold text-slate-100">
                Ostatnia aktywność
              </h2>
              <div className="flex items-center gap-2">
                {refreshingAudit && (
                  <RefreshCw className="w-3.5 h-3.5 text-slate-500 animate-spin" />
                )}
                <span className="text-[11px] text-slate-600 tabular-nums">auto 60 s</span>
              </div>
            </div>

            <div className="max-h-48 overflow-y-auto">
              <AnimatePresence mode="popLayout">
                {auditLog.slice(0, 8).map((entry, i) => (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3, delay: i * 0.04 }}
                    className="flex items-start gap-3 py-2.5"
                    style={{
                      borderBottom: i < Math.min(auditLog.length, 8) - 1
                        ? '1px solid rgba(255,255,255,0.04)'
                        : 'none'
                    }}
                  >
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5"
                      style={{ background: 'rgba(255,255,255,0.06)' }}
                    >
                      <Activity className="w-3 h-3 text-slate-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] text-slate-300 leading-snug">
                        <span className="font-medium text-slate-200">
                          {(entry.user_email ?? 'system').split('@')[0]}
                        </span>{' '}
                        <span className="text-slate-500">{entry.action}</span>
                      </p>
                      <p className="text-[11px] text-slate-600 mt-0.5">
                        {relativeTime(entry.created_at)}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        </motion.div>
      )}

      {/* Bottom spacer */}
      <div className="h-8" />
    </PageShell>
  );
}
