'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Truck, Users, Zap, Building2,
  Plus, RefreshCw, CheckCircle, XCircle,
  ChevronRight, Loader2, Wrench, UserCheck,
  Phone, Briefcase, Tag, ClipboardList,
  Mail, Star, AlertCircle, Calendar,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { showToast } from '@/components/Toast';
import { useAuthFetch, type EmployeeResource, type EquipmentResource } from '@/lib/api-v2';

// ── Local types ────────────────────────────────────────────────────────────────

interface Subcontractor {
  id: string;
  name: string;
  nip: string | null;
  specialization: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  rating: number | null;
  notes: string | null;
  active: boolean;
}

interface OptimizationResult {
  feasible?: boolean;
  infeasible_reason?: string;
  routes?: unknown[];
  assignments?: Array<{
    employee?: string;
    equipment?: string;
    location?: string;
    day?: string;
    task?: string;
    [key: string]: unknown;
  }>;
  [key: string]: unknown;
}

type TabId = 'pracownicy' | 'sprzet' | 'optymalizacja' | 'podwykonawcy' | 'harmonogram';

// ── Helpers ────────────────────────────────────────────────────────────────────

function today() {
  return new Date().toISOString().slice(0, 10);
}
function inDays(n: number) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

// ── Skill chip ─────────────────────────────────────────────────────────────────

function SkillChip({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-accent-primary/10 text-accent-primary border border-accent-primary/20">
      {label}
    </span>
  );
}

// ── Active badge ───────────────────────────────────────────────────────────────

function ActiveBadge({ active }: { active: boolean }) {
  return active ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
      <CheckCircle className="w-3 h-3" /> Aktywny
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-red-500/15 text-red-400 border border-red-500/20">
      <XCircle className="w-3 h-3" /> Nieaktywny
    </span>
  );
}

// ── Empty state ────────────────────────────────────────────────────────────────

