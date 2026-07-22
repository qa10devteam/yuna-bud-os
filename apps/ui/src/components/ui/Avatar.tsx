'use client';

import Image from 'next/image';

// ── Types ──────────────────────────────────────────────────────────────────────

interface AvatarProps {
  name?:     string | null;
  src?:      string | null;
  size?:     'xs' | 'sm' | 'md' | 'lg';
  status?:   'online' | 'offline' | 'busy' | null;
  className?: string;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const SIZE_MAP = {
  xs: 'w-6 h-6 text-[10px]',
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-14 h-14 text-lg',
};

const STATUS_DOT_SIZE = {
  xs: 'w-1.5 h-1.5',
  sm: 'w-2 h-2',
  md: 'w-2.5 h-2.5',
  lg: 'w-3 h-3',
};

const STATUS_COLORS = {
  online:  'bg-go',
  offline: 'bg-slate-600',
  busy:    'bg-nogo',
};

function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('');
}

// Deterministic color from name
function avatarBg(name: string): string {
  const colors = [
    'bg-em/20 text-em',
    'bg-indigo/20 text-indigo-400',
    'bg-violet/20 text-violet-400',
    'bg-warn/20 text-warn',
    'bg-nogo/20 text-nogo',
    'bg-go/20 text-go',
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

// ── Component ──────────────────────────────────────────────────────────────────

export function Avatar({ name, src, size = 'md', status, className = '' }: AvatarProps) {
  const sizeClass = SIZE_MAP[size];

  if (src) {
    return (
      <div className={`relative inline-flex ${className}`}>
        <Image
          src={src}
          alt={name ?? 'Avatar'}
          width={40}
          height={40}
          className={`${sizeClass} rounded-full object-cover border border-ink-700/60`}
        />
        {status && (
          <span className={`absolute -bottom-0.5 -right-0.5 ${STATUS_DOT_SIZE[size]} ${STATUS_COLORS[status]} rounded-full ring-2 ring-ink-950`} />
        )}
      </div>
    );
  }

  const displayName = name || '?';
  const bgColor = avatarBg(displayName);

  return (
    <div className={`relative inline-flex ${className}`}>
      <div className={`${sizeClass} ${bgColor} rounded-full flex items-center justify-center font-bold border border-ink-700/40`}>
        {initials(displayName)}
      </div>
      {status && (
        <span className={`absolute -bottom-0.5 -right-0.5 ${STATUS_DOT_SIZE[size]} ${STATUS_COLORS[status]} rounded-full ring-2 ring-ink-950`} />
      )}
    </div>
  );
}
