// ─── Shared utilities for YU-NA ────────────────────────────────────────────
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
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-yellow-400';
  return 'text-red-400';
}
