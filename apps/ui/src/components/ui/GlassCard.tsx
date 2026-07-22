'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import type { ReactNode } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────────

type GlassVariant = 'default' | 'hover' | 'highlight' | 'overlay';

interface GlassCardProps {
  children:  ReactNode;
  className?: string;
  /** Render as Next.js Link */
  href?:     string;
  /** Render inner button for click handling */
  onClick?:  () => void;
  /**
   * default    — glass-card (standard surface)
   * hover      — glass-card-hover (lift on hover)
   * highlight  — glass-card + emerald border (active/selected)
   * overlay    — glass-overlay (modal / dropdown)
   */
  variant?:  GlassVariant;
}

// ── Style map ──────────────────────────────────────────────────────────────────

const VARIANT_CLS: Record<GlassVariant, string> = {
  default:   'glass-card rounded-xl',
  hover:     'glass-card-hover rounded-xl',
  highlight: 'glass-card rounded-xl border-em-mid',   // override border-color to emerald
  overlay:   'glass-overlay rounded-2xl',
};

// ── Shared motion props ────────────────────────────────────────────────────────

const MOTION = {
  initial:    { opacity: 0, y: 16 },
  animate:    { opacity: 1, y: 0 },
  transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
} as const;

// ── Component ──────────────────────────────────────────────────────────────────
//
// motion.div is always the outermost element (animation + glass surface).
// href / onClick change only the inner navigation/interaction wrapper,
// not the visual card — keeps a single source of style truth.

export function GlassCard({
  children,
  className = '',
  href,
  onClick,
  variant = 'default',
}: GlassCardProps) {
  const base = [VARIANT_CLS[variant], className].filter(Boolean).join(' ');

  return (
    <motion.div className={base} {...MOTION}>
      {href ? (
        <Link href={href} className="block w-full h-full">
          {children}
        </Link>
      ) : onClick ? (
        <button
          type="button"
          onClick={onClick}
          className="block w-full h-full text-left cursor-pointer"
        >
          {children}
        </button>
      ) : (
        children
      )}
    </motion.div>
  );
}
