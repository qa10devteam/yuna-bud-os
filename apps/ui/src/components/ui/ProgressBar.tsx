'use client';

// ── Types ──────────────────────────────────────────────────────────────────────

interface ProgressBarProps {
  /** 0–100 percentage */
  value:     number;
  /** Color variant */
  color?:    'em' | 'go' | 'nogo' | 'warn' | 'indigo' | 'neutral';
  /** Show percentage label */
  showLabel?: boolean;
  /** Height */
  size?:     'xs' | 'sm' | 'md';
  className?: string;
}

// ── Color map ──────────────────────────────────────────────────────────────────

const BAR_COLORS: Record<string, string> = {
  em:      'bg-em',
  go:      'bg-go',
  nogo:    'bg-nogo',
  warn:    'bg-warn',
  indigo:  'bg-indigo',
  neutral: 'bg-slate-600',
};

const SIZE_MAP = {
  xs: 'h-1',
  sm: 'h-1.5',
  md: 'h-2',
};

// ── Component ──────────────────────────────────────────────────────────────────

export function ProgressBar({
  value,
  color = 'em',
  showLabel = false,
  size = 'sm',
  className = '',
}: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const barColor = BAR_COLORS[color] ?? BAR_COLORS.neutral;

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`flex-1 rounded-full bg-ink-800 overflow-hidden ${SIZE_MAP[size]}`}>
        <div
          className={`${barColor} ${SIZE_MAP[size]} rounded-full transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-500 ease-out`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-[11px] font-mono text-slate-500 tabular-nums shrink-0">
          {Math.round(clamped)}%
        </span>
      )}
    </div>
  );
}

// ── ScoreBar (auto-color based on score) ───────────────────────────────────────

export function ScoreBar({ score, showLabel = true, size = 'sm' }: {
  score: number; // 0-100
  showLabel?: boolean;
  size?: 'xs' | 'sm' | 'md';
}) {
  const color = score >= 80 ? 'go' : score >= 50 ? 'warn' : 'nogo';
  return <ProgressBar value={score} color={color} showLabel={showLabel} size={size} />;
}
