"use client";

import { useState, useEffect } from "react";
import { useAuthFetch } from "@/lib/api-v2";
import { PageShell } from "@/components/PageShell";
import { GlassCard } from "@/components/ui/GlassCard";
import { Plus, Link2, Trash2 } from "lucide-react";

interface Webhook {
  id: string;
  name: string;
  url: string;
  events: string[];
  secret?: string;
  enabled: boolean;
  created_at: string;
  last_delivery?: string;
  last_status?: number;
}

const EVENT_OPTIONS = [
  "tender.new",
  "tender.closing_soon",
  "tender.awarded",
  "bid.submitted",
  "bid.won",
  "bid.lost",
  "alert.triggered",
  "axiom.fired",
];

export default function WebhooksPage() {
  const authFetch = useAuthFetch();
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", url: "", events: [] as string[] });

  useEffect(() => { fetchWebhooks(); }, []);

  const fetchWebhooks = async () => {
    try {
      const data = await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/webhooks`);
      setWebhooks(data.webhooks || []);
    } catch (err) {
      console.error("Failed to fetch webhooks:", err);
    } finally {
      setLoading(false);
    }
  };

  const createWebhook = async () => {
    try {
      const data = await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/webhooks`, {
        method: "POST",
        body: JSON.stringify(form),
      });
      setWebhooks((prev) => [...prev, data]);
      setShowCreate(false);
      setForm({ name: "", url: "", events: [] });
    } catch (err) {
      console.error("Failed to create webhook:", err);
    }
  };

  const toggleWebhook = async (id: string, enabled: boolean) => {
    try {
      await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/webhooks/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !enabled }),
      });
      setWebhooks((prev) => prev.map((w) => (w.id === id ? { ...w, enabled: !enabled } : w)));
    } catch (err) {
      console.error("Failed to toggle webhook:", err);
    }
  };

  const deleteWebhook = async (id: string) => {
    try {
      await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/webhooks/${id}`, { method: "DELETE" });
      setWebhooks((prev) => prev.filter((w) => w.id !== id));
    } catch (err) {
      console.error("Failed to delete webhook:", err);
    }
  };

  const testWebhook = async (id: string) => {
    try {
      await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/webhooks/${id}/test`, { method: "POST" });
    } catch (err) {
      console.error("Failed to test webhook:", err);
    }
  };

  const toggleEvent = (event: string) => {
    setForm((prev) => ({
      ...prev,
      events: prev.events.includes(event)
        ? prev.events.filter((e) => e !== event)
        : [...prev.events, event],
    }));
  };

  const actions = (
    <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
      <Plus size={14} /> Nowy webhook
    </button>
  );

  return (
    <PageShell
      title="Webhooki"
      subtitle="Integracje i powiadomienia zewnętrzne"
      actions={actions}
    >
      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 rounded-token-lg bg-earth-900/50 animate-shimmer" />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md card p-6 shadow-token-lg">
            <h3 className="mb-4 text-lg font-semibold text-earth-100">Utwórz webhook</h3>
            <div className="space-y-3">
              <input
                placeholder="Nazwa webhooka"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="input-base"
              />
              <input
                placeholder="Endpoint URL (https://...)"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                className="input-base"
              />
              <div>
                <p className="mb-2 text-xs text-earth-400 label-base">Subskrybowane eventy</p>
                <div className="flex flex-wrap gap-2">
                  {EVENT_OPTIONS.map((event) => (
                    <button
                      key={event}
                      onClick={() => toggleEvent(event)}
                      className={`rounded-token px-2.5 py-1 text-xs transition-colors font-mono ${
                        form.events.includes(event)
                          ? "bg-accent-primary text-earth-950"
                          : "bg-earth-800/50 text-earth-400 hover:bg-earth-700/50 border border-earth-700/40"
                      }`}
                    >
                      {event}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="btn-ghost">Anuluj</button>
              <button
                onClick={createWebhook}
                disabled={!form.name || !form.url || form.events.length === 0}
                className="btn-primary disabled:opacity-40"
              >
                Utwórz
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Webhooks List */}
      {!loading && webhooks.length === 0 && (
        <GlassCard className="flex flex-col items-center justify-center py-16">
          <Link2 size={48} className="text-earth-600 mb-3" />
          <p className="text-sm text-earth-400">Brak skonfigurowanych webhooków</p>
          <p className="text-xs text-earth-500">Połącz zewnętrzne serwisy, aby automatyzować workflow</p>
        </GlassCard>
      )}

      {!loading && webhooks.length > 0 && (
        <div className="space-y-3">
          {webhooks.map((webhook) => (
            <div key={webhook.id} className="card p-5 card-hover">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-earth-100">{webhook.name}</h3>
                    {webhook.last_status && (
                      <span className={`rounded-token px-1.5 py-0.5 text-xs ${
                        webhook.last_status < 300 ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
                      }`}>
                        {webhook.last_status}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 font-mono text-xs text-earth-500">{webhook.url}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {webhook.events.map((ev) => (
                      <span key={ev} className="rounded-token bg-earth-800/50 border border-earth-700/40 px-2 py-0.5 text-xs text-earth-400 font-mono">{ev}</span>
                    ))}
                  </div>
                  {webhook.last_delivery && (
                    <p className="mt-2 text-xs text-earth-500">
                      Ostatnie dostarczenie: {new Date(webhook.last_delivery).toLocaleString('pl-PL')}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => testWebhook(webhook.id)}
                    className="btn-ghost text-xs px-2 py-1"
                  >
                    Test
                  </button>
                  <button
                    onClick={() => toggleWebhook(webhook.id, webhook.enabled)}
                    className={`relative h-6 w-11 rounded-full transition-colors ${webhook.enabled ? "bg-accent-primary" : "bg-earth-700"}`}
                    aria-label={webhook.enabled ? 'Wyłącz' : 'Włącz'}
                  >
                    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${webhook.enabled ? "left-[22px]" : "left-0.5"}`} />
                  </button>
                  <button
                    onClick={() => deleteWebhook(webhook.id)}
                    className="rounded-token p-1 text-earth-500 hover:bg-danger/10 hover:text-danger transition-colors"
                    aria-label="Usuń webhook"
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
