'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import {
  Building2, Phone, Mail, CalendarClock, Trash2, Edit3, Plus, Search, X,
  ChevronRight, AlertTriangle, TrendingUp, CheckCircle, Clock, RefreshCw,
  MapPin, Star, FileText, Users,
} from 'lucide-react';
import { PageShell } from '@/components/PageShell';
import { SkeletonCard } from '@/components/SkeletonCard';
import { showToast } from '@/components/Toast';
import {
  useBuyerCRM, useAuthFetch, fmtMln, fmtPLN, PROVINCE_MAP,
  type BuyerCRM, type Followup,
} from '@/lib/api-v2';

// ── Extended types ─────────────────────────────────────────────────────────────

interface BuyerCRMItem extends BuyerCRM {
  city?: string | null;
  province?: string | null;
  total_value?: number | null;
  preferred_cpv?: string[];
}

interface BuyerSearchResult {
  nip: string;
  name: string;
  city: string | null;
  province: string | null;
  total_tenders: number;
  total_value: number;
  top_cpv: Array<{ code: string; name: string; count: number }>;
}

interface TenderItem {
  ht_id: string;
  title: string;
  submission_deadline: string | null;
  value: number | null;
  cpv5: string | null;
  status: string | null;
}

type CRMStage = 'prospect' | 'contacted' | 'demo' | 'active' | 'churned';

// ── Constants ──────────────────────────────────────────────────────────────────

const STAGES: Array<{ id: CRMStage; label: string }> = [
  { id: 'prospect',  label: 'Prospekt'  },
  { id: 'contacted', label: 'Kontakt'   },
  { id: 'demo',      label: 'Demo'      },
  { id: 'active',    label: 'Aktywny'   },
  { id: 'churned',   label: 'Stracony'  },
];

const STAGE_COLORS: Record<CRMStage, string> = {
  prospect:  'bg-zinc-700 text-zinc-300 border-zinc-600',
  contacted: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
  demo:      'bg-purple-500/20 text-purple-300 border-purple-500/40',
  active:    'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
  churned:   'bg-red-500/20 text-red-300 border-red-500/40',
};

const STAGE_DOT: Record<CRMStage, string> = {
  prospect:  'bg-zinc-400',
  contacted: 'bg-blue-400',
  demo:      'bg-purple-400',
  active:    'bg-emerald-400',
  churned:   'bg-red-400',
};

const PRIORITY_COLORS = ['', 'bg-zinc-500', 'bg-yellow-600', 'bg-yellow-400', 'bg-orange-400', 'bg-red-500'];
const CPV_BAR_COLORS  = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'];

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.${d.getFullYear()}`;
}

function isOverdue(iso: string | null | undefined): boolean {
  if (!iso) return false;
  return new Date(iso) < new Date();
}

function cityLabel(item: BuyerCRMItem): string {
  const c = item.city ?? item.buyer_city;
  const p = item.province ?? item.buyer_province;
  if (c && p) return `${c}, ${PROVINCE_MAP[p] ?? p}`;
  if (c) return c;
  if (p) return PROVINCE_MAP[p] ?? p;
  return '—';
}

// ── StageBadge ─────────────────────────────────────────────────────────────────

function StageBadge({ stage }: { stage: string }) {
  const s = stage as CRMStage;
  const found = STAGES.find(x => x.id === s);
  const cls = STAGE_COLORS[s] ?? 'bg-zinc-700 text-zinc-300 border-zinc-600';
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-0.5 rounded-full border ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${STAGE_DOT[s] ?? 'bg-zinc-400'}`} />
      {found?.label ?? stage}
    </span>
  );
}

// ── PriorityDots ───────────────────────────────────────────────────────────────

function PriorityDots({ priority }: { priority: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <span
          key={i}
          className={`w-2 h-2 rounded-full ${i < priority ? PRIORITY_COLORS[priority] : 'bg-earth-700'}`}
        />
      ))}
    </div>
  );
}

// ── FollowupBanner ─────────────────────────────────────────────────────────────

function FollowupBanner({ followups, onDismiss }: { followups: Followup[]; onDismiss: () => void }) {
  const overdue = followups.filter(f => isOverdue(f.next_followup));
  const upcoming = followups.filter(f => !isOverdue(f.next_followup));
  if (followups.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="flex items-center gap-3 px-4 py-2.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-sm mb-4"
    >
      <AlertTriangle size={15} className="text-amber-400 shrink-0" />
      <div className="flex-1 flex flex-wrap items-center gap-x-4 gap-y-0.5">
        {overdue.length > 0 && (
          <span className="text-amber-300 font-medium">
            {overdue.length} przeterminowanych follow-up
          </span>
        )}
        {upcoming.length > 0 && (
          <span className="text-earth-400">
            {upcoming.length} zaplanowanych w tym tygodniu
          </span>
        )}
        <span className="text-earth-500 text-xs">
          {followups.slice(0, 3).map(f => f.buyer_name ?? f.buyer_nip).join(', ')}
          {followups.length > 3 ? ` +${followups.length - 3}` : ''}
        </span>
      </div>
      <button onClick={onDismiss} className="p-1 hover:bg-earth-800 rounded transition-colors">
        <X size={13} className="text-earth-500" />
      </button>
    </motion.div>
  );
}

