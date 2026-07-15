'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import type { Tender } from '@/types';
import { useStore } from '@/store/useStore';
import { GlassCard } from '@/components/ui/GlassCard';
import { MetricCard } from '@/components/ui/MetricCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonKPI, SkeletonCard, SkeletonTextBlock } from '@/components/ui/SkeletonLoader';
import { PageShell } from '@/components/PageShell';
import { showToast } from '@/components/Toast';
import { motion, AnimatePresence } from 'motion/react';
import {
  Activity,
  TrendingUp,
  Target,
  Zap,
  Bell,
  ArrowRight,
  RefreshCw,
  BarChart3,
  Search,
  Package,
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

function deadlineBadgeVariant(days: number): 'danger' | 'warning' | 'success' {
  if (days < 7) return 'danger';
  if (days < 14) return 'warning';
  return 'success';
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

function renderSimpleMarkdown(content: string): React.ReactNode[] {
  return content.split('\n').map((line, i) => {
    if (line.startsWith('## ')) {
      return (
        <h2 key={i} className="text-lg font-semibold text-earth-100 mt-4 mb-2">
          {line.slice(3)}
        </h2>
      );
    }
    if (line.startsWith('# ')) {
      return (
        <h1 key={i} className="text-xl font-bold text-earth-100 mt-4 mb-2">
          {line.slice(2)}
        </h1>
      );
    }
    const parts = line.split(/\*\*(.*?)\*\*/g);
    const rendered = parts.map((part, j) =>
      j % 2 === 1 ? (
        <strong key={j} className="font-semibold text-earth-100">
          {part}
        </strong>
      ) : (
        <span key={j}>{part}</span>
      ),
    );
    return (
      <p key={i} className="text-earth-300 text-sm leading-relaxed">
        {rendered}
      </p>
    );
  });
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
      // ease-out cubic
      const eased    = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  }, [target, duration]);

  return current;
}

// ─────────────────────────────────────────────────────────────────────────────
// TenderCard — najgorętsze przetargi
// ─────────────────────────────────────────────────────────────────────────────

interface TenderCardProps {
  tender: DashboardTender;
  index: number;
  onClick: () => void;
}

