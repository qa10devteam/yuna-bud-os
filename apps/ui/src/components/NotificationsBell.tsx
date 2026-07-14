'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Bell, Clock, Star, ArrowRight, AtSign, X, CheckCheck, Check } from 'lucide-react';
import { useStore } from '@/store/useStore';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Notification {
  id: string;
  event_type?: string;
  // Legacy shape from bell (type + message)
  type?: 'deadline' | 'new_match' | 'status_change' | 'mention';
  message?: string;
  title?: string;
  body?: string;
  tender_id?: string;
  read: boolean;
  created_at: string;
}

// ── Config ────────────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  deadline:      { icon: Clock,      color: 'text-accent-danger',  bg: 'bg-accent-danger/15'  },
  new_match:     { icon: Star,       color: 'text-accent-primary', bg: 'bg-accent-primary/15' },
  status_change: { icon: ArrowRight, color: 'text-accent-info',    bg: 'bg-accent-info/15'    },
  mention:       { icon: AtSign,     color: 'text-accent-violet',  bg: 'bg-accent-violet/15'  },
  // API event_types
  'alert.deadline': { icon: Clock,      color: 'text-accent-danger',  bg: 'bg-accent-danger/15'  },
  'tender.new':     { icon: Star,       color: 'text-accent-primary', bg: 'bg-accent-primary/15' },
  'agent.done':     { icon: ArrowRight, color: 'text-accent-info',    bg: 'bg-accent-info/15'    },
  'alert.match':    { icon: Star,       color: 'text-accent-primary', bg: 'bg-accent-primary/15' },
};

const FALLBACK_CFG = TYPE_CONFIG.mention;

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return 'przed chwilą';
  if (h < 24) return `${h}h temu`;
  return `${Math.floor(h / 24)}d temu`;
}

// ── Poll interval (ms) ────────────────────────────────────────────────────────

const POLL_MS = 30_000;

// ── NotificationsBell ─────────────────────────────────────────────────────────

export function NotificationsBell() {
  const { accessToken, setCurrentModule } = useStore();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Fetch unread count (lightweight) ───────────────────────────────────────

  const fetchUnreadCount = useCallback(async () => {
    if (!accessToken) return;
    try {
      const res = await fetch('/api/v2/notifications/unread-count', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) return;
      const data = await res.json() as { count: number } | number;
      const count = typeof data === 'number' ? data : (data?.count ?? 0);
      setUnreadCount(count);
    } catch {
      // non-critical
    }
  }, [accessToken]);

  // ── Fetch notification list (on open) ─────────────────────────────────────

  const fetchNotifications = useCallback(async () => {
    if (!accessToken) return;
    try {
      const res = await fetch('/api/v2/notifications?limit=20', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) return;
      const data = await res.json() as Notification[] | { items: Notification[] };
      const items = Array.isArray(data) ? data : (data?.items ?? []);
      setNotifications(items);
      const unread = items.filter((n: Notification) => !n.read).length;
      setUnreadCount(unread);
    } catch {
      // non-critical
    }
  }, [accessToken]);

  // ── Poll unread count every 30s ────────────────────────────────────────────

  useEffect(() => {
    fetchUnreadCount();
    pollRef.current = setInterval(fetchUnreadCount, POLL_MS);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchUnreadCount]);

  // ── Fetch full list when panel opens ─────────────────────────────────────

  useEffect(() => {
    if (open) fetchNotifications();
  }, [open, fetchNotifications]);

  // ── Close on outside click ────────────────────────────────────────────────

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ── Mark single read ──────────────────────────────────────────────────────

  function markRead(id: string) {
    setNotifications(ns => ns.map(n => n.id === id ? { ...n, read: true } : n));
    setUnreadCount(prev => Math.max(0, prev - 1));
    if (accessToken) {
      fetch(`/api/v2/notifications/${id}/read`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
      }).catch(() => {});
    }
  }

  // ── Mark all read ─────────────────────────────────────────────────────────

  function markAllRead() {
    setNotifications(ns => ns.map(n => ({ ...n, read: true })));
    setUnreadCount(0);
    if (accessToken) {
      fetch('/api/v2/notifications/read-all', {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      }).catch(() => {});
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="relative p-1.5 rounded-lg hover:bg-earth-800 text-earth-500 hover:text-earth-200 transition-colors"
        aria-label="Powiadomienia"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-accent-danger rounded-full text-earth-50 text-[9px] font-bold flex items-center justify-center"
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </motion.span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 top-full mt-2 w-80 bg-earth-900 border border-earth-700/60 rounded-xl shadow-xl shadow-black/50 z-50 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-earth-800/60">
              <span className="text-sm font-semibold text-earth-100">
                Powiadomienia
                {unreadCount > 0 && (
                  <span className="ml-2 text-xs font-normal text-accent-danger">{unreadCount} nowych</span>
                )}
              </span>
              <div className="flex items-center gap-2">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllRead}
                    className="text-xs text-accent-primary hover:text-emerald-400 flex items-center gap-1 transition-colors"
                  >
                    <CheckCheck className="w-3 h-3" /> Wszystkie
                  </button>
                )}
                <button onClick={() => setOpen(false)} className="text-earth-600 hover:text-earth-300 transition-colors">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* List */}
            <div className="max-h-72 overflow-y-auto divide-y divide-earth-800/40">
              {notifications.length === 0 ? (
                <div className="px-4 py-6 text-center">
                  <Bell className="w-8 h-8 text-earth-700 mx-auto mb-2" />
                  <p className="text-earth-600 text-sm">Brak powiadomień</p>
                </div>
              ) : (
                notifications.map(n => {
                  const key = n.event_type || n.type || 'mention';
                  const cfg = TYPE_CONFIG[key] ?? FALLBACK_CFG;
                  const Icon = cfg.icon;
                  const message = n.title || n.message || '';
                  const sub = n.body;

                  return (
                    <div
                      key={n.id}
                      onClick={() => {
                        markRead(n.id);
                        if (n.tender_id) setCurrentModule('zwiad');
                        setOpen(false);
                      }}
                      className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-earth-800/40 ${n.read ? 'opacity-60' : ''}`}
                    >
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${cfg.bg}`}>
                        <Icon className={`w-3.5 h-3.5 ${cfg.color}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-earth-200 leading-snug line-clamp-2">{message}</p>
                        {sub && <p className="text-[10px] text-earth-500 mt-0.5 line-clamp-1">{sub}</p>}
                        <p className="text-[10px] text-earth-600 mt-0.5">{timeAgo(n.created_at)}</p>
                      </div>
                      {!n.read && (
                        <button
                          onClick={e => { e.stopPropagation(); markRead(n.id); }}
                          className="p-1 text-earth-600 hover:text-accent-primary transition-colors shrink-0"
                          title="Oznacz jako przeczytane"
                        >
                          <Check className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-earth-800/60 px-4 py-2">
              <button
                onClick={() => { setCurrentModule('notifications'); setOpen(false); }}
                className="text-xs text-accent-primary hover:text-emerald-400 transition-colors w-full text-left"
              >
                Pokaż wszystkie powiadomienia →
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
