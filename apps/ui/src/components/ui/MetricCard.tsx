'use client';

import { GlassCard } from './GlassCard';
import type { LucideIcon } from 'lucide-react';
import { TrendingUp, TrendingDown } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface MetricCardProps {
  icon:         LucideIcon;
  label:        string;
  value:        string | number;
  /** Number — positive = green, negative = red */
  trend?:       number;
  trendLabel?:  string;
  /** Tailwind class for icon colour */
  iconColor?:   string;
  /** Additional className for outer GlassCard */
  className?:   string;
  loading?:     boolean;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function MetricCard({
  icon:       Icon,
  label,
  value,
  trend,
  trendLabel  = 'w tym tygodniu',
  iconColor   = 'text-accent-primary',
  className   = '',
  loading     = false,
}: MetricCardProps) {
  const hasTrend      = trend !== undefined;
  const trendPositive = hasTrend && trend >= 0;

  if (loading) {
    return (
      <GlassCard className={`p-4 flex flex-col gap-3 ${className}`}>
        <div className="flex items-center justify-between">
          <div className="h-3 w-24 rounded bg-earth-800 animate-shimmer" />
          <div className="w-8 h-8 rounded-lg bg-earth-800 animate-shimmer" />
        </div>
        <div className="h-7 w-20 rounded bg-earth-800 animate-shimmer" />
        <div className="h-2.5 w-28 rounded bg-earth-800 animate-shimmer" />
      </GlassCard>
    );
  }

  return (
    <GlassCard
      className={`p-4 flex flex-col gap-3 hover:border-earth-600/50 transition-colors duration-200 ${className}`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-earth-600 font-medium tracking-normal">
          {label}
        </span>
        <div
          className={`w-8 h-8 rounded-lg bg-gradient-to-br from-earth-700/60 to-earth-800/80 flex items-center justify-center ${iconColor}`}
        >
          <Icon className="w-4 h-4" />
        </div>
      </div>

      {/* Value */}
      <div>
        <p className="text-2xl font-bold text-earth-100 tabular-nums leading-none">
          {value}
        </p>

        {/* Trend */}
        {hasTrend && (
          <div
            className={`flex items-center gap-1 mt-1.5 text-xs font-medium ${
              trendPositive ? 'text-accent-success' : 'text-accent-danger'
            }`}
          >
            {trendPositive
              ? <TrendingUp  className="w-3 h-3" />
              : <TrendingDown className="w-3 h-3" />}
            <span>
              {trendPositive ? '+' : ''}{trend} {trendLabel}
            </span>
          </div>
        )}
      </div>
    </GlassCard>
  );
}
