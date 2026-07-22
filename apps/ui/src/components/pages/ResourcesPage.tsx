'use client';

import { useState } from 'react';
import { motion } from 'motion/react';
import { Users, Truck, Calendar, Plus, Search, UserCheck, UserX } from 'lucide-react';
import { PageShell } from '@/components/PageShell';

interface Resource {
  id: string;
  type: 'person' | 'equipment';
  name: string;
  role?: string;
  status: 'available' | 'assigned' | 'on_leave' | 'unavailable';
  project?: string;
  rate_pln?: number;
}

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
  available:   { label: 'Dostępny',    dot: 'bg-success',     bg: 'bg-success/10 text-success' },
  assigned:    { label: 'Zajęty',      dot: 'bg-warning',     bg: 'bg-warning/10 text-warning' },
  on_leave:    { label: 'Urlop',       dot: 'bg-info',        bg: 'bg-info/10 text-info' },
  unavailable: { label: 'Niedostępny', dot: 'bg-ink-600',   bg: 'bg-ink-700/30 text-slate-500' },
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
    total:     DEMO_RESOURCES.length,
    available: DEMO_RESOURCES.filter(r => r.status === 'available').length,
    assigned:  DEMO_RESOURCES.filter(r => r.status === 'assigned').length,
    onLeave:   DEMO_RESOURCES.filter(r => r.status === 'on_leave').length,
  };

  const selected = DEMO_RESOURCES.find(r => r.id === selectedId);

  const actions = (
    <button type="button" className="btn-primary flex items-center gap-2">
      <Plus className="w-4 h-4" /> Dodaj zasób
    </button>
  );

  return (
    <PageShell title="Zasoby" subtitle="Zarządzanie zasobami budowlanymi" actions={actions}>
      <motion.div className="flex flex-col gap-6" variants={container} initial="hidden" animate="show">

        {/* Stat Cards */}
        <motion.div variants={item} className="grid grid-cols-4 gap-3">
          {[
            { label: 'Łącznie',   value: counts.total,     icon: Users,     color: 'text-slate-200' },
            { label: 'Dostępni',  value: counts.available, icon: UserCheck, color: 'text-success' },
            { label: 'Zajęci',    value: counts.assigned,  icon: UserX,     color: 'text-warning' },
            { label: 'Urlopy',    value: counts.onLeave,   icon: Calendar,  color: 'text-info' },
          ].map(s => (
            <div key={s.label} className="card rounded-xl p-4 shadow-md-sm">
              <div className="flex items-center gap-2 text-slate-500 text-xs mb-2">
                <s.icon className="w-3.5 h-3.5" />
                {s.label}
              </div>
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </motion.div>

        {/* Filters */}
        <motion.div variants={item} className="flex items-center gap-3">
          <div className="flex gap-1 p-1 rounded-xl bg-ink-900 border border-ink-800/60">
            {([['all', 'Wszystkie'], ['person', 'Pracownicy'], ['equipment', 'Sprzęt']] as const).map(([key, label]) => (
              <button type="button"
                key={key}
                onClick={() => setFilter(key)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
                  filter === key ? 'bg-ink-800 text-slate-100' : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Szukaj zasobów..."
              className="input-base pl-9"
            />
          </div>
        </motion.div>

        {/* Content: List + Detail */}
        <motion.div variants={item} className="flex gap-4 min-h-[480px]">
          {/* Resource List */}
          <div className="w-[380px] shrink-0 card rounded-xl overflow-y-auto shadow-md-sm">
            <div className="divide-y divide-ink-800/30">
              {resources.map(r => {
                const meta = STATUS_META[r.status];
                return (
                  <button type="button"
                    key={r.id}
                    onClick={() => setSelectedId(r.id)}
                    className={`w-full text-left px-4 py-3 hover:bg-ink-800/30 transition-colors ${
                      selectedId === r.id ? 'bg-ink-800/40' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-ink-800 flex items-center justify-center border border-ink-700/40">
                        {r.type === 'person'
                          ? <Users className="w-4 h-4 text-slate-500" />
                          : <Truck className="w-4 h-4 text-slate-500" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-200 font-medium truncate">{r.name}</p>
                        <p className="text-xs text-slate-500 truncate">{r.role}</p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${meta.bg}`}>
                        {meta.label}
                      </span>
                    </div>
                    {r.project && (
                      <p className="text-xs text-slate-600 mt-1 ml-12 truncate">📍 {r.project}</p>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Detail / Calendar Panel */}
          <div className="flex-1 card rounded-xl p-6 shadow-md-sm">
            {selected ? (
              <div className="space-y-5">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-ink-800 flex items-center justify-center border border-ink-700/40">
                    {selected.type === 'person'
                      ? <Users className="w-7 h-7 text-slate-400" />
                      : <Truck className="w-7 h-7 text-slate-400" />}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-slate-100">{selected.name}</h3>
                    <p className="text-sm text-slate-500">{selected.role}</p>
                  </div>
                  <span className={`ml-auto text-xs px-3 py-1 rounded-full font-medium ${STATUS_META[selected.status].bg}`}>
                    {STATUS_META[selected.status].label}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-xl bg-ink-900/60 border border-ink-800/40">
                    <p className="text-xs text-slate-500 mb-1">Stawka dzienna</p>
                    <p className="text-lg font-bold text-slate-200 font-mono">{selected.rate_pln?.toLocaleString()} PLN</p>
                  </div>
                  <div className="p-3 rounded-xl bg-ink-900/60 border border-ink-800/40">
                    <p className="text-xs text-slate-500 mb-1">Projekt</p>
                    <p className="text-sm text-slate-200">{selected.project || 'Brak przypisania'}</p>
                  </div>
                </div>

                {/* Calendar placeholder */}
                <div className="mt-4">
                  <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                    <Calendar className="w-4 h-4" /> Dostępność — Lipiec 2026
                  </h4>
                  <div className="grid grid-cols-7 gap-1">
                    {['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd'].map(d => (
                      <div key={d} className="text-center text-xs text-slate-600 py-1">{d}</div>
                    ))}
                    {Array.from({ length: 31 }, (_, i) => {
                      const busy  = selected.status === 'assigned' && i < 15;
                      const leave = selected.status === 'on_leave' && i >= 10 && i <= 20;
                      return (
                        <div
                          key={i}
                          className={`text-center text-xs py-2 rounded-md ${
                            leave ? 'bg-info/20 text-info' :
                            busy  ? 'bg-warning/15 text-warning' :
                            'bg-ink-900/40 text-slate-500 hover:bg-ink-800/60'
                          }`}
                        >
                          {i + 1}
                        </div>
                      );
                    })}
                  </div>
                  <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-warning/30" /> Zajęty</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-info/30" /> Urlop</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-ink-900/60" /> Dostępny</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                <Calendar className="w-12 h-12 text-slate-600" />
                <div>
                  <p className="text-slate-300 font-medium">Wybierz zasób</p>
                  <p className="text-slate-500 text-sm mt-1">Kliknij na pracownika lub sprzęt, aby zobaczyć kalendarz dostępności</p>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </PageShell>
  );
}
