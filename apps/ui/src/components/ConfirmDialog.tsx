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
    danger:  { icon: 'text-red-400',    btn: 'bg-red-600 hover:bg-red-500 text-white',    ring: 'ring-red-500/30' },
    warning: { icon: 'text-amber-400',  btn: 'bg-amber-600 hover:bg-amber-500 text-white', ring: 'ring-amber-500/30' },
    info:    { icon: 'text-blue-400',   btn: 'bg-blue-600 hover:bg-blue-500 text-white',   ring: 'ring-blue-500/30' },
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
              w-full max-w-md bg-earth-950 border border-earth-800 rounded-2xl shadow-2xl
              ring-1 ${variantStyles.ring} p-6`}
          >
            {/* Header */}
            <div className="flex items-start gap-3 mb-4">
              <div className={`mt-0.5 shrink-0 ${variantStyles.icon}`}>
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h2 id="confirm-title" className="text-earth-100 font-semibold text-base">
                  {title}
                </h2>
                <p className="text-earth-400 text-sm mt-1 leading-relaxed">{message}</p>
              </div>
              <button
                onClick={onCancel}
                className="text-earth-500 hover:text-earth-300 transition-colors ml-2 shrink-0"
                aria-label="Zamknij"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={onCancel}
                className="px-4 py-2 text-sm font-medium text-earth-300 bg-earth-800/50
                  hover:bg-earth-800 border border-earth-700/50 rounded-lg transition-colors"
              >
                {cancelLabel}
              </button>
              <button
                ref={confirmRef}
                onClick={onConfirm}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${variantStyles.btn}`}
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
