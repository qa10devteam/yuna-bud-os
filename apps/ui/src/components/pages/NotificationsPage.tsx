'use client';
import { useEffect, useState, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';
import { motion } from 'motion/react';
import { Bell, Check, CheckCheck } from 'lucide-react';
import { useRealtime } from '@/hooks/useRealtime';

interface Notification {
  id: string;
  event_type: string;
  title: string;
  body: string;
  link?: string;
  read: boolean;
  created_at: string;
}

const EVENT_ICONS: Record<string, string> = {
  'alert.deadline': '⏰',
  'tender.new':     '📋',
  'agent.done':     '🤖',
};

const EVENT_COLORS: Record<string, string> = {
  'alert.deadline': 'border-l-warning',
  'tender.new':     'border-l-info',
  'agent.done':     'border-l-success',
};

export function NotificationsPage() {
  const authFetch = useAuthFetch();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  // SSE: live notifications
  useRealtime({
    eventTypes: ['alert.deadline', 'tender.new', 'agent.done'],
    onEvent: () => fetchNotifs(),
  });

  const fetchNotifs = useCallback(async () => {
    try {
      const data = await authFetch(`/api/v2/notifications?limit=50&unread_only=${filter === 'unread'}`);
      setNotifications(Array.isArray(data) ? data : []);
    } catch {}
  }, [authFetch, filter]);

  useEffect(() => { fetchNotifs(); }, [fetchNotifs]);

  const markAllRead = async () => {
    await authFetch('/api/v2/notifications/mark-read', { method: 'POST', body: JSON.stringify([]) });
    fetchNotifs();
  };

  const markRead = async (id: string) => {
    await authFetch('/api/v2/notifications/mark-read', { method: 'POST', body: JSON.stringify([id]) });
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  const actions = (
    <div className="flex items-center gap-2">
      <div className="flex gap-1 bg-earth-900/60 rounded-token-lg p-1">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded-token text-xs font-medium transition-colors ${filter === 'all' ? 'bg-accent-primary text-earth-950' : 'text-earth-400 hover:text-earth-200'}`}
        >Wszystkie</button>
        <button
          onClick={() => setFilter('unread')}
          className={`px-3 py-1 rounded-token text-xs font-medium transition-colors ${filter === 'unread' ? 'bg-accent-primary text-earth-950' : 'text-earth-400 hover:text-earth-200'}`}
        >Nieprzeczytane</button>
      </div>
      {unreadCount > 0 && (
        <button onClick={markAllRead} className="btn-ghost flex items-center gap-1 text-xs px-3 py-1.5">
          <CheckCheck size={14} /> Oznacz wszystkie
        </button>
      )}
    </div>
  );

  return (
    <PageShell
      title="Centrum Powiadomień"
      subtitle={`${unreadCount} nieprzeczytanych`}
      actions={actions}
    >
      <div className="space-y-2">
        {notifications.map((n, i) => (
          <motion.div
            key={n.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.03 }}
            className={`border-l-4 rounded-r-token-lg ${EVENT_COLORS[n.event_type] || 'border-l-earth-600'} ${
              n.read ? 'opacity-60' : ''
            }`}
          >
            <div className="flex items-start gap-3 p-3 bg-earth-900/40 hover:bg-earth-800/50 transition-colors rounded-r-token-lg">
              <span className="text-lg mt-0.5">{EVENT_ICONS[n.event_type] || '📌'}</span>
              <div className="flex-1 min-w-0">
                <div className="text-earth-200 text-sm font-medium">{n.title}</div>
                {n.body && <div className="text-earth-400 text-xs mt-0.5">{n.body}</div>}
                <div className="text-earth-600 text-xs mt-1">
                  {new Date(n.created_at).toLocaleString('pl-PL')}
                </div>
              </div>
              {!n.read && (
                <button
                  onClick={() => markRead(n.id)}
                  className="text-earth-500 hover:text-success p-1 transition-colors"
                  aria-label="Oznacz jako przeczytane"
                >
                  <Check size={14} />
                </button>
              )}
            </div>
          </motion.div>
        ))}
        {notifications.length === 0 && (
          <GlassCard className="p-8 text-center">
            <Bell size={32} className="mx-auto text-earth-600 mb-2" />
            <p className="text-earth-400 text-sm">Brak powiadomień</p>
          </GlassCard>
        )}
      </div>
    </PageShell>
  );
}
