'use client';

import type { ReactNode } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────────

/**
 * go      — emerald (BudOS GO signal)
 * nogo    — red    (NO-GO signal)
 * warn    — amber  (caution)
 * score   — indigo (evaluation score)
 * neutral — white/10 (default, no-color)
 *
 * Legacy aliases kept for backward compat:
 *   em → go, indigo → score, violet → kept as violet, nogo alias
 */
type BadgeVariant =
  | 'go'
  | 'nogo'
  | 'warn'
  | 'score'
  | 'neutral'
  // backward-compat legacy
  | 'em'
  | 'indigo'
  | 'violet';

interface BadgeProps {
  variant?:   BadgeVariant;
  /** @deprecated use variant */
  color?:     BadgeVariant;
  children:   ReactNode;
  /** Show a coloured status dot before the label */
  dot?:       boolean;
  className?: string;
}

// ── Style map ──────────────────────────────────────────────────────────────────

const BADGE: Record<BadgeVariant, { badge: string; dot: string; pulse: boolean }> = {
  go: {
    badge: 'bg-[#10b981]/10 text-[#10b981] border border-[#10b981]/25',
    dot:   'bg-[#10b981]',
    pulse: true,
  },
  nogo: {
    badge: 'bg-red-500/10 text-red-400 border border-red-500/25',
    dot:   'bg-red-500',
    pulse: false,
  },
  warn: {
    badge: 'bg-amber-500/10 text-amber-400 border border-amber-500/25',
    dot:   'bg-amber-400',
    pulse: true,
  },
  score: {
    badge: 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/25',
    dot:   'bg-indigo-400',
    pulse: false,
  },
  neutral: {
    badge: 'bg-white/[0.07] text-slate-400 border border-white/10',
    dot:   'bg-slate-500',
    pulse: false,
  },
  // legacy aliases
  em: {
    badge: 'bg-[#10b981]/10 text-[#10b981] border border-[#10b981]/25',
    dot:   'bg-[#10b981]',
    pulse: true,
  },
  indigo: {
    badge: 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/25',
    dot:   'bg-indigo-400',
    pulse: false,
  },
  violet: {
    badge: 'bg-violet-500/10 text-violet-400 border border-violet-500/25',
    dot:   'bg-violet-400',
    pulse: false,
  },
};

// ── Component ──────────────────────────────────────────────────────────────────

export function Badge({
  variant,
  color,
  children,
  dot     = false,
  className = '',
}: BadgeProps) {
  // `color` is the legacy prop; `variant` takes precedence
  const key = (variant ?? color ?? 'neutral') as BadgeVariant;
  const { badge, dot: dotCls, pulse } = BADGE[key];

  return (
    <span
      className={[
        'inline-flex items-center gap-1.5',
        'rounded-full px-2.5 py-0.5',
        'text-[11px] font-semibold',
        badge,
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {dot && (
        <span
          className={[
            'w-1.5 h-1.5 rounded-full shrink-0',
            dotCls,
            pulse ? 'animate-pulse-soft' : '',
          ]
            .filter(Boolean)
            .join(' ')}
        />
      )}
      {children}
    </span>
  );
}
