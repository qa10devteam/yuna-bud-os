import type { ReactNode } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface GlassCardProps {
  children:   ReactNode;
  className?: string;
  /** Elevated — deeper shadow, slightly brighter surface */
  variant?:  'default' | 'elevated' | 'flat';
  /** Forward click handler — renders as <button> when provided */
  onClick?:  () => void;
}

// ── Style map ──────────────────────────────────────────────────────────────────

const VARIANT_CLS: Record<'default' | 'elevated' | 'flat', string> = {
  default:  'bg-earth-900/60 border border-earth-700/50 shadow-token-sm',
  elevated: 'bg-earth-800/70 border border-earth-600/50 shadow-token-md',
  flat:     'bg-earth-900/40 border border-earth-800/50',
};

const INTERACTIVE = 'cursor-pointer hover:border-earth-600/60 transition-all duration-200 text-left w-full';

// ── Component ──────────────────────────────────────────────────────────────────

export function GlassCard({
  children,
  className = '',
  variant   = 'default',
  onClick,
}: GlassCardProps) {
  const base = [
    'backdrop-blur-sm rounded-token-lg',
    VARIANT_CLS[variant],
    onClick ? INTERACTIVE : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={base}>
        {children}
      </button>
    );
  }

  return (
    <div className={base}>
      {children}
    </div>
  );
}