function EmptyState({ icon: Icon, message }: { icon: React.ElementType; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-earth-500">
      <Icon className="w-10 h-10 opacity-30" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ── Tab button ─────────────────────────────────────────────────────────────────

function TabBtn({
  active, onClick, icon: Icon, label,
}: {
  active: boolean; onClick: () => void; icon: React.ElementType; label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${
        active
          ? 'bg-accent-primary/15 text-accent-primary border border-accent-primary/30'
          : 'text-earth-400 hover:text-earth-200 hover:bg-earth-800/60'
      }`}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  );
}

// ════════════════════════════════════════════════════════════════════════════════
// Pracownicy tab
// ════════════════════════════════════════════════════════════════════════════════

function PracownicyTab() {
  const authFetch = useAuthFetch();
  const [employees, setEmployees] = useState<EmployeeResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: '', phone: '', role: '', skills: '' });

  const load = useCallback(() => {
    setLoading(true);
    authFetch('/api/v1/resources/employees')
      .then((d: EmployeeResource[] | { items?: EmployeeResource[] }) => {
        setEmployees(Array.isArray(d) ? d : (d.items ?? []));
      })
      .catch((e: Error) => showToast('error', e.message || 'Błąd pobierania pracowników'))
      .finally(() => setLoading(false));
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) { showToast('error', 'Imię i nazwisko jest wymagane'); return; }
    setSaving(true);
    try {
      const skills = form.skills.split(',').map(s => s.trim()).filter(Boolean);
      await authFetch('/api/v1/resources/employees', {
        method: 'POST',
        body: JSON.stringify({
          name: form.name.trim(),
          phone: form.phone.trim() || undefined,
          role: form.role.trim() || undefined,
          skills: skills.length ? skills : undefined,
        }),
      });
      showToast('success', 'Pracownik dodany');
      setForm({ name: '', phone: '', role: '', skills: '' });
      setShowForm(false);
      load();
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd zapisu');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-earth-300 text-sm">
          <UserCheck className="w-4 h-4 text-accent-primary" />
          <span>{employees.length} pracowników</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="p-2 rounded-lg text-earth-400 hover:text-earth-200 hover:bg-earth-800/60 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowForm(v => !v)}
            className="flex items-center gap-2 px-3 py-2 bg-accent-primary/15 hover:bg-accent-primary/25 text-accent-primary border border-accent-primary/30 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" /> Dodaj pracownika
          </button>
        </div>
      </div>

      {/* Add form */}
      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <GlassCard className="p-4">
              <h3 className="text-sm font-semibold text-earth-200 mb-3">Nowy pracownik</h3>
              <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Imię i nazwisko *</label>
                  <input
                    value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Jan Kowalski"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Telefon</label>
                  <input
                    value={form.phone}
                    onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                    placeholder="+48 600 000 000"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Rola / stanowisko</label>
                  <input
                    value={form.role}
                    onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                    placeholder="Operator maszyn"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Umiejętności (przecinek)</label>
                  <input
                    value={form.skills}
                    onChange={e => setForm(f => ({ ...f, skills: e.target.value }))}
                    placeholder="Koparka, Spawanie, Prawo jazdy C"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div className="sm:col-span-2 flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="px-4 py-2 text-sm text-earth-400 hover:text-earth-200 transition-colors"
                  >
                    Anuluj
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 bg-accent-primary text-earth-950 rounded-lg text-sm font-semibold hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    Zapisz
                  </button>
                </div>
              </form>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Table */}
      <GlassCard className="overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-accent-primary" />
          </div>
        ) : employees.length === 0 ? (
          <EmptyState icon={UserCheck} message="Brak pracowników. Dodaj pierwszego." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-earth-800/60">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Imię i nazwisko</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Telefon</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Rola</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Umiejętności</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody>
                {employees.map((emp, i) => (
                  <motion.tr
                    key={emp.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="border-b border-earth-800/30 hover:bg-earth-800/20 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-earth-100">{emp.name}</td>
                    <td className="px-4 py-3 text-earth-400">
                      {emp.phone ? (
                        <span className="flex items-center gap-1.5">
                          <Phone className="w-3.5 h-3.5" /> {emp.phone}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3 text-earth-300">{emp.role || '—'}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(emp.skills ?? []).length > 0
                          ? (emp.skills ?? []).map((s, j) => <SkillChip key={j} label={s} />)
                          : <span className="text-earth-600 text-xs">—</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <ActiveBadge active={(emp as EmployeeResource & { active?: boolean }).active !== false} />
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════════
// Sprzęt tab
// ════════════════════════════════════════════════════════════════════════════════

function SprzętTab() {
  const authFetch = useAuthFetch();
  const [equipment, setEquipment] = useState<EquipmentResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ type: '', model: '', reg_no: '', active: true });

  const load = useCallback(() => {
    setLoading(true);
    authFetch('/api/v1/resources/equipment')
      .then((d: EquipmentResource[] | { items?: EquipmentResource[] }) => {
        setEquipment(Array.isArray(d) ? d : (d.items ?? []));
      })
      .catch((e: Error) => showToast('error', e.message || 'Błąd pobierania sprzętu'))
      .finally(() => setLoading(false));
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.type.trim()) { showToast('error', 'Typ sprzętu jest wymagany'); return; }
    if (!form.model.trim()) { showToast('error', 'Model jest wymagany'); return; }
    setSaving(true);
    try {
      await authFetch('/api/v1/resources/equipment', {
        method: 'POST',
        body: JSON.stringify({
          type: form.type.trim(),
          model: form.model.trim(),
          reg_no: form.reg_no.trim() || undefined,
          active: form.active,
        }),
      });
      showToast('success', 'Sprzęt dodany');
      setForm({ type: '', model: '', reg_no: '', active: true });
      setShowForm(false);
      load();
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd zapisu');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-earth-300 text-sm">
          <Wrench className="w-4 h-4 text-accent-primary" />
          <span>{equipment.length} maszyn / pojazdów</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="p-2 rounded-lg text-earth-400 hover:text-earth-200 hover:bg-earth-800/60 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowForm(v => !v)}
            className="flex items-center gap-2 px-3 py-2 bg-accent-primary/15 hover:bg-accent-primary/25 text-accent-primary border border-accent-primary/30 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" /> Dodaj sprzęt
          </button>
        </div>
      </div>

      {/* Add form */}
      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <GlassCard className="p-4">
              <h3 className="text-sm font-semibold text-earth-200 mb-3">Nowy sprzęt / pojazd</h3>
              <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Typ *</label>
                  <input
                    value={form.type}
                    onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
                    placeholder="Koparka, Wywrotka, Walec..."
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Model *</label>
                  <input
                    value={form.model}
                    onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
                    placeholder="Komatsu PC210"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Nr rejestracyjny</label>
                  <input
                    value={form.reg_no}
                    onChange={e => setForm(f => ({ ...f, reg_no: e.target.value }))}
                    placeholder="WR 12345"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div className="flex items-center gap-3 pt-5">
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.active}
                      onChange={e => setForm(f => ({ ...f, active: e.target.checked }))}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-earth-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent-primary" />
                    <span className="ml-2 text-sm text-earth-300">Aktywny</span>
                  </label>
                </div>
                <div className="sm:col-span-2 flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="px-4 py-2 text-sm text-earth-400 hover:text-earth-200 transition-colors"
                  >
                    Anuluj
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 bg-accent-primary text-earth-950 rounded-lg text-sm font-semibold hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    Zapisz
                  </button>
                </div>
              </form>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Table */}
      <GlassCard className="overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-accent-primary" />
          </div>
        ) : equipment.length === 0 ? (
          <EmptyState icon={Truck} message="Brak sprzętu. Dodaj pierwszą maszynę." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-earth-800/60">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Typ</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Model</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Nr rejestracyjny</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody>
                {equipment.map((eq, i) => (
                  <motion.tr
                    key={eq.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="border-b border-earth-800/30 hover:bg-earth-800/20 transition-colors"
                  >
                    <td className="px-4 py-3 text-earth-300">
                      <span className="flex items-center gap-2">
                        <Truck className="w-3.5 h-3.5 text-earth-500" />
                        {eq.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-earth-100">{eq.model}</td>
                    <td className="px-4 py-3 text-earth-400 font-mono text-xs">{eq.reg_no || '—'}</td>
                    <td className="px-4 py-3">
                      <ActiveBadge active={eq.active} />
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════════
// Optymalizacja tab
// ════════════════════════════════════════════════════════════════════════════════

function OptymalizacjaTab() {
  const authFetch = useAuthFetch();
  const [from, setFrom] = useState(today());
  const [to, setTo] = useState(inDays(7));
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleOptimize = async () => {
    if (!from || !to) { showToast('error', 'Wybierz zakres dat'); return; }
    if (from > to) { showToast('error', 'Data końcowa musi być późniejsza'); return; }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await authFetch('/api/v1/logistics/optimize', {
        method: 'POST',
        body: JSON.stringify({ day_range: [from, to] }),
      });
      setResult(res);
      showToast('success', 'Optymalizacja zakończona');
    } catch (e: unknown) {
      const msg = (e as Error).message || 'Błąd optymalizacji';
      setError(msg);
      showToast('error', msg);
    } finally {
      setLoading(false);
    }
  };

  const hasAssignments = result?.assignments && Array.isArray(result.assignments) && result.assignments.length > 0;

  return (
    <div className="space-y-4">
      {/* Controls */}
      <GlassCard className="p-5">
        <h3 className="text-sm font-semibold text-earth-200 mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-accent-primary" />
          Parametry optymalizacji
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
          <div>
            <label className="block text-xs text-earth-400 mb-1">Data od</label>
            <input
              type="date"
              value={from}
              onChange={e => setFrom(e.target.value)}
              className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm focus:outline-none focus:border-accent-primary/50"
            />
          </div>
          <div>
            <label className="block text-xs text-earth-400 mb-1">Data do</label>
            <input
              type="date"
              value={to}
              onChange={e => setTo(e.target.value)}
              className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm focus:outline-none focus:border-accent-primary/50"
            />
          </div>
          <button
            onClick={handleOptimize}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-accent-primary text-earth-950 rounded-lg font-semibold text-sm hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Obliczam…
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                Optymalizuj
              </>
            )}
          </button>
        </div>
        <p className="mt-3 text-xs text-earth-500">
          Silnik AI przydzieli dostępnych pracowników i sprzęt do zaplanowanych kontraktów w wybranym zakresie dat.
        </p>
      </GlassCard>

      {/* Error */}
      {error && (
        <GlassCard className="p-4 border-red-500/20 bg-red-500/5">
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        </GlassCard>
      )}

      {/* Result */}
      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <GlassCard className="overflow-hidden">
            <div className="px-4 py-3 border-b border-earth-800/60 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-earth-200 flex items-center gap-2">
                <ClipboardList className="w-4 h-4 text-accent-primary" />
                Wynik optymalizacji
              </h3>
              {hasAssignments && (
                <span className="text-xs text-earth-400 bg-earth-800/60 px-2 py-1 rounded-full">
                  {result.assignments!.length} przypisań
                </span>
              )}
            </div>

            {hasAssignments ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-earth-800/60">
                      {(['day', 'employee', 'equipment', 'location', 'task'] as const).map(col => (
                        <th key={col} className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide capitalize">
                          {col === 'day' ? 'Dzień' : col === 'employee' ? 'Pracownik' : col === 'equipment' ? 'Sprzęt' : col === 'location' ? 'Lokalizacja' : 'Zadanie'}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.assignments!.map((row, i) => (
                      <tr key={i} className="border-b border-earth-800/30 hover:bg-earth-800/20 transition-colors">
                        <td className="px-4 py-2.5 text-earth-400 font-mono text-xs">{row.day ?? '—'}</td>
                        <td className="px-4 py-2.5 text-earth-200">{row.employee ?? '—'}</td>
                        <td className="px-4 py-2.5 text-earth-300">{row.equipment ?? '—'}</td>
                        <td className="px-4 py-2.5 text-earth-400 text-xs">{row.location ?? '—'}</td>
                        <td className="px-4 py-2.5 text-earth-300">{row.task ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              /* Empty assignments — optimizer ran but found no feasible assignments */
              <div className="flex flex-col items-center justify-center py-16 gap-4 text-earth-500">
                <div className="w-16 h-16 rounded-2xl bg-earth-800/40 flex items-center justify-center">
                  <Zap className="w-8 h-8 opacity-30" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-earth-400 mb-1">
                    {result.feasible === false ? 'Brak rozwiązania' : 'Brak przypisań w tym zakresie'}
                  </p>
                  <p className="text-xs text-earth-600 max-w-sm">
                    {result.infeasible_reason ?? 'Optymalizator nie znalazł przypisań dla wybranego zakresu dat. Sprawdź dostępność pracowników i sprzętu.'}
                  </p>
                </div>
                {Array.isArray(result.routes) && result.routes.length > 0 && (
                  <div className="mt-2 text-xs text-earth-500">
                    Trasy: {result.routes.length} zidentyfikowanych tras
                  </div>
                )}
              </div>
            )}
          </GlassCard>
        </motion.div>
      )}

      {!result && !loading && !error && (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-earth-600">
          <Zap className="w-10 h-10 opacity-20" />
          <p className="text-sm">Ustaw zakres dat i kliknij „Optymalizuj"</p>
        </div>
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════════
// Podwykonawcy tab
// ════════════════════════════════════════════════════════════════════════════════

function PodwykonawcyTab() {
  const authFetch = useAuthFetch();
  const [subs, setSubs] = useState<Subcontractor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: '', nip: '', specialization: '',
    contact_email: '', contact_phone: '', rating: '', notes: '',
  });

  const load = useCallback(() => {
    setLoading(true);
    // Try v2 endpoint; gracefully fall back to empty if 404/403
    authFetch('/api/v1/subcontractors?limit=100')
      .then((d: Subcontractor[] | { items?: Subcontractor[] }) => {
        setSubs(Array.isArray(d) ? d : (d.items ?? []));
      })
      .catch(() => setSubs([]))
      .finally(() => setLoading(false));
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) { showToast('error', 'Nazwa podwykonawcy jest wymagana'); return; }
    setSaving(true);
    try {
      await authFetch('/api/v1/subcontractors', {
        method: 'POST',
        body: JSON.stringify({
          name: form.name.trim(),
          nip: form.nip.trim() || undefined,
          specialization: form.specialization.trim() || undefined,
          contact_email: form.contact_email.trim() || undefined,
          contact_phone: form.contact_phone.trim() || undefined,
          rating: form.rating ? parseFloat(form.rating) : undefined,
          notes: form.notes.trim() || undefined,
        }),
      });
      showToast('success', 'Podwykonawca dodany');
      setForm({ name: '', nip: '', specialization: '', contact_email: '', contact_phone: '', rating: '', notes: '' });
      setShowForm(false);
      load();
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd zapisu');
    } finally {
      setSaving(false);
    }
  };

  function ratingStars(r: number | null) {
    if (r == null) return <span className="text-earth-600 text-xs">—</span>;
    const full = Math.round(r);
    return (
      <div className="flex items-center gap-0.5">
        {[1,2,3,4,5].map(i => (
          <Star key={i} className={`w-3 h-3 ${i <= full ? 'text-yellow-400 fill-yellow-400' : 'text-earth-700'}`} />
        ))}
        <span className="ml-1 text-xs text-earth-400">{r.toFixed(1)}</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-earth-300 text-sm">
          <Building2 className="w-4 h-4 text-accent-primary" />
          <span>{subs.length} podwykonawców</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="p-2 rounded-lg text-earth-400 hover:text-earth-200 hover:bg-earth-800/60 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowForm(v => !v)}
            className="flex items-center gap-2 px-3 py-2 bg-accent-primary/15 hover:bg-accent-primary/25 text-accent-primary border border-accent-primary/30 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" /> Dodaj podwykonawcę
          </button>
        </div>
      </div>

      {/* Add form */}
      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <GlassCard className="p-4">
              <h3 className="text-sm font-semibold text-earth-200 mb-3">Nowy podwykonawca</h3>
              <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Nazwa firmy *</label>
                  <input
                    value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Firma Budowlana XYZ"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-earth-400 mb-1">NIP</label>
                  <input
                    value={form.nip}
                    onChange={e => setForm(f => ({ ...f, nip: e.target.value }))}
                    placeholder="1234567890"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Specjalizacja</label>
                  <input
                    value={form.specialization}
                    onChange={e => setForm(f => ({ ...f, specialization: e.target.value }))}
                    placeholder="Instalacje elektryczne, Fundamenty…"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Email kontaktowy</label>
                  <input
                    type="email"
                    value={form.contact_email}
                    onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))}
                    placeholder="kontakt@firma.pl"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Telefon kontaktowy</label>
                  <input
                    value={form.contact_phone}
                    onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))}
                    placeholder="+48 600 000 000"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-earth-400 mb-1">Ocena (1–5)</label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    step="0.1"
                    value={form.rating}
                    onChange={e => setForm(f => ({ ...f, rating: e.target.value }))}
                    placeholder="4.5"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs text-earth-400 mb-1">Notatki</label>
                  <textarea
                    value={form.notes}
                    onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                    rows={2}
                    placeholder="Uwagi, warunki współpracy…"
                    className="w-full px-3 py-2 bg-earth-800/60 border border-earth-700/50 rounded-lg text-earth-100 text-sm placeholder-earth-600 focus:outline-none focus:border-accent-primary/50 resize-none"
                  />
                </div>
                <div className="sm:col-span-2 flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="px-4 py-2 text-sm text-earth-400 hover:text-earth-200 transition-colors"
                  >
                    Anuluj
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 bg-accent-primary text-earth-950 rounded-lg text-sm font-semibold hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    Zapisz
                  </button>
                </div>
              </form>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Table */}
      <GlassCard className="overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-accent-primary" />
          </div>
        ) : subs.length === 0 ? (
          <EmptyState icon={Building2} message="Brak podwykonawców. Dodaj pierwszego." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-earth-800/60">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Nazwa</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">NIP</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Specjalizacja</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Ocena</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Kontakt</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-earth-500 uppercase tracking-wide">Status</th>
                </tr>
              </thead>
              <tbody>
                {subs.map((sub, i) => (
                  <motion.tr
                    key={sub.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="border-b border-earth-800/30 hover:bg-earth-800/20 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-earth-100">{sub.name}</td>
                    <td className="px-4 py-3 text-earth-400 font-mono text-xs">{sub.nip || '—'}</td>
                    <td className="px-4 py-3 text-earth-300">
                      {sub.specialization ? (
                        <span className="flex items-center gap-1.5">
                          <Tag className="w-3 h-3 text-earth-500" />
                          {sub.specialization}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3">{ratingStars(sub.rating)}</td>
                    <td className="px-4 py-3">
                      <div className="space-y-0.5">
                        {sub.contact_email && (
                          <a href={`mailto:${sub.contact_email}`} className="flex items-center gap-1 text-xs text-earth-400 hover:text-accent-primary transition-colors">
                            <Mail className="w-3 h-3" /> {sub.contact_email}
                          </a>
                        )}
                        {sub.contact_phone && (
                          <span className="flex items-center gap-1 text-xs text-earth-400">
                            <Phone className="w-3 h-3" /> {sub.contact_phone}
                          </span>
                        )}
                        {!sub.contact_email && !sub.contact_phone && <span className="text-earth-600 text-xs">—</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <ActiveBadge active={sub.active} />
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════════
// Harmonogram tab — custom CSS Gantt chart
// ════════════════════════════════════════════════════════════════════════════════

interface Contract {
  id: string;
  title: string;
  state: string;
  start_date: string | null;
  end_date: string | null;
  location_address: string | null;
  required_skills: string[];
  required_equipment: string[];
}

interface ContractsResponse {
  items?: Contract[];
  data?: Contract[];
  contracts?: Contract[];
}

// Palette — 8 distinct accent colours, cycling by index
const GANTT_COLORS: string[] = [
  '#4f8ef7', // blue
  '#34d399', // emerald
  '#f59e0b', // amber
  '#a78bfa', // violet
  '#f472b6', // pink
  '#38bdf8', // sky
  '#fb923c', // orange
  '#84cc16', // lime
];

// CURRENT_DATE = max(date) in DB per spec = 2025-12-22
const GANTT_ORIGIN = '2025-12-22';
const GANTT_DAYS = 60;

function addDays(base: string, n: number): string {
  const d = new Date(base);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function daysBetween(a: string, b: string): number {
  return Math.round(
    (new Date(b).getTime() - new Date(a).getTime()) / 86_400_000
  );
}

// Generate header tick marks (every 7 days, show date label)
function buildTicks(): string[] {
  const ticks: string[] = [];
  for (let i = 0; i <= GANTT_DAYS; i += 7) {
    ticks.push(addDays(GANTT_ORIGIN, i));
  }
  return ticks;
}

// Fallback: if a contract has no dates, spread across the window using its index
function syntheticDates(idx: number, total: number): { start: string; end: string } {
  const slotSize = Math.floor(GANTT_DAYS / Math.max(total, 1));
  const start = Math.min(idx * slotSize, GANTT_DAYS - 7);
  const end   = Math.min(start + Math.max(slotSize - 2, 5), GANTT_DAYS);
  return {
    start: addDays(GANTT_ORIGIN, start),
    end:   addDays(GANTT_ORIGIN, end),
  };
}

function stateLabel(state: string): string {
  const map: Record<string, string> = {
    open:       'Otwarte',
    active:     'Aktywne',
    closed:     'Zamknięte',
    draft:      'Szkic',
    cancelled:  'Anulowane',
  };
  return map[state] ?? state;
}

function HarmonogramTab() {
  const authFetch = useAuthFetch();
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [tooltip, setTooltip]     = useState<{ contract: Contract; x: number; y: number } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch('/api/v1/contracts');
      if (!res.ok) throw new Error('HTTP ' + String(res.status));
      const raw: Contract[] | ContractsResponse = await res.json();
      const list: Contract[] = Array.isArray(raw)
        ? raw
        : (raw as ContractsResponse).items
          ?? (raw as ContractsResponse).data
          ?? (raw as ContractsResponse).contracts
          ?? [];
      setContracts(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Błąd pobierania danych');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { void load(); }, [load]);

  const ticks = buildTicks();
  const endDate = addDays(GANTT_ORIGIN, GANTT_DAYS);

  // Enrich contracts with computed bar positions
  const rows = contracts.map((c, idx) => {
    const hasDates = c.start_date && c.end_date;
    const { start: s, end: e } = hasDates
      ? { start: c.start_date as string, end: c.end_date as string }
      : syntheticDates(idx, contracts.length);

    // Clamp to window
    const clampedStart = s < GANTT_ORIGIN ? GANTT_ORIGIN : s > endDate ? endDate : s;
    const clampedEnd   = e > endDate ? endDate : e < GANTT_ORIGIN ? GANTT_ORIGIN : e;

    const offsetDays = daysBetween(GANTT_ORIGIN, clampedStart);
    const spanDays   = Math.max(daysBetween(clampedStart, clampedEnd), 1);

    const left  = (offsetDays / GANTT_DAYS) * 100;
    const width = (spanDays  / GANTT_DAYS) * 100;

    return {
      contract: c,
      start: s,
      end: e,
      left:  Math.max(0, Math.min(left,  100)),
      width: Math.max(0.5, Math.min(width, 100 - left)),
      color: GANTT_COLORS[idx % GANTT_COLORS.length],
      synthetic: !hasDates,
    };
  });

  return (
    <GlassCard className="p-4 md:p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-accent-primary" />
          <h2 className="text-base font-semibold text-earth-100">Harmonogram kontraktów</h2>
          <span className="text-xs text-earth-500 ml-1">
            {GANTT_ORIGIN} → {endDate}
          </span>
        </div>
        <button
          onClick={() => { void load(); }}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-earth-800/60 hover:bg-earth-700/60 border border-earth-700/40 text-earth-300 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={loading ? 'w-3.5 h-3.5 animate-spin' : 'w-3.5 h-3.5'} />
          Odśwież
        </button>
      </div>

      {/* States */}
      {loading && (
        <div className="flex items-center justify-center py-16 gap-2 text-earth-500">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Ładowanie harmonogramu…</span>
        </div>
      )}

      {!loading && error && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {!loading && !error && contracts.length === 0 && (
        <EmptyState icon={Calendar} message="Brak kontraktów do wyświetlenia" />
      )}

      {!loading && !error && contracts.length > 0 && (
        <div
          className="relative overflow-x-auto"
          onMouseLeave={() => setTooltip(null)}
        >
          {/* Gantt grid wrapper */}
          <div style={{ minWidth: '640px' }}>

            {/* ── Timeline header ── */}
            <div className="flex mb-1">
              {/* Row label spacer */}
              <div style={{ width: '200px', flexShrink: 0 }} />
              {/* Tick marks */}
              <div className="relative flex-1 h-6">
                {ticks.map(tick => {
                  const pct = (daysBetween(GANTT_ORIGIN, tick) / GANTT_DAYS) * 100;
                  return (
                    <div
                      key={tick}
                      className="absolute top-0 flex flex-col items-center"
                      style={{ left: String(pct) + '%', transform: 'translateX(-50%)' }}
                    >
                      <span className="text-[10px] text-earth-500 whitespace-nowrap">
                        {tick.slice(5)} {/* MM-DD */}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── Grid lines layer (behind rows) ── */}
            <div className="relative">

              {/* vertical grid lines at each tick */}
              <div
                className="absolute inset-0 pointer-events-none"
                aria-hidden="true"
                style={{ left: '200px' }}
              >
                {ticks.map(tick => {
                  const pct = (daysBetween(GANTT_ORIGIN, tick) / GANTT_DAYS) * 100;
                  return (
                    <div
                      key={tick}
                      className="absolute top-0 bottom-0 border-l border-earth-800/40"
                      style={{ left: String(pct) + '%' }}
                    />
                  );
                })}
              </div>

              {/* ── Rows ── */}
              {rows.map(row => (
                <div
                  key={row.contract.id}
                  className="flex items-center border-b border-earth-800/30 group"
                  style={{ height: '44px' }}
                >
                  {/* Row label */}
                  <div
                    style={{ width: '200px', flexShrink: 0 }}
                    className="pr-3 flex flex-col justify-center"
                  >
                    <span className="text-xs font-medium text-earth-200 truncate leading-tight">
                      {row.contract.title}
                    </span>
                    <span className="text-[10px] text-earth-500 truncate leading-tight">
                      {stateLabel(row.contract.state)}
                      {row.synthetic && (
                        <span className="ml-1 text-earth-600">(est.)</span>
                      )}
                    </span>
                  </div>

                  {/* Bar track */}
                  <div className="relative flex-1 h-full flex items-center">
                    <div
                      className="absolute inset-y-0 flex items-center"
                      style={{ left: String(row.left) + '%', width: String(row.width) + '%' }}
                    >
                      <div
                        className="w-full h-6 rounded-md cursor-pointer transition-opacity hover:opacity-90 flex items-center px-2 overflow-hidden"
                        style={{ backgroundColor: row.color + '33', border: '1px solid ' + row.color + '99' }}
                        onMouseEnter={e => {
                          const rect = (e.target as HTMLElement).getBoundingClientRect();
                          setTooltip({ contract: row.contract, x: rect.left + rect.width / 2, y: rect.top });
                        }}
                        onMouseMove={e => {
                          setTooltip(prev => prev
                            ? { ...prev, x: e.clientX, y: e.clientY - 8 }
                            : prev
                          );
                        }}
                        onMouseLeave={() => setTooltip(null)}
                      >
                        <span
                          className="text-[10px] font-medium truncate leading-none"
                          style={{ color: row.color }}
                        >
                          {row.contract.title}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Legend */}
          <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1.5 text-[11px] text-earth-500">
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 rounded-sm border border-earth-600/60" style={{ background: GANTT_COLORS[0] + '33' }} />
              Kontrakt z datami
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 rounded-sm border border-earth-600/60" style={{ background: GANTT_COLORS[1] + '33' }} />
              Kontrakt estymowany (brak dat)
            </span>
            <span className="text-earth-600">
              Oś czasu: {GANTT_ORIGIN} + {String(GANTT_DAYS)} dni
            </span>
          </div>
        </div>
      )}

      {/* Tooltip portal (fixed position) */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none"
          style={{ left: String(tooltip.x) + 'px', top: String(tooltip.y - 56) + 'px', transform: 'translateX(-50%)' }}
        >
          <div className="bg-earth-900 border border-earth-700/60 rounded-lg px-3 py-2 shadow-xl text-xs space-y-0.5 min-w-max">
            <p className="font-semibold text-earth-100">{tooltip.contract.title}</p>
            <p className="text-earth-400">
              Stan: <span className="text-earth-200">{stateLabel(tooltip.contract.state)}</span>
            </p>
            {tooltip.contract.start_date && (
              <p className="text-earth-400">
                Od: <span className="text-earth-200">{tooltip.contract.start_date}</span>
              </p>
            )}
            {tooltip.contract.end_date && (
              <p className="text-earth-400">
                Do: <span className="text-earth-200">{tooltip.contract.end_date}</span>
              </p>
            )}
            {!tooltip.contract.start_date && (
              <p className="text-earth-600 italic">Brak dat – pozycja estymowana</p>
            )}
            {tooltip.contract.location_address && (
              <p className="text-earth-400 truncate max-w-[200px]">
                {tooltip.contract.location_address}
              </p>
            )}
          </div>
        </div>
      )}
    </GlassCard>
  );
}

// ════════════════════════════════════════════════════════════════════════════════
// Main LogistykaPage
// ════════════════════════════════════════════════════════════════════════════════

const TABS: Array<{ id: TabId; label: string; icon: React.ElementType }> = [
  { id: 'pracownicy',    label: 'Pracownicy',    icon: Users        },
  { id: 'sprzet',       label: 'Sprzęt',        icon: Truck        },
  { id: 'optymalizacja', label: 'Optymalizacja', icon: Zap          },
  { id: 'podwykonawcy', label: 'Podwykonawcy',  icon: Building2    },
  { id: 'harmonogram',  label: 'Harmonogram',   icon: Calendar     },
];

export function LogistykaPage() {
  const [activeTab, setActiveTab] = useState<TabId>('pracownicy');

  return (
    <div className="min-h-screen bg-earth-950 p-4 md:p-6 space-y-5">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center flex-shrink-0">
          <Truck className="w-5 h-5 text-accent-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-earth-100 leading-tight">Logistyka</h1>
          <p className="text-xs text-earth-500">Zarządzaj zasobami — pracownicy, sprzęt, optymalizacja tras</p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-2">
        {TABS.map(tab => (
          <TabBtn
            key={tab.id}
            active={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            icon={tab.icon}
            label={tab.label}
          />
        ))}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.18 }}
        >
          {activeTab === 'pracownicy'    && <PracownicyTab />}
          {activeTab === 'sprzet'        && <SprzętTab />}
          {activeTab === 'optymalizacja' && <OptymalizacjaTab />}
          {activeTab === 'podwykonawcy'  && <PodwykonawcyTab />}
          {activeTab === 'harmonogram'   && <HarmonogramTab />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
