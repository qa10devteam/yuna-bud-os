'use client';

import { forwardRef } from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

type InputVariant = 'default' | 'error' | 'success';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?:      string;
  helperText?: string;
  errorText?:  string;
  variant?:    InputVariant;
  /** Icon to show inside input on the left */
  iconLeft?:   React.ReactNode;
  /** Icon to show inside input on the right */
  iconRight?:  React.ReactNode;
  /** Wrap in a <div> with label + helper text */
  wrapperClassName?: string;
}

// ── Style map ──────────────────────────────────────────────────────────────────

const VARIANT_CLS: Record<InputVariant, string> = {
  default: 'border-earth-700/50 focus:border-accent-primary/60 focus:ring-accent-primary/20',
  error:   'border-accent-danger/50 focus:border-accent-danger/70 focus:ring-accent-danger/20',
  success: 'border-accent-success/50 focus:border-accent-success/70 focus:ring-accent-success/20',
};

// ── Component ──────────────────────────────────────────────────────────────────

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    label,
    helperText,
    errorText,
    variant    = 'default',
    iconLeft,
    iconRight,
    className   = '',
    wrapperClassName = '',
    id,
    ...rest
  },
  ref,
) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-');
  const resolvedVariant: InputVariant = errorText ? 'error' : variant;

  const inputEl = (
    <div className="relative">
      {iconLeft && (
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-earth-500 pointer-events-none">
          {iconLeft}
        </span>
      )}
      <input
        ref={ref}
        id={inputId}
        className={[
          'w-full px-3.5 py-2.5 rounded-token',
          'bg-earth-800/60 border',
          'text-earth-100 placeholder-earth-600 text-sm',
          'focus:outline-none focus:ring-1',
          'transition-colors duration-150',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          // Mobile: font-size 16px prevents iOS zoom
          'text-base md:text-sm',
          iconLeft  ? 'pl-9'  : '',
          iconRight ? 'pr-9'  : '',
          VARIANT_CLS[resolvedVariant],
          className,
        ]
          .filter(Boolean)
          .join(' ')}
        {...rest}
      />
      {iconRight && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-earth-500">
          {iconRight}
        </span>
      )}
    </div>
  );

  // If no label / helper — return bare input
  if (!label && !helperText && !errorText) return inputEl;

  return (
    <div className={wrapperClassName}>
      {label && (
        <label htmlFor={inputId} className="block text-xs font-medium text-earth-400 mb-1.5">
          {label}
        </label>
      )}
      {inputEl}
      {errorText ? (
        <p className="flex items-center gap-1 text-xs text-accent-danger mt-1">
          <AlertCircle className="w-3 h-3 shrink-0" />
          {errorText}
        </p>
      ) : helperText ? (
        <p className="text-xs text-earth-600 mt-1">{helperText}</p>
      ) : null}
    </div>
  );
});

Input.displayName = 'Input';
