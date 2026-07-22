'use client';

import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AlertTriangle, X } from 'lucide-react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'info';
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Potwierdź',
  cancelLabel = 'Anuluj',
  variant = 'danger',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);

  // Focus confirm button when opened + Escape to cancel
  useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => confirmRef.current?.focus());
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onCancel(); };
    document.addEventListener('keydown', onKey);
    return () => { cancelAnimationFrame(frame); document.removeEventListener('keydown', onKey); };
  }, [open, onCancel]);

  const variantStyles = {
    danger:  { icon: 'text-nogo',   btn: 'bg-nogo hover:opacity-90 text-ink-950/30',   ring: 'ring-nogo/30' },
    warning: { icon: 'text-warn',  btn: 'bg-warn hover:opacity-90 text-ink-950', ring: 'ring-warn/30' },
    info:    { icon: 'text-indigo',     btn: 'bg-indigo hover:opacity-90 text-ink-950/30',     ring: 'ring-indigo/30' },
  }[variant];

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={onCancel}
          />

          {/* Dialog */}
          <motion.div
            key="dialog"
            initial={{ opacity: 0, scale: 0.92, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 8 }}
            transition={{ duration: 0.18, ease: [0.4, 0, 0.2, 1] }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            className={`fixed z-50 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
              w-full max-w-md bg-ink-950 border border-ink-800 rounded-2xl shadow-xl
              ring-1 ${variantStyles.ring} p-6`}
          >
            {/* Header */}
            <div className="flex items-start gap-3 mb-4">
              <div className={`mt-0.5 shrink-0 ${variantStyles.icon}`}>
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h2 id="confirm-title" className="text-slate-100 font-semibold text-base">
                  {title}
                </h2>
                <p className="text-slate-400 text-sm mt-1 leading-relaxed">{message}</p>
              </div>
              <button type="button"
                onClick={onCancel}
                className="text-slate-500 hover:text-slate-300 transition-colors ml-2 shrink-0"
                aria-label="Zamknij"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2 mt-6">
              <button type="button"
                onClick={onCancel}
                className="px-4 py-2 text-sm font-medium text-slate-300 bg-ink-800/50
                  hover:bg-ink-800 border border-ink-700/50 rounded-md transition-colors"
              >
                {cancelLabel}
              </button>
              <button type="button"
                ref={confirmRef}
                onClick={onConfirm}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${variantStyles.btn}`}
              >
                {confirmLabel}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ── Hook helper ────────────────────────────────────────────────────────────────
import { useState, useCallback } from 'react';

interface UseConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  variant?: ConfirmDialogProps['variant'];
}

export function useConfirm() {
  const [state, setState] = useState<{ open: boolean; resolve?: (v: boolean) => void } & Partial<UseConfirmOptions>>({ open: false });

  const confirm = useCallback((opts: UseConfirmOptions): Promise<boolean> => {
    return new Promise(resolve => {
      setState({ open: true, resolve, ...opts });
    });
  }, []);

  const handleConfirm = useCallback(() => {
    state.resolve?.(true);
    setState(s => ({ ...s, open: false }));
  }, [state]);

  const handleCancel = useCallback(() => {
    state.resolve?.(false);
    setState(s => ({ ...s, open: false }));
  }, [state]);

  const dialog = (
    <ConfirmDialog
      open={state.open}
      title={state.title ?? ''}
      message={state.message ?? ''}
      confirmLabel={state.confirmLabel}
      variant={state.variant}
      onConfirm={handleConfirm}
      onCancel={handleCancel}
    />
  );

  return { confirm, dialog };
}
