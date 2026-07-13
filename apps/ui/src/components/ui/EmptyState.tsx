import type { ReactNode } from 'react';
import { FileSearch } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon?:        ReactNode;
  title?:       string;
  description?: string;
  cta?:         ReactNode;
  /** Smaller padding for use inside tables/panels */
  compact?:     boolean;
  className?:   string;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function EmptyState({
  icon,
  title       = 'Brak danych',
  description,
  cta,
  compact     = false,
  className   = '',
}: EmptyStateProps) {
  return (
    <div
      className={[
        'flex flex-col items-center justify-center text-center',
        compact ? 'py-6 gap-2' : 'py-16 gap-3',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {/* Icon */}
      <div
        className={[
          'flex items-center justify-center rounded-full bg-earth-800/60 border border-earth-700/40 text-earth-600',
          compact ? 'w-10 h-10' : 'w-14 h-14',
        ].join(' ')}
      >
        {icon ?? <FileSearch className={compact ? 'w-4 h-4' : 'w-6 h-6'} />}
      </div>

      {/* Text */}
      <div>
        <p className={['font-semibold text-earth-400', compact ? 'text-sm' : 'text-base'].join(' ')}>
          {title}
        </p>
        {description && (
          <p className={['text-earth-600 mt-1 max-w-sm mx-auto', compact ? 'text-xs' : 'text-sm'].join(' ')}>
            {description}
          </p>
        )}
      </div>

      {/* CTA */}
      {cta && <div className="mt-1">{cta}</div>}
    </div>
  );
}
