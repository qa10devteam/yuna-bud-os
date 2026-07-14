'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Building2, Users, Send, Settings2,
  Save, Loader2, Trash2, Shield, User, Crown, Eye,
  Mail, XCircle, Plus, RefreshCw, CheckCircle2,
  ChevronRight, Tag, MapPin, Calendar, Hash, Target,
  SlidersHorizontal, Zap, TrendingUp,
  CreditCard, Key, Webhook, Copy, ExternalLink, AlertCircle,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';
import { PageShell } from '@/components/PageShell';

// ─── Types ─────────────────────────────────────────────────────────────────────

type SectionId = 'organizacja' | 'zespol' | 'zaproszenia' | 'ustawienia' | 'scoring' | 'uzycie' | 'billing' | 'api_keys' | 'webhooks';

interface OrgData {
  id: string;
  name: string;
  nip: string;
  plan: 'free' | 'pro' | 'enterprise';
  settings: { default_cpv: string[]; default_regions: string[] };
  member_count: number;
  created_at: string;
}

interface Member {
  id: string;
  email: string;
  name: string;
  role: 'owner' | 'admin' | 'estimator';
  is_active: boolean;
  created_at: string;
  is_me: boolean;
}

interface Invite {
  id: string;
  email: string;
  role: 'estimator' | 'admin';
  invited_by: string | null;
  created_at: string;
  expires_at: string | null;
}

interface ScoringConfig {
  cpv_weight: number;
  value_weight: number;
  region_weight: number;
  deadline_weight: number;
  historical_win_weight: number;
  min_value_pln: number;
  max_value_pln: number;
  preferred_cpvs: string[];
  preferred_regions: string[];
  is_default: boolean;
}

interface RescoreResult {
  total: number;
  processed: number;
  avg_score_before: number;
  avg_score_after: number;
  message: string;
}

// ─── Constants ─────────────────────────────────────────────────────────────────

const SECTIONS: { id: SectionId; label: string; icon: typeof Building2 }[] = [
  { id: 'organizacja', label: 'Organizacja',  icon: Building2  },
  { id: 'zespol',      label: 'Zespol',       icon: Users      },
  { id: 'zaproszenia', label: 'Zaproszenia',  icon: Send       },
  { id: 'ustawienia',  label: 'Ustawienia',   icon: Settings2  },
  { id: 'scoring',     label: 'Scoring AI',   icon: Target     },
  { id: 'billing',     label: 'Billing',      icon: CreditCard },
  { id: 'api_keys',    label: 'API Keys',     icon: Key        },
  { id: 'webhooks',    label: 'Webhooki',     icon: Webhook    },
  { id: 'uzycie',      label: 'Użycie',       icon: Zap        },
];

const CPV_OPTIONS = [
  { code: '45000000', label: 'Roboty budowlane' },
  { code: '45200000', label: 'Roboty obiektow budowlanych' },
  { code: '45300000', label: 'Roboty instalacyjne' },
  { code: '45400000', label: 'Roboty wykonczeniowe' },
  { code: '71000000', label: 'Uslugi inzynieryjne' },
  { code: '50000000', label: 'Uslugi naprawcze i konserwacyjne' },
  { code: '90000000', label: 'Uslugi odpadow i sanitarno-higieniczne' },
  { code: '72000000', label: 'Uslugi informatyczne' },
];

const VOIVODESHIPS = [
  'dolnoslaskie', 'kujawsko-pomorskie', 'lubelskie', 'lubuskie',
  'lodzkie', 'malopolskie', 'mazowieckie', 'opolskie',
  'podkarpackie', 'podlaskie', 'pomorskie', 'slaskie',
  'swietokrzyskie', 'warminsko-mazurskie', 'wielkopolskie', 'zachodniopomorskie',
];

const PLAN_BADGE: Record<string, { label: string; className: string }> = {
  free:       { label: 'Free',       className: 'bg-earth-700/50 text-earth-300 border border-earth-600/40' },
  pro:        { label: 'Pro',        className: 'bg-accent-info/15 text-accent-info border border-accent-info/30' },
  enterprise: { label: 'Enterprise', className: 'bg-accent-warning/15 text-accent-warning border border-accent-warning/30' },
};

const ROLE_META: Record<string, { label: string; Icon: typeof User; color: string }> = {
  owner:     { label: 'Wlasciciel',   Icon: Crown,   color: 'text-accent-warning'  },
  admin:     { label: 'Administrator', Icon: Shield,  color: 'text-accent-info'     },
  estimator: { label: 'Kosztorysant', Icon: User,    color: 'text-accent-primary'  },
  viewer:    { label: 'Przegladajacy', Icon: Eye,    color: 'text-earth-400'       },
};

const DEFAULT_SCORING_CONFIG: ScoringConfig = {
  cpv_weight: 0.2,
  value_weight: 0.2,
  region_weight: 0.2,
  deadline_weight: 0.2,
  historical_win_weight: 0.2,
  min_value_pln: 0,
  max_value_pln: 10000000,
  preferred_cpvs: [],
  preferred_regions: [],
  is_default: true,
};

const WEIGHT_FIELDS: { key: keyof Pick<ScoringConfig, 'cpv_weight' | 'value_weight' | 'region_weight' | 'deadline_weight' | 'historical_win_weight'>; label: string; description: string }[] = [
  { key: 'cpv_weight',            label: 'Waga CPV',                description: 'Dopasowanie kodow CPV do preferencji' },
  { key: 'value_weight',          label: 'Waga wartosci',           description: 'Wartosc przetargu w stosunku do zakresu' },
  { key: 'region_weight',         label: 'Waga regionu',            description: 'Dopasowanie lokalizacji przetargu' },
  { key: 'deadline_weight',       label: 'Waga terminu',            description: 'Czas pozostaly na zlozenie oferty' },
  { key: 'historical_win_weight', label: 'Waga historii wygranych', description: 'Historyczny wskaznik wygranych w kategorii' },
];

// ─── Shared micro-components ───────────────────────────────────────────────────

const INPUT = 'w-full bg-earth-800/60 border border-earth-700/60 rounded-token-lg px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/50 transition-colors';

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-earth-500 mb-1.5 font-medium">{label}</label>
      {children}
    </div>
  );
}

