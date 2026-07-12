"use client";

import { useState, useEffect } from "react";
import { useAuthFetch } from "@/lib/api-v2";

interface Axiom {
  id: string;
  name: string;
  description: string;
  condition: string;
  action: string;
  enabled: boolean;
  priority: number;
  created_at: string;
}

export default function AxiomEnginePage() {
  const authFetch = useAuthFetch();
  const [axioms, setAxioms] = useState<Axiom[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newAxiom, setNewAxiom] = useState({ name: "", description: "", condition: "", action: "", priority: 0 });

  useEffect(() => {
    fetchAxioms();
  }, []);

  const fetchAxioms = async () => {
    try {
      const data = await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/axioms`);
      setAxioms(data.axioms || []);
    } catch (err) {
      console.error("Failed to fetch axioms:", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleAxiom = async (id: string, enabled: boolean) => {
    try {
      await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/axioms/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !enabled }),
      });
      setAxioms((prev) => prev.map((a) => (a.id === id ? { ...a, enabled: !enabled } : a)));
    } catch (err) {
      console.error("Failed to toggle axiom:", err);
    }
  };

  const deleteAxiom = async (id: string) => {
    try {
      await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/axioms/${id}`, { method: "DELETE" });
      setAxioms((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      console.error("Failed to delete axiom:", err);
    }
  };

  const createAxiom = async () => {
    try {
      const data = await authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/axioms`, {
        method: "POST",
        body: JSON.stringify(newAxiom),
      });
      setAxioms((prev) => [...prev, data]);
      setShowCreate(false);
      setNewAxiom({ name: "", description: "", condition: "", action: "", priority: 0 });
    } catch (err) {
      console.error("Failed to create axiom:", err);
    }
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
          <h1 className="text-2xl font-bold text-white">Axiom Engine</h1>
          <p className="mt-1 text-sm text-gray-400">Define rules that automate your bidding workflow</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-[#3B82F6] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#3B82F6]/80"
        >
          + New Axiom
        </button>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#1E293B] p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">Create Axiom</h3>
            <div className="space-y-3">
              <input
                placeholder="Name"
                value={newAxiom.name}
                onChange={(e) => setNewAxiom({ ...newAxiom, name: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
              />
              <input
                placeholder="Description"
                value={newAxiom.description}
                onChange={(e) => setNewAxiom({ ...newAxiom, description: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
              />
              <textarea
                placeholder="Condition (e.g., tender.value > 1000000)"
                value={newAxiom.condition}
                onChange={(e) => setNewAxiom({ ...newAxiom, condition: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
                rows={2}
              />
              <textarea
                placeholder="Action (e.g., auto_bid with markup 12%)"
                value={newAxiom.action}
                onChange={(e) => setNewAxiom({ ...newAxiom, action: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
                rows={2}
              />
              <input
                type="number"
                placeholder="Priority (0 = highest)"
                value={newAxiom.priority}
                onChange={(e) => setNewAxiom({ ...newAxiom, priority: parseInt(e.target.value) || 0 })}
                className="w-full rounded-lg border border-white/10 bg-[#0A1628] px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#3B82F6]"
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:text-white">
                Cancel
              </button>
              <button onClick={createAxiom} className="rounded-lg bg-[#3B82F6] px-4 py-2 text-sm font-medium text-white hover:bg-[#3B82F6]/80">
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Axioms List */}
      {axioms.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-white/5 bg-[#1E293B] py-16">
          <svg className="h-12 w-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <p className="mt-3 text-sm text-gray-400">No axioms defined yet</p>
          <p className="text-xs text-gray-500">Create rules to automate your workflow</p>
        </div>
      ) : (
        <div className="space-y-3">
          {axioms.map((axiom) => (
            <div key={axiom.id} className="rounded-xl border border-white/5 bg-[#1E293B] p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-sm font-semibold text-white">{axiom.name}</h3>
                    <span className="rounded bg-white/10 px-1.5 py-0.5 text-xs text-gray-400">
                      Priority: {axiom.priority}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-400">{axiom.description}</p>
                  <div className="mt-3 space-y-1">
                    <p className="text-xs text-gray-500">
                      <span className="text-[#3B82F6]">IF</span> {axiom.condition}
                    </p>
                    <p className="text-xs text-gray-500">
                      <span className="text-emerald-400">THEN</span> {axiom.action}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleAxiom(axiom.id, axiom.enabled)}
                    className={`relative h-6 w-11 rounded-full transition-colors ${axiom.enabled ? "bg-[#3B82F6]" : "bg-gray-600"}`}
                  >
                    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${axiom.enabled ? "left-[22px]" : "left-0.5"}`} />
                  </button>
                  <button onClick={() => deleteAxiom(axiom.id)} className="rounded p-1 text-gray-500 hover:bg-red-400/10 hover:text-red-400">
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
