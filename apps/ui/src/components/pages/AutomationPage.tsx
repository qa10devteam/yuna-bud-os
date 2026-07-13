'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Zap, Send, CheckCircle, AlertTriangle, Clock, Search,
  FileText, TrendingDown, Bell, Settings, Plus, Trash2,
  ExternalLink, Activity, ToggleLeft, ToggleRight
} from 'lucide-react';
import { PageShell } from '@/components/PageShell';
import { GlassCard } from '@/components/ui/GlassCard';
import { StatusBadge } from '@/components/ui/StatusBadge';

interface Suggestion {
  event: string;
  label: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  icon: string;
}

interface WebhookItem {
  id: string;
  name: string;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
}

interface EventLogItem {
  id: string;
  event: string;
  entity_id: string;
  triggered_by: string;
  triggered_at: string;
  status: string;
  response_code: number;
}

const ICON_MAP: Record<string, React.ReactNode> = {
  'send': <Send className="w-4 h-4" />,
  'check-circle': <CheckCircle className="w-4 h-4" />,
  'alert-triangle': <AlertTriangle className="w-4 h-4" />,
  'clock': <Clock className="w-4 h-4" />,
  'search': <Search className="w-4 h-4" />,
  'file-plus': <FileText className="w-4 h-4" />,
  'trending-down': <TrendingDown className="w-4 h-4" />,
};

const PRIORITY_TOKEN: Record<string, string> = {
  critical: 'bg-accent-danger/15 border border-accent-danger/30 text-accent-danger hover:bg-accent-danger/25',
  high:     'bg-accent-warning/15 border border-accent-warning/30 text-accent-warning hover:bg-accent-warning/25',
  medium:   'bg-accent-info/15 border border-accent-info/30 text-accent-info hover:bg-accent-info/25',
  low:      'bg-earth-800/60 border border-earth-700/40 text-earth-400 hover:bg-earth-800',
};

// ─── Action Button ────────────────────────────────────────────────────────────

function ActionButton({
  suggestion,
  onTrigger,
  loading,
}: {
  suggestion: Suggestion;
  onTrigger: () => void;
  loading: boolean;
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onTrigger}
      disabled={loading}
      className={`
        w-full flex items-center gap-3 px-4 py-3 rounded-token transition-all duration-200 text-left
        ${PRIORITY_TOKEN[suggestion.priority]}
        ${loading ? 'opacity-50 cursor-wait' : 'cursor-pointer'}
      `}
    >
      <div className="flex-shrink-0">
        {ICON_MAP[suggestion.icon] || <Zap className="w-4 h-4" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm">{suggestion.label}</div>
        <div className="text-xs opacity-75 truncate">{suggestion.description}</div>
      </div>
      {loading && (
        <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
      )}
    </motion.button>
  );
}

// ─── Smart Suggestions Panel ──────────────────────────────────────────────────

