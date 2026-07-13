'use client';

// ── Types ──────────────────────────────────────────────────────────────────────

export type BadgeVariant =
  | 'new'
  | 'matched'
  | 'watching'
  | 'analyzing'
  | 'estimated'
  | 'decided_go'
  | 'decided_nogo'
  | 'archived'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral';

interface StatusBadgeProps {
  status:     BadgeVariant | string;
  /** Override display label */
  label?:     string;
  size?:      'xs' | 'sm';
  className?: string;
}

// ── Config ─────────────────────────────────────────────────────────────────────

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  new:           { label: 'Nowy',           cls: 'bg-accent-info/15 text-blue-300 border-accent-info/20' },
  matched:       { label: 'Dopasowany',     cls: 'bg-accent-violet/15 text-violet-300 border-accent-violet/20' },
  watching:      { label: 'Obserwowany',    cls: 'bg-sky-500/15 text-sky-300 border-sky-500/20' },
  analyzing:     { label: 'W analizie',     cls: 'bg-accent-warning/15 text-yellow-300 border-accent-warning/20' },
  estimated:     { label: 'Wyceniony',      cls: 'bg-accent-primary/15 text-emerald-300 border-accent-primary/20' },
  decided_go:    { label: 'GO',             cls: 'bg-accent-success/20 text-green-300 border-accent-success/25' },
  decided_nogo:  { label: 'NO-GO',          cls: 'bg-accent-danger/15 text-red-300 border-accent-danger/20' },
  archived:      { label: 'Archiwum',       cls: 'bg-earth-700/40 text-earth-500 border-earth-700/30' },
  // Semantic
  success:       { label: 'Sukces',         cls: 'bg-accent-success/15 text-green-300 border-accent-success/20' },
  warning:       { label: 'Ostrzeżenie',    cls: 'bg-accent-warning/15 text-yellow-300 border-accent-warning/20' },
  danger:        { label: 'Błąd',           cls: 'bg-accent-danger/15 text-red-300 border-accent-danger/20' },
  info:          { label: 'Info',           cls: 'bg-accent-info/15 text-blue-300 border-accent-info/20' },
  neutral:       { label: 'Neutralny',      cls: 'bg-earth-700/40 text-earth-400 border-earth-700/30' },
};

// ── Component ──────────────────────────────────────────────────────────────────

export function StatusBadge({
  status,
  label,
  size      = 'sm',
  className = '',
}: StatusBadgeProps) {
  const cfg = STATUS_MAP[status] ?? {
    label: status,
    cls: 'bg-earth-700/40 text-earth-400 border-earth-700/30',
  };

  const displayLabel = label ?? cfg.label;
  const sizeClass    = size === 'xs'
    ? 'px-1.5 py-0.5 text-[10px]'
    : 'px-2 py-0.5 text-xs';

  return (
    <span
      className={[
        'inline-flex items-center rounded-full border font-semibold whitespace-nowrap',
        sizeClass,
        cfg.cls,
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {displayLabel}
    </span>
  );
}
