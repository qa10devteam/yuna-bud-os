'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Bell, Trophy, Clock, Info,
  CheckCheck, Loader2, RefreshCw,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';

// ─── Types ─────────────────────────────────────────────────────────────────────

type NotifType = 'alert_match' | 'competitor_win' | 'bookmark_deadline' | 'system';
type FilterTab = 'all' | 'unread' | 'alerts' | 'competitors' | 'deadlines';

interface Notification {
  id: string;
  type: NotifType;
  title: string;
  body: string;
  read: boolean;
  created_at: string;
  data: Record<string, unknown>;
}

interface NotifPage {
  items: Notification[];
  total: number;
  next_cursor: string | null;
}

// ─── Constants ─────────────────────────────────────────────────────────────────

const FILTER_TABS: { id: FilterTab; label: string }[] = [
  { id: 'all',         label: 'Wszystkie'  },
  { id: 'unread',      label: 'Nieprzeczytane' },
  { id: 'alerts',      label: 'Alerty'     },
  { id: 'competitors', label: 'Konkurenci' },
  { id: 'deadlines',   label: 'Terminy'    },
];

const NOTIF_META: Record<NotifType, {
  Icon: typeof Bell;
  iconColor: string;
  bgColor: string;
  borderColor: string;
  label: string;
}> = {
  alert_match: {
    Icon: Bell,
    iconColor: 'text-blue-400',
    bgColor:   'bg-blue-500/15',
    borderColor: 'border-blue-500/25',
    label: 'Alert przetargowy',
  },
  competitor_win: {
    Icon: Trophy,
    iconColor: 'text-orange-400',
    bgColor:   'bg-orange-500/15',
    borderColor: 'border-orange-500/25',
    label: 'Wynik konkurenta',
  },
  bookmark_deadline: {
    Icon: Clock,
    iconColor: 'text-red-400',
    bgColor:   'bg-red-500/15',
    borderColor: 'border-red-500/25',
    label: 'Deadline',
  },
  system: {
    Icon: Info,
    iconColor: 'text-zinc-400',
    bgColor:   'bg-zinc-500/15',
    borderColor: 'border-zinc-500/20',
    label: 'Systemowe',
  },
};

const FILTER_TYPES: Partial<Record<FilterTab, NotifType[]>> = {
  alerts:      ['alert_match'],
  competitors: ['competitor_win'],
  deadlines:   ['bookmark_deadline'],
};

const AUTO_REFRESH_MS = 30_000;

// ─── Helpers ───────────────────────────────────────────────────────────────────

function relativeTime(iso: string): string {
  const now  = Date.now();
  const then = new Date(iso).getTime();
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60)       return 'przed chwila';
  if (diff < 3600)     return `${Math.floor(diff / 60)}min temu`;
  if (diff < 86400)    return `${Math.floor(diff / 3600)}h temu`;
  if (diff < 86400 * 2) {
    const t = new Date(iso);
    const hh = t.getHours().toString().padStart(2, '0');
    const mm = t.getMinutes().toString().padStart(2, '0');
    return `wczoraj ${hh}:${mm}`;
  }
  return new Date(iso).toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' });
}

function groupByDate(notifications: Notification[]): Array<{ label: string; items: Notification[] }> {
  const now   = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yest  = today - 86400_000;

  const groups: Record<string, Notification[]> = { Dzisiaj: [], Wczoraj: [], Starsze: [] };

  for (const n of notifications) {
    const d = new Date(n.created_at).getTime();
    if (d >= today)     groups['Dzisiaj'].push(n);
    else if (d >= yest) groups['Wczoraj'].push(n);
    else                groups['Starsze'].push(n);
  }

  return Object.entries(groups)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }));
}

// ─── Notification card ─────────────────────────────────────────────────────────

