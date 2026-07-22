'use client';

import type { ReactNode, ElementType } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────────

export interface TabItem {
  id: string;
  label: string;
  icon?: ElementType;
  badge?: string | number;
}

interface TabsProps {
  tabs:      TabItem[];
  active:    string;
  onChange:  (id: string) => void;
  size?:     'sm' | 'md';
  className?: string;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function Tabs({ tabs, active, onChange, size = 'md', className = '' }: TabsProps) {
  const base = size === 'sm'
    ? 'text-xs px-3 py-1.5 gap-1.5'
    : 'text-sm px-4 py-2 gap-2';

  return (
    <div className={`flex bg-ink-900 rounded-xl p-1 border border-ink-800 ${className}`}>
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={[
              'flex items-center justify-center font-medium rounded-lg transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200',
              base,
              isActive
                ? 'bg-ink-800 text-slate-100 shadow-sm'
                : 'text-slate-500 hover:text-slate-300 hover:bg-ink-800/50',
            ].join(' ')}
          >
            {Icon && <Icon className="w-3.5 h-3.5" />}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span className={[
                'text-[10px] font-bold px-1.5 py-0.5 rounded-full tabular-nums',
                isActive ? 'bg-em/20 text-em' : 'bg-ink-700 text-slate-500',
              ].join(' ')}>
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
