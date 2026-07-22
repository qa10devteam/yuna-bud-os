'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  DndContext, DragOverlay, PointerSensor, useSensor, useSensors,
  closestCenter, type DragStartEvent, type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext, useSortable, verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Bell, BellPlus, Bookmark, Trash2, AlertTriangle,
  CheckCircle2, Clock, Plus, X, RefreshCw, Filter,
  ChevronDown, ChevronRight,
} from 'lucide-react';
import { PageShell } from '@/components/PageShell';
import { SkeletonCard } from '@/components/SkeletonCard';
import {
  useBookmarks, useAlerts,
  fmtMln, fmtPLN,
  type TenderBookmark, type TenderAlert, type AlertCreateBody,
} from '@/lib/api-v2';
import { showToast } from '@/components/Toast';

// ── Stage config ──────────────────────────────────────────────────────────────
const STAGES = [
  { key: 'watching',    label: 'Obserwacja', color: '#60a5fa', border: 'border-indigo/30',   bg: 'bg-indigo/8',    head: 'bg-indigo/15' },
  { key: 'analyzing',  label: 'Analiza',    color: '#a78bfa', border: 'border-purple-500/30', bg: 'bg-purple-500/8',  head: 'bg-purple-500/15' },
  { key: 'estimated',  label: 'Wyceniony',  color: '#fbbf24', border: 'border-warn-brd', bg: 'bg-warn/8',  head: 'bg-warn-bg' },
  { key: 'bid',        label: 'Złożono',    color: '#34d399', border: 'border-em-brd', bg: 'bg-em/8', head: 'bg-em/15' },
  { key: 'won',        label: 'Wygrano',    color: '#10b981', border: 'border-em/40', bg: 'bg-em/8', head: 'bg-em/20' },
  { key: 'lost',       label: 'Przegrano',  color: '#f87171', border: 'border-nogo-brd',    bg: 'bg-nogo/8',     head: 'bg-nogo/15' },
];

function fmtDate(s: string | null) {
  if (!s) return null;
  return new Date(s).toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' });
}

function daysUntil(d: string | null) {
  if (!d) return null;
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86_400_000);
}

