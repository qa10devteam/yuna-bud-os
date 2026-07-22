'use client';

import { motion } from 'motion/react';
import type { ReactNode } from 'react';
import { useStore } from '@/store/useStore';
import { ChevronRight } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface BreadcrumbSegment {
  label:    string;
  onClick?: () => void;
}

interface PageShellProps {
  title:       string;
  subtitle?:   string;
  breadcrumb?: BreadcrumbSegment[];
  actions?:    ReactNode;
  children:    ReactNode;
  noPadding?:  boolean;
}

// ── Breadcrumb ─────────────────────────────────────────────────────────────────

function Breadcrumb({ segments }: { segments: BreadcrumbSegment[] }) {
  return (
    <nav
      aria-label="Breadcrumb"
      className="flex items-center gap-1 mb-2 text-[11px] text-slate-600 font-medium tracking-wide uppercase"
    >
      {segments.map((seg, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="w-3 h-3 text-slate-700" />}
          {seg.onClick ? (
            <button type="button"
              onClick={seg.onClick}
              className="hover:text-slate-400 transition-colors duration-150"
            >
              {seg.label}
            </button>
          ) : (
            <span className={i === segments.length - 1 ? 'text-slate-500' : ''}>
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

  const segments: BreadcrumbSegment[] = breadcrumb ?? [
    { label: 'BudOS', onClick: () => setCurrentModule('dashboard') },
    { label: title },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={noPadding ? 'w-full' : 'pt-5 px-6 md:px-8 pb-10 max-w-7xl mx-auto w-full'}
    >
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div className="min-w-0">
          <Breadcrumb segments={segments} />
          <h1 className="text-xl font-bold text-slate-100 leading-tight tracking-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          )}
        </div>
        {actions && (
          <div className="flex items-center gap-2 shrink-0 mt-1">
            {actions}
          </div>
        )}
      </div>

      {/* ── Content ────────────────────────────────────────────── */}
      {children}
    </motion.div>
  );
}
