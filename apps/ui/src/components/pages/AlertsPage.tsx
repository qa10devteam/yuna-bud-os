"use client";

import { useState, useEffect } from "react";
import { useAuthFetch } from "@/lib/api-v2";
import { PageShell } from "@/components/PageShell";
import { GlassCard } from "@/components/ui/GlassCard";
import { Plus, Bell, Trash2 } from "lucide-react";

interface Alert {
  id: string;
  name: string;
  keywords: string[];
  categories: string[];
  min_value?: number;
  max_value?: number;
  notify_email: boolean;
  notify_webhook: boolean;
  enabled: boolean;
  created_at: string;
  last_triggered?: string;
}

export default function AlertsPage() {
  const authFetch = useAuthFetch();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: "",
    keywords: "",
    categories: "",
    min_value: "",
    max_value: "",
    notify_email: true,
    notify_webhook: false,
  });

  useEffect(() => { fetchAlerts(); }, []);

  const fetchAlerts = async () => {
    try {
      const data = await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/alerts`);
      setAlerts(data.alerts || []);
    } catch (err) {
      console.error("Failed to fetch alerts:", err);
    } finally {
      setLoading(false);
    }
  };

  const createAlert = async () => {
    try {
      const payload = {
        name: form.name,
        keywords: form.keywords.split(",").map((k) => k.trim()).filter(Boolean),
        categories: form.categories.split(",").map((c) => c.trim()).filter(Boolean),
        min_value: form.min_value ? parseFloat(form.min_value) : undefined,
        max_value: form.max_value ? parseFloat(form.max_value) : undefined,
        notify_email: form.notify_email,
        notify_webhook: form.notify_webhook,
      };
      const data = await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/alerts`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setAlerts((prev) => [...prev, data]);
      setShowCreate(false);
      setForm({ name: "", keywords: "", categories: "", min_value: "", max_value: "", notify_email: true, notify_webhook: false });
    } catch (err) {
      console.error("Failed to create alert:", err);
    }
  };

  const toggleAlert = async (id: string, enabled: boolean) => {
    try {
      await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/alerts/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !enabled }),
      });
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, enabled: !enabled } : a)));
    } catch (err) {
      console.error("Failed to toggle alert:", err);
    }
  };

  const deleteAlert = async (id: string) => {
    try {
      await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/alerts/${id}`, { method: "DELETE" });
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      console.error("Failed to delete alert:", err);
    }
  };

  const actions = (
    <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
      <Plus size={14} /> Nowy alert
    </button>
  );

  return (
    <PageShell
      title="Powiadomienia"
      subtitle="Alerty i powiadomienia systemowe"
      actions={actions}
    >
      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 rounded-token-lg bg-earth-900/50 animate-shimmer" />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md card p-6 shadow-token-lg">
            <h3 className="mb-4 text-lg font-semibold text-earth-100">Utwórz alert</h3>
            <div className="space-y-3">
              <input
                placeholder="Nazwa alertu"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="input-base"
              />
              <input
                placeholder="Słowa kluczowe (oddzielone przecinkami)"
                value={form.keywords}
                onChange={(e) => setForm({ ...form, keywords: e.target.value })}
                className="input-base"
              />
              <input
                placeholder="Kategorie (oddzielone przecinkami)"
                value={form.categories}
                onChange={(e) => setForm({ ...form, categories: e.target.value })}
                className="input-base"
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="number"
                  placeholder="Min wartość (PLN)"
                  value={form.min_value}
                  onChange={(e) => setForm({ ...form, min_value: e.target.value })}
                  className="input-base"
                />
                <input
                  type="number"
                  placeholder="Max wartość (PLN)"
                  value={form.max_value}
                  onChange={(e) => setForm({ ...form, max_value: e.target.value })}
                  className="input-base"
                />
              </div>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-sm text-earth-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.notify_email}
                    onChange={(e) => setForm({ ...form, notify_email: e.target.checked })}
                    className="rounded border-earth-700 bg-earth-900 text-accent-primary"
                  />
                  Email
                </label>
                <label className="flex items-center gap-2 text-sm text-earth-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.notify_webhook}
                    onChange={(e) => setForm({ ...form, notify_webhook: e.target.checked })}
                    className="rounded border-earth-700 bg-earth-900 text-accent-primary"
                  />
                  Webhook
                </label>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="btn-ghost">Anuluj</button>
              <button onClick={createAlert} className="btn-primary">Utwórz</button>
            </div>
          </div>
        </div>
      )}

      {/* Alerts List */}
      {!loading && alerts.length === 0 && (
        <GlassCard className="flex flex-col items-center justify-center py-16">
          <Bell size={48} className="text-earth-600 mb-3" />
          <p className="text-sm text-earth-400">Brak skonfigurowanych alertów</p>
          <p className="text-xs text-earth-500">Utwórz alerty, aby być powiadamianym o pasujących przetargach</p>
        </GlassCard>
      )}

      {!loading && alerts.length > 0 && (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div key={alert.id} className="card p-5 card-hover">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-earth-100">{alert.name}</h3>
                    {!alert.enabled && (
                      <span className="rounded-token bg-earth-700/30 px-1.5 py-0.5 text-xs text-earth-400">Wstrzymany</span>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {alert.keywords.map((kw) => (
                      <span key={kw} className="rounded-token bg-info/10 px-2 py-0.5 text-xs text-info">{kw}</span>
                    ))}
                    {alert.categories.map((cat) => (
                      <span key={cat} className="rounded-token bg-violet/10 px-2 py-0.5 text-xs text-violet">{cat}</span>
                    ))}
                  </div>
                  <div className="mt-2 flex items-center gap-4 text-xs text-earth-500">
                    {alert.min_value && <span>Min: {alert.min_value.toLocaleString()} PLN</span>}
                    {alert.max_value && <span>Max: {alert.max_value.toLocaleString()} PLN</span>}
                    {alert.notify_email && <span>📧 Email</span>}
                    {alert.notify_webhook && <span>🔗 Webhook</span>}
                    {alert.last_triggered && (
                      <span>Ostatnio: {new Date(alert.last_triggered).toLocaleDateString('pl-PL')}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => toggleAlert(alert.id, alert.enabled)}
                    className={`relative h-6 w-11 rounded-full transition-colors ${alert.enabled ? "bg-accent-primary" : "bg-earth-700"}`}
                    aria-label={alert.enabled ? 'Wyłącz alert' : 'Włącz alert'}
                  >
                    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${alert.enabled ? "left-[22px]" : "left-0.5"}`} />
                  </button>
                  <button
                    onClick={() => deleteAlert(alert.id)}
                    className="rounded-token p-1 text-earth-500 hover:bg-danger/10 hover:text-danger transition-colors"
                    aria-label="Usuń alert"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </PageShell>
  );
}
