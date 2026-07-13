/**
 * SkeletonLoader — warianty shimmer dla loading states.
 *
 * Warianty:
 *   SkeletonRow      — wiersz tabeli (N kolumn)
 *   SkeletonCard     — karta z nagłówkiem + wierszami tekstu
 *   SkeletonBlock    — prosty prostokąt (dowolna wysokość)
 *   SkeletonKPI      — karta KPI (ikona + wartość + label)
 *   SkeletonTextBlock — blok akapitu (kilka wierszy o różnej długości)
 *
 * Wszystkie korzystają z `.animate-shimmer` z globals.css.
 * Obsługuje prefers-reduced-motion — animate-shimmer deaktywuje się automatycznie.
 */

// ── Row ────────────────────────────────────────────────────────────────────────

export function SkeletonRow({ cols = 5 }: { cols?: number }) {
  return (
    <div className="flex gap-3 px-3 py-2.5">
      {Array.from({ length: cols }).map((_, i) => (
        <div
          key={i}
          className="h-3.5 rounded animate-shimmer flex-1"
          style={{ maxWidth: `${70 + (i * 13) % 30}%` }}
        />
      ))}
    </div>
  );
}

// ── Card ───────────────────────────────────────────────────────────────────────

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  const widths = ['w-3/4', 'w-full', 'w-5/6', 'w-2/3', 'w-4/5', 'w-1/2'];
  return (
    <div className="p-4 rounded-token-lg bg-earth-900/60 border border-earth-800/50 space-y-2.5">
      {/* Header bar */}
      <div className="h-4 w-2/5 rounded animate-shimmer" />
      <div className="h-px bg-earth-800/50 my-1" />
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`h-3 rounded animate-shimmer ${widths[i % widths.length]}`}
        />
      ))}
    </div>
  );
}

// ── Block ──────────────────────────────────────────────────────────────────────

export function SkeletonBlock({
  className = 'h-24',
}: {
  className?: string;
}) {
  return (
    <div className={`rounded-token-lg animate-shimmer ${className}`} />
  );
}

// ── KPI card ───────────────────────────────────────────────────────────────────

export function SkeletonKPI() {
  return (
    <div className="p-4 rounded-token-lg bg-earth-900/60 border border-earth-800/50 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="h-3 w-24 rounded animate-shimmer" />
        <div className="w-8 h-8 rounded-lg animate-shimmer" />
      </div>
      <div className="h-7 w-20 rounded animate-shimmer" />
      <div className="h-2.5 w-28 rounded animate-shimmer" />
    </div>
  );
}

// ── Text block ─────────────────────────────────────────────────────────────────

export function SkeletonTextBlock({ lines = 4 }: { lines?: number }) {
  const widths = ['w-full', 'w-5/6', 'w-4/5', 'w-full', 'w-2/3', 'w-3/4'];
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`h-3 rounded animate-shimmer ${widths[i % widths.length]}`} />
      ))}
    </div>
  );
}