// ── Bookmark card (sortable) ──────────────────────────────────────────────────
function BookmarkCard({
  item, color, onDelete, onStageChange,
}: {
  item: TenderBookmark;
  color: string;
  onDelete: (id: string) => void;
  onStageChange: (id: string, stage: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });
  const [showMenu, setShowMenu] = useState(false);
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.3 : 1 };
  const days = daysUntil(item.due_date);
  const overdue = days !== null && days < 0;
  const urgent = days !== null && days >= 0 && days <= 3;

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners} className="touch-manipulation">
      <motion.div
        layout
        className="card-hover p-3 cursor-grab active:cursor-grabbing transition-[color,background-color,border-color,opacity,transform,box-shadow] group"
        style={{ borderLeftWidth: 3, borderLeftColor: color }}
      >
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="text-sm text-slate-100 line-clamp-2 leading-snug flex-1">
            {item.title || item.ht_id || 'Przetarg'}
          </div>
          <button type="button"
            onPointerDown={e => { e.stopPropagation(); }}
            onClick={e => { e.stopPropagation(); onDelete(item.id); }}
            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-nogo/20 text-slate-600 hover:text-nogo transition-[color,background-color,border-color,opacity,transform,box-shadow] shrink-0"
          >
            <Trash2 size={13} />
          </button>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {item.estimated_value && (
            <span className="text-xs text-em font-mono">{fmtPLN(item.estimated_value)}</span>
          )}
          {item.buyer_name && (
            <span className="text-xs text-slate-500 truncate max-w-[120px]">{item.buyer_name}</span>
          )}
        </div>

        {days !== null && (
          <div className={`flex items-center gap-1 mt-2 text-xs ${overdue ? 'text-nogo' : urgent ? 'text-warn' : 'text-slate-500'}`}>
            <Clock size={11} />
            {overdue ? `Przeterminowane ${Math.abs(days)} dni temu` : days === 0 ? 'Dziś!' : `Za ${days} dni`}
          </div>
        )}

        {item.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {item.tags.slice(0, 3).map(tag => (
              <span key={tag} className="text-xs bg-ink-800 text-slate-500 px-1.5 py-0.5 rounded">{tag}</span>
            ))}
          </div>
        )}

        {/* Quick stage change */}
        <div className="relative mt-2">
          <button type="button"
            onPointerDown={e => e.stopPropagation()}
            onClick={e => { e.stopPropagation(); setShowMenu(v => !v); }}
            className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-400 transition-colors"
          >
            <ChevronDown size={11} />
            Przenieś
          </button>
          {showMenu && (
            <div className="absolute bottom-6 left-0 z-20 bg-ink-900 border border-ink-700 rounded-lg shadow-xl min-w-[140px]">
              {STAGES.filter(s => s.key !== item.stage).map(s => (
                <button type="button"
                  key={s.key}
                  onPointerDown={e => e.stopPropagation()}
                  onClick={e => { e.stopPropagation(); onStageChange(item.id, s.key); setShowMenu(false); }}
                  className="w-full text-left px-3 py-1.5 text-xs hover:bg-ink-800 text-slate-400 hover:text-slate-100 transition-colors first:rounded-t-lg last:rounded-b-lg"
                >
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

// ── Kanban column ─────────────────────────────────────────────────────────────
function KanbanColumn({
  stage, items, count, overdue, onDelete, onStageChange,
}: {
  stage: typeof STAGES[number];
  items: TenderBookmark[];
  count: number;
  overdue: number;
  onDelete: (id: string) => void;
  onStageChange: (id: string, newStage: string) => void;
}) {
  return (
    <div className={`flex flex-col rounded-xl border ${stage.border} ${stage.bg} min-h-[200px]`}>
      <div className={`${stage.head} rounded-t-xl px-3 py-2 flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: stage.color }}>
            {stage.label}
          </span>
          <span className="text-xs bg-ink-900/60 text-slate-400 px-1.5 py-0.5 rounded-full">{count}</span>
        </div>
        {overdue > 0 && (
          <span className="flex items-center gap-1 text-xs text-nogo">
            <AlertTriangle size={10} />
            {overdue}
          </span>
        )}
      </div>

      <SortableContext items={items.map(i => i.id)} strategy={verticalListSortingStrategy}>
        <div className="p-2 flex flex-col gap-2 flex-1">
          {items.map(item => (
            <BookmarkCard
              key={item.id}
              item={item}
              color={stage.color}
              onDelete={onDelete}
              onStageChange={onStageChange}
            />
          ))}
          {items.length === 0 && (
            <div className="flex-1 flex items-center justify-center py-6 text-xs text-slate-700 select-none">
              Przeciągnij tutaj
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

// ── Alert form ────────────────────────────────────────────────────────────────
function AlertForm({ onClose, onCreate }: { onClose: () => void; onCreate: (body: AlertCreateBody) => Promise<void> }) {
  const [form, setForm] = useState<AlertCreateBody>({
    name: '',
    cpv_prefixes: [],
    keywords: [],
    frequency: 'daily',
    channel: 'push',
  });
  const [cpvInput, setCpvInput] = useState('');
  const [kwInput, setKwInput] = useState('');
  const [saving, setSaving] = useState(false);

  const addCpv = () => {
    const v = cpvInput.trim();
    if (v && !form.cpv_prefixes?.includes(v)) {
      setForm(f => ({ ...f, cpv_prefixes: [...(f.cpv_prefixes || []), v] }));
    }
    setCpvInput('');
  };

  const addKw = () => {
    const v = kwInput.trim();
    if (v && !form.keywords?.includes(v)) {
      setForm(f => ({ ...f, keywords: [...(f.keywords || []), v] }));
    }
    setKwInput('');
  };

  const handleSubmit = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await onCreate(form);
      showToast('success', 'Alert utworzony ✓');
      onClose();
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd tworzenia alertu');
    } finally {
      setSaving(false);
    }
  };

  const field = 'input-base';

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
        exit={{ scale: 0.95 }}
        onClick={e => e.stopPropagation()}
        className="bg-ink-900 border border-ink-800/50 rounded-2xl w-full max-w-lg p-6 shadow-xl max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-base font-bold text-ink-950/30 flex items-center gap-2">
            <Bell size={16} className="text-em" />
            Nowy Alert
          </h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1.5">
            <X size={16} className="text-slate-400" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Nazwa alertu *</label>
            <input className={field} placeholder="np. Drogi w Mazowszu 2025" value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Prefiksy CPV</label>
            <div className="flex gap-2 mb-2">
              <input className={field + ' flex-1'} placeholder="np. 4523" value={cpvInput}
                onChange={e => setCpvInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addCpv()} />
              <button type="button" onClick={addCpv} className="px-3 bg-ink-700 rounded-lg text-slate-300 hover:bg-ink-600 text-sm">+</button>
            </div>
            <div className="flex flex-wrap gap-1">
              {form.cpv_prefixes?.map(c => (
                <span key={c} className="flex items-center gap-1 text-xs bg-indigo/20 text-indigo-300 px-2 py-0.5 rounded-full">
                  {c}
                  <button type="button" onClick={() => setForm(f => ({ ...f, cpv_prefixes: f.cpv_prefixes?.filter(x => x !== c) }))}>
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Słowa kluczowe</label>
            <div className="flex gap-2 mb-2">
              <input className={field + ' flex-1'} placeholder="np. remont, kanalizacja" value={kwInput}
                onChange={e => setKwInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addKw()} />
              <button type="button" onClick={addKw} className="px-3 bg-ink-700 rounded-lg text-slate-300 hover:bg-ink-600 text-sm">+</button>
            </div>
            <div className="flex flex-wrap gap-1">
              {form.keywords?.map(k => (
                <span key={k} className="flex items-center gap-1 text-xs bg-em/20 text-em px-2 py-0.5 rounded-full">
                  {k}
                  <button type="button" onClick={() => setForm(f => ({ ...f, keywords: f.keywords?.filter(x => x !== k) }))}>
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Częstość</label>
              <select className={field} value={form.frequency}
                onChange={e => setForm(f => ({ ...f, frequency: e.target.value as AlertCreateBody['frequency'] }))}>
                <option value="realtime">Natychmiast</option>
                <option value="daily">Codziennie</option>
                <option value="weekly">Co tydzień</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Kanał</label>
              <select className={field} value={form.channel}
                onChange={e => setForm(f => ({ ...f, channel: e.target.value as AlertCreateBody['channel'] }))}>
                <option value="push">W aplikacji (push)</option>
                <option value="email">Email</option>
                <option value="webhook">Webhook</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Wartość min (PLN)</label>
              <input type="number" className={field} placeholder="0"
                onChange={e => setForm(f => ({ ...f, value_min: e.target.value ? +e.target.value : undefined }))} />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Wartość max (PLN)</label>
              <input type="number" className={field} placeholder="∞"
                onChange={e => setForm(f => ({ ...f, value_max: e.target.value ? +e.target.value : undefined }))} />
            </div>
          </div>

          {form.channel === 'webhook' && (
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Webhook URL</label>
              <input type="url" className={field} placeholder="https://…"
                onChange={e => setForm(f => ({ ...f, webhook_url: e.target.value }))} />
            </div>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <button type="button" onClick={onClose} className="btn-secondary flex-1 py-2.5">
            Anuluj
          </button>
          <button type="button"
            onClick={handleSubmit}
            disabled={saving || !form.name.trim()}
            className="btn-primary flex-1 py-2.5"
          >
            {saving ? <RefreshCw size={14} className="animate-spin" /> : <BellPlus size={14} />}
            Utwórz alert
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Alert list ────────────────────────────────────────────────────────────────
function AlertsList() {
  const { data, loading, create, toggle, remove } = useAlerts();
  const [showForm, setShowForm] = useState(false);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            <Bell size={14} className="text-em" />
            Moje alerty
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">{data.length} aktywnych alertów</p>
        </div>
        <button type="button"
          onClick={() => setShowForm(true)}
          className="btn-secondary flex items-center gap-1.5 text-xs"
        >
          <Plus size={13} />
          Nowy alert
        </button>
      </div>

      {loading && <div className="h-20 animate-pulse bg-ink-800 rounded-xl" />}

      {!loading && data.length === 0 && (
        <div className="text-center py-8 text-slate-600 text-sm border border-dashed border-ink-800 rounded-xl">
          Brak alertów — utwórz pierwszy
        </div>
      )}

      <div className="space-y-2">
        {data.map((alert: TenderAlert) => (
          <motion.div
            key={alert.id}
            layout
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-3 p-3 bg-ink-900 border border-ink-800/50 rounded-md hover:border-ink-700 transition-colors"
          >
            <button type="button"
              onClick={() => toggle(alert.id, !alert.is_active)}
              className={`shrink-0 w-9 h-5 rounded-full transition-colors relative ${alert.is_active ? 'bg-em' : 'bg-ink-700'}`}
            >
              <span className={`absolute top-0.5 w-4 h-4 bg-slate-100 rounded-full shadow transition-transform ${alert.is_active ? 'translate-x-4' : 'translate-x-0.5'}`} />
            </button>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-slate-100 font-medium truncate">{alert.name}</div>
              <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                {alert.cpv_prefixes.length > 0 && (
                  <span className="text-xs text-indigo-400">CPV: {alert.cpv_prefixes.join(', ')}</span>
                )}
                {alert.keywords.length > 0 && (
                  <span className="text-xs text-em">&quot;{alert.keywords.slice(0, 2).join('&quot;, &quot;')}&quot;</span>
                )}
                <span className="text-xs text-slate-600">{alert.frequency}</span>
                {alert.match_count > 0 && (
                  <span className="text-xs text-warn">{alert.match_count} dopasowań</span>
                )}
              </div>
            </div>
            <button type="button"
              onClick={() => remove(alert.id)}
              className="p-1.5 hover:bg-nogo/20 rounded-lg text-slate-600 hover:text-nogo transition-colors shrink-0"
            >
              <Trash2 size={13} />
            </button>
          </motion.div>
        ))}
      </div>

      <AnimatePresence>
        {showForm && <AlertForm key="form" onClose={() => setShowForm(false)} onCreate={create} />}
      </AnimatePresence>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export function BookmarksBoardPage() {
  const { data, loading, stats, patch, remove } = useBookmarks();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'kanban' | 'alerts'>('kanban');

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const byStage = useCallback((key: string) => data.filter(i => i.stage === key), [data]);

  const statsMap = Object.fromEntries(stats.map(s => [s.stage, s]));

  const handleDragStart = ({ active }: DragStartEvent) => setActiveId(active.id as string);

  const handleDragEnd = useCallback(async ({ active, over }: DragEndEvent) => {
    setActiveId(null);
    if (!over || active.id === over.id) return;
    // Find target stage from over.id (could be item id in column)
    const targetItem = data.find(i => i.id === over.id);
    if (!targetItem) return;
    if (targetItem.stage === data.find(i => i.id === active.id)?.stage) return;
    try {
      await patch(active.id as string, { stage: targetItem.stage });
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd zmiany etapu');
    }
  }, [data, patch]);

  const handleDelete = async (id: string) => {
    try {
      await remove(id);
      showToast('success', 'Usunięto zakładkę');
    } catch {
      showToast('error', 'Błąd usuwania');
    }
  };

  const handleStageChange = async (id: string, stage: string) => {
    try {
      await patch(id, { stage });
      showToast('success', `Przeniesiono → ${STAGES.find(s => s.key === stage)?.label}`);
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd');
    }
  };

  const dragItem = activeId ? data.find(i => i.id === activeId) : null;
  const totalCount = data.length;
  const overdueTotal = stats.reduce((s, r) => s + r.overdue, 0);

  return (
    <PageShell
      title="Tablica Przetargów Ofertowych"
      subtitle="Zarządzaj etapami ofertowania i konfiguruj alerty branżowe"
      actions={
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Bookmark size={12} className="text-indigo" />
          <span>{totalCount} zakładek</span>
          {overdueTotal > 0 && (
            <span className="flex items-center gap-1 text-nogo">
              <AlertTriangle size={11} />
              {overdueTotal} przeterminowanych
            </span>
          )}
        </div>
      }
    >
      <div className="space-y-5">

        {/* ── Stats strip ──────────────────────────────────────────────────── */}
        {!loading && stats.length > 0 && (
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
            {STAGES.map(s => {
              const st = statsMap[s.key];
              return (
                <div key={s.key} className="card p-2.5 text-center">
                  <div className="text-xs section-label" style={{ color: s.color }}>{s.label}</div>
                  <div className="text-xl font-bold text-slate-100 mt-0.5">{st?.count ?? 0}</div>
                  {(st?.overdue ?? 0) > 0 && (
                    <div className="text-xs text-nogo flex items-center justify-center gap-0.5 mt-0.5">
                      <AlertTriangle size={9} />{st?.overdue}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* ── Tabs ─────────────────────────────────────────────────────────── */}
        <div className="flex gap-1 bg-ink-900/40 rounded-xl p-1 w-fit border border-ink-700/50">
          {[
            { key: 'kanban', label: 'Kanban', icon: Filter },
            { key: 'alerts', label: 'Alerty', icon: Bell },
          ].map(({ key, label, icon: Icon }) => (
            <button type="button"
              key={key}
              onClick={() => setActiveTab(key as typeof activeTab)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
                activeTab === key
                  ? 'bg-ink-700 text-ink-950/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        {/* ── Kanban board ─────────────────────────────────────────────────── */}
        {activeTab === 'kanban' && (
          <div>
            {loading && (
              <div className="grid grid-cols-3 gap-3">
                {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
              </div>
            )}

            {!loading && totalCount === 0 && (
              <div className="text-center py-16 border border-dashed border-ink-800 rounded-2xl text-slate-600">
                <Bookmark size={32} className="mx-auto mb-3 text-ink-800" />
                <p className="text-sm">Brak zakładek — dodaj przetargi z widoku Zwiad</p>
              </div>
            )}

            {!loading && totalCount > 0 && (
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
              >
                <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 items-start">
                  {STAGES.map(stage => {
                    const items = byStage(stage.key);
                    const st = statsMap[stage.key];
                    return (
                      <KanbanColumn
                        key={stage.key}
                        stage={stage}
                        items={items}
                        count={st?.count ?? items.length}
                        overdue={st?.overdue ?? 0}
                        onDelete={handleDelete}
                        onStageChange={handleStageChange}
                      />
                    );
                  })}
                </div>

                <DragOverlay>
                  {dragItem && (
                    <div className="bg-ink-900 border border-em rounded-xl p-3 shadow-2xl rotate-1 w-56">
                      <div className="text-sm text-slate-100 line-clamp-2">{dragItem.title || dragItem.ht_id}</div>
                    </div>
                  )}
                </DragOverlay>
              </DndContext>
            )}
          </div>
        )}

        {/* ── Alerts ───────────────────────────────────────────────────────── */}
        {activeTab === 'alerts' && (
          <div className="card p-5">
            <AlertsList />
          </div>
        )}

      </div>
    </PageShell>
  );
}
