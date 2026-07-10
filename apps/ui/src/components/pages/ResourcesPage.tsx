'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Users, Truck, Calendar, Plus, Search, UserCheck, UserX,
} from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Resource {
  id: string;
  type: 'person' | 'equipment';
  name: string;
  role?: string;
  status: 'available' | 'assigned' | 'on_leave' | 'unavailable';
  project?: string;
  rate_pln?: number;
}

// ── Demo data ─────────────────────────────────────────────────────────────────
const DEMO_RESOURCES: Resource[] = [
  { id: '1', type: 'person', name: 'Jan Kowalski', role: 'Kierownik budowy', status: 'assigned', project: 'Droga gminna Pieszyce', rate_pln: 650 },
  { id: '2', type: 'person', name: 'Anna Nowak', role: 'Inżynier kosztorysant', status: 'available', rate_pln: 550 },
  { id: '3', type: 'person', name: 'Piotr Wiśniewski', role: 'Operator koparki', status: 'assigned', project: 'Kanalizacja Łagiewniki', rate_pln: 450 },
  { id: '4', type: 'equipment', name: 'Koparko-ładowarka CAT 428F2', role: 'Klasa 0.6m³', status: 'available', rate_pln: 1200 },
  { id: '5', type: 'equipment', name: 'Walec wibracyjny Bomag', role: 'BW 177', status: 'assigned', project: 'Droga gminna Pieszyce', rate_pln: 800 },
  { id: '6', type: 'person', name: 'Marek Zieliński', role: 'Geodeta', status: 'on_leave', rate_pln: 500 },
  { id: '7', type: 'equipment', name: 'Wywrotka MAN TGS', role: '8x4, 32t', status: 'available', rate_pln: 950 },
  { id: '8', type: 'person', name: 'Karolina Maj', role: 'BHP / Koordynator', status: 'available', rate_pln: 400 },
];

