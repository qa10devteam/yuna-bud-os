'use client';

import { useState } from 'react';
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';
import { EmptyState } from '@/components/ui/EmptyState';

// ── Types ──────────────────────────────────────────────────────────────────────

export interface ColumnDef<T> {
  key:              string;
  header:           string;
  render?:          (row: T) => React.ReactNode;
  sortable?:        boolean;
  className?:       string;
  headerClassName?: string;
  hideOnMobile?:    boolean;
  minWidth?:        number;
}

interface DataTableProps<T extends { id: string }> {
  columns:       ColumnDef<T>[];
  data:          T[];
  loading?:      boolean;
  onRowClick?:   (row: T) => void;
  emptyIcon?:    React.ReactNode;
  emptyTitle?:   string;
  emptyDesc?:    string;
  emptyCta?:     React.ReactNode;
  skeletonRows?: number;
}

// ── Skeleton ───────────────────────────────────────────────────────────────────

function TableSkeleton({ cols, rows }: { cols: number; rows: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, ri) => (
        <tr key={ri} className="border-b border-ink-line/40">
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

  const hasData = data.length > 0 || loading;

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        {/* ── Head ──────────────────────────────────────────────────── */}
        <thead>
          <tr className="border-b border-ink-line">
            {columns.map((col) => (
              <th
                key={col.key}
                style={col.minWidth ? { minWidth: col.minWidth } : undefined}
                className={[
                  'px-3 py-2.5 text-left',
                  'text-[11px] font-semibold text-slate-600 uppercase tracking-widest',
                  'select-none',
                  col.hideOnMobile ? 'hidden md:table-cell' : '',
                  col.sortable ? 'cursor-pointer hover:text-slate-400 transition-colors' : '',
                  col.headerClassName ?? '',
                ].filter(Boolean).join(' ')}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
                onKeyDown={col.sortable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort(col.key); } } : undefined}
                tabIndex={col.sortable ? 0 : undefined}
                role={col.sortable ? 'button' : undefined}
              >
                <span className="flex items-center gap-1">
                  {col.header}
                  {col.sortable && (
                    <span className="text-slate-700">
                      {sortKey === col.key ? (
                        sortDir === 'asc'
                          ? <ChevronUp className="w-3 h-3 text-em" />
                          : <ChevronDown className="w-3 h-3 text-em" />
                      ) : (
                        <ChevronsUpDown className="w-3 h-3" />
                      )}
                    </span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>

        {/* ── Body ──────────────────────────────────────────────────── */}
        <tbody>
          {loading ? (
            <TableSkeleton cols={columns.length} rows={skeletonRows} />
          ) : sorted.length === 0 ? (
            <tr>
              <td colSpan={columns.length}>
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
            sorted.map((row) => (
              <tr
                key={row.id}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={onRowClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onRowClick(row); } } : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                role={onRowClick ? 'row' : undefined}
                className={[
                  'border-b border-ink-line/40',
                  'transition-colors duration-100',
                  onRowClick
                    ? 'cursor-pointer hover:bg-ink-800/60'
                    : '',
                ].filter(Boolean).join(' ')}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={[
                      'px-3 py-2.5 text-slate-300',
                      col.hideOnMobile ? 'hidden md:table-cell' : '',
                      col.className ?? '',
                    ].filter(Boolean).join(' ')}
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
