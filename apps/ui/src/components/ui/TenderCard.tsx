'use client';

import { motion } from 'motion/react';
import { Calendar, MapPin, DollarSign, ChevronRight } from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';

// ── Types ──────────────────────────────────────────────────────────────────────

interface TenderCardProps {
  tender: {
    id: string;
    title: string;
    buyer?: string | null;
    voivodeship?: string | null;
    value_pln?: number | null;
    deadline_at?: string | null;
    match_score?: number | null;
    status?: string;
  };
  index?: number;
  onClick?: () => void;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmtPLN(v: number | null | undefined): string {
  if (v == null) return '—';
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1).replace('.0', '') + ' M zł';
  if (v >= 1_000) return Math.round(v / 1_000).toLocaleString('pl-PL') + ' tys. zł';
  return Math.round(v).toLocaleString('pl-PL') + ' zł';
}

function daysUntil(s: string | null | undefined): number | null {
  if (!s) return null;
  return Math.ceil((new Date(s).getTime() - Date.now()) / 86_400_000);
}

function deadlineLabel(days: number | null): { text: string; color: string } {
  if (days === null) return { text: '—', color: 'text-slate-600' };
  if (days < 0) return { text: `${Math.abs(days)}d po terminie`, color: 'text-nogo' };
  if (days === 0) return { text: 'Dziś!', color: 'text-nogo' };
  if (days <= 3) return { text: `${days}d`, color: 'text-nogo' };
  if (days <= 7) return { text: `${days}d`, color: 'text-warn' };
  return { text: `${days}d`, color: 'text-slate-500' };
}

function scoreBadgeVariant(score: number | null): 'go' | 'nogo' | 'warn' | 'neutral' {
  if (score === null) return 'neutral';
  const pct = score > 1 ? score : score * 100;
  if (pct >= 80) return 'go';
  if (pct >= 50) return 'warn';
  return 'nogo';
}

// ── ScoreArc — mini SVG ────────────────────────────────────────────────────────

function ScoreArc({ score }: { score: number | null }) {
  if (score === null) return null;
  const pct = Math.round(score > 1 ? score : score * 100);
  const r = 14, cx = 18, cy = 18;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const variant = scoreBadgeVariant(score);
  const color = variant === 'go' ? '#10b981' : variant === 'warn' ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative shrink-0">
      <svg width="36" height="36" viewBox="0 0 36 36">
        <circle cx={cx} cy={cy} r={r} stroke="rgba(255,255,255,0.05)" strokeWidth="3" fill="none" />
        <circle
          cx={cx} cy={cy} r={r}
          stroke={color} strokeWidth="3" fill="none"
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cy})`}
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-[10px] font-bold font-mono"
        style={{ color }}
      >
        {pct}
      </span>
    </div>
  );
}

// ── Component ──────────────────────────────────────────────────────────────────

export function TenderCard({ tender, index = 0, onClick }: TenderCardProps) {
  const days = daysUntil(tender.deadline_at);
  const dl = deadlineLabel(days);
  const isUrgent = days !== null && days >= 0 && days <= 3;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      onClick={onClick}
      onKeyDown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && onClick) { e.preventDefault(); onClick(); } }}
      tabIndex={0}
      role="button"
      className={[
        'group relative flex items-start gap-3 p-4 rounded-xl cursor-pointer',
        'bg-ink-900/40 border transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150',
        isUrgent
          ? 'border-nogo/20 hover:border-nogo/40'
          : 'border-ink-800/50 hover:border-ink-700/70',
        'hover:bg-ink-900/70',
      ].join(' ')}
    >
      {/* Score Arc */}
      <ScoreArc score={tender.match_score ?? null} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Title */}
        <p className="text-sm text-slate-200 font-medium leading-snug line-clamp-2 group-hover:text-slate-100 transition-colors">
          {tender.title}
        </p>

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5">
          {tender.buyer && (
            <span className="text-[11px] text-slate-500 truncate max-w-[180px]">
              {tender.buyer}
            </span>
          )}
          {tender.voivodeship && (
            <span className="flex items-center gap-0.5 text-[11px] text-slate-600">
              <MapPin className="w-2.5 h-2.5" />
              {tender.voivodeship}
            </span>
          )}
        </div>

        {/* Bottom row — value + deadline */}
        <div className="flex items-center gap-3 mt-2">
          <span className="text-xs font-mono text-slate-400 tabular-nums flex items-center gap-1">
            <DollarSign className="w-3 h-3 text-slate-600" />
            {fmtPLN(tender.value_pln)}
          </span>
          <span className={`text-[11px] font-mono tabular-nums flex items-center gap-1 ${dl.color}`}>
            <Calendar className="w-3 h-3" />
            {dl.text}
          </span>
          {tender.status && (
            <StatusBadge
              status={tender.status}
              size="xs"
            />
          )}
        </div>
      </div>

      {/* Chevron */}
      <ChevronRight className="w-4 h-4 text-slate-700 group-hover:text-em shrink-0 mt-1 transition-colors" />
    </motion.div>
  );
}