const STATUS_META: Record<string, { label: string; dot: string; bg: string }> = {
  available: { label: 'Dostępny', dot: 'bg-emerald-400', bg: 'bg-emerald-500/10 text-emerald-400' },
  assigned: { label: 'Zajęty', dot: 'bg-amber-400', bg: 'bg-amber-500/10 text-amber-400' },
  on_leave: { label: 'Urlop', dot: 'bg-blue-400', bg: 'bg-blue-500/10 text-blue-400' },
  unavailable: { label: 'Niedostępny', dot: 'bg-earth-600', bg: 'bg-earth-700/30 text-earth-500' },
};

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};
const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export function ResourcesPage() {
  const [filter, setFilter] = useState<'all' | 'person' | 'equipment'>('all');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const resources = DEMO_RESOURCES.filter(r => {
    if (filter !== 'all' && r.type !== filter) return false;
    if (search && !r.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const counts = {
    total: DEMO_RESOURCES.length,
    available: DEMO_RESOURCES.filter(r => r.status === 'available').length,
    assigned: DEMO_RESOURCES.filter(r => r.status === 'assigned').length,
    onLeave: DEMO_RESOURCES.filter(r => r.status === 'on_leave').length,
  };

  const selected = DEMO_RESOURCES.find(r => r.id === selectedId);

  return (
    <motion.div
      className="flex flex-col gap-6 p-6 h-full overflow-y-auto"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {/* Header */}
      <motion.div variants={item} className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-earth-100">Zasoby</h2>
          <p className="text-earth-500 text-sm mt-0.5">Pracownicy i sprzęt — zarządzanie dostępnością</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary text-earth-950 font-semibold text-sm hover:bg-emerald-400 transition-colors">
          <Plus className="w-4 h-4" /> Dodaj zasób
        </button>
      </motion.div>

      {/* Stat Cards */}
      <motion.div variants={item} className="grid grid-cols-4 gap-3">
        {[
          { label: 'Łącznie', value: counts.total, icon: Users, color: 'text-earth-200' },
          { label: 'Dostępni', value: counts.available, icon: UserCheck, color: 'text-emerald-400' },
          { label: 'Zajęci', value: counts.assigned, icon: UserX, color: 'text-amber-400' },
          { label: 'Urlopy', value: counts.onLeave, icon: Calendar, color: 'text-blue-400' },
        ].map(s => (
          <div key={s.label} className="glass-card rounded-xl p-4 border border-earth-800/40">
            <div className="flex items-center gap-2 text-earth-500 text-xs mb-2">
              <s.icon className="w-3.5 h-3.5" />
              {s.label}
            </div>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </motion.div>

      {/* Filters */}
      <motion.div variants={item} className="flex items-center gap-3">
        <div className="flex gap-1 p-1 rounded-lg bg-earth-900 border border-earth-800/60">
          {([['all', 'Wszystkie'], ['person', 'Pracownicy'], ['equipment', 'Sprzęt']] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                filter === key ? 'bg-earth-800 text-earth-100' : 'text-earth-500 hover:text-earth-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-earth-600" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Szukaj zasobów..."
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-earth-900 border border-earth-800/60 text-earth-200 text-sm placeholder:text-earth-600 focus:outline-none focus:border-accent-primary/40"
          />
        </div>
      </motion.div>

      {/* Content: List + Detail */}
      <motion.div variants={item} className="flex gap-4 flex-1 min-h-0">
        {/* Resource List */}
        <div className="w-[380px] shrink-0 glass-card rounded-xl border border-earth-800/40 overflow-y-auto">
          <div className="divide-y divide-earth-800/30">
            {resources.map(r => {
              const meta = STATUS_META[r.status];
              return (
                <button
                  key={r.id}
                  onClick={() => setSelectedId(r.id)}
                  className={`w-full text-left px-4 py-3 hover:bg-earth-800/30 transition-colors ${
                    selectedId === r.id ? 'bg-earth-800/40' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-earth-800 flex items-center justify-center border border-earth-700/40">
                      {r.type === 'person'
                        ? <Users className="w-4 h-4 text-earth-500" />
                        : <Truck className="w-4 h-4 text-earth-500" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-earth-200 font-medium truncate">{r.name}</p>
                      <p className="text-xs text-earth-500 truncate">{r.role}</p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${meta.bg}`}>
                      {meta.label}
                    </span>
                  </div>
                  {r.project && (
                    <p className="text-xs text-earth-600 mt-1 ml-12 truncate">📍 {r.project}</p>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Detail / Calendar Panel */}
        <div className="flex-1 glass-card rounded-xl border border-earth-800/40 p-6">
          {selected ? (
            <div className="space-y-5">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-xl bg-earth-800 flex items-center justify-center border border-earth-700/40">
                  {selected.type === 'person'
                    ? <Users className="w-7 h-7 text-earth-400" />
                    : <Truck className="w-7 h-7 text-earth-400" />}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-earth-100">{selected.name}</h3>
                  <p className="text-sm text-earth-500">{selected.role}</p>
                </div>
                <span className={`ml-auto text-xs px-3 py-1 rounded-full font-medium ${STATUS_META[selected.status].bg}`}>
                  {STATUS_META[selected.status].label}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded-lg bg-earth-900/60 border border-earth-800/40">
                  <p className="text-xs text-earth-500 mb-1">Stawka dzienna</p>
                  <p className="text-lg font-bold text-earth-200 font-mono">{selected.rate_pln?.toLocaleString()} PLN</p>
                </div>
                <div className="p-3 rounded-lg bg-earth-900/60 border border-earth-800/40">
                  <p className="text-xs text-earth-500 mb-1">Projekt</p>
                  <p className="text-sm text-earth-200">{selected.project || 'Brak przypisania'}</p>
                </div>
              </div>

              {/* Calendar placeholder */}
              <div className="mt-4">
                <h4 className="text-sm font-semibold text-earth-300 mb-3 flex items-center gap-2">
                  <Calendar className="w-4 h-4" /> Dostępność — Lipiec 2026
                </h4>
                <div className="grid grid-cols-7 gap-1">
                  {['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd'].map(d => (
                    <div key={d} className="text-center text-xs text-earth-600 py-1">{d}</div>
                  ))}
                  {Array.from({ length: 31 }, (_, i) => {
                    const busy = selected.status === 'assigned' && i < 15;
                    const leave = selected.status === 'on_leave' && i >= 10 && i <= 20;
                    return (
                      <div
                        key={i}
                        className={`text-center text-xs py-2 rounded-md ${
                          leave ? 'bg-blue-500/20 text-blue-400' :
                          busy ? 'bg-amber-500/15 text-amber-400' :
                          'bg-earth-900/40 text-earth-500 hover:bg-earth-800/60'
                        }`}
                      >
                        {i + 1}
                      </div>
                    );
                  })}
                </div>
                <div className="flex items-center gap-4 mt-3 text-xs text-earth-500">
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-amber-500/30" /> Zajęty</span>
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-blue-500/30" /> Urlop</span>
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-earth-900/60" /> Dostępny</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
              <Calendar className="w-12 h-12 text-earth-600" />
              <div>
                <p className="text-earth-300 font-medium">Wybierz zasób</p>
                <p className="text-earth-500 text-sm mt-1">Kliknij na pracownika lub sprzęt, aby zobaczyć kalendarz dostępności</p>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
