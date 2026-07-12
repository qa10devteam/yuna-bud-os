"use client";

import { useState, useEffect } from "react";
import { useAuthFetch } from "@/lib/api-v2";

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

  useEffect(() => {
    fetchWebhooks();
  }, []);

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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A1628] p-6">
        <div className="mb-8 h-8 w-48 animate-pulse rounded bg-white/10" />
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-[#1E293B]" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A1628] p-6">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Webhooks</h1>
          <p className="mt-1 text-sm text-gray-400">Automate workflows by sending events to external services</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-[#3B82F6] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#3B82F6]/80"
        >
          + New Webhook
        </button>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#1E293B] p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">Create Webhook</h3>
            <div className="space-y-3">
              <input
                placeholder="Webhook name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
              />
              <input
                placeholder="Endpoint URL (https://...)"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
              />
              <div>
                <p className="mb-2 text-xs text-gray-400">Events to subscribe</p>
                <div className="flex flex-wrap gap-2">
                  {EVENT_OPTIONS.map((event) => (
                    <button
                      key={event}
                      onClick={() => toggleEvent(event)}
                      className={`rounded-lg px-2.5 py-1 text-xs transition-colors ${
                        form.events.includes(event)
                          ? "bg-[#3B82F6] text-white"
                          : "bg-white/5 text-gray-400 hover:bg-white/10"
                      }`}
                    >
                      {event}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:text-white">
                Cancel
              </button>
              <button
                onClick={createWebhook}
                disabled={!form.name || !form.url || form.events.length === 0}
                className="rounded-lg bg-[#3B82F6] px-4 py-2 text-sm font-medium text-white hover:bg-[#3B82F6]/80 disabled:opacity-40"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Webhooks List */}
      {webhooks.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-white/5 bg-[#1E293B] py-16">
          <svg className="h-12 w-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <p className="mt-3 text-sm text-gray-400">No webhooks configured</p>
          <p className="text-xs text-gray-500">Connect external services to automate your workflow</p>
        </div>
      ) : (
        <div className="space-y-3">
          {webhooks.map((webhook) => (
            <div key={webhook.id} className="rounded-xl border border-white/5 bg-[#1E293B] p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-white">{webhook.name}</h3>
                    {webhook.last_status && (
                      <span className={`rounded px-1.5 py-0.5 text-xs ${
                        webhook.last_status < 300 ? "bg-emerald-400/10 text-emerald-400" : "bg-red-400/10 text-red-400"
                      }`}>
                        {webhook.last_status}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 font-mono text-xs text-gray-400">{webhook.url}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {webhook.events.map((ev) => (
                      <span key={ev} className="rounded bg-white/5 px-2 py-0.5 text-xs text-gray-400">{ev}</span>
                    ))}
                  </div>
                  {webhook.last_delivery && (
                    <p className="mt-2 text-xs text-gray-500">
                      Last delivery: {new Date(webhook.last_delivery).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => testWebhook(webhook.id)}
                    className="rounded px-2 py-1 text-xs text-[#3B82F6] hover:bg-[#3B82F6]/10"
                  >
                    Test
                  </button>
                  <button
                    onClick={() => toggleWebhook(webhook.id, webhook.enabled)}
                    className={`relative h-6 w-11 rounded-full transition-colors ${webhook.enabled ? "bg-[#3B82F6]" : "bg-gray-600"}`}
                  >
                    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${webhook.enabled ? "left-[22px]" : "left-0.5"}`} />
                  </button>
                  <button onClick={() => deleteWebhook(webhook.id)} className="rounded p-1 text-gray-500 hover:bg-red-400/10 hover:text-red-400">
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
