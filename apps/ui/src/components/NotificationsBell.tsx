'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Bell, Clock, Star, ArrowRight, AtSign, X, CheckCheck } from 'lucide-react';
import { useStore } from '@/store/useStore';

interface Notification {
  id: string;
  type: 'deadline' | 'new_match' | 'status_change' | 'mention';
  message: string;
  tender_id?: string;
  read: boolean;
  created_at: string;
}

const TYPE_CONFIG = {
  deadline:      { icon: Clock, color: 'text-red-400', bg: 'bg-red-500/15' },
  new_match:     { icon: Star, color: 'text-green-400', bg: 'bg-green-500/15' },
  status_change: { icon: ArrowRight, color: 'text-blue-400', bg: 'bg-blue-500/15' },
  mention:       { icon: AtSign, color: 'text-purple-400', bg: 'bg-purple-500/15' },
};

const MOCK_NOTIFICATIONS: Notification[] = [
  { id: '1', type: 'deadline', message: 'Przetarg "Budowa drogi..." kończy się za 2 dni', tender_id: '1', read: false, created_at: new Date(Date.now() - 3600000).toISOString() },
  { id: '2', type: 'new_match', message: 'Nowy przetarg pasujący do Twojego profilu (95%)', tender_id: '2', read: false, created_at: new Date(Date.now() - 7200000).toISOString() },
  { id: '3', type: 'status_change', message: 'Przetarg przeszedł do etapu GO ✓', tender_id: '3', read: true, created_at: new Date(Date.now() - 86400000).toISOString() },
];

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3600000);
  if (h < 1) return 'przed chwilą';
  if (h < 24) return `${h}h temu`;
  return `${Math.floor(h / 24)}d temu`;
}

export function NotificationsBell() {
  const { accessToken, setCurrentModule } = useStore();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>(MOCK_NOTIFICATIONS);
  const ref = useRef<HTMLDivElement>(null);

  const unread = notifications.filter(n => !n.read).length;

  useEffect(() => {
    if (!accessToken) return;
    fetch('/api/v2/notifications?limit=20', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.items?.length > 0) setNotifications(data.items);
      })
      .catch(() => {});
  }, [accessToken]);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  function markRead(id: string) {
    setNotifications(ns => ns.map(n => n.id === id ? { ...n, read: true } : n));
    if (accessToken) {
      fetch(`/api/v2/notifications/${id}/read`, {
        method: 'POST',
        headers: { Authorization: *** ${accessToken}` },
      }).catch(() => {});
    }
  }

  function markAllRead() {
    setNotifications(ns => ns.map(n => ({ ...n, read: true })));
    if (accessToken) {
      fetch('/api/v2/notifications/read-all', {
        method: 'POST',
        headers: { Authorization: *** ${accessToken}` },
      }).catch(() => {});
    }
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="relative p-1.5 rounded-lg hover:bg-earth-800 text-earth-500 hover:text-earth-200 transition-colors"
        aria-label="Powiadomienia"
      >
        <Bell className="w-4 h-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full text-white text-[9px] font-bold flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 top-full mt-2 w-80 bg-earth-900 border border-earth-700/60 rounded-xl shadow-xl shadow-black/50 z-50 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-earth-800/60">
              <span className="text-sm font-semibold text-earth-100">Powiadomienia</span>
              <div className="flex items-center gap-2">
                {unread > 0 && (
                  <button onClick={markAllRead} className="text-xs text-accent-primary hover:text-emerald-400 flex items-center gap-1">
                    <CheckCheck className="w-3 h-3" /> Wszystkie
                  </button>
                )}
                <button onClick={() => setOpen(false)} className="text-earth-600 hover:text-earth-300">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="max-h-72 overflow-y-auto divide-y divide-earth-800/40">
              {notifications.length === 0 ? (
                <p className="px-4 py-6 text-center text-earth-600 text-sm">Brak powiadomień</p>
              ) : notifications.map(n => {
                const cfg = TYPE_CONFIG[n.type] ?? TYPE_CONFIG.mention;
                const Icon = cfg.icon;
                return (
                  <div
                    key={n.id}
                    onClick={() => { markRead(n.id); if (n.tender_id) setCurrentModule('zwiad'); setOpen(false); }}
                    className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-earth-800/40 ${n.read ? 'opacity-60' : ''}`}
                  >
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${cfg.bg}`}>
                      <Icon className={`w-3.5 h-3.5 ${cfg.color}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-earth-200 leading-snug">{n.message}</p>
                      <p className="text-[10px] text-earth-600 mt-0.5">{timeAgo(n.created_at)}</p>
                    </div>
                    {!n.read && <div className="w-1.5 h-1.5 bg-accent-primary rounded-full shrink-0 mt-1.5" />}
                  </div>
                );
              })}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
