'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, AlertTriangle, X } from 'lucide-react';

interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

let toastId = 0;
const toasts: Toast[] = [];

export function showToast(type: 'success' | 'error' | 'info', message: string) {
  const id = String(++toastId);
  toasts.push({ id, type, message });
  setTimeout(() => {
    const index = toasts.findIndex(t => t.id === id);
    if (index !== -1) toasts.splice(index, 1);
  }, 3000);
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  
  useEffect(() => {
    const interval = setInterval(() => {
      setToasts([...toasts]);
    }, 100);
    return () => clearInterval(interval);
  }, []);
  
  const getIcon = (type: string) => {
    switch (type) {
      case 'success': return <CheckCircle className="w-5 h-5 text-accent-success" />;
      case 'error': return <AlertTriangle className="w-5 h-5 text-accent-danger" />;
      default: return <AlertTriangle className="w-5 h-5 text-accent-info" />;
    }
  };
  
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 100 }}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border ${
              toast.type === 'success' ? 'bg-accent-success/10 border-accent-success/30' :
              toast.type === 'error' ? 'bg-accent-danger/10 border-accent-danger/30' :
              'bg-accent-info/10 border-accent-info/30'
            }`}
          >
            {getIcon(toast.type)}
            <span className="text-earth-100 text-sm">{toast.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
