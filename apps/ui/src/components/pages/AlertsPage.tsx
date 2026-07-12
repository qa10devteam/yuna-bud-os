"use client";

import { useState, useEffect } from "react";
import { useAuthFetch } from "@/lib/api-v2";

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

  useEffect(() => {
    fetchAlerts();
  }, []);

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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A1628] p-6">
        <div className="mb-8 h-8 w-48 animate-pulse rounded bg-white/10" />
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-[#1E293B]" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A1628] p-6">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Tender Alerts</h1>
          <p className="mt-1 text-sm text-gray-400">Get notified when matching tenders are published</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-[#3B82F6] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#3B82F6]/80"
        >
          + New Alert
        </button>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#1E293B] p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">Create Alert</h3>
            <div className="space-y-3">
              <input
                placeholder="Alert name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
              />
              <input
                placeholder="Keywords (comma-separated)"
                value={form.keywords}
                onChange={(e) => setForm({ ...form, keywords: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
              />
              <input
                placeholder="Categories (comma-separated)"
                value={form.categories}
                onChange={(e) => setForm({ ...form, categories: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="number"
                  placeholder="Min value (R)"
                  value={form.min_value}
                  onChange={(e) => setForm({ ...form, min_value: e.target.value })}
                  className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
                />
                <input
                  type="number"
                  placeholder="Max value (R)"
                  value={form.max_value}
                  onChange={(e) => setForm({ ...form, max_value: e.target.value })}
                  className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
                />
              </div>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={form.notify_email}
                    onChange={(e) => setForm({ ...form, notify_email: e.target.checked })}
                    className="rounded border-gray-600 bg-[#0A1628] text-[#3B82F6]"
                  />
                  Email
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={form.notify_webhook}
                    onChange={(e) => setForm({ ...form, notify_webhook: e.target.checked })}
                    className="rounded border-gray-600 bg-[#0A1628] text-[#3B82F6]"
                  />
                  Webhook
                </label>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:text-white">
                Cancel
              </button>
              <button onClick={createAlert} className="rounded-lg bg-[#3B82F6] px-4 py-2 text-sm font-medium text-white hover:bg-[#3B82F6]/80">
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Alerts List */}
      {alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-white/5 bg-[#1E293B] py-16">
          <svg className="h-12 w-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <p className="mt-3 text-sm text-gray-400">No alerts configured</p>
          <p className="text-xs text-gray-500">Create alerts to get notified about matching tenders</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div key={alert.id} className="rounded-xl border border-white/5 bg-[#1E293B] p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-white">{alert.name}</h3>
                    {!alert.enabled && (
                      <span className="rounded bg-gray-600/30 px-1.5 py-0.5 text-xs text-gray-400">Paused</span>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {alert.keywords.map((kw) => (
                      <span key={kw} className="rounded bg-[#3B82F6]/10 px-2 py-0.5 text-xs text-[#3B82F6]">{kw}</span>
                    ))}
                    {alert.categories.map((cat) => (
                      <span key={cat} className="rounded bg-purple-400/10 px-2 py-0.5 text-xs text-purple-400">{cat}</span>
                    ))}
                  </div>
                  <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                    {alert.min_value && <span>Min: R{alert.min_value.toLocaleString()}</span>}
                    {alert.max_value && <span>Max: R{alert.max_value.toLocaleString()}</span>}
                    {alert.notify_email && <span>📧 Email</span>}
                    {alert.notify_webhook && <span>🔗 Webhook</span>}
                    {alert.last_triggered && (
                      <span>Last triggered: {new Date(alert.last_triggered).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleAlert(alert.id, alert.enabled)}
                    className={`relative h-6 w-11 rounded-full transition-colors ${alert.enabled ? "bg-[#3B82F6]" : "bg-gray-600"}`}
                  >
                    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${alert.enabled ? "left-[22px]" : "left-0.5"}`} />
                  </button>
                  <button onClick={() => deleteAlert(alert.id)} className="rounded p-1 text-gray-500 hover:bg-red-400/10 hover:text-red-400">
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
