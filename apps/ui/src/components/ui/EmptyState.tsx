'use client';

import React from 'react';
import { motion } from 'motion/react';
import { Inbox, Search, FileX, AlertCircle } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  icon?: LucideIcon | React.ComponentType<any> | React.ReactNode;
  title?: string;
  description?: string;
  variant?: 'default' | 'search' | 'error' | 'empty';
  compact?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
  cta?: React.ReactNode;
}

const VARIANTS: Record<string, { icon: LucideIcon; title: string; description: string }> = {
  default: {
    icon: Inbox,
    title: 'Brak danych',
    description: 'Tutaj pojawią się nowe elementy.',
  },
  search: {
    icon: Search,
    title: 'Brak wyników',
    description: 'Spróbuj zmienić kryteria wyszukiwania.',
  },
  error: {
    icon: AlertCircle,
    title: 'Błąd ładowania',
    description: 'Nie udało się pobrać danych. Spróbuj ponownie.',
  },
  empty: {
    icon: FileX,
    title: 'Pusto',
    description: 'Nie ma jeszcze żadnych elementów w tej sekcji.',
  },
};

export function EmptyState({
  icon,
  title,
  description,
  variant = 'default',
  compact,
  action,
  cta,
}: EmptyStateProps) {
  const v = VARIANTS[variant];
  const heading = title || v.title;
  const desc = description || v.description;

  // Determine if icon is a component or ReactNode
  const isComponent = typeof icon === 'function';
  const FallbackIcon = v.icon;

  const renderIcon = () => {
    if (!icon) return <FallbackIcon className="w-6 h-6 text-slate-500" strokeWidth={1.5} />;
    if (isComponent) {
      const Comp = icon as React.ComponentType<{ className?: string; strokeWidth?: number }>;
      return <Comp className="w-6 h-6 text-slate-500" strokeWidth={1.5} />;
    }
    return <>{icon}</>;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex flex-col items-center justify-center px-6 ${compact ? 'py-8' : 'py-16'}`}
    >
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
        style={{
          background: 'rgba(148,163,184,0.06)',
          border: '1px solid rgba(148,163,184,0.1)',
        }}
      >
        {renderIcon()}
      </div>
      <h3 className="text-sm font-medium text-slate-300 mb-1">{heading}</h3>
      <p className="text-xs text-slate-500 text-center max-w-[240px]">{desc}</p>
      {cta && <div className="mt-4">{cta}</div>}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-3.5 py-1.5 text-xs font-medium text-emerald-400 rounded-lg transition-colors"
          style={{
            background: 'rgba(16,185,129,0.08)',
            border: '1px solid rgba(16,185,129,0.2)',
          }}
        >
          {action.label}
        </button>
      )}
    </motion.div>
  );
}
