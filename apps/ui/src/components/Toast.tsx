'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle, AlertTriangle, XCircle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  createdAt: number;
}

const TOAST_DURATION = 4000;
const MAX_TOASTS = 3;

// Global state via module-level subscribers pattern
const listeners = new Set<(toasts: ToastItem[]) => void>();
let globalToasts: ToastItem[] = [];
let counter = 0;

function notifyListeners() {
  listeners.forEach(fn => fn([...globalToasts]));
}

export function showToast(type: ToastType, message: string) {
  const id = String(++counter);
  const toast: ToastItem = { id, type, message, createdAt: Date.now() };

  // Keep max 3
  if (globalToasts.length >= MAX_TOASTS) {
    globalToasts = globalToasts.slice(globalToasts.length - MAX_TOASTS + 1);
  }
  globalToasts = [...globalToasts, toast];
  notifyListeners();

  setTimeout(() => {
    globalToasts = globalToasts.filter(t => t.id !== id);
    notifyListeners();
  }, TOAST_DURATION);
}

const TOAST_CONFIG: Record<ToastType, {
  Icon: typeof CheckCircle;
  iconClass: string;
  borderClass: string;
  bgClass: string;
  textClass: string;
  barClass: string;
}> = {
  success: {
    Icon: CheckCircle,
    iconClass: 'text-em',
    borderClass: 'border-em-brd',
    bgClass: 'bg-em/10',
    textClass: 'text-slate-100',
    barClass: 'bg-em',
  },
  error: {
    Icon: XCircle,
    iconClass: 'text-nogo',
    borderClass: 'border-nogo-brd',
    bgClass: 'bg-nogo/10',
    textClass: 'text-slate-100',
    barClass: 'bg-nogo',
  },
  warning: {
    Icon: AlertTriangle,
    iconClass: 'text-warn',
    borderClass: 'border-warn-brd',
    bgClass: 'bg-warn/10',
    textClass: 'text-slate-100',
    barClass: 'bg-warn',
  },
  info: {
    Icon: Info,
    iconClass: 'text-indigo-400',
    borderClass: 'border-indigo/30',
    bgClass: 'bg-indigo/10',
    textClass: 'text-slate-100',
    barClass: 'bg-indigo',
  },
};

function ToastProgress({ duration, barClass }: { duration: number; barClass: string }) {
  const [width, setWidth] = useState(100);
  const startRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    startRef.current = Date.now();
    const tick = () => {
      const elapsed = Date.now() - startRef.current!;
      const pct = Math.max(0, 100 - (elapsed / duration) * 100);
      setWidth(pct);
      if (pct > 0) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [duration]);

  return (
    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-ink-800/60">
      <div
        className={`h-full ${barClass} transition-none rounded-full`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

function SingleToast({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: string) => void }) {
  const config = TOAST_CONFIG[toast.type];
  const Icon = config.Icon;
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.9, transition: { duration: 0.18 } }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      className={`relative flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border overflow-hidden min-w-[280px] max-w-[380px] ${config.bgClass} ${config.borderClass}`}
      style={{ backdropFilter: 'blur(12px)' }}
    >
      <Icon className={`w-5 h-5 shrink-0 ${config.iconClass}`} />
      <span className={`text-sm font-medium flex-1 ${config.textClass}`}>{toast.message}</span>
      <button type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Zamknij"
        className="w-5 h-5 rounded flex items-center justify-center text-slate-500 hover:text-slate-300 transition-colors shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
      <ToastProgress duration={TOAST_DURATION} barClass={config.barClass} />
    </motion.div>
  );
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    const handler = (updated: ToastItem[]) => setToasts(updated);
    listeners.add(handler);
    return () => { listeners.delete(handler); };
  }, []);

  const dismiss = useCallback((id: string) => {
    globalToasts = globalToasts.filter(t => t.id !== id);
    notifyListeners();
  }, []);

  return (
    <div className="fixed bottom-24 right-6 z-[60] flex flex-col-reverse gap-2 items-end pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map(toast => (
          <div key={toast.id} className="pointer-events-auto">
            <SingleToast toast={toast} onDismiss={dismiss} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  );
}
