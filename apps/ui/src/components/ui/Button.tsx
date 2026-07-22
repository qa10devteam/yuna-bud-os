'use client';

import { forwardRef, cloneElement, isValidElement } from 'react';
import type { ReactElement, ReactNode } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────────

/**
 * primary   — white pill (high-priority CTA)
 * ghost     — dim border, transparent bg (nav / inline)
 * danger    — red tint, destructive
 * em        — emerald pill (BudOS GO signal)
 * secondary — ink surface (standard actions, backward-compat alias)
 */
type ButtonVariant = 'primary' | 'ghost' | 'danger' | 'em' | 'secondary';
type ButtonSize    = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:  ButtonVariant;
  size?:     ButtonSize;
  loading?:  boolean;
  fullWidth?: boolean;
  /** Icon rendered before label */
  iconLeft?:  ReactNode;
  /** Icon rendered after label */
  iconRight?: ReactNode;
  /**
   * asChild — renders the component as its direct child element,
   * merging all props (Radix-style Slot lite).
   * No class-variance-authority needed.
   */
  asChild?:  boolean;
}

// ── Style maps ─────────────────────────────────────────────────────────────────

const VARIANT: Record<ButtonVariant, string> = {
  primary:
    'bg-white text-black rounded-full ' +
    'hover:bg-slate-100 ' +
    'border border-transparent',
  ghost:
    'bg-transparent text-white/60 ' +
    'border border-white/10 ' +
    'hover:bg-white/5 hover:text-white/80',
  danger:
    'bg-transparent text-red-400 ' +
    'border border-red-500/30 ' +
    'hover:bg-red-500/10 hover:border-red-500/50',
  em:
    'bg-[#10b981] text-black rounded-full ' +
    'hover:bg-[#34d399] ' +
    'border border-transparent',
  /** secondary — ink surface, backward-compat alias */
  secondary:
    'bg-ink-800 text-slate-200 ' +
    'border border-ink-line ' +
    'hover:bg-ink-700 hover:border-ink-line-strong hover:text-slate-100 ' +
    'rounded-md',
};

const SIZE: Record<ButtonSize, string> = {
  sm: 'px-4 py-1.5 text-[13px] gap-1.5',
  md: 'px-6 py-3   text-[15px] gap-2',
  lg: 'px-8 py-4   text-[17px] gap-2.5',
};

const BASE =
  'inline-flex items-center justify-center ' +
  'font-semibold ' +
  'transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150 ' +
  'active:scale-[0.97] ' +
  'disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100 ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10b981]/60 focus-visible:ring-offset-1';

// ── Slot helper ────────────────────────────────────────────────────────────────

function mergeIntoChild(
  child: ReactElement<{ className?: string; [key: string]: unknown }>,
  mergedClass: string,
  rest: Record<string, unknown>,
): ReactElement {
  return cloneElement(child, {
    ...rest,
    ...child.props,
    className: [mergedClass, child.props.className].filter(Boolean).join(' '),
  });
}

// ── Component ──────────────────────────────────────────────────────────────────

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant   = 'primary',
    size      = 'md',
    loading   = false,
    fullWidth = false,
    asChild   = false,
    iconLeft,
    iconRight,
    children,
    disabled,
    className = '',
    ...rest
  },
  ref,
) {
  const mergedClass = [
    BASE,
    VARIANT[variant],
    SIZE[size],
    fullWidth ? 'w-full' : '',
    loading   ? 'cursor-wait' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  // ── asChild mode ──────────────────────────────────────────────────────────
  if (asChild && isValidElement(children)) {
    return mergeIntoChild(
      children as ReactElement<{ className?: string; [key: string]: unknown }>,
      mergedClass,
      rest as Record<string, unknown>,
    );
  }

  return (
    <button type="button"
      ref={ref}
      disabled={disabled ?? loading}
      className={mergedClass}
      {...rest}
    >
      {loading ? (
        <span className="w-4 h-4 rounded-full border-2 border-current border-t-transparent animate-spin shrink-0" />
      ) : (
        iconLeft && <span className="shrink-0">{iconLeft}</span>
      )}
      {children && <span className="truncate">{children}</span>}
      {!loading && iconRight && <span className="shrink-0">{iconRight}</span>}
    </button>
  );
});

Button.displayName = 'Button';
