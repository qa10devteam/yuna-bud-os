'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import {
  Search, Plus, Trash2, Eye, TrendingUp, Award,
  Building2, MapPin, ChevronRight, X, ExternalLink,
  RefreshCw, Users, Target,
} from 'lucide-react';
import { PageShell } from '@/components/PageShell';
import { SkeletonCard } from '@/components/SkeletonCard';
import {
  useCompetitorWatch, useCompetitorIntel, useCompetitorSearch,
  fmtMln, PROVINCE_MAP,
  type CompetitorWatch, type CompetitorIntel,
} from '@/lib/api-v2';
import { showToast } from '@/components/Toast';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#84cc16'];

// ── Intel side panel ──────────────────────────────────────────────────────────
function IntelPanel({ nip, onClose }: { nip: string; onClose: () => void }) {
  const { data, loading } = useCompetitorIntel(nip);

  const cpvEntries = data?.top_cpv
    ? Object.entries(data.top_cpv).sort((a, b) => b[1] - a[1]).slice(0, 6)
    : [];
  const cpvChart = cpvEntries.map(([cpv, wins]) => ({ cpv: cpv.slice(0, 5), wins }));

  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', damping: 28, stiffness: 300 }}
      className="fixed right-0 top-0 h-full w-full max-w-lg bg-earth-950 border-l border-earth-700 z-50 overflow-y-auto shadow-2xl"
    >
      {/* Header */}
      <div className="sticky top-0 bg-earth-950/95 backdrop-blur border-b border-earth-800 px-6 py-4 flex items-center justify-between">
        <div>
          <div className="text-xs text-earth-500 uppercase tracking-widest mb-0.5">Profil konkurenta</div>
          <div className="font-bold text-earth-50 truncate max-w-[300px]">
            {loading ? <span className="animate-pulse bg-earth-700 rounded h-5 w-48 block" /> : (data?.name || nip)}
          </div>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-earth-800 rounded-lg transition-colors">
          <X size={18} className="text-earth-400" />
        </button>
      </div>

      {loading && (
        <div className="p-6 space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse bg-earth-800 rounded-xl" />
          ))}
        </div>
      )}

      {!loading && data && (
        <div className="p-6 space-y-6">

          {/* KPI row */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Wygrane', value: (data.total_wins ?? 0).toLocaleString('pl-PL'), color: '#10b981' },
              { label: 'Win rate', value: `${((data.win_rate ?? 0) * 100).toFixed(0)}%`, color: '#3b82f6' },
              { label: 'Wartość', value: fmtMln((data.total_value ?? 0) / 1_000_000), color: '#f59e0b' },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-earth-900 rounded-xl p-3 border border-earth-700 text-center">
                <div className="text-xs text-earth-500 mb-1">{label}</div>
                <div className="font-bold text-lg" style={{ color }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Location */}
          <div className="flex flex-wrap gap-3 text-sm text-earth-400">
            <div className="flex items-center gap-1.5">
              <MapPin size={14} className="text-earth-500" />
              {data.city || '—'}
            </div>
            {data.province && (
              <div className="flex items-center gap-1.5">
                <Building2 size={14} className="text-earth-500" />
                {PROVINCE_MAP[data.province] || data.province}
              </div>
            )}
            <div className="flex items-center gap-1.5 font-mono text-xs text-earth-600">
              NIP: {data.nip}
            </div>
          </div>

          {/* CPV breakdown */}
          {cpvChart.length > 0 && (
            <div>
              <h4 className="text-xs uppercase tracking-widest text-earth-500 mb-3">Specjalizacja CPV</h4>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={cpvChart} margin={{ top: 0, right: 4, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="cpv" tick={{ fill: '#71717a', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#71717a', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ background: '#1a1712', border: '1px solid #3f3f46', borderRadius: 8 }}
                    formatter={(v: number) => [v, 'Wygrane']}
                  />
                  <Bar dataKey="wins" radius={[3, 3, 0, 0]}>
                    {cpvChart.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.85} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Recent wins */}
          {data.recent_wins.length > 0 && (
            <div>
              <h4 className="text-xs uppercase tracking-widest text-earth-500 mb-3">
                Ostatnie wygrane ({data.recent_wins.length})
              </h4>
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {data.recent_wins.map((win, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: 8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="p-3 bg-earth-900 rounded-lg border border-earth-800 hover:border-earth-700 transition-colors"
                  >
                    <div className="text-sm text-earth-100 line-clamp-2">{win.title}</div>
                    <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                      <span className="text-xs text-earth-500">{(win.win_date ?? '').slice(0, 10)}</span>
                      {win.buyer_name && (
                        <span className="text-xs text-earth-400 truncate max-w-[160px]">{win.buyer_name}</span>
                      )}
                      {win.value != null && (
                        <span className="text-xs text-emerald-400 font-mono ml-auto">
                          {fmtMln(win.value / 1_000_000)}
                        </span>
                      )}
                    </div>
                    {win.cpv5 && (
                      <span className="inline-block mt-1 text-xs font-mono bg-earth-800 text-earth-500 px-2 py-0.5 rounded">
                        CPV {win.cpv5.slice(0, 8)}
                      </span>
                    )}
                  </motion.div>
                ))}
              </div>
            </div>
          )}

        </div>
      )}

      {!loading && !data && (
        <div className="p-12 text-center text-earth-500">
          <Target size={32} className="mx-auto mb-3 text-earth-700" />
          <p className="text-sm">Brak danych dla NIP {nip}</p>
          <p className="text-xs mt-1">Firma mogła nie wygrywać przetargów w bazie</p>
        </div>
      )}
    </motion.div>
  );
}

// ── Add competitor form ───────────────────────────────────────────────────────
function AddCompetitorModal({ onClose, onAdd }: { onClose: () => void; onAdd: (nip: string, notes?: string) => Promise<void> }) {
  const [q, setQ] = useState('');
  const [notes, setNotes] = useState('');
  const [selected, setSelected] = useState<{ nip: string; name: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const { data: results, loading } = useCompetitorSearch(q);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleAdd = async () => {
    const nip = selected?.nip || (q.match(/^\d{10}$/) ? q : null);
    if (!nip) return;
    setSaving(true);
    try {
      await onAdd(nip, notes || undefined);
      showToast('success', 'Konkurent dodany ✓');
      onClose();
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd dodawania');
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, y: 16 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 16 }}
        onClick={e => e.stopPropagation()}
        className="bg-earth-900 border border-earth-700 rounded-2xl w-full max-w-md p-6 shadow-2xl"
      >
        <h3 className="text-base font-bold text-earth-50 mb-4">Dodaj do obserwowanych</h3>

        <div className="relative mb-3">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-earth-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={e => { setQ(e.target.value); setSelected(null); }}
            placeholder="Nazwa firmy lub NIP (10 cyfr)…"
            className="w-full bg-earth-800 border border-earth-700 rounded-lg pl-9 pr-4 py-2.5 text-sm text-earth-100 placeholder-earth-500 focus:outline-none focus:border-emerald-500"
          />
          {loading && <RefreshCw size={12} className="absolute right-3 top-1/2 -translate-y-1/2 text-earth-400 animate-spin" />}
        </div>

        {/* Search results */}
        {results.length > 0 && !selected && (
          <div className="mb-3 border border-earth-700 rounded-lg overflow-hidden">
            {results.map(r => (
              <button
                key={r.nip}
                onClick={() => { setSelected(r); setQ(r.name); }}
                className="w-full flex items-center justify-between px-3 py-2 hover:bg-earth-800 text-left transition-colors border-b border-earth-800 last:border-0"
              >
                <div>
                  <div className="text-sm text-earth-100">{r.name}</div>
                  <div className="text-xs text-earth-500 font-mono">{r.nip} {r.city && `· ${r.city}`}</div>
                </div>
                <div className="text-xs text-earth-500">{r.wins} wyg.</div>
              </button>
            ))}
          </div>
        )}

        {selected && (
          <div className="mb-3 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center justify-between">
            <div>
              <div className="text-sm text-emerald-300">{selected.name}</div>
              <div className="text-xs text-emerald-600 font-mono">{selected.nip}</div>
            </div>
            <button onClick={() => setSelected(null)} className="text-earth-500 hover:text-earth-300">
              <X size={14} />
            </button>
          </div>
        )}

        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          placeholder="Notatka (opcjonalnie)…"
          rows={2}
          className="w-full bg-earth-800 border border-earth-700 rounded-lg px-3 py-2 text-sm text-earth-100 placeholder-earth-500 focus:outline-none focus:border-emerald-500 resize-none mb-4"
        />

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-lg border border-earth-700 text-earth-400 text-sm hover:border-earth-600 transition-colors">
            Anuluj
          </button>
          <button
            onClick={handleAdd}
            disabled={saving || (!selected && !q.match(/^\d{10}$/))}
            className="flex-1 py-2.5 rounded-lg bg-emerald-500 text-white text-sm font-medium hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {saving ? <RefreshCw size={14} className="animate-spin" /> : <Plus size={14} />}
            Dodaj
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Competitor row card ───────────────────────────────────────────────────────
function CompetitorCard({
  c, onIntel, onDelete,
}: {
  c: CompetitorWatch;
  onIntel: (nip: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -16 }}
      className="bg-earth-900 border border-earth-700 rounded-xl p-4 hover:border-earth-600 transition-all group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-earth-100 truncate">
              {c.competitor_name || c.competitor_nip}
            </span>
            {c.created_at && (
              <span className="text-xs text-earth-600 shrink-0">
                dodano {c.created_at.slice(0, 10)}
              </span>
            )}
          </div>
          <div className="text-xs text-earth-500 font-mono mb-3">{c.competitor_nip}</div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <div className="text-xs text-earth-500 mb-0.5">Wygrane</div>
              <div className="text-base font-bold text-earth-100">{c.total_wins ?? '—'}</div>
            </div>
            <div>
              <div className="text-xs text-earth-500 mb-0.5">Wartość</div>
              <div className="text-base font-bold text-emerald-400">{fmtMln((c.total_value ?? 0) / 1_000_000)}</div>
            </div>
            <div>
              <div className="text-xs text-earth-500 mb-0.5">Win rate</div>
              <div className="flex items-center gap-1.5">
                <div className="h-1.5 flex-1 bg-earth-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${Math.min(100, (c.win_rate ?? 0) * 100)}%` }}
                  />
                </div>
                <span className="text-xs text-earth-300 shrink-0">{((c.win_rate ?? 0) * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>

          {/* CPV tags */}
          {c.top_cpv && Object.keys(c.top_cpv).length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {Object.entries(c.top_cpv).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([cpv, count]) => (
                <span key={cpv} className="text-xs bg-earth-800 text-earth-400 px-2 py-0.5 rounded-full font-mono">
                  {cpv.slice(0, 5)} ({count})
                </span>
              ))}
            </div>
          )}

          {c.notes && (
            <div className="mt-2 text-xs text-earth-500 italic line-clamp-1">{c.notes}</div>
          )}
        </div>

        <div className="flex flex-col gap-1.5 shrink-0">
          <button
            onClick={() => onIntel(c.competitor_nip)}
            title="Profil intel"
            className="p-2 rounded-lg hover:bg-earth-700 text-earth-400 hover:text-emerald-400 transition-colors"
          >
            <Eye size={16} />
          </button>
          <button
            onClick={() => onDelete(c.id)}
            title="Usuń z obserwowanych"
            className="p-2 rounded-lg hover:bg-red-500/10 text-earth-600 hover:text-red-400 transition-colors"
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export function CompetitorPage() {
  const { data, loading, add, remove } = useCompetitorWatch();
  const [intelNip, setIntelNip] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [searchQ, setSearchQ] = useState('');

  const filtered = data.filter(c =>
    !searchQ || c.competitor_name?.toLowerCase().includes(searchQ.toLowerCase()) || c.competitor_nip.includes(searchQ),
  );

  const totalValue = data.reduce((s, c) => s + (c.total_value ?? 0) / 1_000_000, 0);
  const totalWins = data.reduce((s, c) => s + (c.total_wins ?? 0), 0);

  const handleDelete = async (id: string) => {
    try {
      await remove(id);
      showToast('success', 'Usunięto z obserwowanych');
    } catch {
      showToast('error', 'Błąd usuwania');
    }
  };

  return (
    <>
      <PageShell
        title="Obserwowani Konkurenci"
        subtitle="Śledzenie aktywności rynkowej i win-rate firm"
        actions={
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-400 transition-colors"
          >
            <Plus size={15} />
            Dodaj firmę
          </button>
        }
      >
        <div className="space-y-6">

          {/* ── Stats strip ──────────────────────────────────────────────── */}
          {!loading && data.length > 0 && (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: 'Obserwowane firmy', value: data.length, icon: Users, color: '#10b981' },
                { label: 'Łączne wygrane', value: totalWins.toLocaleString('pl-PL'), icon: Award, color: '#3b82f6' },
                { label: 'Łączna wartość', value: fmtMln(totalValue), icon: TrendingUp, color: '#f59e0b' },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="bg-earth-900 border border-earth-700 rounded-xl p-4 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: color + '22' }}>
                    <Icon size={18} style={{ color }} />
                  </div>
                  <div>
                    <div className="text-xs text-earth-500">{label}</div>
                    <div className="text-xl font-bold text-earth-50">{value}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Search ───────────────────────────────────────────────────── */}
          {data.length > 0 && (
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-earth-400" />
              <input
                value={searchQ}
                onChange={e => setSearchQ(e.target.value)}
                placeholder="Filtruj po nazwie lub NIP…"
                className="w-full bg-earth-900 border border-earth-700 rounded-lg pl-9 pr-4 py-2.5 text-sm text-earth-100 placeholder-earth-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
            </div>
          )}

          {/* ── List ─────────────────────────────────────────────────────── */}
          {loading && (
            <div className="grid gap-3 sm:grid-cols-2">
              {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          )}

          {!loading && data.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-20 border border-dashed border-earth-700 rounded-2xl"
            >
              <Target size={40} className="mx-auto mb-4 text-earth-700" />
              <h3 className="text-base font-semibold text-earth-400 mb-2">Brak obserwowanych firm</h3>
              <p className="text-sm text-earth-600 mb-6">Dodaj konkurentów, żeby śledzić ich aktywność przetargową</p>
              <button
                onClick={() => setShowAdd(true)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-400 transition-colors"
              >
                <Plus size={15} />
                Dodaj pierwszą firmę
              </button>
            </motion.div>
          )}

          {!loading && filtered.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2">
              <AnimatePresence>
                {filtered.map(c => (
                  <CompetitorCard
                    key={c.id}
                    c={c}
                    onIntel={setIntelNip}
                    onDelete={handleDelete}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}

          {!loading && filtered.length === 0 && data.length > 0 && (
            <div className="text-center py-8 text-earth-500 text-sm">
              Brak wyników dla &quot;{searchQ}&quot;
            </div>
          )}

        </div>
      </PageShell>

      {/* ── Modals & panels ────────────────────────────────────────────────── */}
      <AnimatePresence>
        {intelNip && (
          <IntelPanel key="intel" nip={intelNip} onClose={() => setIntelNip(null)} />
        )}
        {showAdd && (
          <AddCompetitorModal
            key="add"
            onClose={() => setShowAdd(false)}
            onAdd={add}
          />
        )}
      </AnimatePresence>
    </>
  );
}