// ── BuyerCard (left list) ──────────────────────────────────────────────────────

function BuyerCard({
  item, selected, onClick,
}: {
  item: BuyerCRMItem; selected: boolean; onClick: () => void;
}) {
  const overdue = isOverdue(item.next_followup);
  return (
    <motion.button
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -12 }}
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border transition-all group
        ${selected
          ? 'bg-earth-800 border-emerald-500/50 shadow-lg shadow-emerald-500/5'
          : 'bg-earth-900 border-earth-700 hover:border-earth-600 hover:bg-earth-850'}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-earth-100 truncate text-sm leading-tight">
            {item.buyer_name ?? item.buyer_nip}
          </div>
          <div className="text-xs text-earth-500 font-mono mt-0.5">{item.buyer_nip}</div>
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <StageBadge stage={item.crm_stage} />
          <PriorityDots priority={item.priority} />
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs text-earth-500 flex-wrap">
        {(item.city ?? item.buyer_city) && (
          <span className="flex items-center gap-1">
            <MapPin size={11} className="shrink-0" />
            {cityLabel(item)}
          </span>
        )}
        {item.contact_name && (
          <span className="flex items-center gap-1">
            <Users size={11} className="shrink-0" />
            {item.contact_name}
          </span>
        )}
      </div>

      {item.next_followup && (
        <div className={`mt-2 flex items-center gap-1 text-xs ${overdue ? 'text-red-400' : 'text-amber-400'}`}>
          {overdue ? <AlertTriangle size={11} /> : <Clock size={11} />}
          Follow-up: {fmtDate(item.next_followup)}
        </div>
      )}

      <div className="flex items-center justify-between mt-2">
        <div className="flex gap-3 text-xs">
          {item.total_tenders != null && (
            <span className="text-earth-400">{item.total_tenders} przetargów</span>
          )}
          {(item.total_value != null || item.annual_budget_est != null) && (
            <span className="text-emerald-400 font-mono">
              {fmtPLN(item.annual_budget_est ?? item.total_value ?? 0)}
            </span>
          )}
        </div>
        <ChevronRight size={14} className={`text-earth-600 group-hover:text-earth-400 transition-colors ${selected ? 'text-emerald-500' : ''}`} />
      </div>
    </motion.button>
  );
}

// ── TendersTab ─────────────────────────────────────────────────────────────────

