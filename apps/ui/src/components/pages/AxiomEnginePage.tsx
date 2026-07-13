"use client";

import { useState, useEffect } from "react";
import { useAuthFetch } from "@/lib/api-v2";
import { PageShell } from "@/components/PageShell";
import { GlassCard } from "@/components/ui/GlassCard";
import { Plus, Settings, Trash2 } from "lucide-react";

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
  const [axioms, setAxioms]       = useState<Axiom[]>([]);
  const [loading, setLoading]     = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newAxiom, setNewAxiom]   = useState({ name: "", description: "", condition: "", action: "", priority: 0 });

  useEffect(() => { fetchAxioms(); }, []);

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

  const actions = (
    <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
      <Plus size={14} /> Nowy aksjomat
    </button>
  );

  return (
    <PageShell
      title="Silnik Aksjomatów"
      subtitle="Reguły biznesowe i ograniczenia"
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
            <h3 className="mb-4 text-lg font-semibold text-earth-100">Utwórz aksjomat</h3>
            <div className="space-y-3">
              <input
                placeholder="Nazwa"
                value={newAxiom.name}
                onChange={(e) => setNewAxiom({ ...newAxiom, name: e.target.value })}
                className="input-base"
              />
              <input
                placeholder="Opis"
                value={newAxiom.description}
                onChange={(e) => setNewAxiom({ ...newAxiom, description: e.target.value })}
                className="input-base"
              />
              <textarea
                placeholder="Warunek (np. tender.value > 1000000)"
                value={newAxiom.condition}
                onChange={(e) => setNewAxiom({ ...newAxiom, condition: e.target.value })}
                className="input-base font-mono resize-none"
                rows={2}
              />
              <textarea
                placeholder="Akcja (np. auto_bid with markup 12%)"
                value={newAxiom.action}
                onChange={(e) => setNewAxiom({ ...newAxiom, action: e.target.value })}
                className="input-base font-mono resize-none"
                rows={2}
              />
              <input
                type="number"
                placeholder="Priorytet (0 = najwyższy)"
                value={newAxiom.priority}
                onChange={(e) => setNewAxiom({ ...newAxiom, priority: parseInt(e.target.value) || 0 })}
                className="input-base"
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="btn-ghost">Anuluj</button>
              <button onClick={createAxiom} className="btn-primary">Utwórz</button>
            </div>
          </div>
        </div>
      )}

      {/* Axioms List */}
      {!loading && axioms.length === 0 && (
        <GlassCard className="flex flex-col items-center justify-center py-16">
          <Settings size={48} className="text-earth-600 mb-3" />
          <p className="text-sm text-earth-400">Brak zdefiniowanych aksjomatów</p>
          <p className="text-xs text-earth-500">Utwórz reguły, aby automatyzować workflow</p>
        </GlassCard>
      )}

      {!loading && axioms.length > 0 && (
        <div className="space-y-3">
          {axioms.map((axiom) => (
            <div key={axiom.id} className="card p-5 card-hover">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-sm font-semibold text-earth-100">{axiom.name}</h3>
                    <span className="rounded-token bg-earth-800/60 border border-earth-700/40 px-1.5 py-0.5 text-xs text-earth-400">
                      P: {axiom.priority}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-earth-400">{axiom.description}</p>
                  <div className="mt-3 space-y-1">
                    <p className="text-xs text-earth-500 font-mono">
                      <span className="text-info font-semibold">IF</span>{' '}{axiom.condition}
                    </p>
                    <p className="text-xs text-earth-500 font-mono">
                      <span className="text-success font-semibold">THEN</span>{' '}{axiom.action}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => toggleAxiom(axiom.id, axiom.enabled)}
                    className={`relative h-6 w-11 rounded-full transition-colors ${axiom.enabled ? "bg-accent-primary" : "bg-earth-700"}`}
                    aria-label={axiom.enabled ? 'Wyłącz' : 'Włącz'}
                  >
                    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${axiom.enabled ? "left-[22px]" : "left-0.5"}`} />
                  </button>
                  <button
                    onClick={() => deleteAxiom(axiom.id)}
                    className="rounded-token p-1 text-earth-500 hover:bg-danger/10 hover:text-danger transition-colors"
                    aria-label="Usuń aksjomat"
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