function TenderCard({ tender, index, onClick }: TenderCardProps) {
  const days    = daysUntil(tender.deadline);
  const variant = deadlineBadgeVariant(days);

  // Match-score gradient — kolor końcowy zależy od poziomu dopasowania
  const scoreEndColor =
    tender.match_score > 80
      ? 'var(--color-accent-success)'
      : tender.match_score > 60
        ? 'var(--color-accent-warning)'
        : 'var(--color-accent-danger)';

  return (
    <motion.div
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
      onClick={onClick}
      className={[
        'group p-4 rounded-token-lg',
        'bg-earth-900/40 border border-earth-800/50',
        'hover:border-accent-primary/40 hover:bg-earth-900/60',
        'cursor-pointer transition-all duration-300',
      ].join(' ')}
    >
      {/* Wiersz: tytuł + badge terminu */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-earth-100 group-hover:text-accent-primary transition-colors truncate">
            {truncate(tender.title, 60)}
          </h4>
          <p className="text-xs text-earth-400 mt-1">{tender.buyer}</p>
        </div>
        <StatusBadge
          status={variant}
          label={`${days}d`}
          size="xs"
          className="shrink-0"
        />
      </div>

      {/* Pasek dopasowania */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="text-earth-400">Dopasowanie</span>
          <span className="text-earth-200 font-medium">{tender.match_score}%</span>
        </div>
        <div className="h-1.5 bg-earth-800 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${tender.match_score}%` }}
            transition={{ duration: 0.8, delay: index * 0.1 + 0.3 }}
            className="h-full rounded-full"
            style={{
              background: `linear-gradient(90deg, var(--color-accent-info), ${scoreEndColor})`,
            }}
          />
        </div>
      </div>

      {/* Wartość + strzałka */}
      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-earth-300">{formatPLN(tender.value)}</span>
        <ArrowRight className="w-3.5 h-3.5 text-earth-500 group-hover:text-accent-primary transition-colors" />
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ActivityIcon — ikona w osi czasu aktywności
// ─────────────────────────────────────────────────────────────────────────────

function ActivityIcon({ type }: { type: string }) {
  const cls = 'w-3.5 h-3.5';
  switch (type) {
    case 'create':
      return (
        <svg className={`${cls} text-accent-primary`} viewBox="0 0 16 16" fill="none">
          <path
            d="M8 3v10M3 8h10"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      );
    case 'update':
      return (
        <svg className={`${cls} text-accent-warning`} viewBox="0 0 16 16" fill="none">
          <path
            d="M11.5 1.5l3 3-9 9H2.5v-3l9-9z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'delete':
      return (
        <svg className={`${cls} text-accent-danger`} viewBox="0 0 16 16" fill="none">
          <path
            d="M2 4h12M5.33 4V2.67a1.33 1.33 0 011.34-1.34h2.66a1.33 1.33 0 011.34 1.34V4m2 0v9.33a1.33 1.33 0 01-1.34 1.34H4.67a1.33 1.33 0 01-1.34-1.34V4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'login':
      return (
        <svg className={`${cls} text-accent-info`} viewBox="0 0 16 16" fill="none">
          <path
            d="M10 2h2.67A1.33 1.33 0 0114 3.33v9.34A1.33 1.33 0 0112.67 14H10M6.67 11.33L10 8 6.67 4.67M10 8H2"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    default:
      return <Activity className={`${cls} text-earth-400`} />;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// ActivityItem — pojedynczy wpis w osi czasu
// ─────────────────────────────────────────────────────────────────────────────

interface ActivityItemProps {
  entry: AuditEntry;
  index: number;
  isLast: boolean;
}

function ActivityItem({ entry, index, isLast }: ActivityItemProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="flex gap-3 relative"
    >
      {/* Oś czasu */}
      <div className="flex flex-col items-center">
        <div className="w-7 h-7 rounded-full bg-earth-800/80 border border-earth-700 flex items-center justify-center shrink-0">
          <ActivityIcon type={entry.action_type} />
        </div>
        {!isLast && <div className="w-px flex-1 bg-earth-800 mt-1" />}
      </div>

      {/* Treść wpisu */}
      <div className="pb-4 flex-1 min-w-0">
        <p className="text-xs text-earth-200 leading-relaxed">
          <span className="font-medium text-earth-100">
            {(entry.user_email ?? 'system').split('@')[0]}
          </span>{' '}
          <span className="text-earth-400">{entry.action}</span>
        </p>
        <p className="text-[11px] text-earth-500 mt-0.5">
          {relativeTime(entry.created_at)}
        </p>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// QuickActionCard — kafelki szybkich akcji
// ─────────────────────────────────────────────────────────────────────────────

interface QuickActionProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  delay: number;
}

function QuickActionCard({ icon, label, onClick, delay }: QuickActionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, delay }}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      className="group relative cursor-pointer"
    >
      {/* Gradient border on hover */}
      <div className="absolute -inset-[1px] rounded-token-lg bg-gradient-to-br from-accent-primary/0 via-accent-primary/0 to-accent-primary/0 group-hover:from-accent-primary/50 group-hover:via-accent-primary/20 group-hover:to-accent-primary/50 transition-all duration-500" />
      <div className="relative p-6 rounded-token-lg bg-earth-900/60 border border-earth-800 group-hover:border-transparent transition-all duration-300">
        <div className="flex flex-col items-center gap-3">
          <div className="p-3 rounded-token-lg bg-earth-800/60 group-hover:bg-accent-primary/10 transition-colors duration-300">
            {icon}
          </div>
          <span className="text-sm font-medium text-earth-200 group-hover:text-earth-100 transition-colors">
            {label}
          </span>
        </div>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DigestSkeleton — loading state digestu AI
// ─────────────────────────────────────────────────────────────────────────────

function DigestSkeleton() {
  return <SkeletonTextBlock lines={5} />;
}

// ─────────────────────────────────────────────────────────────────────────────
// TenderListSkeleton — loading state listy przetargów
// ─────────────────────────────────────────────────────────────────────────────

function TenderListSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <SkeletonCard key={i} lines={2} />
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main — DashboardPage
// ─────────────────────────────────────────────────────────────────────────────

export function DashboardPage() {
  const authFetch = useAuthFetch();
  const { setCurrentModule, setSelectedTender } = useStore();

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

  // Pipeline: animujemy wartość w dziesiątkach tysięcy → wyświetlamy M PLN
  const animActiveTenders = useAnimatedCounter(kpi?.active_tenders ?? 0);
  const animPipelineTenths = useAnimatedCounter(
    kpi?.pipeline_value ? Math.round((kpi.pipeline_value / 1_000_000) * 10) : 0,
  );
  const animWinRate  = useAnimatedCounter(kpi?.win_rate_mtd ?? 0);
  const animAvgDeal  = useAnimatedCounter(kpi?.avg_deal_size ?? 0);
  const animNewToday = useAnimatedCounter(kpi?.new_today ?? 0);

  // ── Formatted KPI values ───────────────────────────────────────────────────

  const pipelineLabel = `${(animPipelineTenths / 10).toLocaleString('pl-PL', {
    minimumFractionDigits: 1,
  })} M PLN`;

  const winRateTrend = kpi?.win_rate_mtd
    ? kpi.win_rate_mtd > 50 ? 5 : -3
    : 0;

  // ── Data Fetching ──────────────────────────────────────────────────────────

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/dashboard/stats') as DashboardKPI;
      setKpi(data);
    } catch (err) {
      // Fallback to tenders/stats endpoint when dashboard/stats returns 404
      try {
        const fallback = await authFetch('/api/v2/tenders/stats') as DashboardKPI;
        setKpi(fallback);
      } catch {
        console.error('Dashboard KPI fetch failed:', err);
        showToast('error', 'Nie udało się pobrać KPI');
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

  // ── Render helpers ─────────────────────────────────────────────────────────

  const handleRefreshAll = () => {
    fetchDashboard();
    fetchTenders();
    fetchAuditLog();
    fetchDigest();
    showToast('info', 'Odświeżam dane…');
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <PageShell
      title="Dashboard"
      subtitle="Przegląd aktywności przetargowej"
      actions={
        <Button
          variant="secondary"
          size="sm"
          iconLeft={<RefreshCw className="w-3.5 h-3.5" />}
          onClick={handleRefreshAll}
        >
          Odśwież
        </Button>
      }
    >
      {/* ════════════════════════════════════════════════════════════════════
          ROW 1 — Karty KPI
          ════════════════════════════════════════════════════════════════════ */}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4 mb-8">
        {loading ? (
          <>
            {[...Array(6)].map((_, i) => (
              <SkeletonKPI key={i} />
            ))}
          </>
        ) : (
          <>
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0 }}
            >
              <MetricCard
                icon={Activity}
                label="Aktywne przetargi"
                value={animActiveTenders.toLocaleString('pl-PL')}
                trend={12}
                trendLabel="vs. poprzedni tydzień"
                iconColor="text-accent-info"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <MetricCard
                icon={TrendingUp}
                label="Pipeline"
                value={pipelineLabel}
                trend={8}
                trendLabel="wzrost wartości"
                iconColor="text-accent-primary"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.15 }}
            >
              <MetricCard
                icon={Package}
                label="Wartość portfela"
                value={formatPLN(kpi?.total_value ?? kpi?.pipeline_value ?? 0)}
                trendLabel="wszystkie przetargi"
                iconColor="text-accent-success"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <MetricCard
                icon={Target}
                label="Win Rate MTD"
                value={`${animWinRate}%`}
                trend={winRateTrend}
                trendLabel="wobec celu"
                iconColor="text-accent-violet"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <MetricCard
                icon={Zap}
                label="Śr. wartość oferty"
                value={formatPLN(animAvgDeal)}
                trend={3}
                trendLabel="vs. poprzedni miesiąc"
                iconColor="text-accent-warning"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              <MetricCard
                icon={Bell}
                label="Nowe dziś"
                value={animNewToday.toLocaleString('pl-PL')}
                iconColor="text-accent-danger"
              />
            </motion.div>
          </>
        )}
      </div>

      {/* ════════════════════════════════════════════════════════════════════
          ROW 2 — Najgorętsze przetargi (3/5) + Feed aktywności (2/5)
          ════════════════════════════════════════════════════════════════════ */}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-8">
        {/* Najgorętsze przetargi */}
        <div className="lg:col-span-3">
          <GlassCard className="p-6 h-full">
            {/* Nagłówek sekcji */}
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse-soft" />
                <h2 className="text-base font-semibold text-earth-100">
                  Najgorętsze dziś
                </h2>
              </div>
              <button
                onClick={() => setCurrentModule('zwiad')}
                className="flex items-center gap-1 text-xs text-earth-400 hover:text-accent-primary transition-colors"
              >
                Wszystkie <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            {/* Zawartość */}
            {loading ? (
              <TenderListSkeleton />
            ) : tenders.length === 0 ? (
              <EmptyState
                icon={<Target className="w-6 h-6" />}
                title="Brak gorących przetargów"
                description="Nowe przetargi pojawią się po następnym skanie rynku."
                compact
              />
            ) : (
              <div className="space-y-3">
                {tenders.map((tender, i) => (
                  <TenderCard
                    key={tender.id}
                    tender={tender}
                    index={i}
                    onClick={() => {
                      setSelectedTender(tender as unknown as Tender);
                      setCurrentModule('decyzja');
                    }}
                  />
                ))}
              </div>
            )}
          </GlassCard>
        </div>

        {/* Feed aktywności */}
        <div className="lg:col-span-2">
          <GlassCard className="p-6 h-full flex flex-col">
            {/* Nagłówek sekcji */}
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-semibold text-earth-100">Aktywność</h2>
              <div className="flex items-center gap-2">
                {refreshingAudit && (
                  <RefreshCw className="w-3.5 h-3.5 text-earth-500 animate-spin" />
                )}
                <span className="text-[11px] text-earth-500 tabular-nums">
                  auto 60 s
                </span>
              </div>
            </div>

            {/* Zawartość */}
            {auditError ? (
              <EmptyState
                icon={<Activity className="w-6 h-6" />}
                title="Feed aktywności niedostępny"
                description="Dane pojawią się wkrótce."
                compact
              />
            ) : auditLog.length === 0 ? (
              <EmptyState
                icon={<Activity className="w-6 h-6" />}
                title="Brak ostatniej aktywności"
                compact
              />
            ) : (
              <div className="flex-1 max-h-[420px] overflow-y-auto pr-2 scrollbar-thin scrollbar-track-earth-900 scrollbar-thumb-earth-700">
                <AnimatePresence mode="popLayout">
                  {auditLog.map((entry, i) => (
                    <ActivityItem
                      key={entry.id}
                      entry={entry}
                      index={i}
                      isLast={i === auditLog.length - 1}
                    />
                  ))}
                </AnimatePresence>
              </div>
            )}
          </GlassCard>
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════════
          ROW 3 — Szybkie akcje
          ════════════════════════════════════════════════════════════════════ */}

      <div className="mb-8">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="section-label mb-4"
        >
          Szybkie akcje
        </motion.p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <QuickActionCard
            icon={
              <Bell className="w-6 h-6 text-accent-info group-hover:text-blue-300 transition-colors" />
            }
            label="Nowy Alert"
            onClick={() => setCurrentModule('notifications')}
            delay={0.7}
          />
          <QuickActionCard
            icon={
              <BarChart3 className="w-6 h-6 text-accent-primary group-hover:text-emerald-300 transition-colors" />
            }
            label="Pipeline"
            onClick={() => setCurrentModule('pipeline')}
            delay={0.8}
          />
          <QuickActionCard
            icon={
              <Search className="w-6 h-6 text-accent-violet group-hover:text-violet-300 transition-colors" />
            }
            label="Zwiad AI"
            onClick={() => setCurrentModule('zwiad')}
            delay={0.9}
          />
          <QuickActionCard
            icon={
              <Package className="w-6 h-6 text-accent-warning group-hover:text-amber-300 transition-colors" />
            }
            label="InterCenBud"
            onClick={() => setCurrentModule('icb')}
            delay={1.0}
          />
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════════
          ROW 4 — AI Digest
          ════════════════════════════════════════════════════════════════════ */}

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 1.0 }}
      >
        <GlassCard className="p-6">
          {/* Nagłówek digestu */}
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-token-lg bg-gradient-to-br from-accent-primary/20 to-accent-violet/20">
                <Zap className="w-5 h-5 text-accent-primary" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-earth-100">AI Digest</h2>
                <p className="text-xs text-earth-500">
                  Podsumowanie inteligencji rynkowej
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
              Odśwież
            </Button>
          </div>

          {/* Zawartość digestu */}
          {digestLoading ? (
            <DigestSkeleton />
          ) : digestError || !digest ? (
            <EmptyState
              icon={<Zap className="w-6 h-6" />}
              title="Digest zostanie wygenerowany dziś o 8:00"
              description='Kliknij „Odśwież" aby wygenerować teraz.'
              compact
            />
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              {renderSimpleMarkdown(digest)}
            </div>
          )}
        </GlassCard>
      </motion.div>

      {/* Spacer dolny */}
      <div className="h-8" />
    </PageShell>
  );
}
