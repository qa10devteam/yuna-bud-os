'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Users, Shield, Mail, MoreHorizontal, Plus, Crown, UserCog, Eye } from 'lucide-react';
import { PageShell } from '@/components/PageShell';

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'owner' | 'admin' | 'manager' | 'viewer';
  avatar_initials: string;
  last_active: string;
  projects: number;
}

const DEMO_TEAM: TeamMember[] = [
  { id: '1', name: 'Mateusz Jakimów',    email: 'mateusz@qa10.io',            role: 'owner',   avatar_initials: 'MJ', last_active: '2 min temu',    projects: 5 },
  { id: '2', name: 'Anna Kowalska',      email: 'a.kowalska@firma.pl',        role: 'admin',   avatar_initials: 'AK', last_active: '15 min temu',   projects: 4 },
  { id: '3', name: 'Piotr Nowak',        email: 'p.nowak@firma.pl',           role: 'manager', avatar_initials: 'PN', last_active: '1h temu',       projects: 3 },
  { id: '4', name: 'Karolina Wiśniewska',email: 'k.wisniewska@firma.pl',      role: 'manager', avatar_initials: 'KW', last_active: '3h temu',       projects: 2 },
  { id: '5', name: 'Tomasz Zieliński',   email: 't.zielinski@firma.pl',       role: 'viewer',  avatar_initials: 'TZ', last_active: '1 dzień temu', projects: 1 },
];

const ROLE_META: Record<string, { label: string; icon: React.ReactNode; bg: string }> = {
  owner:   { label: 'Właściciel',    icon: <Crown   className="w-3 h-3" />, bg: 'bg-warning/10 text-warning border-warning/20' },
  admin:   { label: 'Administrator', icon: <Shield  className="w-3 h-3" />, bg: 'bg-violet/10 text-violet border-violet/20' },
  manager: { label: 'Kierownik',     icon: <UserCog className="w-3 h-3" />, bg: 'bg-info/10 text-info border-info/20' },
  viewer:  { label: 'Podgląd',       icon: <Eye     className="w-3 h-3" />, bg: 'bg-earth-700/30 text-earth-400 border-earth-700/40' },
};

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item      = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.3 } } };

export function TeamPage() {
  const [members] = useState<TeamMember[]>(DEMO_TEAM);

  const actions = (
    <button className="btn-primary flex items-center gap-2">
      <Plus className="w-4 h-4" /> Zaproś użytkownika
    </button>
  );

  return (
    <PageShell title="Zespół" subtitle="Zarządzanie użytkownikami i rolami" actions={actions}>
      <motion.div className="flex flex-col gap-6" variants={container} initial="hidden" animate="show">

        {/* Stats */}
        <motion.div variants={item} className="grid grid-cols-4 gap-3">
          {[
            { label: 'Członkowie',     value: members.length },
            { label: 'Administratorzy', value: members.filter(m => m.role === 'owner' || m.role === 'admin').length },
            { label: 'Kierownicy',     value: members.filter(m => m.role === 'manager').length },
            { label: 'Aktywni dziś',   value: members.filter(m => m.last_active.includes('min') || m.last_active.includes('h temu')).length },
          ].map(s => (
            <div key={s.label} className="card rounded-token-lg p-4 shadow-token-sm">
              <p className="text-earth-500 text-xs mb-1">{s.label}</p>
              <p className="text-2xl font-bold text-earth-200">{s.value}</p>
            </div>
          ))}
        </motion.div>

        {/* Roles legend */}
        <motion.div variants={item} className="flex items-center gap-4 text-xs text-earth-500">
          <span>Role:</span>
          {Object.entries(ROLE_META).map(([key, meta]) => (
            <span key={key} className={`flex items-center gap-1 px-2 py-0.5 rounded-full border ${meta.bg}`}>
              {meta.icon} {meta.label}
            </span>
          ))}
        </motion.div>

        {/* Members Table */}
        <motion.div variants={item} className="card rounded-token-lg overflow-hidden shadow-token-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-earth-800/60 text-earth-500 text-xs">
                <th className="text-left px-5 py-3 font-medium">Użytkownik</th>
                <th className="text-left px-4 py-3 font-medium">Rola</th>
                <th className="text-left px-4 py-3 font-medium">Projekty</th>
                <th className="text-left px-4 py-3 font-medium">Ostatnia aktywność</th>
                <th className="text-right px-4 py-3 font-medium w-12"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-earth-800/30">
              {members.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-16 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <Users className="w-10 h-10 text-earth-600" />
                      <p className="text-earth-400 text-sm font-medium">Brak członków zespołu</p>
                      <p className="text-earth-600 text-xs">Zaproś pierwszego użytkownika</p>
                    </div>
                  </td>
                </tr>
              )}
              {members.map(m => {
                const meta = ROLE_META[m.role];
                return (
                  <tr key={m.id} className="hover:bg-earth-800/20 transition-colors">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-accent-primary/30 to-accent-secondary/30 flex items-center justify-center text-xs font-bold text-earth-200 border border-earth-700/40">
                          {m.avatar_initials}
                        </div>
                        <div>
                          <p className="text-earth-200 font-medium">{m.name}</p>
                          <p className="text-earth-500 text-xs flex items-center gap-1">
                            <Mail className="w-3 h-3" /> {m.email}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border font-medium ${meta.bg}`}>
                        {meta.icon} {meta.label}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-earth-400">{m.projects}</td>
                    <td className="px-4 py-4 text-earth-500 text-xs">{m.last_active}</td>
                    <td className="px-4 py-4 text-right">
                      <button className="p-1.5 rounded-token hover:bg-earth-800/60 text-earth-500 hover:text-earth-300 transition-colors">
                        <MoreHorizontal className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </motion.div>
      </motion.div>
    </PageShell>
  );
}