function Spinner({ label = 'Ladowanie...' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-earth-600 text-sm py-6">
      <Loader2 className="w-4 h-4 animate-spin" /> {label}
    </div>
  );
}

function ActionBtn({
  children, onClick, loading, icon, disabled, variant = 'primary',
}: {
  children: React.ReactNode;
  onClick?: () => void;
  loading?: boolean;
  icon?: React.ReactNode;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'danger' | 'accent';
}) {
  const styles = {
    primary:   'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30',
    secondary: 'bg-earth-800/60 text-earth-300 hover:bg-earth-700/60 border border-earth-700/60',
    danger:    'bg-red-500/15 text-red-400 hover:bg-red-500/25 border border-red-500/25',
    accent:    'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 border border-blue-500/30',
  }[variant];
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-40 ${styles}`}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : icon}
      {children}
    </button>
  );
}

function PillTag({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-earth-800 border border-earth-700/60 text-xs text-earth-300">
      {label}
      <button onClick={onRemove} className="text-earth-600 hover:text-red-400 transition-colors">
        <XCircle className="w-3 h-3" />
      </button>
    </span>
  );
}

// ─── Section: Organizacja ──────────────────────────────────────────────────────

function OrganizacjaSection() {
  const authFetch = useAuthFetch();
  const [org, setOrg]       = useState<OrgData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ name: '', nip: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data: OrgData = await authFetch('/api/v2/organizations/me');
      setOrg(data);
      setForm({ name: data.name ?? '', nip: data.nip ?? '' });
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad wczytywania organizacji');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  async function save() {
    if (!org) return;
    setSaving(true);
    try {
      const updated: OrgData = await authFetch('/api/v2/organizations/me', {
        method: 'PUT',
        body: JSON.stringify({ name: form.name || undefined, nip: form.nip || undefined }),
      });
      setOrg(updated);
      setEditing(false);
      showToast('success', 'Dane organizacji zostaly zapisane');
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad zapisu');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Spinner />;
  if (!org) return null;

  const planBadge = PLAN_BADGE[org.plan] ?? PLAN_BADGE.free;

  return (
    <div className="space-y-5 max-w-xl">
      {/* Header card */}
      <GlassCard className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-earth-800 border border-earth-700/60 flex items-center justify-center shrink-0">
              <Building2 className="w-6 h-6 text-earth-400" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-earth-100">{org.name || 'Twoja organizacja'}</h3>
              <p className="text-xs text-earth-500 mt-0.5 font-mono">NIP: {org.nip || 'nie podano'}</p>
            </div>
          </div>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${planBadge.className}`}>
            {planBadge.label}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="flex items-center gap-2 text-xs text-earth-500">
            <Users className="w-3.5 h-3.5 text-earth-600" />
            <span>{org.member_count} {org.member_count === 1 ? 'czlonek' : 'czlonkow'}</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-earth-500">
            <Calendar className="w-3.5 h-3.5 text-earth-600" />
            <span>od {new Date(org.created_at).toLocaleDateString('pl-PL', { year: 'numeric', month: 'long' })}</span>
          </div>
        </div>
      </GlassCard>

      {/* Edit form */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold text-earth-400 uppercase tracking-wide">Dane firmy</p>
          {!editing && (
            <button onClick={() => setEditing(true)} className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
              Edytuj
            </button>
          )}
        </div>

        <AnimatePresence mode="wait">
          {editing ? (
            <motion.div
              key="edit"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18 }}
              className="space-y-3"
            >
              <Field label="Nazwa firmy">
                <input
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Kowalski Budownictwo Sp. z o.o."
                  className={INPUT}
                />
              </Field>
              <Field label="NIP">
                <input
                  value={form.nip}
                  onChange={e => setForm(f => ({ ...f, nip: e.target.value }))}
                  placeholder="1234567890"
                  maxLength={10}
                  className={INPUT}
                />
              </Field>
              <div className="flex items-center gap-2 pt-1">
                <ActionBtn onClick={save} loading={saving} icon={<Save className="w-4 h-4" />}>
                  Zapisz zmiany
                </ActionBtn>
                <ActionBtn variant="secondary" onClick={() => { setEditing(false); setForm({ name: org.name, nip: org.nip }); }}>
                  Anuluj
                </ActionBtn>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="space-y-2"
            >
              <GlassCard className="p-4 space-y-3">
                <InfoRow label="Nazwa" value={org.name || 'nie podano'} />
                <InfoRow label="NIP" value={org.nip || 'nie podano'} mono />
                <InfoRow label="Plan" value={planBadge.label} />
                <InfoRow label="Czlonkowie" value={String(org.member_count)} />
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function InfoRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-xs text-earth-500 shrink-0">{label}</span>
      <span className={`text-sm text-earth-200 text-right truncate ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  );
}

// ─── Section: Zespol ───────────────────────────────────────────────────────────

function ZespolSection() {
  const authFetch  = useAuthFetch();
  const [members, setMembers]   = useState<Member[]>([]);
  const [loading, setLoading]   = useState(true);
  const [removing, setRemoving] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data: { items: Member[] } = await authFetch('/api/v2/organizations/me/members');
      setMembers(data.items ?? []);
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad wczytywania zespolu');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  async function changeRole(memberId: string, newRole: string) {
    try {
      await authFetch(`/api/v2/organizations/me/members/${memberId}`, {
        method: 'PATCH',
        body: JSON.stringify({ role: newRole }),
      });
      setMembers(prev => prev.map(m => m.id === memberId ? { ...m, role: newRole as Member['role'] } : m));
      showToast('success', 'Rola zostala zmieniona');
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad zmiany roli');
    }
  }

  async function removeMember(memberId: string, email: string) {
    if (!confirm(`Usunac uzytkownika ${email} z organizacji?`)) return;
    setRemoving(memberId);
    try {
      await authFetch(`/api/v2/organizations/me/members/${memberId}`, { method: 'DELETE' });
      setMembers(prev => prev.filter(m => m.id !== memberId));
      showToast('success', 'Uzytkownik usuniety z organizacji');
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad usuniecia');
    } finally {
      setRemoving(null);
    }
  }

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4 max-w-xl">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-earth-400 uppercase tracking-wide">
          Czlonkowie ({members.length})
        </p>
        <button onClick={load} className="p-1.5 text-earth-600 hover:text-earth-400 transition-colors rounded-lg hover:bg-earth-800/60">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {members.length === 0 ? (
        <GlassCard className="p-8 text-center">
          <Users className="w-8 h-8 text-earth-700 mx-auto mb-2" />
          <p className="text-sm text-earth-500">Brak czlonkow w organizacji</p>
        </GlassCard>
      ) : (
        <div className="space-y-2">
          {members.map(member => {
            const meta = ROLE_META[member.role] ?? ROLE_META.viewer;
            const RoleIcon = meta.Icon;
            return (
              <motion.div
                key={member.id}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.2 }}
              >
                <GlassCard className="p-3.5 flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-earth-800 border border-earth-700/60 flex items-center justify-center text-sm font-bold text-earth-300 shrink-0">
                    {(member.name || member.email).slice(0, 1).toUpperCase()}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-earth-200 font-medium truncate">{member.name || member.email}</p>
                      {member.is_me && (
                        <span className="text-xs text-earth-600 bg-earth-800 px-1.5 py-0.5 rounded-md border border-earth-700/60 shrink-0">Ty</span>
                      )}
                      {!member.is_active && (
                        <span className="text-xs text-earth-500 bg-earth-800/60 px-1.5 py-0.5 rounded-md border border-earth-700/50 shrink-0">Nieaktywny</span>
                      )}
                    </div>
                    <p className="text-xs text-earth-600 truncate">{member.email}</p>
                  </div>

                  {!member.is_me ? (
                    <select
                      value={member.role}
                      onChange={e => changeRole(member.id, e.target.value)}
                      className="text-xs bg-earth-800 border border-earth-700/60 rounded-lg px-2 py-1.5 text-earth-300 focus:outline-none focus:border-blue-500/60 transition-colors cursor-pointer"
                    >
                      <option value="admin">Administrator</option>
                      <option value="estimator">Kosztorysant</option>
                      <option value="viewer">Przegladajacy</option>
                    </select>
                  ) : (
                    <span className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-earth-800 border border-earth-700/60 ${meta.color} shrink-0`}>
                      <RoleIcon className="w-3 h-3" />
                      {meta.label}
                    </span>
                  )}

                  {!member.is_me && (
                    <button
                      onClick={() => removeMember(member.id, member.email)}
                      disabled={removing === member.id}
                      title="Usun z organizacji"
                      className="p-1.5 text-earth-700 hover:text-red-400 transition-colors rounded-lg hover:bg-red-500/10 disabled:opacity-40 shrink-0"
                    >
                      {removing === member.id
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <Trash2 className="w-3.5 h-3.5" />
                      }
                    </button>
                  )}
                </GlassCard>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Section: Zaproszenia ──────────────────────────────────────────────────────