function TendersTab({ itemId }: { itemId: string }) {
  const authFetch = useAuthFetch();
  const [tenders, setTenders] = useState<TenderItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    authFetch(`/api/v2/buyer-crm/${itemId}/tenders?offset=0&limit=20`)
      .then((d: { tenders?: TenderItem[]; items?: TenderItem[]; total_tenders_all_time?: number; total?: number }) => {
        if (!cancelled) {
          setTenders(d.tenders || d.items || []);
          setTotal(d.total_tenders_all_time ?? d.total ?? 0);
        }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [authFetch, itemId]);

  if (loading) return (
    <div className="space-y-2 pt-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-14 animate-pulse bg-earth-800 rounded-lg" />
      ))}
    </div>
  );

  if (tenders.length === 0) return (
    <div className="text-center py-10 text-earth-500 text-sm">
      <FileText size={28} className="mx-auto mb-2 text-earth-700" />
      Brak przetargów w historii
    </div>
  );

  return (
    <div className="space-y-2 pt-1">
      <div className="text-xs text-earth-500 mb-2">
        Łącznie: {total} przetargów
      </div>
      {tenders.map((t, i) => (
        <motion.div
          key={t.ht_id}
          initial={{ opacity: 0, x: 6 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.03 }}
          className="p-3 bg-earth-800 rounded-lg border border-earth-700 hover:border-earth-600 transition-colors"
        >
          <div className="text-sm text-earth-100 line-clamp-2 mb-1.5">{t.title}</div>
          <div className="flex items-center gap-3 flex-wrap">
            {t.submission_deadline && (
              <span className="text-xs text-earth-500 flex items-center gap-1">
                <CalendarClock size={11} />
                {fmtDate(t.submission_deadline)}
              </span>
            )}
            {t.cpv5 && (
              <span className="text-xs font-mono bg-earth-700 text-earth-400 px-1.5 py-0.5 rounded">
                CPV {t.cpv5.slice(0, 8)}
              </span>
            )}
            {t.status && (
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                t.status === 'completed' ? 'bg-emerald-500/15 text-emerald-400' :
                t.status === 'cancelled' ? 'bg-red-500/15 text-red-400' :
                'bg-earth-700 text-earth-400'
              }`}>{t.status}</span>
            )}
            {t.value != null && (
              <span className="text-xs text-emerald-400 font-mono ml-auto">
                {fmtMln(t.value / 1_000_000)}
              </span>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ── BuyerProfilePanel (right slide-in) ────────────────────────────────────────

type ProfileTab = 'kontakt' | 'notatki' | 'historia' | 'followup';

function BuyerProfilePanel({
  item,
  onClose,
  onUpdate,
  onDelete,
}: {
  item: BuyerCRMItem;
  onClose: () => void;
  onUpdate: (id: string, body: Record<string, unknown>) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [tab, setTab] = useState<ProfileTab>('kontakt');
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saving, setSaving] = useState(false);

  // Editable form state
  const [form, setForm] = useState({
    contact_name:     item.contact_name     ?? '',
    contact_email:    item.contact_email    ?? '',
    contact_phone:    item.contact_phone    ?? '',
    territory:        item.territory        ?? '',
    annual_budget_est: item.annual_budget_est != null ? String(item.annual_budget_est) : '',
    preferred_cpv:    (item.preferred_cpv ?? []).join(', '),
    notes:            item.notes            ?? '',
    last_contact:     item.last_contact     ? item.last_contact.slice(0, 10) : '',
    next_followup:    item.next_followup    ? item.next_followup.slice(0, 10) : '',
    crm_stage:        item.crm_stage,
    priority:         item.priority,
  });

  // Sync form when item changes (after save/reload)
  useEffect(() => {
    setForm({
      contact_name:     item.contact_name     ?? '',
      contact_email:    item.contact_email    ?? '',
      contact_phone:    item.contact_phone    ?? '',
      territory:        item.territory        ?? '',
      annual_budget_est: item.annual_budget_est != null ? String(item.annual_budget_est) : '',
      preferred_cpv:    (item.preferred_cpv ?? []).join(', '),
      notes:            item.notes            ?? '',
      last_contact:     item.last_contact     ? item.last_contact.slice(0, 10) : '',
      next_followup:    item.next_followup    ? item.next_followup.slice(0, 10) : '',
      crm_stage:        item.crm_stage,
      priority:         item.priority,
    });
    setEditing(false);
  }, [item.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = async () => {
    setSaving(true);
    try {
      const body: Record<string, unknown> = {
        contact_name:  form.contact_name  || null,
        contact_email: form.contact_email || null,
        contact_phone: form.contact_phone || null,
        territory:     form.territory     || null,
        notes:         form.notes         || null,
        crm_stage:     form.crm_stage,
        priority:      form.priority,
        last_contact:  form.last_contact  || null,
        next_followup: form.next_followup || null,
        annual_budget_est: form.annual_budget_est ? Number(form.annual_budget_est) : null,
        preferred_cpv: form.preferred_cpv
          ? form.preferred_cpv.split(',').map(s => s.trim()).filter(Boolean)
          : [],
      };
      await onUpdate(item.id, body);
      setEditing(false);
      showToast('success', 'Zapisano zmiany');
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd zapisu');
    } finally {
      setSaving(false);
    }
  };

  const handleStageQuick = async (stage: CRMStage) => {
    try {
      await onUpdate(item.id, { crm_stage: stage });
      showToast('success', `Etap zmieniony na: ${STAGES.find(s => s.id === stage)?.label}`);
    } catch {
      showToast('error', 'Błąd zmiany etapu');
    }
  };

  const handleDelete = async () => {
    if (!deleting) { setDeleting(true); return; }
    try {
      await onDelete(item.id);
      showToast('success', 'Rekord usunięty');
      onClose();
    } catch {
      showToast('error', 'Błąd usuwania');
    } finally {
      setDeleting(false);
    }
  };

  const tabs: Array<{ id: ProfileTab; label: string; icon: React.ReactNode }> = [
    { id: 'kontakt',  label: 'Kontakt',   icon: <Phone size={13} />        },
    { id: 'notatki',  label: 'Notatki',   icon: <Edit3 size={13} />        },
    { id: 'historia', label: 'Historia',  icon: <TrendingUp size={13} />   },
    { id: 'followup', label: 'Follow-up', icon: <CalendarClock size={13} /> },
  ];

  const inputCls = 'w-full bg-earth-800 border border-earth-700 rounded-lg px-3 py-2 text-sm text-earth-100 placeholder-earth-500 focus:outline-none focus:border-emerald-500 transition-colors';
  const labelCls = 'block text-xs text-earth-500 mb-1';

  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', damping: 28, stiffness: 300 }}
      className="fixed right-0 top-0 h-full w-full max-w-lg bg-earth-950 border-l border-earth-700 z-50 overflow-y-auto shadow-2xl flex flex-col"
    >
      {/* Header */}
      <div className="sticky top-0 bg-earth-950/95 backdrop-blur border-b border-earth-800 px-5 py-4 shrink-0">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <div className="text-xs text-earth-500 uppercase tracking-widest mb-0.5 font-mono">
              NIP: {item.buyer_nip}
            </div>
            <h2 className="font-bold text-earth-50 text-base leading-tight truncate">
              {item.buyer_name ?? item.buyer_nip}
            </h2>
            {(item.city ?? item.buyer_city) && (
              <div className="flex items-center gap-1 mt-1 text-xs text-earth-500">
                <MapPin size={11} />
                {cityLabel(item)}
              </div>
            )}
          </div>
          <button onClick={onClose} className="p-2 hover:bg-earth-800 rounded-lg transition-colors shrink-0">
            <X size={17} className="text-earth-400" />
          </button>
        </div>

        {/* Stage + Priority row */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <StageBadge stage={item.crm_stage} />
            <PriorityDots priority={item.priority} />
          </div>
          <div className="flex gap-1">
            {!editing && (
              <button
                onClick={() => setEditing(true)}
                className="flex items-center gap-1 px-3 py-1.5 bg-earth-800 hover:bg-earth-700 border border-earth-700 rounded-lg text-xs text-earth-300 transition-colors"
              >
                <Edit3 size={12} /> Edytuj
              </button>
            )}
            <button
              onClick={handleDelete}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs transition-colors border
                ${deleting
                  ? 'bg-red-500/20 border-red-500/50 text-red-300'
                  : 'bg-earth-800 hover:bg-red-500/10 border-earth-700 text-earth-500 hover:text-red-400 hover:border-red-500/30'}`}
            >
              <Trash2 size={12} />
              {deleting ? 'Potwierdź' : 'Usuń'}
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* KPI strip */}
        <div className="grid grid-cols-3 gap-3 px-5 pt-4 pb-3 border-b border-earth-800">
          {[
            { label: 'Przetargi',  value: item.total_tenders != null ? String(item.total_tenders) : '—', color: '#3b82f6' },
            { label: 'Wartość',    value: fmtMln((item.total_value ?? 0) / 1_000_000), color: '#10b981' },
            { label: 'Budżet est.', value: item.annual_budget_est != null ? fmtPLN(item.annual_budget_est) : '—', color: '#f59e0b' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-earth-900 rounded-xl p-3 border border-earth-800 text-center">
              <div className="text-xs text-earth-500 mb-0.5">{label}</div>
              <div className="font-bold text-sm leading-tight" style={{ color }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Quick stage change */}
        <div className="px-5 pt-3 pb-2 border-b border-earth-800">
          <div className="text-xs text-earth-500 mb-2 uppercase tracking-widest">Zmień etap</div>
          <div className="flex flex-wrap gap-1.5">
            {STAGES.map(s => (
              <button
                key={s.id}
                onClick={() => handleStageQuick(s.id)}
                className={`px-2.5 py-1 rounded-full text-xs border transition-colors
                  ${item.crm_stage === s.id
                    ? STAGE_COLORS[s.id]
                    : 'border-earth-700 text-earth-500 hover:border-earth-600 hover:text-earth-300'}`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-earth-800 px-5 overflow-x-auto">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => { setTab(t.id); setEditing(false); }}
              className={`flex items-center gap-1.5 px-3 py-3 text-xs font-medium border-b-2 shrink-0 transition-colors
                ${tab === t.id
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-earth-500 hover:text-earth-300'}`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        <div className="px-5 py-4">
          {/* ── Kontakt tab ── */}
          {tab === 'kontakt' && !editing && (
            <motion.div key="kontakt-view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
              {[
                { icon: <Users size={14} />, label: 'Kontakt', value: item.contact_name },
                { icon: <Mail size={14} />, label: 'E-mail', value: item.contact_email },
                { icon: <Phone size={14} />, label: 'Telefon', value: item.contact_phone },
                { icon: <Building2 size={14} />, label: 'Terytorium', value: item.territory },
                { icon: <CalendarClock size={14} />, label: 'Ostatni kontakt', value: fmtDate(item.last_contact) },
              ].map(({ icon, label, value }) => (
                <div key={label} className="flex items-start gap-3 p-3 bg-earth-900 rounded-lg border border-earth-800">
                  <span className="text-earth-500 mt-0.5">{icon}</span>
                  <div>
                    <div className="text-xs text-earth-500">{label}</div>
                    <div className="text-sm text-earth-200 mt-0.5">{value ?? '—'}</div>
                  </div>
                </div>
              ))}
              {item.preferred_cpv && item.preferred_cpv.length > 0 && (
                <div className="p-3 bg-earth-900 rounded-lg border border-earth-800">
                  <div className="text-xs text-earth-500 mb-2">Preferowane CPV</div>
                  <div className="flex flex-wrap gap-1.5">
                    {item.preferred_cpv.map(cpv => (
                      <span key={cpv} className="text-xs font-mono bg-earth-800 text-earth-400 px-2 py-0.5 rounded">
                        {cpv}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {tab === 'kontakt' && editing && (
            <motion.div key="kontakt-edit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className={labelCls}>Etap CRM</label>
                  <select
                    value={form.crm_stage}
                    onChange={e => setForm(f => ({ ...f, crm_stage: e.target.value }))}
                    className={inputCls}
                  >
                    {STAGES.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className={labelCls}>Priorytet (1-5)</label>
                  <select
                    value={form.priority}
                    onChange={e => setForm(f => ({ ...f, priority: Number(e.target.value) }))}
                    className={inputCls}
                  >
                    {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className={labelCls}>Osoba kontaktowa</label>
                  <input value={form.contact_name} onChange={e => setForm(f => ({ ...f, contact_name: e.target.value }))} className={inputCls} placeholder="Jan Kowalski" />
                </div>
                <div>
                  <label className={labelCls}>E-mail</label>
                  <input type="email" value={form.contact_email} onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))} className={inputCls} placeholder="jan@urzad.gov.pl" />
                </div>
                <div>
                  <label className={labelCls}>Telefon</label>
                  <input value={form.contact_phone} onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))} className={inputCls} placeholder="+48 000 000 000" />
                </div>
                <div>
                  <label className={labelCls}>Ostatni kontakt</label>
                  <input type="date" value={form.last_contact} onChange={e => setForm(f => ({ ...f, last_contact: e.target.value }))} className={inputCls} />
                </div>
                <div>
                  <label className={labelCls}>Budżet roczny est.</label>
                  <input type="number" value={form.annual_budget_est} onChange={e => setForm(f => ({ ...f, annual_budget_est: e.target.value }))} className={inputCls} placeholder="500000" />
                </div>
                <div className="col-span-2">
                  <label className={labelCls}>Terytorium</label>
                  <input value={form.territory} onChange={e => setForm(f => ({ ...f, territory: e.target.value }))} className={inputCls} placeholder="Mazowieckie" />
                </div>
                <div className="col-span-2">
                  <label className={labelCls}>Preferowane CPV (oddziel przecinkami)</label>
                  <input value={form.preferred_cpv} onChange={e => setForm(f => ({ ...f, preferred_cpv: e.target.value }))} className={inputCls} placeholder="45000000, 45200000" />
                </div>
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  onClick={() => setEditing(false)}
                  className="flex-1 py-2.5 border border-earth-700 text-earth-400 text-sm rounded-lg hover:border-earth-600 transition-colors"
                >
                  Anuluj
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex-1 py-2.5 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-400 disabled:opacity-40 flex items-center justify-center gap-2 transition-colors"
                >
                  {saving ? <RefreshCw size={13} className="animate-spin" /> : <CheckCircle size={13} />}
                  Zapisz
                </button>
              </div>
            </motion.div>
          )}

          {/* ── Notatki tab ── */}
          {tab === 'notatki' && (
            <motion.div key="notatki" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
              <textarea
                value={form.notes}
                onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                rows={8}
                placeholder="Notatki o zamawiającym, relacjach, strategii..."
                className={`${inputCls} resize-none`}
              />
              <button
                onClick={handleSave}
                disabled={saving}
                className="w-full py-2.5 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-400 disabled:opacity-40 flex items-center justify-center gap-2 transition-colors"
              >
                {saving ? <RefreshCw size={13} className="animate-spin" /> : <CheckCircle size={13} />}
                Zapisz notatki
              </button>
            </motion.div>
          )}

          {/* ── Historia przetargów tab ── */}
          {tab === 'historia' && (
            <motion.div key="historia" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <TendersTab itemId={item.id} />
            </motion.div>
          )}

          {/* ── Follow-up tab ── */}
          {tab === 'followup' && (
            <motion.div key="followup" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
              <div className={`p-4 rounded-xl border ${
                isOverdue(item.next_followup)
                  ? 'bg-red-500/10 border-red-500/30'
                  : item.next_followup
                    ? 'bg-amber-500/10 border-amber-500/30'
                    : 'bg-earth-900 border-earth-700'
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  {isOverdue(item.next_followup)
                    ? <AlertTriangle size={15} className="text-red-400" />
                    : <CalendarClock size={15} className="text-amber-400" />
                  }
                  <span className="text-xs font-medium text-earth-300 uppercase tracking-wide">
                    Następny follow-up
                  </span>
                </div>
                <div className={`text-xl font-bold ${isOverdue(item.next_followup) ? 'text-red-300' : 'text-earth-100'}`}>
                  {fmtDate(item.next_followup)}
                </div>
                {isOverdue(item.next_followup) && (
                  <div className="text-xs text-red-400 mt-0.5">Termin przekroczony</div>
                )}
              </div>

              <div>
                <label className={labelCls}>Zmień datę follow-up</label>
                <input
                  type="date"
                  value={form.next_followup}
                  onChange={e => setForm(f => ({ ...f, next_followup: e.target.value }))}
                  className={inputCls}
                />
              </div>

              <div className="p-3 bg-earth-900 border border-earth-800 rounded-lg">
                <div className="text-xs text-earth-500 mb-1">Ostatni kontakt</div>
                <div className="text-sm text-earth-200">{fmtDate(item.last_contact)}</div>
              </div>

              {item.notes && (
                <div className="p-3 bg-earth-900 border border-earth-800 rounded-lg">
                  <div className="text-xs text-earth-500 mb-1">Notatka</div>
                  <div className="text-sm text-earth-300 whitespace-pre-wrap">{item.notes}</div>
                </div>
              )}

              <button
                onClick={handleSave}
                disabled={saving}
                className="w-full py-2.5 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-400 disabled:opacity-40 flex items-center justify-center gap-2 transition-colors"
              >
                {saving ? <RefreshCw size={13} className="animate-spin" /> : <CheckCircle size={13} />}
                Zapisz follow-up
              </button>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ── AddBuyerModal ──────────────────────────────────────────────────────────────

function AddBuyerModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (body: Record<string, unknown>) => Promise<void>;
}) {
  const authFetch = useAuthFetch();
  const inputRef   = useRef<HTMLInputElement>(null);

  const [q,         setQ]         = useState('');
  const [results,   setResults]   = useState<BuyerSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [selected,  setSelected]  = useState<BuyerSearchResult | null>(null);
  const [saving,    setSaving]    = useState(false);

  const [form, setForm] = useState({
    crm_stage:    'prospect' as CRMStage,
    priority:     3,
    contact_name:  '',
    contact_email: '',
    contact_phone: '',
    notes:         '',
    next_followup: '',
  });

  useEffect(() => { inputRef.current?.focus(); }, []);

  // Debounced search
  useEffect(() => {
    if (!q || q.length < 2) { setResults([]); return; }
    const timer = setTimeout(() => {
      setSearching(true);
      authFetch(`/api/v2/buyer-crm/search?q=${encodeURIComponent(q)}&limit=10`)
        .then((d: { items: BuyerSearchResult[] }) => setResults(d.items || []))
        .catch(() => {})
        .finally(() => setSearching(false));
    }, 350);
    return () => clearTimeout(timer);
  }, [authFetch, q]);

  const handleCreate = async () => {
    if (!selected && !q.match(/^\d{10}$/)) return;
    const nip = selected?.nip ?? q;
    setSaving(true);
    try {
      await onCreate({
        buyer_nip:    nip,
        crm_stage:    form.crm_stage,
        priority:     form.priority,
        contact_name:  form.contact_name  || null,
        contact_email: form.contact_email || null,
        contact_phone: form.contact_phone || null,
        notes:         form.notes         || null,
        next_followup: form.next_followup || null,
      });
      showToast('success', 'Zamawiający dodany do CRM');
      onClose();
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd dodawania');
    } finally {
      setSaving(false);
    }
  };

  const inputCls = 'w-full bg-earth-800 border border-earth-700 rounded-lg px-3 py-2 text-sm text-earth-100 placeholder-earth-500 focus:outline-none focus:border-emerald-500 transition-colors';

  const cpvChart = selected?.top_cpv?.slice(0, 5).map(c => ({ name: c.code.slice(0, 5), value: c.count })) ?? [];

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
        className="bg-earth-900 border border-earth-700 rounded-2xl w-full max-w-md shadow-2xl overflow-y-auto max-h-[90vh]"
      >
        <div className="sticky top-0 bg-earth-900 border-b border-earth-800 px-6 py-4 flex items-center justify-between">
          <h3 className="text-base font-bold text-earth-50">Dodaj zamawiającego do CRM</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-earth-800 rounded-lg transition-colors">
            <X size={15} className="text-earth-400" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Search */}
          <div>
            <label className="block text-xs text-earth-500 mb-1.5">Wyszukaj zamawiającego</label>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-earth-400" />
              <input
                ref={inputRef}
                value={q}
                onChange={e => { setQ(e.target.value); setSelected(null); }}
                placeholder="Nazwa urzędu lub NIP (10 cyfr)..."
                className="w-full bg-earth-800 border border-earth-700 rounded-lg pl-9 pr-4 py-2.5 text-sm text-earth-100 placeholder-earth-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
              {searching && (
                <RefreshCw size={12} className="absolute right-3 top-1/2 -translate-y-1/2 text-earth-400 animate-spin" />
              )}
            </div>
          </div>

          {/* Search results */}
          {results.length > 0 && !selected && (
            <div className="border border-earth-700 rounded-xl overflow-hidden">
              {results.map(r => (
                <button
                  key={r.nip}
                  onClick={() => { setSelected(r); setQ(r.name); }}
                  className="w-full flex items-start justify-between px-4 py-3 hover:bg-earth-800 text-left transition-colors border-b border-earth-800 last:border-0"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-earth-100 truncate">{r.name}</div>
                    <div className="text-xs text-earth-500 font-mono mt-0.5">
                      {r.nip} {r.city ? `· ${r.city}` : ''}
                    </div>
                  </div>
                  <div className="text-xs text-earth-400 ml-3 shrink-0">
                    {r.total_tenders} przetargów
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Selected buyer info */}
          {selected && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-sm text-emerald-300 font-medium">{selected.name}</div>
                  <div className="text-xs text-emerald-600 font-mono mt-0.5">
                    {selected.nip} {selected.city ? `· ${selected.city}` : ''}
                  </div>
                  <div className="text-xs text-earth-400 mt-1">
                    {selected.total_tenders} przetargów - łącznie {fmtMln(selected.total_value / 1_000_000)}
                  </div>
                </div>
                <button onClick={() => setSelected(null)} className="text-earth-500 hover:text-earth-300 p-1">
                  <X size={13} />
                </button>
              </div>
              {cpvChart.length > 0 && (
                <div className="mt-3 h-16">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={cpvChart} margin={{ top: 0, right: 0, left: -30, bottom: 0 }}>
                      <XAxis dataKey="name" tick={{ fill: '#71717a', fontSize: 9 }} />
                      <Tooltip
                        contentStyle={{ background: '#1a1712', border: '1px solid #3f3f46', borderRadius: 6, fontSize: 11 }}
                        formatter={(v: number) => [v, 'Przetargi']}
                      />
                      <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                        {cpvChart.map((_, i) => <Cell key={i} fill={CPV_BAR_COLORS[i % CPV_BAR_COLORS.length]} fillOpacity={0.8} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )}

          {/* Contact details */}
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-earth-500 mb-1">Etap CRM</label>
                <select value={form.crm_stage} onChange={e => setForm(f => ({ ...f, crm_stage: e.target.value as CRMStage }))} className={inputCls}>
                  {STAGES.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-earth-500 mb-1">Priorytet</label>
                <select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: Number(e.target.value) }))} className={inputCls}>
                  {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs text-earth-500 mb-1">Osoba kontaktowa</label>
              <input value={form.contact_name} onChange={e => setForm(f => ({ ...f, contact_name: e.target.value }))} className={inputCls} placeholder="Jan Kowalski" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-earth-500 mb-1">E-mail</label>
                <input type="email" value={form.contact_email} onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))} className={inputCls} placeholder="jan@urzad.gov.pl" />
              </div>
              <div>
                <label className="block text-xs text-earth-500 mb-1">Telefon</label>
                <input value={form.contact_phone} onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))} className={inputCls} placeholder="+48 ..." />
              </div>
            </div>
            <div>
              <label className="block text-xs text-earth-500 mb-1">Następny follow-up</label>
              <input type="date" value={form.next_followup} onChange={e => setForm(f => ({ ...f, next_followup: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className="block text-xs text-earth-500 mb-1">Notatka</label>
              <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={3} className={`${inputCls} resize-none`} placeholder="Ważne informacje o zamawiającym..." />
            </div>
          </div>

          <div className="flex gap-3 pt-1">
            <button onClick={onClose} className="flex-1 py-2.5 border border-earth-700 text-earth-400 text-sm rounded-lg hover:border-earth-600 transition-colors">
              Anuluj
            </button>
            <button
              onClick={handleCreate}
              disabled={saving || (!selected && !q.match(/^\d{10}$/))}
              className="flex-1 py-2.5 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
            >
              {saving ? <RefreshCw size={13} className="animate-spin" /> : <Plus size={13} />}
              Dodaj do CRM
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export function BuyerCRMPage() {
  const authFetch   = useAuthFetch();
  const { data: rawData, loading, followups, reload, update, remove } = useBuyerCRM();
  const data = rawData as BuyerCRMItem[];

  const [selected,      setSelected]      = useState<BuyerCRMItem | null>(null);
  const [showAdd,       setShowAdd]       = useState(false);
  const [showFollowups, setShowFollowups] = useState(true);
  const [stageFilter,   setStageFilter]   = useState<CRMStage | 'all'>('all');
  const [searchQ,       setSearchQ]       = useState('');

  // Sync selected item when data reloads
  useEffect(() => {
    if (selected) {
      const fresh = data.find(d => d.id === selected.id);
      if (fresh) setSelected(fresh as BuyerCRMItem);
    }
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = data.filter(item => {
    if (stageFilter !== 'all' && item.crm_stage !== stageFilter) return false;
    if (searchQ) {
      const q = searchQ.toLowerCase();
      return (
        item.buyer_name?.toLowerCase().includes(q) ||
        item.buyer_nip.includes(q) ||
        item.contact_name?.toLowerCase().includes(q) ||
        (item.city ?? item.buyer_city)?.toLowerCase().includes(q) ||
        false
      );
    }
    return true;
  });

  const handleCreate = useCallback(async (body: Record<string, unknown>) => {
    await authFetch('/api/v2/buyer-crm', { method: 'POST', body: JSON.stringify(body) });
    reload();
  }, [authFetch, reload]);

  const handleUpdate = useCallback(async (id: string, body: Record<string, unknown>) => {
    await update(id, body);
  }, [update]);

  const handleDelete = useCallback(async (id: string) => {
    await remove(id);
    setSelected(null);
  }, [remove]);

  const overdueCount = followups.filter(f => isOverdue(f.next_followup)).length;

  // Stage tab counts
  const stageCounts: Record<string, number> = { all: data.length };
  STAGES.forEach(s => { stageCounts[s.id] = data.filter(d => d.crm_stage === s.id).length; });

  return (
    <>
      <PageShell
        title="CRM Zamawiających"
        subtitle="Zarządzaj relacjami z zamawiającymi i planuj follow-upy"
        actions={
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-400 transition-colors"
          >
            <Plus size={15} />
            Dodaj zamawiającego
          </button>
        }
      >
        <div className="space-y-4">

          {/* ── Followup banner ─────────────────────────────────────────── */}
          <AnimatePresence>
            {(showFollowups && followups.length > 0) ? (
              <FollowupBanner
                key="banner"
                followups={followups}
                onDismiss={() => setShowFollowups(false)}
              />
            ) : null}
          </AnimatePresence>

          {/* ── Stats strip ─────────────────────────────────────────────── */}
          {!loading && data.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Zamawiający', value: data.length,   icon: Building2,    color: '#3b82f6' },
                { label: 'Aktywni',     value: stageCounts.active ?? 0, icon: CheckCircle, color: '#10b981' },
                { label: 'Follow-upy',  value: followups.length, icon: CalendarClock, color: '#f59e0b' },
                { label: 'Przeterminowane', value: overdueCount, icon: AlertTriangle, color: overdueCount > 0 ? '#ef4444' : '#71717a' },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="bg-earth-900 border border-earth-700 rounded-xl p-3 flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: color + '22' }}>
                    <Icon size={16} style={{ color }} />
                  </div>
                  <div>
                    <div className="text-xs text-earth-500 leading-none">{label}</div>
                    <div className="text-xl font-bold text-earth-50 leading-tight">{value}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Stage filter tabs + search ───────────────────────────────── */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex gap-1 overflow-x-auto pb-1 sm:pb-0 shrink-0">
              <button
                onClick={() => setStageFilter('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium shrink-0 transition-colors border
                  ${stageFilter === 'all'
                    ? 'bg-earth-700 border-earth-600 text-earth-100'
                    : 'border-earth-800 text-earth-500 hover:text-earth-300 hover:border-earth-700'}`}
              >
                Wszystkie ({stageCounts.all})
              </button>
              {STAGES.map(s => (
                <button
                  key={s.id}
                  onClick={() => setStageFilter(s.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium shrink-0 transition-colors border
                    ${stageFilter === s.id
                      ? STAGE_COLORS[s.id]
                      : 'border-earth-800 text-earth-500 hover:text-earth-300 hover:border-earth-700'}`}
                >
                  {s.label} ({stageCounts[s.id] ?? 0})
                </button>
              ))}
            </div>

            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-earth-400" />
              <input
                value={searchQ}
                onChange={e => setSearchQ(e.target.value)}
                placeholder="Szukaj po nazwie, NIP, kontakcie..."
                className="w-full bg-earth-900 border border-earth-700 rounded-lg pl-9 pr-4 py-2 text-sm text-earth-100 placeholder-earth-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
              {searchQ && (
                <button
                  onClick={() => setSearchQ('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-earth-500 hover:text-earth-300"
                >
                  <X size={13} />
                </button>
              )}
            </div>
          </div>

          {/* ── List ────────────────────────────────────────────────────── */}
          {loading && (
            <div className="grid gap-2 sm:grid-cols-2">
              {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          )}

          {!loading && data.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-20 border border-dashed border-earth-700 rounded-2xl"
            >
              <Building2 size={40} className="mx-auto mb-4 text-earth-700" />
              <h3 className="text-base font-semibold text-earth-400 mb-2">Brak zamawiających w CRM</h3>
              <p className="text-sm text-earth-600 mb-6">Dodaj zamawiających, żeby zarządzać relacjami i planować follow-upy</p>
              <button
                onClick={() => setShowAdd(true)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-400 transition-colors"
              >
                <Plus size={15} />
                Dodaj pierwszego zamawiającego
              </button>
            </motion.div>
          )}

          {!loading && filtered.length === 0 && data.length > 0 && (
            <div className="text-center py-8 text-earth-500 text-sm">
              Brak wyników{searchQ ? ` dla "${searchQ}"` : ` w etapie "${STAGES.find(s => s.id === stageFilter)?.label}"`}
            </div>
          )}

          {!loading && filtered.length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2">
              <AnimatePresence>
                {filtered.map(item => (
                  <BuyerCard
                    key={item.id}
                    item={item}
                    selected={selected?.id === item.id}
                    onClick={() => setSelected(selected?.id === item.id ? null : item)}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}

        </div>
      </PageShell>

      {/* ── Right panel + Add modal ────────────────────────────────────────── */}
      <AnimatePresence>
        {selected ? (
          <BuyerProfilePanel
            key={`panel-${selected.id}`}
            item={selected}
            onClose={() => setSelected(null)}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
          />
        ) : null}
      </AnimatePresence>

      <AnimatePresence>
        {showAdd ? (
          <AddBuyerModal
            key="add-modal"
            onClose={() => setShowAdd(false)}
            onCreate={handleCreate}
          />
        ) : null}
      </AnimatePresence>

      {/* Backdrop for panel */}
      <AnimatePresence>
        {selected ? (
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 z-40 lg:hidden"
            onClick={() => setSelected(null)}
          />
        ) : null}
      </AnimatePresence>
    </>
  );
}
