'use client';

import { useState } from 'react';
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';
import { EmptyState } from '@/components/ui/EmptyState';

// ── Types ──────────────────────────────────────────────────────────────────────

export interface ColumnDef<T> {
  key:           string;
  header:        string;
  render?:       (row: T) => React.ReactNode;
  sortable?:     boolean;
  className?:    string;
  headerClassName?: string;
  hideOnMobile?: boolean;
  /** Min width in px — prevents squishing on small viewports */
  minWidth?:     number;
}

interface DataTableProps<T extends { id: string }> {
  columns:      ColumnDef<T>[];
  data:         T[];
  loading?:     boolean;
  onRowClick?:  (row: T) => void;
  emptyIcon?:   React.ReactNode;
  emptyTitle?:  string;
  emptyDesc?:   string;
  emptyCta?:    React.ReactNode;
  /** Number of skeleton rows to show during loading (default: 5) */
  skeletonRows?: number;
}

// ── Skeleton ───────────────────────────────────────────────────────────────────

function TableSkeleton({ cols, rows }: { cols: number; rows: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, ri) => (
        <tr key={ri} className="border-b border-earth-800/30">
          {Array.from({ length: cols }).map((__, ci) => (
            <td key={ci} className="px-3 py-2.5">
              <div
                className="h-3.5 rounded animate-shimmer"
                style={{ width: `${60 + ((ci * 17 + ri * 7) % 35)}%` }}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

// ── Component ──────────────────────────────────────────────────────────────────

export function DataTable<T extends { id: string }>({
  columns,
  data,
  loading      = false,
  onRowClick,
  emptyIcon,
  emptyTitle   = 'Brak danych',
  emptyDesc,
  emptyCta,
  skeletonRows = 5,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  function handleSort(key: string) {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  const sorted = [...data].sort((a, b) => {
    if (!sortKey) return 0;
    const av = (a as Record<string, unknown>)[sortKey];
    const bv = (b as Record<string, unknown>)[sortKey];
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = String(av).localeCompare(String(bv), 'pl', { numeric: true });
    return sortDir === 'asc' ? cmp : -cmp;
  });

  return (
    <div className="overflow-x-auto rounded-token-lg border border-earth-700/40">
      <table className="w-full text-sm">
        {/* ── Sticky header ───────────────────────────────────────────── */}
        <thead className="sticky top-0 z-10 bg-earth-900/95 backdrop-blur-sm">
          <tr className="border-b border-earth-700/50">
            {columns.map(col => {
              const isSorted = sortKey === col.key;
              return (
                <th
                  key={col.key}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                  style={col.minWidth ? { minWidth: col.minWidth } : undefined}
                  className={[
                    'px-3 py-2.5 text-left text-[11px] font-semibold text-earth-500 uppercase tracking-wide select-none',
                    col.sortable !== false
                      ? 'cursor-pointer hover:text-earth-300 transition-colors'
                      : '',
                    col.hideOnMobile ? 'hidden md:table-cell' : '',
                    col.headerClassName ?? '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  <div className="flex items-center gap-1">
                    {col.header}
                    {col.sortable !== false && (
                      isSorted ? (
                        sortDir === 'asc'
                          ? <ChevronUp   className="w-3 h-3 text-accent-primary" />
                          : <ChevronDown className="w-3 h-3 text-accent-primary" />
                      ) : (
                        <ChevronsUpDown className="w-3 h-3 opacity-30" />
                      )
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>

        <tbody>
          {loading ? (
            <TableSkeleton cols={columns.length} rows={skeletonRows} />
          ) : sorted.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-10 text-center">
                <EmptyState
                  icon={emptyIcon}
                  title={emptyTitle}
                  description={emptyDesc}
                  cta={emptyCta}
                  compact
                />
              </td>
            </tr>
          ) : (
            sorted.map(row => (
              <tr
                key={row.id}
                onClick={() => onRowClick?.(row)}
                className={[
                  'border-b border-earth-800/30',
                  'transition-colors duration-100',
                  onRowClick ? 'cursor-pointer hover:bg-earth-800/40' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                {columns.map(col => (
                  <td
                    key={col.key}
                    className={[
                      'px-3 py-2.5',
                      col.hideOnMobile ? 'hidden md:table-cell' : '',
                      col.className ?? '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                  >
                    {col.render
                      ? col.render(row)
                      : String((row as Record<string, unknown>)[col.key] ?? '—')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
