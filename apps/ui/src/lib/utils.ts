// ─── Shared utilities for BudOS ────────────────────────────────────────────
// Single source of truth — import from here, never redefine locally.

/** Format number as Polish PLN: 1 200 000 zł */
export function fmtPLN(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '—';
  return value.toLocaleString('pl-PL', {
    style: 'currency',
    currency: 'PLN',
    maximumFractionDigits: 0,
  });
}

/** Format date as DD.MM.YYYY */
export function fmtDate(value: string | null | undefined): string {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString('pl-PL');
  } catch {
    return value;
  }
}

/** Match score color class: ≥80 green, 60-79 yellow, <60 red */
export function matchColor(score: number | null | undefined): string {
  if (score == null) return 'text-zinc-400';
  if (score >= 80) return 'text-go';
  if (score >= 60) return 'text-warn';
  return 'text-nogo';
}

// ─── BudOS extended utilities ───────────────────────────────────────────────

/**
 * Format budget as human-readable Polish string: 2 190 000 zł
 * Uses non-breaking spaces (U+00A0) between digit groups.
 */
export function formatBudget(n: number): string {
  if (!isFinite(n)) return '—';
  const formatted = Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0');
  return `${formatted} zł`;
}

/**
 * Format ISO date string as Polish long date: 15 września 2026
 */
export function formatDate(s: string): string {
  if (!s) return '—';
  try {
    return new Date(s).toLocaleDateString('pl-PL', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return s;
  }
}

/**
 * Return hex color for a score 0–100:
 *   ≥ 75 → green  #10b981
 *   ≥ 50 → amber  #f59e0b
 *   < 50 → red    #ef4444
 */
export function scoreColor(n: number): string {
  if (n >= 75) return '#10b981';
  if (n >= 50) return '#f59e0b';
  return '#ef4444';
}

/**
 * Merge class names — lightweight cn() without clsx/tailwind-merge dep.
 * Filters falsy values and joins with a space.
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}
