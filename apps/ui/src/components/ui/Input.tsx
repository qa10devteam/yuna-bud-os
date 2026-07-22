'use client';

import { forwardRef } from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

type InputVariant = 'default' | 'error' | 'success';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?:            string;
  helperText?:       string;
  errorText?:        string;
  variant?:          InputVariant;
  /** Icon to show inside input on the left */
  iconLeft?:         React.ReactNode;
  /** Icon to show inside input on the right */
  iconRight?:        React.ReactNode;
  wrapperClassName?: string;
}

// ── Style map — Brand Bible BudOS ─────────────────────────────────────────────

const VARIANT_CLS: Record<InputVariant, string> = {
  default: 'border-ink-line     focus:border-em/60  focus:ring-em/20',
  error:   'border-nogo/50      focus:border-nogo/70 focus:ring-nogo/20',
  success: 'border-go/50        focus:border-go/70  focus:ring-go/20',
};

// ── Component ──────────────────────────────────────────────────────────────────

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    label,
    helperText,
    errorText,
    variant          = 'default',
    iconLeft,
    iconRight,
    className        = '',
    wrapperClassName = '',
    id,
    ...rest
  },
  ref,
) {
  const inputId          = id ?? label?.toLowerCase().replace(/\s+/g, '-');
  const resolvedVariant: InputVariant = errorText ? 'error' : variant;

  const inputEl = (
    <div className="relative">
      {iconLeft && (
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none">
          {iconLeft}
        </span>
      )}
      <input
        ref={ref}
        id={inputId}
        className={[
          'w-full px-3.5 py-2.5 rounded-md',
          'bg-ink-800 border',
          'text-slate-100 placeholder-slate-600 text-sm',
          'focus:outline-none focus:ring-1',
          'transition-colors duration-150',
          'disabled:opacity-40 disabled:cursor-not-allowed',
          iconLeft  ? 'pl-10' : '',
          iconRight ? 'pr-10' : '',
          VARIANT_CLS[resolvedVariant],
          className,
        ]
          .filter(Boolean)
          .join(' ')}
        {...rest}
      />
      {iconRight && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none">
          {iconRight}
        </span>
      )}
    </div>
  );

  if (!label && !helperText && !errorText) return inputEl;

  return (
    <div className={wrapperClassName}>
      {label && (
        <label htmlFor={inputId} className="block text-xs font-medium text-slate-400 mb-1.5">
          {label}
        </label>
      )}
      {inputEl}
      {errorText ? (
        <p className="flex items-center gap-1 mt-1 text-xs text-nogo">
          <AlertCircle className="w-3 h-3 shrink-0" />
          {errorText}
        </p>
      ) : helperText ? (
        <p className="mt-1 text-xs text-slate-600">{helperText}</p>
      ) : null}
      {resolvedVariant === 'success' && !errorText && (
        <p className="flex items-center gap-1 mt-1 text-xs text-go">
          <CheckCircle2 className="w-3 h-3 shrink-0" />
          OK
        </p>
      )}
    </div>
  );
});

Input.displayName = 'Input';
