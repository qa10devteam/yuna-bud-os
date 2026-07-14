'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonCard } from '@/components/ui/SkeletonLoader';
import { PageShell } from '@/components/PageShell';
import { showToast } from '@/components/Toast';
import { motion, AnimatePresence } from 'motion/react';
import { Bell, Check, CheckCheck, RefreshCw, AlertCircle } from 'lucide-react';
import { useRealtime } from '@/hooks/useRealtime';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Notification {
  id: string;
  event_type: string;
  title: string;
  body: string;
  link?: string;
  read: boolean;
  created_at: string;
}

// ── Config ────────────────────────────────────────────────────────────────────

const EVENT_ICONS: Record<string, string> = {
  'alert.deadline': '⏰',
  'tender.new':     '📋',
  'agent.done':     '🤖',
  'alert.match':    '🎯',
  'system':         '⚙️',
};

const EVENT_COLORS: Record<string, string> = {
  'alert.deadline': 'border-l-accent-warning',
  'tender.new':     'border-l-accent-info',
  'agent.done':     'border-l-accent-primary',
  'alert.match':    'border-l-accent-primary',
};

// ── Notification item ─────────────────────────────────────────────────────────

function NotificationItem({
  notification,
  onMarkRead,
  index,
}: {
  notification: Notification;
  onMarkRead: (id: string) => void;
  index: number;
}) {
  const colorClass = EVENT_COLORS[notification.event_type] || 'border-l-earth-600';
  const icon = EVENT_ICONS[notification.event_type] || '📌';

  return (
    <motion.div
      key={notification.id}
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ delay: index * 0.03 }}
      className={`border-l-4 rounded-r-token-lg ${colorClass} ${notification.read ? 'opacity-60' : ''}`}
    >
      <div className="flex items-start gap-3 p-4 bg-earth-900/40 hover:bg-earth-800/50 transition-colors rounded-r-token-lg">
        <span className="text-lg mt-0.5 shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="text-earth-200 text-sm font-medium leading-snug">{notification.title}</div>
          {notification.body && (
            <div className="text-earth-400 text-xs mt-0.5 line-clamp-2">{notification.body}</div>
          )}
          <div className="text-earth-600 text-xs mt-1.5">
            {new Date(notification.created_at).toLocaleString('pl-PL')}
          </div>
        </div>
        {!notification.read && (
          <button
            onClick={() => onMarkRead(notification.id)}
            className="text-earth-500 hover:text-accent-primary p-1 transition-colors shrink-0"
            aria-label="Oznacz jako przeczytane"
            title="Oznacz jako przeczytane"
          >
            <Check className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </motion.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function NotificationsPage() {
  const authFetch = useAuthFetch();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const [unreadCount, setUnreadCount] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // SSE: live notifications
  useRealtime({
    eventTypes: ['alert.deadline', 'tender.new', 'agent.done', 'alert.match'],
    onEvent: () => fetchNotifs(),
  });

  const fetchUnreadCount = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/notifications/unread-count') as { count: number } | number;
      const count = typeof data === 'number' ? data : (data?.count ?? 0);
      setUnreadCount(count);
    } catch {
      // non-critical
    }
  }, [authFetch]);

  const fetchNotifs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `/api/v2/notifications?limit=50${filter === 'unread' ? '&unread_only=true' : ''}`;
      const data = await authFetch(url) as Notification[] | { items: Notification[] };
      const items = Array.isArray(data) ? data : (data?.items ?? []);
      setNotifications(items);
      // Update unread badge
      const unread = items.filter((n: Notification) => !n.read).length;
      if (filter === 'all') setUnreadCount(unread);
    } catch (e: unknown) {
      setError((e as Error).message || 'Błąd ładowania powiadomień');
    } finally {
      setLoading(false);
    }
  }, [authFetch, filter]);

  // Load on mount and filter change
  useEffect(() => { fetchNotifs(); }, [fetchNotifs]);

  // Poll unread count every 30s
  useEffect(() => {
    fetchUnreadCount();
    pollRef.current = setInterval(fetchUnreadCount, 30_000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchUnreadCount]);

  const markAllRead = async () => {
    try {
      await authFetch('/api/v2/notifications/read-all', { method: 'POST' });
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
      showToast('success', 'Wszystkie oznaczone jako przeczytane');
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd');
    }
  };

  const markRead = async (id: string) => {
    try {
      await authFetch(`/api/v2/notifications/${id}/read`, { method: 'POST' });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {
      // silent fail — optimistic already done
    }
  };

  const displayed = filter === 'unread'
    ? notifications.filter(n => !n.read)
    : notifications;

  const actions = (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Filter tabs */}
      <div className="flex gap-1 bg-earth-900/60 rounded-token-lg p-1 border border-earth-800/50">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded-token text-xs font-medium transition-colors ${filter === 'all' ? 'bg-accent-primary text-earth-950' : 'text-earth-400 hover:text-earth-200'}`}
        >
          Wszystkie
        </button>
        <button
          onClick={() => setFilter('unread')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-token text-xs font-medium transition-colors ${filter === 'unread' ? 'bg-accent-primary text-earth-950' : 'text-earth-400 hover:text-earth-200'}`}
        >
          Nieprzeczytane
          {unreadCount > 0 && (
            <span className={`text-[10px] font-bold px-1 py-0.5 rounded-full ${filter === 'unread' ? 'bg-earth-900 text-accent-primary' : 'bg-accent-danger text-earth-50'}`}>
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </button>
      </div>

      {unreadCount > 0 && (
        <Button variant="ghost" size="sm" iconLeft={<CheckCheck className="w-3.5 h-3.5" />} onClick={markAllRead}>
          Oznacz wszystkie
        </Button>
      )}
      <Button variant="secondary" size="sm" iconLeft={<RefreshCw className="w-3.5 h-3.5" />} onClick={fetchNotifs} loading={loading}>
        Odśwież
      </Button>
    </div>
  );

  return (
    <PageShell
      title="Centrum Powiadomień"
      subtitle={loading ? 'Ładowanie…' : `${unreadCount} nieprzeczytanych`}
      actions={actions}
    >
      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <GlassCard className="p-8">
          <EmptyState
            icon={<AlertCircle className="w-6 h-6" />}
            title="Błąd ładowania powiadomień"
            description={error}
            cta={
              <Button variant="secondary" size="sm" onClick={fetchNotifs} iconLeft={<RefreshCw className="w-3.5 h-3.5" />}>
                Spróbuj ponownie
              </Button>
            }
          />
        </GlassCard>
      )}

      {/* Empty state */}
      {!loading && !error && displayed.length === 0 && (
        <GlassCard className="p-8">
          <EmptyState
            icon={<Bell className="w-6 h-6" />}
            title={filter === 'unread' ? 'Brak nieprzeczytanych powiadomień' : 'Brak powiadomień'}
            description={filter === 'unread' ? 'Wszystkie powiadomienia zostały przeczytane.' : 'Nowe powiadomienia pojawią się tutaj.'}
          />
        </GlassCard>
      )}

      {/* Notification list */}
      {!loading && !error && displayed.length > 0 && (
        <div className="space-y-2">
          <AnimatePresence mode="popLayout">
            {displayed.map((n, i) => (
              <NotificationItem
                key={n.id}
                notification={n}
                onMarkRead={markRead}
                index={i}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </PageShell>
  );
}
