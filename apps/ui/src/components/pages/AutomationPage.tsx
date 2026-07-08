import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Zap, Send, CheckCircle, AlertTriangle, Clock, Search,
  FileText, TrendingDown, Bell, Settings, Plus, Trash2,
  ExternalLink, Activity, ToggleLeft, ToggleRight
} from 'lucide-react';

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

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-50 border-red-200 text-red-800 hover:bg-red-100',
  high: 'bg-amber-50 border-amber-200 text-amber-800 hover:bg-amber-100',
  medium: 'bg-blue-50 border-blue-200 text-blue-800 hover:bg-blue-100',
  low: 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100',
};

// ─── Simply-Clever Action Button ─────────────────────────────────────────────

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
        w-full flex items-center gap-3 px-4 py-3 rounded-lg border
        transition-all duration-200 text-left
        ${PRIORITY_COLORS[suggestion.priority]}
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

// ─── Smart Suggestions Panel ─────────────────────────────────────────────────

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
  }, [entityType, entityId]);

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
      <div className="flex items-center gap-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
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
              <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
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

// ─── Webhook Manager (Settings page) ─────────────────────────────────────────

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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Webhooki n8n
        </h3>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="text-xs px-3 py-1.5 rounded-md bg-indigo-50 text-indigo-600 hover:bg-indigo-100 flex items-center gap-1"
        >
          <Plus className="w-3 h-3" /> Dodaj
        </button>
      </div>

      {showAdd && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="p-3 rounded-lg border border-indigo-100 bg-indigo-50/50 space-y-2"
        >
          <input
            value={newName}
            onChange={e => setNewName(e.target.value)}
            placeholder="Nazwa (np. 'n8n — powiadomienia')"
            className="w-full px-3 py-2 text-sm rounded border border-gray-200 focus:border-indigo-300 focus:ring-1 focus:ring-indigo-200"
          />
          <input
            value={newUrl}
            onChange={e => setNewUrl(e.target.value)}
            placeholder="URL webhook (np. http://localhost:5678/webhook/...)"
            className="w-full px-3 py-2 text-sm rounded border border-gray-200 focus:border-indigo-300 focus:ring-1 focus:ring-indigo-200"
          />
          <div className="flex gap-2">
            <button onClick={addWebhook} className="px-3 py-1.5 text-xs rounded bg-indigo-600 text-white hover:bg-indigo-700">
              Zapisz
            </button>
            <button onClick={() => setShowAdd(false)} className="px-3 py-1.5 text-xs rounded text-gray-500 hover:text-gray-700">
              Anuluj
            </button>
          </div>
        </motion.div>
      )}

      <div className="space-y-2">
        {webhooks.map(wh => (
          <div key={wh.id} className="flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-100 bg-white">
            <button onClick={() => toggleWebhook(wh.id, wh.active)}>
              {wh.active ? (
                <ToggleRight className="w-5 h-5 text-green-500" />
              ) : (
                <ToggleLeft className="w-5 h-5 text-gray-300" />
              )}
            </button>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-800 truncate">{wh.name}</div>
              <div className="text-xs text-gray-400 truncate">{wh.url}</div>
            </div>
            <a href={wh.url} target="_blank" rel="noopener" className="text-gray-300 hover:text-gray-500">
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <button onClick={() => deleteWebhook(wh.id)} className="text-gray-300 hover:text-red-500">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
        {!webhooks.length && (
          <div className="text-center py-6 text-sm text-gray-400">
            <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
            Brak webhooków. Dodaj URL n8n aby aktywować automatyzacje.
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Event History (Activity Feed) ───────────────────────────────────────────

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
  }, []);

  if (!events.length) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
        <Activity className="w-3 h-3" />
        <span>Historia automatyzacji</span>
      </div>
      <div className="space-y-1">
        {events.map(ev => (
          <div key={ev.id} className="flex items-center gap-2 text-xs py-1.5 px-2 rounded hover:bg-gray-50">
            <div className={`w-1.5 h-1.5 rounded-full ${
              ev.status === 'delivered' ? 'bg-green-400' :
              ev.status === 'failed' ? 'bg-red-400' : 'bg-yellow-400'
            }`} />
            <span className="font-mono text-gray-600">{ev.event}</span>
            <span className="text-gray-300">|</span>
            <span className="text-gray-400 truncate">
              {new Date(ev.triggered_at).toLocaleString('pl-PL', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })}
            </span>
            {ev.response_code > 0 && (
              <span className={`ml-auto font-mono ${ev.response_code < 300 ? 'text-green-500' : 'text-red-500'}`}>
                {ev.response_code}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
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
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Zap className="w-6 h-6 text-indigo-500" />
          Automatyzacje
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Podepnij n8n i uruchamiaj akcje jednym klikiem. Zero konfiguracji, maximum efekt.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <WebhookManager authFetch={authFetch} />
        </div>
        <div className="space-y-6">
          <AutomationHistory authFetch={authFetch} />
        </div>
      </div>
    </div>
  );
}
