'use client';

import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize    = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:  ButtonVariant;
  size?:     ButtonSize;
  loading?:  boolean;
  /** Renders a full-width block button */
  fullWidth?: boolean;
  /** Icon to render before label */
  iconLeft?:  React.ReactNode;
  /** Icon to render after label */
  iconRight?: React.ReactNode;
}

// ── Style maps ─────────────────────────────────────────────────────────────────

const VARIANT: Record<ButtonVariant, string> = {
  primary:
    'bg-accent-primary text-earth-950 font-semibold ' +
    'hover:bg-accent-primary/90 hover:shadow-token-glow ' +
    'border border-transparent',
  secondary:
    'bg-earth-800/60 text-earth-200 font-medium ' +
    'border border-earth-700/50 ' +
    'hover:bg-earth-700/60 hover:border-earth-600/60 hover:text-earth-100',
  ghost:
    'text-earth-400 font-medium ' +
    'border border-transparent ' +
    'hover:bg-earth-800/60 hover:text-earth-200',
  danger:
    'bg-accent-danger/10 text-accent-danger font-medium ' +
    'border border-accent-danger/20 ' +
    'hover:bg-accent-danger/20 hover:border-accent-danger/40',
};

const SIZE: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs rounded-token gap-1.5 h-7',
  md: 'px-4 py-2 text-sm rounded-token gap-2 h-9',
  lg: 'px-5 py-2.5 text-base rounded-token-lg gap-2.5 h-11',
};

// ── Component ──────────────────────────────────────────────────────────────────

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant   = 'primary',
    size      = 'md',
    loading   = false,
    fullWidth = false,
    iconLeft,
    iconRight,
    children,
    disabled,
    className = '',
    ...rest
  },
  ref,
) {
  const isDisabled = disabled || loading;
  return (
    <button
      ref={ref}
      disabled={isDisabled}
      className={[
        'inline-flex items-center justify-center',
        'transition-all duration-150',
        'active:scale-[0.97]',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/60 focus-visible:ring-offset-1 focus-visible:ring-offset-earth-950',
        VARIANT[variant],
        SIZE[size],
        fullWidth ? 'w-full' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {loading ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
      ) : (
        iconLeft && <span className="shrink-0">{iconLeft}</span>
      )}
      {children && <span className="truncate">{children}</span>}
      {!loading && iconRight && <span className="shrink-0">{iconRight}</span>}
    </button>
  );
});

Button.displayName = 'Button';
