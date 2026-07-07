'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Building2, Users, Send, Settings2,
  Save, Loader2, Trash2, Shield, User, Crown, Eye,
  Mail, XCircle, Plus, RefreshCw, CheckCircle2,
  ChevronRight, Tag, MapPin, Calendar, Hash,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';

// ─── Types ─────────────────────────────────────────────────────────────────────

type SectionId = 'organizacja' | 'zespol' | 'zaproszenia' | 'ustawienia';

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

// ─── Constants ─────────────────────────────────────────────────────────────────

const SECTIONS: { id: SectionId; label: string; icon: typeof Building2 }[] = [
  { id: 'organizacja', label: 'Organizacja',  icon: Building2 },
  { id: 'zespol',      label: 'Zespol',       icon: Users     },
  { id: 'zaproszenia', label: 'Zaproszenia',  icon: Send      },
  { id: 'ustawienia',  label: 'Ustawienia',   icon: Settings2 },
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
  free:       { label: 'Free',       className: 'bg-zinc-700/50 text-zinc-300 border border-zinc-600/40' },
  pro:        { label: 'Pro',        className: 'bg-blue-500/15 text-blue-400 border border-blue-500/30' },
  enterprise: { label: 'Enterprise', className: 'bg-amber-500/15 text-amber-400 border border-amber-500/30' },
};

const ROLE_META: Record<string, { label: string; Icon: typeof User; color: string }> = {
  owner:     { label: 'Wlasciciel',   Icon: Crown,   color: 'text-amber-400'   },
  admin:     { label: 'Administrator', Icon: Shield,  color: 'text-blue-400'    },
  estimator: { label: 'Kosztorysant', Icon: User,    color: 'text-emerald-400' },
  viewer:    { label: 'Przegladajacy', Icon: Eye,    color: 'text-earth-400'   },
};

// ─── Shared micro-components ───────────────────────────────────────────────────

const INPUT = 'w-full bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-blue-500/60 transition-colors';

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
  variant?: 'primary' | 'secondary' | 'danger';
}) {
  const styles = {
    primary:   'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30',
    secondary: 'bg-earth-800/60 text-earth-300 hover:bg-earth-700/60 border border-earth-700/60',
    danger:    'bg-red-500/15 text-red-400 hover:bg-red-500/25 border border-red-500/25',
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
                        <span className="text-xs text-zinc-500 bg-zinc-800/60 px-1.5 py-0.5 rounded-md border border-zinc-700/50 shrink-0">Nieaktywny</span>
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
  expired:  'bg-zinc-700/50 text-zinc-500 border-zinc-600/30',
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

// ─── Main component ────────────────────────────────────────────────────────────

export function SettingsPage() {
  const [section, setSection] = useState<SectionId>('organizacja');

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Page header */}
      <div className="px-6 py-4 border-b border-earth-800/60 shrink-0">
        <h2 className="text-lg font-semibold text-earth-100">Ustawienia</h2>
        <p className="text-earth-500 text-xs mt-0.5">Konfiguracja organizacji, zespolu i preferencji</p>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <div className="w-52 border-r border-earth-800/60 py-3 px-2 space-y-0.5 shrink-0 overflow-y-auto">
          {SECTIONS.map(s => {
            const Icon = s.icon;
            const active = section === s.id;
            return (
              <button
                key={s.id}
                onClick={() => setSection(s.id)}
                className={`w-full flex items-center justify-between gap-2.5 px-3 py-2.5 rounded-xl text-sm transition-colors ${
                  active
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
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
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
