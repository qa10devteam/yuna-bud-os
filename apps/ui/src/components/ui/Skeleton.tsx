'use client';

import React from 'react';
import { motion } from 'motion/react';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circle' | 'card' | 'chart';
  lines?: number;
}

function SkeletonPulse({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <motion.div
      className={`rounded-lg bg-slate-800/60 ${className}`}
      style={style}
      animate={{ opacity: [0.4, 0.7, 0.4] }}
      transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
    />
  );
}

export function Skeleton({ className = '', variant = 'text', lines = 3 }: SkeletonProps) {
  if (variant === 'circle') {
    return <SkeletonPulse className={`w-10 h-10 rounded-full ${className}`} />;
  }

  if (variant === 'card') {
    return (
      <div className={`rounded-xl border border-slate-800/50 p-5 space-y-3 ${className}`}>
        <SkeletonPulse className="h-4 w-1/3" />
        <SkeletonPulse className="h-8 w-2/3" />
        <SkeletonPulse className="h-3 w-1/2" />
      </div>
    );
  }

  if (variant === 'chart') {
    return (
      <div className={`rounded-xl border border-slate-800/50 p-5 ${className}`}>
        <SkeletonPulse className="h-4 w-1/4 mb-4" />
        <div className="flex items-end gap-2 h-32">
          {[40, 65, 45, 80, 55, 70, 60].map((h, i) => (
            <SkeletonPulse key={i} className="flex-1" style={{ height: `${h}%` }} />
          ))}
        </div>
      </div>
    );
  }

  // text variant
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonPulse
          key={i}
          className={`h-3 ${i === lines - 1 ? 'w-2/3' : 'w-full'}`}
        />
      ))}
    </div>
  );
}

export function SkeletonGrid({ cards = 4 }: { cards?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: cards }).map((_, i) => (
        <Skeleton key={i} variant="card" />
      ))}
    </div>
  );
}

export function TableSkeleton({ cols = 5, rows = 5 }: { cols?: number; rows?: number }) {
  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex gap-4 pb-2 border-b border-slate-800/30">
        {Array.from({ length: cols }).map((_, i) => (
          <SkeletonPulse key={i} className="h-3 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 py-2">
          {Array.from({ length: cols }).map((_, c) => (
            <SkeletonPulse key={c} className="h-3 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
