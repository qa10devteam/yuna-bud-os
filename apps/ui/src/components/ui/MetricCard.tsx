'use client';

import { TrendingUp, TrendingDown } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { GlassCard } from './GlassCard';

// ── Types ──────────────────────────────────────────────────────────────────────

interface MetricCardProps {
  /** Lucide icon component */
  icon?:        LucideIcon;
  /** Short label, displayed as uppercase 11px caption */
  label:        string;
  /** Primary numeric or text value (48px bold) */
  value:        string | number;
  /** Optional unit/suffix shown in smaller mono text (e.g. "PLN", "%") */
  suffix?:      string;
  /**
   * Numeric trend — positive = emerald (+), negative = red (-)
   * Example: 3.2 → "+3.2 w tym tygodniu"
   */
  trend?:       number;
  trendLabel?:  string;
  /** Tailwind colour class for the icon container (default: text-em) */
  iconColor?:   string;
  className?:   string;
  /** Renders shimmer skeleton while true */
  loading?:     boolean;
}

// ── Skeleton ───────────────────────────────────────────────────────────────────

function Skeleton({ className = '' }: { className?: string }) {
  return (
    <GlassCard className={`p-5 flex flex-col gap-4 ${className}`}>
      {/* header row */}
      <div className="flex items-center justify-between">
        <div className="h-2.5 w-24 rounded-full bg-ink-700 animate-shimmer" />
        <div className="w-9 h-9 rounded-xl bg-ink-700 animate-shimmer" />
      </div>
      {/* value */}
      <div className="h-12 w-28 rounded-lg bg-ink-700 animate-shimmer" />
      {/* trend */}
      <div className="h-3 w-32 rounded-full bg-ink-700 animate-shimmer" />
    </GlassCard>
  );
}

// ── Component ──────────────────────────────────────────────────────────────────
//
// PRECYZJA: value rendered in font-mono tabular-nums (Bloomberg-style).
// PRZEWAGA: positive trend = emerald, negative = red.
// glass-card surface via GlassCard.

export function MetricCard({
  icon:       Icon,
  label,
  value,
  suffix,
  trend,
  trendLabel  = 'w tym tygodniu',
  iconColor   = 'text-em',
  className   = '',
  loading     = false,
}: MetricCardProps) {
  if (loading) return <Skeleton className={className} />;

  const hasTrend      = trend !== undefined;
  const trendPositive = hasTrend && trend! >= 0;

  return (
    <GlassCard className={`p-5 flex flex-col gap-4 ${className}`}>

      {/* ── Header row: label + icon ──────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500">
          {label}
        </span>

        {Icon && (
          <div
            className={[
              'w-9 h-9 rounded-xl flex items-center justify-center',
              'bg-white/[0.06] border border-white/10',
              iconColor,
            ].join(' ')}
          >
            <Icon className="w-4 h-4" strokeWidth={1.75} />
          </div>
        )}
      </div>

      {/* ── Primary value — 48px bold mono ───────────────────────────────── */}
      <div>
        <p className="flex items-baseline gap-1.5 leading-none">
          <span
            className="text-[48px] font-bold leading-none text-slate-50 tabular-nums"
            style={{ fontFamily: 'var(--font-jetbrains), "JetBrains Mono", monospace' }}
            data-value
          >
            {value}
          </span>
          {suffix && (
            <span
              className="text-base text-slate-500 font-mono"
              style={{ fontFamily: 'var(--font-jetbrains), "JetBrains Mono", monospace' }}
            >
              {suffix}
            </span>
          )}
        </p>

        {/* ── Trend ──────────────────────────────────────────────────────── */}
        {hasTrend && (
          <div
            className={[
              'flex items-center gap-1 mt-2 text-xs font-mono font-medium',
              trendPositive ? 'text-[#10b981]' : 'text-red-400',
            ].join(' ')}
            style={{ fontFamily: 'var(--font-jetbrains), "JetBrains Mono", monospace' }}
          >
            {trendPositive
              ? <TrendingUp  className="w-3.5 h-3.5 shrink-0" />
              : <TrendingDown className="w-3.5 h-3.5 shrink-0" />}
            <span>
              {trendPositive ? '+' : ''}{trend} {trendLabel}
            </span>
          </div>
        )}
      </div>

    </GlassCard>
  );
}