const STATUS_BADGE: Record<string, string> = {
  pending:  'bg-amber-500/15 text-amber-400 border-amber-500/25',
  accepted: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
  expired:  'bg-earth-800/50 text-earth-500 border-earth-700/30',
};
const STATUS_LABEL: Record<string, string> = {
  pending:  'Oczekuje',
  accepted: 'Zaakceptowane',
  expired:  'Wygasle',
};

function ZaproszeniaSSection() {
  const authFetch = useAuthFetch();
  const [invites, setInvites]       = useState<Invite[]>([]);
  const [loading, setLoading]       = useState(true);
  const [revoking, setRevoking]     = useState<string | null>(null);
  const [sending, setSending]       = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole]   = useState<'estimator' | 'admin'>('estimator');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data: { items: Invite[]; total: number } = await authFetch('/api/v2/organizations/me/invites');
      setInvites(data.items ?? []);
    } catch {
      setInvites([]);
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  async function sendInvite() {
    if (!inviteEmail.trim()) return;
    setSending(true);
    try {
      await authFetch('/api/v2/organizations/me/invite', {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      });
      showToast('success', `Zaproszenie wyslane do ${inviteEmail.trim()}`);
      setInviteEmail('');
      load();
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad wysylania zaproszenia');
    } finally {
      setSending(false);
    }
  }

  async function revokeInvite(id: string, email: string) {
    setRevoking(id);
    try {
      await authFetch(`/api/v2/organizations/me/invites/${id}`, { method: 'DELETE' });
      setInvites(prev => prev.filter(i => i.id !== id));
      showToast('success', `Zaproszenie dla ${email} zostalo anulowane`);
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad anulowania');
    } finally {
      setRevoking(null);
    }
  }

  return (
    <div className="space-y-5 max-w-xl">
      {/* Send invite form */}
      <GlassCard className="p-5 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Send className="w-4 h-4 text-earth-500" />
          <p className="text-sm font-semibold text-earth-200">Zaproś nowego czlonka</p>
        </div>
        <Field label="Adres email">
          <input
            value={inviteEmail}
            onChange={e => setInviteEmail(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendInvite()}
            placeholder="jan.kowalski@firma.pl"
            type="email"
            className={INPUT}
          />
        </Field>
        <Field label="Rola">
          <select
            value={inviteRole}
            onChange={e => setInviteRole(e.target.value as 'estimator' | 'admin')}
            className={INPUT}
          >
            <option value="estimator">Kosztorysant</option>
            <option value="admin">Administrator</option>
          </select>
        </Field>
        <ActionBtn
          onClick={sendInvite}
          loading={sending}
          disabled={!inviteEmail.trim()}
          icon={<Send className="w-4 h-4" />}
        >
          Wyslij zaproszenie
        </ActionBtn>
        <p className="text-xs text-earth-700">Zaproszony uzytkownik otrzyma link aktywacyjny wazny 7 dni.</p>
      </GlassCard>

      {/* Pending invites list */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold text-earth-400 uppercase tracking-wide">
            Wyslane zaproszenia {invites.length > 0 ? `(${invites.length})` : ''}
          </p>
          <button onClick={load} className="p-1.5 text-earth-600 hover:text-earth-400 transition-colors rounded-lg hover:bg-earth-800/60">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {loading ? <Spinner label="Wczytywanie zaproszen..." /> : invites.length === 0 ? (
          <GlassCard className="p-6 text-center">
            <Mail className="w-7 h-7 text-earth-700 mx-auto mb-2" />
            <p className="text-sm text-earth-500">Brak wyslanych zaproszen</p>
          </GlassCard>
        ) : (
          <AnimatePresence initial={false}>
            {invites.map(inv => {
              const statusCls = STATUS_BADGE.pending;
              return (
                <motion.div
                  key={inv.id}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <GlassCard className="p-3.5 flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 rounded-full bg-earth-800 border border-earth-700/60 flex items-center justify-center shrink-0">
                      <Mail className="w-3.5 h-3.5 text-earth-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-earth-200 truncate">{inv.email}</p>
                      <p className="text-xs text-earth-600">
                        {ROLE_META[inv.role]?.label ?? inv.role}
                        {' · '}wygasa {inv.expires_at ? new Date(inv.expires_at!).toLocaleDateString('pl-PL') : 'brak'}
                      </p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full border shrink-0 ${statusCls}`}>
                      Oczekuje
                    </span>
                    {true && (
                      <button
                        onClick={() => revokeInvite(inv.id, inv.email)}
                        disabled={revoking === inv.id}
                        title="Anuluj zaproszenie"
                        className="p-1.5 text-earth-700 hover:text-red-400 transition-colors rounded-lg hover:bg-red-500/10 disabled:opacity-40 shrink-0"
                      >
                        {revoking === inv.id
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <XCircle className="w-3.5 h-3.5" />
                        }
                      </button>
                    )}
                  </GlassCard>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}

// ─── Section: Ustawienia ───────────────────────────────────────────────────────

function UstawieniaSection() {
  const authFetch = useAuthFetch();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const [cpv, setCpv]         = useState<string[]>([]);
  const [regions, setRegions] = useState<string[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data: OrgData = await authFetch('/api/v2/organizations/me');
      setCpv(data.settings?.default_cpv ?? []);
      setRegions(data.settings?.default_regions ?? []);
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad wczytywania ustawien');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  async function save() {
    setSaving(true);
    try {
      await authFetch('/api/v2/organizations/me', {
        method: 'PUT',
        body: JSON.stringify({ settings: { default_cpv: cpv, default_regions: regions } }),
      });
      showToast('success', 'Ustawienia zostaly zapisane');
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad zapisu ustawien');
    } finally {
      setSaving(false);
    }
  }

  function toggleCpv(code: string) {
    setCpv(prev => prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]);
  }
  function toggleRegion(r: string) {
    setRegions(prev => prev.includes(r) ? prev.filter(x => x !== r) : [...prev, r]);
  }

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6 max-w-xl">
      {/* CPV pills preview */}
      {cpv.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {cpv.map(code => {
            const opt = CPV_OPTIONS.find(o => o.code === code);
            return (
              <PillTag
                key={code}
                label={opt ? `${code} - ${opt.label}` : code}
                onRemove={() => toggleCpv(code)}
              />
            );
          })}
        </div>
      )}

      {/* CPV selector */}
      <GlassCard className="p-4 space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <Tag className="w-4 h-4 text-earth-500" />
          <p className="text-sm font-semibold text-earth-200">Domyslne kody CPV</p>
          <span className="text-xs text-earth-600 ml-auto">{cpv.length} wybranych</span>
        </div>
        <div className="space-y-2">
          {CPV_OPTIONS.map(opt => (
            <label key={opt.code} className="flex items-center gap-2.5 cursor-pointer group">
              <input
                type="checkbox"
                checked={cpv.includes(opt.code)}
                onChange={() => toggleCpv(opt.code)}
                className="accent-emerald-500 w-3.5 h-3.5"
              />
              <span className="font-mono text-xs text-earth-600 w-20 shrink-0">{opt.code}</span>
              <span className="text-sm text-earth-400 group-hover:text-earth-300 transition-colors">{opt.label}</span>
            </label>
          ))}
        </div>
      </GlassCard>

      {/* Regions selector */}
      <GlassCard className="p-4 space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <MapPin className="w-4 h-4 text-earth-500" />
          <p className="text-sm font-semibold text-earth-200">Domyslne regiony</p>
          <span className="text-xs text-earth-600 ml-auto">{regions.length} wybranych</span>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          {VOIVODESHIPS.map(v => (
            <label key={v} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={regions.includes(v)}
                onChange={() => toggleRegion(v)}
                className="accent-emerald-500 w-3.5 h-3.5"
              />
              <span className="text-sm text-earth-400 group-hover:text-earth-300 transition-colors capitalize">{v}</span>
            </label>
          ))}
        </div>
      </GlassCard>

      <ActionBtn onClick={save} loading={saving} icon={<Save className="w-4 h-4" />}>
        Zapisz ustawienia
      </ActionBtn>
    </div>
  );
}

// ─── Section: Scoring AI ───────────────────────────────────────────────────────

function WeightSlider({
  label,
  description,
  value,
  onChange,
}: {
  label: string;
  description: string;
  value: number;
  onChange: (v: number) => void;
}) {
  const pct = Math.round(value * 100);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-sm text-earth-200 font-medium">{label}</p>
          <p className="text-xs text-earth-600">{description}</p>
        </div>
        <span className="text-sm font-mono font-semibold text-emerald-400 shrink-0 w-12 text-right">
          {pct}%
        </span>
      </div>
      <div className="relative h-2 bg-earth-800 rounded-full border border-earth-700/40">
        <div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={value}
          onChange={e => onChange(parseFloat(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
      </div>
    </div>
  );
}

function ScoringSection() {
  const authFetch = useAuthFetch();
  const [loading, setLoading]   = useState(true);
  const [saving, setSaving]     = useState(false);
  const [rescoring, setRescoring] = useState(false);
  const [config, setConfig]     = useState<ScoringConfig>(DEFAULT_SCORING_CONFIG);
  const [rescoreResult, setRescoreResult] = useState<RescoreResult | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data: ScoringConfig = await authFetch('/api/v2/scoring/config');
      setConfig(data);
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad wczytywania konfiguracji scoringu');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  // Auto-normalize all 5 weights so they sum to 1.0
  function setWeight(key: keyof Pick<ScoringConfig, 'cpv_weight' | 'value_weight' | 'region_weight' | 'deadline_weight' | 'historical_win_weight'>, newVal: number) {
    setConfig(prev => {
      const updated = { ...prev, [key]: newVal };
      const sum = updated.cpv_weight + updated.value_weight + updated.region_weight + updated.deadline_weight + updated.historical_win_weight;
      if (sum === 0) return updated;
      // Normalize
      return {
        ...updated,
        cpv_weight:            updated.cpv_weight            / sum,
        value_weight:          updated.value_weight          / sum,
        region_weight:         updated.region_weight         / sum,
        deadline_weight:       updated.deadline_weight       / sum,
        historical_win_weight: updated.historical_win_weight / sum,
      };
    });
  }

  function toggleCpv(code: string) {
    setConfig(prev => ({
      ...prev,
      preferred_cpvs: prev.preferred_cpvs.includes(code)
        ? prev.preferred_cpvs.filter(c => c !== code)
        : [...prev.preferred_cpvs, code],
    }));
  }

  function toggleRegion(r: string) {
    setConfig(prev => ({
      ...prev,
      preferred_regions: prev.preferred_regions.includes(r)
        ? prev.preferred_regions.filter(x => x !== r)
        : [...prev.preferred_regions, r],
    }));
  }

  async function save() {
    setSaving(true);
    try {
      const saved: ScoringConfig = await authFetch('/api/v2/scoring/config', {
        method: 'PUT',
        body: JSON.stringify({
          cpv_weight:            config.cpv_weight,
          value_weight:          config.value_weight,
          region_weight:         config.region_weight,
          deadline_weight:       config.deadline_weight,
          historical_win_weight: config.historical_win_weight,
          min_value_pln:         config.min_value_pln,
          max_value_pln:         config.max_value_pln,
          preferred_cpvs:        config.preferred_cpvs,
          preferred_regions:     config.preferred_regions,
        }),
      });
      setConfig(saved);
      showToast('success', 'Konfiguracja scoringu zostala zapisana');
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad zapisu konfiguracji scoringu');
    } finally {
      setSaving(false);
    }
  }

  async function rescore() {
    setRescoring(true);
    setRescoreResult(null);
    try {
      const result: RescoreResult = await authFetch('/api/v2/scoring/rescore', { method: 'POST' });
      setRescoreResult(result);
      showToast('success', result.message ?? `Przeliczono ${result.processed} przetargow`);
    } catch (e: unknown) {
      showToast('error', (e as Error).message ?? 'Blad przeliczania scoringu');
    } finally {
      setRescoring(false);
    }
  }

  const weightSum = config.cpv_weight + config.value_weight + config.region_weight + config.deadline_weight + config.historical_win_weight;
  const sumPct = Math.round(weightSum * 100);

  if (loading) return <Spinner label="Wczytywanie konfiguracji AI..." />;

  return (
    <div className="space-y-6 max-w-2xl">

      {/* Header info card */}
      <GlassCard className="p-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center shrink-0">
            <Target className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-earth-100">Konfiguracja Scoring AI</h3>
            <p className="text-xs text-earth-500 mt-0.5">
              Dostosuj wagi i filtry uzywane przez algorytm do oceny przetargow
              {config.is_default && (
                <span className="ml-2 text-amber-400/80">(konfiguracja domyslna)</span>
              )}
            </p>
          </div>
        </div>
      </GlassCard>

      {/* Weight sliders */}
      <GlassCard className="p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-earth-500" />
            <p className="text-sm font-semibold text-earth-200">Wagi algorytmu</p>
          </div>
          <span className={`text-xs font-mono px-2 py-0.5 rounded-lg border ${
            Math.abs(sumPct - 100) < 2
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
          }`}>
            Suma: {sumPct}%
          </span>
        </div>
        <p className="text-xs text-earth-600 -mt-2">
          Wagi sa automatycznie normalizowane do sumy 100%. Przeciagnij suwaki aby dostosowac priorytety.
        </p>

        <div className="space-y-4">
          {WEIGHT_FIELDS.map(f => (
            <WeightSlider
              key={f.key}
              label={f.label}
              description={f.description}
              value={config[f.key]}
              onChange={v => setWeight(f.key, v)}
            />
          ))}
        </div>
      </GlassCard>

      {/* Value range */}
      <GlassCard className="p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Hash className="w-4 h-4 text-earth-500" />
          <p className="text-sm font-semibold text-earth-200">Zakres wartosci przetargow (PLN)</p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Minimalna wartość (PLN)">
            <input
              type="number"
              min={0}
              step={1000}
              value={config.min_value_pln}
              onChange={e => setConfig(prev => ({ ...prev, min_value_pln: Math.max(0, parseFloat(e.target.value) || 0) }))}
              className={INPUT}
              placeholder="0"
            />
          </Field>
          <Field label="Maksymalna wartość (PLN)">
            <input
              type="number"
              min={0}
              step={1000}
              value={config.max_value_pln}
              onChange={e => setConfig(prev => ({ ...prev, max_value_pln: Math.max(0, parseFloat(e.target.value) || 0) }))}
              className={INPUT}
              placeholder="10000000"
            />
          </Field>
        </div>
        <p className="text-xs text-earth-700">
          Przetargi poza tym zakresem otrzymaja nizszy score wartosci. Ustaw 0 aby wylaczych filtr.
        </p>
      </GlassCard>

      {/* Preferred CPVs */}
      <GlassCard className="p-5 space-y-3">
        <div className="flex items-center gap-2">
          <Tag className="w-4 h-4 text-earth-500" />
          <p className="text-sm font-semibold text-earth-200">Preferowane kody CPV</p>
          <span className="text-xs text-earth-600 ml-auto">{config.preferred_cpvs.length} wybranych</span>
        </div>

        {config.preferred_cpvs.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {config.preferred_cpvs.map(code => {
              const opt = CPV_OPTIONS.find(o => o.code === code);
              return (
                <PillTag
                  key={code}
                  label={opt ? `${opt.code} – ${opt.label}` : code}
                  onRemove={() => toggleCpv(code)}
                />
              );
            })}
          </div>
        )}

        <div className="space-y-2 pt-1">
          {CPV_OPTIONS.map(opt => (
            <label key={opt.code} className="flex items-center gap-2.5 cursor-pointer group">
              <input
                type="checkbox"
                checked={config.preferred_cpvs.includes(opt.code)}
                onChange={() => toggleCpv(opt.code)}
                className="accent-emerald-500 w-3.5 h-3.5"
              />
              <span className="font-mono text-xs text-earth-600 w-20 shrink-0">{opt.code}</span>
              <span className="text-sm text-earth-400 group-hover:text-earth-300 transition-colors">{opt.label}</span>
            </label>
          ))}
        </div>
      </GlassCard>

      {/* Preferred Regions */}
      <GlassCard className="p-5 space-y-3">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-earth-500" />
          <p className="text-sm font-semibold text-earth-200">Preferowane regiony</p>
          <span className="text-xs text-earth-600 ml-auto">{config.preferred_regions.length} wybranych</span>
        </div>

        {config.preferred_regions.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {config.preferred_regions.map(r => (
              <PillTag key={r} label={r} onRemove={() => toggleRegion(r)} />
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 gap-1.5 pt-1">
          {VOIVODESHIPS.map(v => (
            <label key={v} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={config.preferred_regions.includes(v)}
                onChange={() => toggleRegion(v)}
                className="accent-emerald-500 w-3.5 h-3.5"
              />
              <span className="text-sm text-earth-400 group-hover:text-earth-300 transition-colors capitalize">{v}</span>
            </label>
          ))}
        </div>
      </GlassCard>

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        <ActionBtn onClick={save} loading={saving} icon={<Save className="w-4 h-4" />}>
          Zapisz konfigurację
        </ActionBtn>
        <ActionBtn
          variant="accent"
          onClick={rescore}
          loading={rescoring}
          icon={<Zap className="w-4 h-4" />}
        >
          Przelicz scoring
        </ActionBtn>
      </div>

      {/* Rescore result */}
      <AnimatePresence>
        {rescoreResult && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.2 }}
          >
            <GlassCard className="p-5 space-y-3 border border-emerald-500/20">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <p className="text-sm font-semibold text-emerald-400">Scoring przeliczony pomyslnie</p>
              </div>
              <p className="text-xs text-earth-500">{rescoreResult.message}</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-earth-800/60 rounded-xl p-3 border border-earth-700/40">
                  <p className="text-xs text-earth-600 mb-1">Przetwarzone</p>
                  <p className="text-lg font-bold text-earth-100 font-mono">
                    {rescoreResult.processed}
                    <span className="text-xs text-earth-600 font-normal ml-1">/ {rescoreResult.total}</span>
                  </p>
                </div>
                <div className="bg-earth-800/60 rounded-xl p-3 border border-earth-700/40">
                  <p className="text-xs text-earth-600 mb-1">Zmiana avg. score</p>
                  <div className="flex items-baseline gap-2">
                    <p className="text-base font-bold text-earth-500 font-mono">
                      {rescoreResult.avg_score_before.toFixed(2)}
                    </p>
                    <TrendingUp className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    <p className="text-base font-bold text-emerald-400 font-mono">
                      {rescoreResult.avg_score_after.toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Main component ────────────────────────────────────────────────────────────

// ─── Usage section ─────────────────────────────────────────────────────────────

interface UsageData {
  tenders_this_month: number;
  ai_analyses_this_month: number;
}

function UsageSection() {
  const authFetch = useAuthFetch();
  const [usage, setUsage]     = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    authFetch('/api/v2/settings/usage')
      .then((d: unknown) => setUsage(d as UsageData))
      .catch((e: unknown) => setError((e as Error).message ?? 'Błąd pobierania danych'))
      .finally(() => setLoading(false));
  }, [authFetch]);

  if (loading) return (
    <div className="flex items-center justify-center h-32">
      <Loader2 className="w-6 h-6 animate-spin text-accent-primary" />
    </div>
  );

  if (error) return (
    <GlassCard className="p-6 text-center text-accent-danger text-sm">{error}</GlassCard>
  );

  return (
    <div className="space-y-6">
      <GlassCard className="p-6">
        <h3 className="text-sm font-semibold text-earth-300 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-accent-primary" />
          Użycie w bieżącym miesiącu
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-earth-800/40 rounded-token-lg p-4 border border-earth-700/30">
            <div className="text-2xl font-bold text-earth-100">
              {usage?.tenders_this_month ?? 0}
            </div>
            <div className="text-xs text-earth-400 mt-1">Przetargi (ten miesiąc)</div>
          </div>
          <div className="bg-earth-800/40 rounded-token-lg p-4 border border-earth-700/30">
            <div className="text-2xl font-bold text-earth-100">
              {usage?.ai_analyses_this_month ?? 0}
            </div>
            <div className="text-xs text-earth-400 mt-1">Analizy AI (ten miesiąc)</div>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}

// ─── Billing Section ────────────────────────────────────────────────────────

interface BillingPlan {
  id: string;
  name: string;
  status: 'active' | 'trialing' | 'past_due' | 'canceled';
  current_period_end: string;
  cancel_at_period_end: boolean;
  features: string[];
  seats: number;
}

function BillingSection() {
  const authFetch = useAuthFetch();
  const [sub, setSub] = useState<BillingPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch('/api/v2/billing/subscription')
      .then(d => setSub(d as BillingPlan))
      .catch((e: unknown) => setError((e as Error).message ?? 'Błąd pobierania subskrypcji'))
      .finally(() => setLoading(false));
  }, [authFetch]);

  const STATUS_CFG: Record<string, { label: string; className: string }> = {
    active:   { label: 'Aktywna',        className: 'bg-accent-primary/15 text-accent-primary' },
    trialing: { label: 'Trial',          className: 'bg-accent-info/15 text-accent-info' },
    past_due: { label: 'Nieopłacona',    className: 'bg-accent-danger/15 text-accent-danger' },
    canceled: { label: 'Anulowana',      className: 'bg-earth-700/30 text-earth-500' },
  };

  if (loading) return <div className="flex items-center justify-center h-32"><Loader2 className="w-5 h-5 animate-spin text-accent-primary" /></div>;
  if (error) return <GlassCard className="p-6 text-center"><p className="text-accent-danger text-sm flex items-center justify-center gap-2"><AlertCircle className="w-4 h-4" />{error}</p></GlassCard>;

  return (
    <div className="space-y-4">
      <GlassCard className="p-6">
        <h3 className="text-sm font-semibold text-earth-300 uppercase tracking-wider mb-4 flex items-center gap-2">
          <CreditCard className="w-4 h-4 text-accent-primary" /> Plan i subskrypcja
        </h3>
        {sub ? (
          <div className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-earth-100 font-bold text-lg">{sub.name}</span>
                  {sub.status && STATUS_CFG[sub.status] && (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CFG[sub.status].className}`}>
                      {STATUS_CFG[sub.status].label}
                    </span>
                  )}
                </div>
                <p className="text-xs text-earth-500 mt-1">
                  {sub.seats} stanowisk · Odnowienie: {sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString('pl-PL') : '—'}
                  {sub.cancel_at_period_end && <span className="text-accent-warning ml-2">· Anuluje się na koniec okresu</span>}
                </p>
              </div>
              <button
                onClick={async () => {
                  try {
                    const data = await authFetch('/api/v2/billing/checkout-url') as { url?: string };
                    if (data?.url) window.open(data.url, '_blank');
                  } catch { /* noop */ }
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-accent-primary/10 text-accent-primary hover:bg-accent-primary/20 rounded-token-lg transition-colors border border-accent-primary/20"
              >
                <ExternalLink className="w-3.5 h-3.5" /> Zarządzaj
              </button>
            </div>
            {sub.features && sub.features.length > 0 && (
              <div>
                <p className="text-xs text-earth-600 mb-2 font-medium">Dostępne funkcje:</p>
                <div className="flex flex-wrap gap-1.5">
                  {sub.features.map(f => (
                    <span key={f} className="text-xs bg-earth-800/50 text-earth-400 border border-earth-700/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-accent-primary" /> {f}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-earth-500">Brak danych subskrypcji</p>
        )}
      </GlassCard>
    </div>
  );
}

// ─── API Keys Section ────────────────────────────────────────────────────────

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
}

interface ApiKeyCreated extends ApiKey {
  plaintext_key?: string;
}

function APIKeysSection() {
  const authFetch = useAuthFetch();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await authFetch('/api/v2/api-keys') as ApiKey[];
      setKeys(Array.isArray(data) ? data : []);
    } catch (e: unknown) {
      setError((e as Error).message ?? 'Błąd pobierania kluczy API');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const data = await authFetch('/api/v2/api-keys', {
        method: 'POST',
        body: JSON.stringify({ name: newKeyName.trim(), scopes: ['read'] }),
      }) as ApiKeyCreated;
      setCreatedKey(data);
      setKeys(prev => [data, ...prev]);
      setNewKeyName('');
    } catch (e: unknown) {
      setError((e as Error).message ?? 'Błąd tworzenia klucza');
    } finally {
      setCreating(false);
    }
  };

  const deleteKey = async (id: string) => {
    try {
      await authFetch(`/api/v2/api-keys/${id}`, { method: 'DELETE' });
      setKeys(prev => prev.filter(k => k.id !== id));
    } catch (e: unknown) {
      setError((e as Error).message ?? 'Błąd usuwania klucza');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-32"><Loader2 className="w-5 h-5 animate-spin text-accent-primary" /></div>;

  return (
    <div className="space-y-4">
      {/* New key created banner */}
      {createdKey?.plaintext_key && (
        <GlassCard className="p-4 border border-accent-warning/30 bg-accent-warning/5">
          <p className="text-xs text-accent-warning font-semibold mb-2 flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5" /> Zapisz klucz — nie będzie widoczny ponownie!
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-earth-950 rounded px-3 py-2 text-xs text-earth-200 font-mono truncate">
              {createdKey.plaintext_key}
            </code>
            <button
              onClick={() => { navigator.clipboard.writeText(createdKey.plaintext_key!); }}
              className="p-2 text-earth-400 hover:text-accent-primary transition-colors"
              title="Kopiuj klucz"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
          <button onClick={() => setCreatedKey(null)} className="text-xs text-earth-600 hover:text-earth-400 mt-2 transition-colors">Zamknij</button>
        </GlassCard>
      )}

      {error && <p className="text-xs text-accent-danger">{error}</p>}

      {/* Create new key */}
      <GlassCard className="p-6">
        <h3 className="text-sm font-semibold text-earth-300 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Key className="w-4 h-4 text-accent-primary" /> Klucze API
        </h3>
        <div className="flex gap-2 mb-4">
          <input
            className="input-base flex-1"
            placeholder="Nazwa klucza (np. CI/CD pipeline)"
            value={newKeyName}
            onChange={e => setNewKeyName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && create()}
          />
          <button
            onClick={create}
            disabled={creating || !newKeyName.trim()}
            className="flex items-center gap-1.5 px-4 py-2 text-sm bg-accent-primary text-earth-950 font-semibold rounded-token-lg hover:bg-emerald-400 disabled:opacity-50 transition-colors"
          >
            {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Utwórz
          </button>
        </div>

        {keys.length === 0 ? (
          <p className="text-sm text-earth-600 py-4 text-center">Brak kluczy API</p>
        ) : (
          <div className="space-y-2">
            {keys.map(k => (
              <div key={k.id} className="flex items-center gap-3 p-3 bg-earth-800/40 rounded-token border border-earth-700/30">
                <Key className="w-3.5 h-3.5 text-earth-500 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-earth-200 font-medium">{k.name}</div>
                  <div className="text-xs text-earth-600 flex items-center gap-2">
                    <code className="font-mono">{k.prefix}****</code>
                    <span>·</span>
                    <span>{new Date(k.created_at).toLocaleDateString('pl-PL')}</span>
                    {k.last_used_at && <span>· Użyty: {new Date(k.last_used_at).toLocaleDateString('pl-PL')}</span>}
                  </div>
                </div>
                <div className="flex gap-1">
                  {k.scopes.map(s => (
                    <span key={s} className="text-[10px] px-1.5 py-0.5 bg-earth-700/50 text-earth-400 rounded">{s}</span>
                  ))}
                </div>
                <button
                  onClick={() => deleteKey(k.id)}
                  className="p-1.5 text-earth-600 hover:text-accent-danger transition-colors"
                  title="Usuń klucz"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ─── Webhooks Section ────────────────────────────────────────────────────────

interface WebhookOut {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
  last_triggered_at: string | null;
}

function WebhooksSection() {
  const authFetch = useAuthFetch();
  const [webhooks, setWebhooks] = useState<WebhookOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ url: '', events: 'tender.new,alert.match' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await authFetch('/api/v3/webhooks') as WebhookOut[];
      setWebhooks(Array.isArray(data) ? data : []);
    } catch (e: unknown) {
      setError((e as Error).message ?? 'Błąd pobierania webhooków');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.url.trim()) return;
    setCreating(true);
    try {
      const events = form.events.split(',').map(s => s.trim()).filter(Boolean);
      const data = await authFetch('/api/v3/webhooks', {
        method: 'POST',
        body: JSON.stringify({ url: form.url.trim(), events }),
      }) as WebhookOut;
      setWebhooks(prev => [data, ...prev]);
      setForm({ url: '', events: 'tender.new,alert.match' });
    } catch (e: unknown) {
      setError((e as Error).message ?? 'Błąd tworzenia webhooka');
    } finally {
      setCreating(false);
    }
  };

  const deleteWebhook = async (id: string) => {
    try {
      await authFetch(`/api/v3/webhooks/${id}`, { method: 'DELETE' });
      setWebhooks(prev => prev.filter(w => w.id !== id));
    } catch (e: unknown) {
      setError((e as Error).message ?? 'Błąd usuwania webhooka');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-32"><Loader2 className="w-5 h-5 animate-spin text-accent-primary" /></div>;

  return (
    <div className="space-y-4">
      {error && <p className="text-xs text-accent-danger">{error}</p>}
      <GlassCard className="p-6">
        <h3 className="text-sm font-semibold text-earth-300 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Webhook className="w-4 h-4 text-accent-primary" /> Webhooki
        </h3>
        <div className="space-y-3 mb-4">
          <div>
            <label className="block text-xs text-earth-500 mb-1.5">URL endpointu *</label>
            <input
              className="input-base w-full"
              type="url"
              placeholder="https://your-server.com/webhook"
              value={form.url}
              onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-xs text-earth-500 mb-1.5">Zdarzenia (przecinkami)</label>
            <input
              className="input-base w-full"
              placeholder="tender.new, alert.match"
              value={form.events}
              onChange={e => setForm(f => ({ ...f, events: e.target.value }))}
            />
          </div>
          <button
            onClick={create}
            disabled={creating || !form.url.trim()}
            className="flex items-center gap-1.5 px-4 py-2 text-sm bg-accent-primary text-earth-950 font-semibold rounded-token-lg hover:bg-emerald-400 disabled:opacity-50 transition-colors"
          >
            {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Dodaj webhook
          </button>
        </div>

        {webhooks.length === 0 ? (
          <p className="text-sm text-earth-600 py-4 text-center">Brak webhooków</p>
        ) : (
          <div className="space-y-2">
            {webhooks.map(w => (
              <div key={w.id} className="flex items-start gap-3 p-3 bg-earth-800/40 rounded-token border border-earth-700/30">
                <Webhook className="w-3.5 h-3.5 text-earth-500 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-mono text-earth-300 truncate">{w.url}</div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {w.events.map(ev => (
                      <span key={ev} className="text-[10px] px-1.5 py-0.5 bg-accent-info/10 text-accent-info rounded border border-accent-info/20">{ev}</span>
                    ))}
                  </div>
                  {w.last_triggered_at && (
                    <div className="text-[10px] text-earth-600 mt-0.5">Ostatnio: {new Date(w.last_triggered_at).toLocaleString('pl-PL')}</div>
                  )}
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${w.is_active ? 'bg-accent-primary/15 text-accent-primary' : 'bg-earth-700/30 text-earth-500'}`}>
                  {w.is_active ? 'Aktywny' : 'Wstrzymany'}
                </span>
                <button
                  onClick={() => deleteWebhook(w.id)}
                  className="p-1.5 text-earth-600 hover:text-accent-danger transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ─── Settings Page ────────────────────────────────────────────────────────────

export function SettingsPage() {
  const [section, setSection] = useState<SectionId>('organizacja');

  return (
    <PageShell title="Ustawienia" subtitle="Konfiguracja konta i platformy" noPadding>
      <div className="flex flex-1 overflow-hidden h-full">
        {/* Left sidebar */}
        <div className="w-52 border-r border-earth-800/60 py-3 px-2 space-y-0.5 shrink-0 overflow-y-auto">
          {SECTIONS.map(s => {
            const Icon = s.icon;
            const active = section === s.id;
            return (
              <button
                key={s.id}
                onClick={() => setSection(s.id)}
                className={`w-full flex items-center justify-between gap-2.5 px-3 py-2.5 rounded-token-lg text-sm transition-colors ${
                  active
                    ? 'bg-accent-primary/10 text-accent-primary border border-accent-primary/20'
                    : 'text-earth-400 hover:text-earth-200 hover:bg-earth-800/60'
                }`}
              >
                <span className="flex items-center gap-2.5">
                  <Icon className="w-4 h-4 shrink-0" />
                  {s.label}
                </span>
                {active && <ChevronRight className="w-3.5 h-3.5 opacity-60" />}
              </button>
            );
          })}
        </div>

        {/* Right content */}
        <div className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={section}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            >
              {section === 'organizacja' ? <OrganizacjaSection /> : null}
              {section === 'zespol'      ? <ZespolSection />       : null}
              {section === 'zaproszenia' ? <ZaproszeniaSSection /> : null}
              {section === 'ustawienia'  ? <UstawieniaSection />   : null}
              {section === 'scoring'     ? <ScoringSection />      : null}
              {section === 'billing'     ? <BillingSection />      : null}
              {section === 'api_keys'    ? <APIKeysSection />      : null}
              {section === 'webhooks'    ? <WebhooksSection />     : null}
              {section === 'uzycie'      ? <UsageSection />        : null}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </PageShell>
  );
}