function NotifCard({
  notif,
  onRead,
}: {
  notif: Notification;
  onRead: (id: string) => void;
}) {
  const meta = NOTIF_META[notif.type] ?? NOTIF_META.system;
  const Icon = meta.Icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4, scale: 0.98 }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
    >
      <button
        onClick={() => !notif.read && onRead(notif.id)}
        className={`w-full text-left transition-colors rounded-xl border overflow-hidden group ${
          notif.read
            ? 'bg-earth-900/60 border-earth-800/60 hover:border-earth-700/60'
            : 'bg-earth-800/80 border-earth-700/60 hover:border-earth-600/80'
        }`}
        style={{ cursor: notif.read ? 'default' : 'pointer' }}
      >
        <div className="flex items-start gap-3 p-3.5">
          {/* Unread indicator */}
          <div className="relative shrink-0 mt-0.5">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${meta.bgColor} border ${meta.borderColor}`}>
              <Icon className={`w-4.5 h-4.5 ${meta.iconColor}`} />
            </div>
            {!notif.read && (
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-blue-500 border border-earth-950 shrink-0" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2 mb-0.5">
              <p className={`text-sm leading-snug ${notif.read ? 'text-earth-300 font-normal' : 'text-earth-100 font-semibold'}`}>
                {notif.title}
              </p>
              <span className="text-xs text-earth-600 shrink-0 mt-0.5 whitespace-nowrap">
                {relativeTime(notif.created_at)}
              </span>
            </div>
            <p className={`text-xs leading-relaxed ${notif.read ? 'text-earth-600' : 'text-earth-400'}`}>
              {notif.body}
            </p>
            <div className="mt-1.5 flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full border ${meta.bgColor} ${meta.borderColor} ${meta.iconColor}`}>
                {meta.label}
              </span>
            </div>
          </div>

          {/* Left unread border accent */}
          {!notif.read && (
            <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-blue-500 rounded-l-xl" />
          )}
        </div>
      </button>
    </motion.div>
  );
}

// ─── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ tab }: { tab: FilterTab }) {
  const labels: Record<FilterTab, string> = {
    all:         'Brak powiadomien',
    unread:      'Wszystkie przeczytane',
    alerts:      'Brak alertow przetargowych',
    competitors: 'Brak powiadomien o konkurentach',
    deadlines:   'Brak zbliżajacych sie terminow',
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col items-center justify-center py-16 gap-3"
    >
      <div className="w-14 h-14 rounded-2xl bg-earth-800/60 border border-earth-700/60 flex items-center justify-center">
        <Bell className="w-6 h-6 text-earth-600" />
      </div>
      <p className="text-sm text-earth-500 font-medium">{labels[tab]}</p>
      <p className="text-xs text-earth-700">Nowe powiadomienia pojawia sie tutaj automatycznie</p>
    </motion.div>
  );
}

// ─── Main component ────────────────────────────────────────────────────────────

