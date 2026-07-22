/**
 * SkeletonLoader — shimmer loading states.
 * Brand Bible BudOS: ink-800 base, ink-700 shimmer highlight.
 */

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

const CARD_WIDTHS = ['w-3/4', 'w-full', 'w-5/6', 'w-2/3', 'w-4/5', 'w-1/2'];

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  const widths = CARD_WIDTHS;
  return (
    <div className="p-4 rounded-xl bg-ink-900 border border-ink-line space-y-2.5">
      <div className="h-4 w-2/5 rounded animate-shimmer" />
      <div className="h-px bg-ink-line my-1" />
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`h-3 rounded animate-shimmer ${widths[i % widths.length]}`}
        />
      ))}
    </div>
  );
}

export function SkeletonBlock({ className = 'h-24' }: { className?: string }) {
  return (
    <div className={`rounded-xl animate-shimmer ${className}`} />
  );
}

export function SkeletonKPI() {
  return (
    <div className="p-4 rounded-xl bg-ink-900 border border-ink-line flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="h-3 w-24 rounded animate-shimmer" />
        <div className="w-8 h-8 rounded-lg animate-shimmer" />
      </div>
      <div className="h-7 w-20 rounded animate-shimmer" />
      <div className="h-2.5 w-28 rounded animate-shimmer" />
    </div>
  );
}

const TEXT_WIDTHS = ['w-full', 'w-5/6', 'w-4/5', 'w-3/4', 'w-2/3', 'w-1/2'];

export function SkeletonTextBlock({ lines = 4 }: { lines?: number }) {
  const widths = TEXT_WIDTHS;
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`h-3 rounded animate-shimmer ${widths[i % widths.length]}`}
        />
      ))}
    </div>
  );
}
