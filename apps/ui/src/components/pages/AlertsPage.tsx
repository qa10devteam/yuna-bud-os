'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { PageShell } from '@/components/PageShell';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonCard } from '@/components/ui/SkeletonLoader';
import { showToast } from '@/components/Toast';
import { motion, AnimatePresence } from 'motion/react';
import {
  Plus, Bell, Trash2, RefreshCw, Play, AlertCircle,
  CheckCircle2, XCircle, Clock, Tag, Mail, Webhook,
} from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────

interface TenderAlert {
  id: string;
  name: string;
  cpv_prefixes: string[];
  keywords: string[];
  frequency: 'realtime' | 'daily' | 'weekly';
  channel: 'push' | 'email' | 'webhook';
  is_active: boolean;
  match_count: number;
  last_matched_at: string | null;
  webhook_url?: string | null;
  created_at: string;
}

interface AlertTestResult {
  matched: number;
  sample: { id: string; title: string; value_pln: number | null }[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(s: string | null): string {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('pl-PL', { day: '2-digit', month: 'short', year: 'numeric' });
}

const FREQ_LABELS: Record<string, string> = {
  realtime: 'Natychmiast',
  daily: 'Codziennie',
  weekly: 'Co tydzień',
};

const CHANNEL_ICONS: Record<string, React.ReactNode> = {
  email: <Mail className="w-3.5 h-3.5" />,
  webhook: <Webhook className="w-3.5 h-3.5" />,
  push: <Bell className="w-3.5 h-3.5" />,
};

// ── Create form ───────────────────────────────────────────────────────────────

interface CreateFormState {
  name: string;
  cpv: string;
  keyword: string;
  cpv_prefixes: string[];
  keywords: string[];
  frequency: 'realtime' | 'daily' | 'weekly';
  channel: 'push' | 'email' | 'webhook';
  webhook_url: string;
  value_min: string;
  value_max: string;
}

const EMPTY_FORM: CreateFormState = {
  name: '', cpv: '', keyword: '',
  cpv_prefixes: [], keywords: [],
  frequency: 'daily', channel: 'push',
  webhook_url: '', value_min: '', value_max: '',
};

function CreateAlertModal({
  onClose, onCreate,
}: {
  onClose: () => void;
  onCreate: (form: CreateFormState) => Promise<void>;
}) {
  const [form, setForm] = useState<CreateFormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const addCpv = () => {
    const v = form.cpv.trim();
    if (v && !form.cpv_prefixes.includes(v)) {
      setForm(f => ({ ...f, cpv_prefixes: [...f.cpv_prefixes, v], cpv: '' }));
    }
  };

  const addKeyword = () => {
    const v = form.keyword.trim();
    if (v && !form.keywords.includes(v)) {
      setForm(f => ({ ...f, keywords: [...f.keywords, v], keyword: '' }));
    }
  };

  const handleSubmit = async () => {
    if (!form.name.trim()) { showToast('error', 'Wpisz nazwę alertu'); return; }
    setSaving(true);
    try {
      await onCreate(form);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ scale: 0.95, y: 12 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 8 }}
        className="bg-ink-900 border border-ink-700/60 rounded-2xl w-full max-w-md p-6 shadow-xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Bell className="w-4 h-4 text-em" /> Nowy Alert
          </h3>
          <button type="button" onClick={onClose} className="text-slate-600 hover:text-slate-300 transition-colors">
            <XCircle className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-xs text-slate-500 mb-1.5 font-medium">Nazwa alertu *</label>
            <input
              className="input-base w-full"
              placeholder="np. Drogi Mazowsze 2025"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            />
          </div>

          {/* CPV */}
          <div>
            <label className="block text-xs text-slate-500 mb-1.5 font-medium">Prefiksy CPV</label>
            <div className="flex gap-2">
              <input
                className="input-base flex-1"
                placeholder="np. 4523"
                value={form.cpv}
                onChange={e => setForm(f => ({ ...f, cpv: e.target.value }))}
                onKeyDown={e => e.key === 'Enter' && addCpv()}
              />
              <button type="button" onClick={addCpv} className="px-3 bg-ink-700 rounded-lg text-slate-300 hover:bg-ink-600 text-sm transition-colors">+</button>
            </div>
            {form.cpv_prefixes.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {form.cpv_prefixes.map(c => (
                  <span key={c} className="flex items-center gap-1 text-xs bg-indigo/15 text-indigo border border-indigo/20 px-2 py-0.5 rounded-full">
                    {c}
                    <button type="button" onClick={() => setForm(f => ({ ...f, cpv_prefixes: f.cpv_prefixes.filter(x => x !== c) }))} className="hover:text-nogo"><XCircle className="w-2.5 h-2.5" /></button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Keywords */}
          <div>
            <label className="block text-xs text-slate-500 mb-1.5 font-medium">Słowa kluczowe</label>
            <div className="flex gap-2">
              <input
                className="input-base flex-1"
                placeholder="np. remont, kanalizacja"
                value={form.keyword}
                onChange={e => setForm(f => ({ ...f, keyword: e.target.value }))}
                onKeyDown={e => e.key === 'Enter' && addKeyword()}
              />
              <button type="button" onClick={addKeyword} className="px-3 bg-ink-700 rounded-lg text-slate-300 hover:bg-ink-600 text-sm transition-colors">+</button>
            </div>
            {form.keywords.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {form.keywords.map(k => (
                  <span key={k} className="flex items-center gap-1 text-xs bg-em/15 text-em border border-em/20 px-2 py-0.5 rounded-full">
                    {k}
                    <button type="button" onClick={() => setForm(f => ({ ...f, keywords: f.keywords.filter(x => x !== k) }))} className="hover:text-nogo"><XCircle className="w-2.5 h-2.5" /></button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Frequency + channel */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1.5 font-medium">Częstość</label>
              <select className="input-base w-full" value={form.frequency} onChange={e => setForm(f => ({ ...f, frequency: e.target.value as CreateFormState['frequency'] }))}>
                <option value="realtime">Natychmiast</option>
                <option value="daily">Codziennie</option>
                <option value="weekly">Co tydzień</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1.5 font-medium">Kanał</label>
              <select className="input-base w-full" value={form.channel} onChange={e => setForm(f => ({ ...f, channel: e.target.value as CreateFormState['channel'] }))}>
                <option value="push">W aplikacji</option>
                <option value="email">Email</option>
                <option value="webhook">Webhook</option>
              </select>
            </div>
          </div>

          {/* Value range */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1.5 font-medium">Wartość min (PLN)</label>
              <input type="number" className="input-base w-full" placeholder="0" value={form.value_min} onChange={e => setForm(f => ({ ...f, value_min: e.target.value }))} />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1.5 font-medium">Wartość max (PLN)</label>
              <input type="number" className="input-base w-full" placeholder="∞" value={form.value_max} onChange={e => setForm(f => ({ ...f, value_max: e.target.value }))} />
            </div>
          </div>

          {/* Webhook URL */}
          {form.channel === 'webhook' && (
            <div>
              <label className="block text-xs text-slate-500 mb-1.5 font-medium">Webhook URL</label>
              <input type="url" className="input-base w-full" placeholder="https://…" value={form.webhook_url} onChange={e => setForm(f => ({ ...f, webhook_url: e.target.value }))} />
            </div>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <Button variant="secondary" fullWidth onClick={onClose}>Anuluj</Button>
          <Button variant="primary" fullWidth loading={saving} onClick={handleSubmit} iconLeft={<Bell className="w-3.5 h-3.5" />}>
            Utwórz alert
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Alert card ────────────────────────────────────────────────────────────────

function AlertCard({
  alert, onToggle, onDelete, onTest,
}: {
  alert: TenderAlert;
  onToggle: (id: string, current: boolean) => void;
  onDelete: (id: string) => void;
  onTest: (id: string) => void;
}) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AlertTestResult | null>(null);

  const handleTest = async () => {
    setTesting(true);
    try {
      await onTest(alert.id);
    } finally {
      setTesting(false);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      className={`p-5 rounded-xl border transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
        alert.is_active
          ? 'bg-ink-900/50 border-ink-700/50 hover:border-ink-600/60'
          : 'bg-ink-900/30 border-ink-800/40 opacity-70'
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Name + status */}
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-slate-100">{alert.name}</h3>
            {!alert.is_active && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-ink-800 text-slate-500 border border-ink-700">Wstrzymany</span>
            )}
          </div>

          {/* Tags: CPV + keywords */}
          {(alert.cpv_prefixes.length > 0 || alert.keywords.length > 0) && (
            <div className="flex flex-wrap gap-1 mt-2">
              {alert.cpv_prefixes.map(c => (
                <span key={c} className="flex items-center gap-1 text-[10px] bg-indigo/10 text-indigo border border-indigo/20 px-1.5 py-0.5 rounded">
                  <Tag className="w-2.5 h-2.5" /> CPV: {c}
                </span>
              ))}
              {alert.keywords.map(k => (
                <span key={k} className="text-[10px] bg-em/10 text-em border border-em/20 px-1.5 py-0.5 rounded">
                  &ldquo;{k}&rdquo;
                </span>
              ))}
            </div>
          )}

          {/* Meta row */}
          <div className="flex items-center gap-3 mt-2 flex-wrap text-xs text-slate-500">
            <span className="flex items-center gap-1">
              {CHANNEL_ICONS[alert.channel] ?? <Bell className="w-3.5 h-3.5" />}
              {alert.channel}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {FREQ_LABELS[alert.frequency] ?? alert.frequency}
            </span>
            {alert.match_count > 0 && (
              <span className="flex items-center gap-1 text-warn">
                <CheckCircle2 className="w-3 h-3" />
                {alert.match_count} dopasowań
              </span>
            )}
            {alert.last_matched_at && (
              <span className="text-slate-600">Ostatnio: {fmtDate(alert.last_matched_at)}</span>
            )}
          </div>

          {/* Test result */}
          {testResult && (
            <div className="mt-2 p-2 rounded-md bg-em/10 border border-em/20 text-xs text-em">
              Znaleziono {testResult.matched} dopasowań
              {testResult.sample.length > 0 && (
                <ul className="mt-1 text-slate-300 space-y-0.5">
                  {testResult.sample.slice(0, 3).map(s => (
                    <li key={s.id} className="truncate">• {s.title}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Toggle */}
          <button type="button"
            onClick={() => onToggle(alert.id, alert.is_active)}
            className={`relative h-6 w-11 rounded-full transition-colors ${alert.is_active ? 'bg-em' : 'bg-ink-700'}`}
            aria-label={alert.is_active ? 'Wyłącz alert' : 'Włącz alert'}
          >
            <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-slate-100 transition-transform ${alert.is_active ? 'translate-x-5' : 'translate-x-0.5'}`} />
          </button>

          {/* Test */}
          <button type="button"
            onClick={handleTest}
            disabled={testing}
            title="Testuj alert"
            className="p-1.5 rounded-md hover:bg-em/10 text-slate-500 hover:text-em transition-colors disabled:opacity-40"
          >
            {testing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          </button>

          {/* Delete */}
          <button type="button"
            onClick={() => onDelete(alert.id)}
            title="Usuń alert"
            className="p-1.5 rounded-md hover:bg-nogo/10 text-slate-500 hover:text-nogo transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function AlertsPage() {
  const authFetch = useAuthFetch();
  const [alerts, setAlerts] = useState<TenderAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await authFetch('/api/v2/tender-alerts') as { alerts: TenderAlert[]; alert_count: number } | TenderAlert[];
      const items = Array.isArray(data) ? data : (data?.alerts ?? []);
      setAlerts(items);
    } catch (e: unknown) {
      setError((e as Error).message || 'Błąd ładowania alertów');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { fetchAlerts(); }, [fetchAlerts]);

  const handleCreate = async (form: CreateFormState) => {
    try {
      const body: Record<string, unknown> = {
        name: form.name,
        cpv_prefixes: form.cpv_prefixes,
        keywords: form.keywords,
        frequency: form.frequency,
        channel: form.channel,
      };
      if (form.value_min) body.value_min = parseFloat(form.value_min);
      if (form.value_max) body.value_max = parseFloat(form.value_max);
      if (form.webhook_url) body.webhook_url = form.webhook_url;

      const created = await authFetch('/api/v2/tender-alerts', {
        method: 'POST',
        body: JSON.stringify(body),
      }) as TenderAlert;
      setAlerts(prev => [created, ...prev]);
      showToast('success', 'Alert utworzony ✓');
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd tworzenia alertu');
      throw e;
    }
  };

  const handleToggle = async (id: string, current: boolean) => {
    try {
      await authFetch(`/api/v2/tender-alerts/${id}/toggle`, { method: 'PATCH' });
      setAlerts(prev => prev.map(a => a.id === id ? { ...a, is_active: !current } : a));
      showToast('success', current ? 'Alert wstrzymany' : 'Alert aktywowany');
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd przełączania alertu');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await authFetch(`/api/v2/tender-alerts/${id}`, { method: 'DELETE' });
      setAlerts(prev => prev.filter(a => a.id !== id));
      showToast('success', 'Alert usunięty');
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd usuwania alertu');
    }
  };

  const handleTest = async (id: string) => {
    try {
      const result = await authFetch(`/api/v2/tender-alerts/${id}/test`, { method: 'POST' }) as AlertTestResult;
      showToast('info', `Test alertu: ${result.matched} dopasowań`);
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd testu alertu');
    }
  };

  const activeCount = alerts.filter(a => a.is_active).length;

  const actions = (
    <div className="flex items-center gap-2">
      <Button variant="secondary" size="sm" iconLeft={<RefreshCw className="w-3.5 h-3.5" />} onClick={fetchAlerts} loading={loading}>
        Odśwież
      </Button>
      <Button variant="primary" size="sm" iconLeft={<Plus className="w-3.5 h-3.5" />} onClick={() => setShowCreate(true)}>
        Nowy alert
      </Button>
    </div>
  );

  return (
    <PageShell
      title="Alerty Przetargowe"
      subtitle={loading ? 'Ładowanie…' : `${alerts.length} alertów · ${activeCount} aktywnych`}
      actions={actions}
    >
      {/* Loading */}
      {loading && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} lines={3} />)}
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <GlassCard className="p-8">
          <EmptyState
            icon={AlertCircle}
            title="Błąd ładowania alertów"
            description={error}
            cta={
              <Button variant="secondary" size="sm" onClick={fetchAlerts} iconLeft={<RefreshCw className="w-3.5 h-3.5" />}>
                Spróbuj ponownie
              </Button>
            }
          />
        </GlassCard>
      )}

      {/* Empty state */}
      {!loading && !error && alerts.length === 0 && (
        <GlassCard className="p-8">
          <EmptyState
            icon={Bell}
            title="Brak alertów"
            description="Utwórz alerty, aby być powiadamianym o nowych przetargach pasujących do Twojego profilu."
            cta={
              <Button variant="primary" size="sm" onClick={() => setShowCreate(true)} iconLeft={<Plus className="w-3.5 h-3.5" />}>
                Utwórz pierwszy alert
              </Button>
            }
          />
        </GlassCard>
      )}

      {/* Alert list */}
      {!loading && !error && alerts.length > 0 && (
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {alerts.map(alert => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onToggle={handleToggle}
                onDelete={handleDelete}
                onTest={handleTest}
              />
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Create modal */}
      <AnimatePresence>
        {showCreate && (
          <CreateAlertModal onClose={() => setShowCreate(false)} onCreate={handleCreate} />
        )}
      </AnimatePresence>
    </PageShell>
  );
}