export function NotificationsPage() {
  const authFetch = useAuthFetch();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading]       = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [markingAll, setMarkingAll] = useState(false);
  const [cursor, setCursor]         = useState<string | null>(null);
  const [hasMore, setHasMore]       = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [tab, setTab]               = useState<FilterTab>('all');
  const eventSourceRef              = useRef<EventSource | null>(null);

  // ── Data fetchers ───────────────────────────────────────────────────────────

  const loadNotifications = useCallback(async (replace = true) => {
    replace ? setLoading(true) : setRefreshing(true);
    try {
      const params = new URLSearchParams({ limit: '50' });
      const data: NotifPage = await authFetch(`/api/v2/notifications?${params}`);
      if (replace) {
        setNotifications(data.items ?? []);
      } else {
        setNotifications(prev => {
          const ids = new Set(prev.map(n => n.id));
          const fresh = (data.items ?? []).filter(n => !ids.has(n.id));
          return [...fresh, ...prev];
        });
      }
      setCursor(data.next_cursor ?? null);
      setHasMore(!!data.next_cursor);
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad ladowania powiadomien');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [authFetch]);

  const loadUnreadCount = useCallback(async () => {
    try {
      const data: { unread_count: number } = await authFetch('/api/v2/notifications/count');
      setUnreadCount(data.unread_count ?? 0);
    } catch {
      // silently ignore
    }
  }, [authFetch]);

  const loadMore = useCallback(async () => {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const params = new URLSearchParams({ limit: '50', cursor });
      const data: NotifPage = await authFetch(`/api/v2/notifications?${params}`);
      setNotifications(prev => [...prev, ...(data.items ?? [])]);
      setCursor(data.next_cursor ?? null);
      setHasMore(!!data.next_cursor);
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad ladowania');
    } finally {
      setLoadingMore(false);
    }
  }, [authFetch, cursor, loadingMore]);

  // ── Actions ─────────────────────────────────────────────────────────────────

  const markRead = useCallback(async (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    setUnreadCount(c => Math.max(0, c - 1));
    try {
      await authFetch(`/api/v2/notifications/${id}/read`, { method: 'POST' });
    } catch {
      // revert on error
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: false } : n));
      setUnreadCount(c => c + 1);
    }
  }, [authFetch]);

  const markAllRead = useCallback(async () => {
    if (unreadCount === 0) return;
    setMarkingAll(true);
    try {
      await authFetch('/api/v2/notifications/read-all', { method: 'POST' });
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
      showToast('success', 'Wszystkie powiadomienia oznaczone jako przeczytane');
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad oznaczania');
    } finally {
      setMarkingAll(false);
    }
  }, [authFetch, unreadCount]);

  // ── SSE connection ──────────────────────────────────────────────────────────

  useEffect(() => {
    const es = new EventSource('/api/v2/notifications/stream');
    eventSourceRef.current = es;
    es.onmessage = () => {
      loadNotifications(false);
      loadUnreadCount();
    };
    es.onerror = () => {
      // silently ignore SSE errors; auto-refresh handles recovery
    };
    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [loadNotifications, loadUnreadCount]);

  // ── Auto-refresh ────────────────────────────────────────────────────────────

  useEffect(() => {
    const timer = setInterval(() => {
      loadNotifications(false);
      loadUnreadCount();
    }, AUTO_REFRESH_MS);
    return () => clearInterval(timer);
  }, [loadNotifications, loadUnreadCount]);

  // ── Initial load ────────────────────────────────────────────────────────────

  useEffect(() => {
    loadNotifications(true);
    loadUnreadCount();
  }, [loadNotifications, loadUnreadCount]);

  // ── Filtering ───────────────────────────────────────────────────────────────

  const filtered = notifications.filter(n => {
    if (tab === 'unread') return !n.read;
    const types = FILTER_TYPES[tab];
    if (types) return types.includes(n.type);
    return true;
  });

  const grouped = groupByDate(filtered);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-earth-800/60 shrink-0">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-earth-100">Powiadomienia</h2>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-blue-500/20 border border-blue-500/30 text-blue-400 text-xs font-semibold">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => loadNotifications(true)}
              disabled={loading || refreshing}
              title="Odswiez"
              className="p-2 text-earth-600 hover:text-earth-400 transition-colors rounded-lg hover:bg-earth-800/60 disabled:opacity-40"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                disabled={markingAll}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-earth-400 hover:text-earth-200 bg-earth-800/60 hover:bg-earth-800 border border-earth-700/60 rounded-xl transition-colors disabled:opacity-40"
              >
                {markingAll
                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  : <CheckCheck className="w-3.5 h-3.5" />
                }
                Oznacz wszystkie
              </button>
            )}
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex items-center gap-1 mt-3 overflow-x-auto scrollbar-none">
          {FILTER_TABS.map(t => {
            const active = tab === t.id;
            const countBadge = t.id === 'unread' && unreadCount > 0 ? unreadCount : null;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors ${
                  active
                    ? 'bg-earth-800 text-earth-100 border border-earth-700/60'
                    : 'text-earth-500 hover:text-earth-300 hover:bg-earth-800/60'
                }`}
              >
                {t.label}
                {countBadge !== null && (
                  <span className="px-1.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 text-xs font-semibold leading-none">
                    {countBadge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {loading ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <GlassCard key={i} className="p-4 animate-pulse">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-earth-800" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3.5 bg-earth-800 rounded-lg w-2/3" />
                    <div className="h-3 bg-earth-800/60 rounded-lg w-full" />
                    <div className="h-3 bg-earth-800/60 rounded-lg w-1/2" />
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState tab={tab} />
        ) : (
          <div className="space-y-6 max-w-2xl">
            <AnimatePresence initial={false}>
              {grouped.map(group => (
                <motion.div
                  key={group.label}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  {/* Date group header */}
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-xs font-semibold text-earth-500 uppercase tracking-wide">
                      {group.label}
                    </span>
                    <div className="flex-1 h-px bg-earth-800/60" />
                    <span className="text-xs text-earth-700">{group.items.length}</span>
                  </div>

                  {/* Notification cards */}
                  <div className="space-y-2 relative">
                    <AnimatePresence initial={false}>
                      {group.items.map(n => (
                        <NotifCard key={n.id} notif={n} onRead={markRead} />
                      ))}
                    </AnimatePresence>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Load more */}
            {hasMore && (
              <div className="flex justify-center pt-2">
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="flex items-center gap-2 px-4 py-2 text-sm text-earth-400 hover:text-earth-200 bg-earth-800/60 hover:bg-earth-800 border border-earth-700/60 rounded-xl transition-colors disabled:opacity-40"
                >
                  {loadingMore ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  {loadingMore ? 'Ladowanie...' : 'Zaladuj wiecej'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