export function AutomationSuggestions({
  entityType,
  entityId,
  authFetch,
}: {
  entityType: 'kosztorys' | 'tender';
  entityId: string;
  authFetch: (url: string, opts?: RequestInit) => Promise<Response>;
}) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const [triggered, setTriggered] = useState<string[]>([]);

  useEffect(() => {
    authFetch(`/api/v2/automations/suggestions/${entityType}/${entityId}`)
      .then(r => r.json())
      .then(setSuggestions)
      .catch(() => {});
  }, [entityType, entityId, authFetch]);

  const handleTrigger = async (suggestion: Suggestion) => {
    setLoading(suggestion.event);
    try {
      await authFetch('/api/v2/automations/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: suggestion.event,
          entity_id: entityId,
          payload: {},
        }),
      });
      setTriggered(prev => [...prev, suggestion.event]);
    } catch (e) {
      console.error('Trigger failed:', e);
    } finally {
      setLoading(null);
    }
  };

  if (!suggestions.length) return null;

  return (
    <div className="space-y-2">
      <div className="section-label flex items-center gap-2">
        <Zap className="w-3 h-3" />
        <span>Akcje</span>
      </div>
      <AnimatePresence>
        {suggestions.map((s) => (
          <motion.div
            key={s.event}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: -20 }}
          >
            {triggered.includes(s.event) ? (
              <div className="flex items-center gap-2 px-4 py-3 rounded-token bg-accent-primary/10 border border-accent-primary/20 text-accent-primary text-sm">
                <CheckCircle className="w-4 h-4" />
                <span>{s.label} — wysłano!</span>
              </div>
            ) : (
              <ActionButton
                suggestion={s}
                onTrigger={() => handleTrigger(s)}
                loading={loading === s.event}
              />
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

// ─── Webhook Manager ──────────────────────────────────────────────────────────

export function WebhookManager({
  authFetch,
}: {
  authFetch: (url: string, opts?: RequestInit) => Promise<Response>;
}) {
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState('');
  const [newUrl, setNewUrl] = useState('');

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadWebhooks = () => {
    authFetch('/api/v2/automations/webhooks')
      .then(r => r.json())
      .then(setWebhooks)
      .catch(() => {});
  };

  const addWebhook = async () => {
    if (!newName || !newUrl) return;
    await authFetch('/api/v2/automations/webhooks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName, url: newUrl, events: [] }),
    });
    setNewName('');
    setNewUrl('');
    setShowAdd(false);
    loadWebhooks();
  };

  const toggleWebhook = async (wid: string, active: boolean) => {
    await authFetch(`/api/v2/automations/webhooks/${wid}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: !active }),
    });
    loadWebhooks();
  };

  const deleteWebhook = async (wid: string) => {
    await authFetch(`/api/v2/automations/webhooks/${wid}`, { method: 'DELETE' });
    loadWebhooks();
  };

  return (
    <GlassCard className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-earth-200 flex items-center gap-2">
          <Settings className="w-4 h-4 text-earth-500" />
          Webhooki n8n
        </h3>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="btn-ghost flex items-center gap-1 text-xs px-3 py-1.5"
        >
          <Plus className="w-3 h-3" /> Dodaj
        </button>
      </div>

      {showAdd && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="p-3 rounded-token-lg border border-earth-700/40 bg-earth-800/30 space-y-2"
        >
          <input
            value={newName}
            onChange={e => setNewName(e.target.value)}
            placeholder="Nazwa (np. 'n8n — powiadomienia')"
            className="input-base w-full text-sm"
          />
          <input
            value={newUrl}
            onChange={e => setNewUrl(e.target.value)}
            placeholder="URL webhook (np. http://localhost:5678/webhook/...)"
            className="input-base w-full text-sm"
          />
          <div className="flex gap-2">
            <button onClick={addWebhook} className="btn-primary px-3 py-1.5 text-xs">
              Zapisz
            </button>
            <button onClick={() => setShowAdd(false)} className="btn-ghost px-3 py-1.5 text-xs">
              Anuluj
            </button>
          </div>
        </motion.div>
      )}

      <div className="space-y-2">
        {webhooks.map(wh => (
          <div key={wh.id} className="flex items-center gap-3 px-3 py-2 rounded-token border border-earth-800/60 bg-earth-900/40">
            <button onClick={() => toggleWebhook(wh.id, wh.active)}>
              {wh.active ? (
                <ToggleRight className="w-5 h-5 text-accent-primary" />
              ) : (
                <ToggleLeft className="w-5 h-5 text-earth-600" />
              )}
            </button>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-earth-200 truncate">{wh.name}</div>
              <div className="text-xs text-earth-500 truncate">{wh.url}</div>
            </div>
            <a href={wh.url} target="_blank" rel="noopener" className="text-earth-600 hover:text-earth-400 transition-colors">
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <button onClick={() => deleteWebhook(wh.id)} className="text-earth-600 hover:text-accent-danger transition-colors">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
        {!webhooks.length && (
          <div className="text-center py-6 text-sm text-earth-500">
            <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
            Brak webhooków. Dodaj URL n8n aby aktywować automatyzacje.
          </div>
        )}
      </div>
    </GlassCard>
  );
}

// ─── Event History ────────────────────────────────────────────────────────────

export function AutomationHistory({
  authFetch,
}: {
  authFetch: (url: string, opts?: RequestInit) => Promise<Response>;
}) {
  const [events, setEvents] = useState<EventLogItem[]>([]);

  useEffect(() => {
    authFetch('/api/v2/automations/history?limit=10')
      .then(r => r.json())
      .then(setEvents)
      .catch(() => {});
  }, [authFetch]);

  if (!events.length) return null;

  return (
    <GlassCard className="p-4 space-y-3">
      <div className="section-label flex items-center gap-2">
        <Activity className="w-3 h-3" />
        <span>Historia automatyzacji</span>
      </div>
      <div className="space-y-1">
        {events.map(ev => (
          <div key={ev.id} className="flex items-center gap-2 text-xs py-1.5 px-2 rounded-token hover:bg-earth-800/40 transition-colors">
            <div className={`w-1.5 h-1.5 rounded-full ${
              ev.status === 'delivered' ? 'bg-accent-primary' :
              ev.status === 'failed' ? 'bg-accent-danger' : 'bg-accent-warning'
            }`} />
            <span className="font-mono text-earth-400">{ev.event}</span>
            <span className="text-earth-700">|</span>
            <span className="text-earth-500 truncate">
              {new Date(ev.triggered_at).toLocaleString('pl-PL', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })}
            </span>
            {ev.response_code > 0 && (
              <span className={`ml-auto font-mono ${ev.response_code < 300 ? 'text-accent-primary' : 'text-accent-danger'}`}>
                {ev.response_code}
              </span>
            )}
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

// ─── N8n Status Panel ─────────────────────────────────────────────────────────

interface N8nWorkflow {
  id: string;
  name: string;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

export function N8nStatusPanel({ authFetch }: { authFetch: (url: string, opts?: RequestInit) => Promise<Response> }) {
  const [status, setStatus] = useState<{ healthy: boolean; version?: string; workflow_count?: number } | null>(null);
  const [workflows, setWorkflows] = useState<N8nWorkflow[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    authFetch('/api/v2/automations/n8n/status')
      .then(r => r.json())
      .then(data => setStatus(data?.n8n || data))
      .catch(() => setStatus({ healthy: false }));
    authFetch('/api/v2/automations/n8n/workflows')
      .then(r => r.json())
      .then(data => setWorkflows(Array.isArray(data?.workflows) ? data.workflows : []))
      .catch(() => {});
  }, [authFetch]);

  return (
    <GlassCard className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 font-semibold text-earth-100 text-sm">
          <Activity className="w-4 h-4 text-accent-violet" />
          <span>n8n Engine</span>
          {status && (
            <StatusBadge
              status={status.healthy ? 'success' : 'danger'}
              label={status.healthy ? `v${status.version || '?'} — aktywny` : 'niedostępny'}
            />
          )}
        </div>
        {status && (
          <div className={`w-2 h-2 rounded-full ${status.healthy ? 'bg-accent-primary shadow-glow' : 'bg-accent-danger'}`} />
        )}
      </div>

      <div className="flex items-center gap-4 text-xs text-earth-500 mb-3">
        <span>Workflows: <strong className="text-earth-300">{status?.workflow_count ?? workflows.length}</strong></span>
        <span>Aktywne: <strong className="text-earth-300">{workflows.filter(w => w.active).length}</strong></span>
        <button
          onClick={() => setExpanded(v => !v)}
          className="btn-ghost ml-auto flex items-center gap-1 text-xs px-2 py-1"
        >
          <Settings className="w-3 h-3" />
          {expanded ? 'Ukryj' : 'Szczegóły'}
        </button>
      </div>

      {expanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="space-y-2 mt-2"
        >
          {workflows.length === 0 ? (
            <p className="text-xs text-earth-600 italic">Brak wdrożonych workflow.</p>
          ) : (
            workflows.map(wf => (
              <div key={wf.id} className="flex items-center gap-2 text-xs bg-earth-800/40 rounded-token px-3 py-2">
                {wf.active
                  ? <ToggleRight className="w-4 h-4 text-accent-primary flex-shrink-0" />
                  : <ToggleLeft className="w-4 h-4 text-earth-600 flex-shrink-0" />
                }
                <span className="flex-1 truncate text-earth-300">{wf.name}</span>
                <span className="text-earth-600 font-mono">{wf.id.substring(0, 8)}</span>
              </div>
            ))
          )}
          <a
            href="http://localhost:5678"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-accent-violet hover:underline mt-1"
          >
            <ExternalLink className="w-3 h-3" />
            Otwórz n8n UI
          </a>
        </motion.div>
      )}
    </GlassCard>
  );
}

// ─── Full Automation Page ────────────────────────────────────────────────────

export default function AutomationPage() {
  const authFetch = async (url: string, opts?: RequestInit) => {
    const token = localStorage.getItem('token');
    return fetch(url, {
      ...opts,
      headers: { ...opts?.headers, Authorization: `Bearer ${token}` },
    });
  };

  return (
    <PageShell
      title="Automatyzacja"
      subtitle="Reguły i workflow AI"
      actions={
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-token bg-accent-violet/10 border border-accent-violet/20 text-accent-violet text-xs font-medium">
          <Zap className="w-3.5 h-3.5" />
          n8n połączony
        </div>
      }
    >
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <N8nStatusPanel authFetch={authFetch} />
          <WebhookManager authFetch={authFetch} />
        </div>
        <div className="space-y-6">
          <AutomationHistory authFetch={authFetch} />
        </div>
      </div>
    </PageShell>
  );
}
