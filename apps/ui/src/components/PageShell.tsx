'use client';

import { motion } from 'motion/react';
import type { ReactNode } from 'react';
import { useStore } from '@/store/useStore';
import { ChevronRight } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface BreadcrumbSegment {
  label:   string;
  /** If provided renders as clickable segment */
  onClick?: () => void;
}

interface PageShellProps {
  title:       string;
  subtitle?:   string;
  /** Explicit breadcrumb segments — auto-generated from module name if omitted */
  breadcrumb?: BreadcrumbSegment[];
  /** Action buttons — rendered right of the title */
  actions?:    ReactNode;
  children:    ReactNode;
  /** Override outer padding for full-bleed pages */
  noPadding?:  boolean;
}

// ── Breadcrumb ─────────────────────────────────────────────────────────────────

function Breadcrumb({ segments }: { segments: BreadcrumbSegment[] }) {
  return (
    <nav
      aria-label="Breadcrumb"
      className="flex items-center gap-1 mb-2 text-[11px] text-earth-600 font-medium tracking-wide uppercase"
    >
      {segments.map((seg, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="w-3 h-3 text-earth-700" />}
          {seg.onClick ? (
            <button
              onClick={seg.onClick}
              className="hover:text-earth-400 transition-colors"
            >
              {seg.label}
            </button>
          ) : (
            <span className={i === segments.length - 1 ? 'text-earth-500' : ''}>
              {seg.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}

// ── Component ──────────────────────────────────────────────────────────────────

export function PageShell({
  title,
  subtitle,
  breadcrumb,
  actions,
  children,
  noPadding = false,
}: PageShellProps) {
  const { setCurrentModule } = useStore();

  // Auto-breadcrumb: YU-NA / <title>
  const segments: BreadcrumbSegment[] = breadcrumb ?? [
    {
      label:   'YU-NA',
      onClick: () => setCurrentModule('dashboard'),
    },
    { label: title },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={noPadding ? 'w-full' : 'pt-6 px-6 md:px-8 pb-10 max-w-7xl mx-auto w-full'}
    >
      {/* ── Breadcrumb ──────────────────────────────────────────────── */}
      <Breadcrumb segments={segments} />

      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-earth-100 tracking-tight leading-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-1 text-sm text-earth-500">{subtitle}</p>
          )}
        </div>

        {actions && (
          <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
            {actions}
          </div>
        )}
      </div>

      {/* ── Content ─────────────────────────────────────────────────── */}
      {children}
    </motion.div>
  );
}
