'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  FileText, Plus, Search, ChevronRight, ChevronLeft,
  Loader2, Check, Download, Save, Edit2, Trash2,
  Building2, Calendar, AlertCircle, X, RefreshCw,
  Package, FileCheck, Send, Trophy, XCircle, Clock,
  SlidersHorizontal, ClipboardList,
} from 'lucide-react';
import { useAuthFetch } from '@/lib/api-v2';
import { useStore } from '@/store/useStore';
import { showToast } from '@/components/Toast';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Offer {
  id: string;
  title: string;
  status: 'draft' | 'ready' | 'submitted' | 'won' | 'lost';
  tender_id: string | null;
  estimate_id: string | null;
  contractor_name: string | null;
  contractor_nip: string | null;
  contractor_address: string | null;
  delivery_days: number;
  warranty_months: number;
  payment_terms: string;
  notes: string | null;
  price_gross_pln: number | null;
  vat_pct: number;
  created_at: string;
}

interface KosztorysItem {
  id: string;
  description: string;
  unit: string;
  quantity: number;
  unit_price: number;
  line_total_pln: number;
}

interface TenderOption {
  id: string;
  title: string;
  contracting_authority: string;
  value_pln: number | null;
  cpv_code: string | null;
  deadline_date: string | null;
}

interface EditableItem extends KosztorysItem {
  _edited?: boolean;
}

interface FinalizacjaData {
  name: string;
  nip: string;
  address: string;
  delivery_days: number;
  warranty_months: number;
  payment_terms: string;
  notes: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtPLN(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(Number(n))) return '—';
  return Number(n).toLocaleString('pl-PL', {
    style: 'currency',
    currency: 'PLN',
    maximumFractionDigits: 0,
  });
}

function fmtDate(d: string | null | undefined): string {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('pl-PL', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return d;
  }
}

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  draft: {
    label: 'Szkic',
    color: 'bg-slate-700/50 text-slate-300 border-slate-600/40',
    icon: Clock,
  },
  ready: {
    label: 'Gotowa',
    color: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    icon: FileCheck,
  },
  submitted: {
    label: 'Złożona',
    color: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    icon: Send,
  },
  won: {
    label: 'Wygrana',
    color: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    icon: Trophy,
  },
  lost: {
    label: 'Przegrana',
    color: 'bg-red-500/15 text-red-400 border-red-500/30',
    icon: XCircle,
  },
} as const;



function OfferStatusBadge({ status }: { status: Offer['status'] }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft;
  const Icon = cfg.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${cfg.color} shrink-0`}
    >
      <Icon className="w-2.5 h-2.5" />
      {cfg.label}
    </span>
  );
}

// ── Wizard steps ──────────────────────────────────────────────────────────────

const STEPS = ['Przetarg', 'Kosztorys', 'Finalizacja', 'PDF'] as const;
type WizardStep = 0 | 1 | 2 | 3;

// ── Skeleton ──────────────────────────────────────────────────────────────────

function SkeletonOfferCard() {
  return (
    <div className="animate-shimmer rounded-xl border border-ink-800/40 bg-ink-900/40 p-3 mb-2 space-y-2">
      <div className="h-3 bg-ink-800 rounded-md w-3/4" />
      <div className="h-2.5 bg-ink-800 rounded-md w-1/2" />
      <div className="flex justify-between">
        <div className="h-4 bg-ink-800 rounded-md w-20" />
        <div className="h-3 bg-ink-800 rounded-md w-16" />
      </div>
    </div>
  );
}

// ── StepperBar ────────────────────────────────────────────────────────────────

function StepperBar({
  step,
  setStep,
}: {
  step: WizardStep;
  setStep: (s: WizardStep) => void;
}) {
  return (
    <div className="flex items-center mb-6">
      {STEPS.map((name, i) => {
        const done = i < step;
        const active = i === step;
        return (
          <div key={name} className="flex items-center flex-1 last:flex-none">
            <button type="button"
              onClick={() => {
                if (done) setStep(i as WizardStep);
              }}
              disabled={!done && !active}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200 ${
                active
                  ? 'bg-em/15 text-em border border-em/30'
                  : done
                  ? 'text-em hover:bg-em/10 cursor-pointer'
                  : 'text-slate-600 cursor-default'
              }`}
            >
              <span
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
                  done
                    ? 'bg-em text-ink-950'
                    : active
                    ? 'bg-em/20 border border-em/50 text-em'
                    : 'bg-ink-800 text-slate-600 border border-ink-700'
                }`}
              >
                {done ? <Check className="w-3 h-3" /> : i + 1}
              </span>
              <span className="hidden sm:inline">{name}</span>
            </button>
            {i < STEPS.length - 1 && (
              <div
                className={`flex-1 h-px mx-1 transition-colors ${
                  done ? 'bg-em/40' : 'bg-ink-800'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Step 1 – Przetarg
// ═══════════════════════════════════════════════════════════════════════════════

interface Step1Props {
  tenders: TenderOption[];
  loadingTenders: boolean;
  selectedTenderId: string;
  setSelectedTenderId: (id: string) => void;
  offerTitle: string;
  setOfferTitle: (t: string) => void;
  onNext: () => void;
}

function Step1Przetarg({
  tenders,
  loadingTenders,
  selectedTenderId,
  setSelectedTenderId,
  offerTitle,
  setOfferTitle,
  onNext,
}: Step1Props) {
  const [query, setQuery] = useState('');
  const [dropOpen, setDropOpen] = useState(false);
  const dropRef = useRef<HTMLDivElement>(null);

  const filtered =
    query.length > 0
      ? tenders.filter(
          (t) =>
            t.title.toLowerCase().includes(query.toLowerCase()) ||
            t.contracting_authority.toLowerCase().includes(query.toLowerCase()),
        )
      : tenders;

  const selectedTender = tenders.find((t) => t.id === selectedTenderId) ?? null;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) {
        setDropOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  function selectTender(t: TenderOption) {
    setSelectedTenderId(t.id);
    setDropOpen(false);
    setQuery('');
    if (!offerTitle) setOfferTitle(`Oferta – ${t.title}`);
  }

  return (
    <div className="space-y-5">
      {/* Tender select */}
      <div>
        <label className="label-base">
          Przetarg <span className="text-nogo">*</span>
        </label>
        <div className="relative" ref={dropRef}>
          {/* Trigger */}
          <div
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setDropOpen((v) => !v); }}
            onClick={() => setDropOpen((v) => !v)}
            className="flex items-center gap-2 w-full px-3 py-2.5 bg-ink-800/60 border border-ink-700/50 rounded-xl text-slate-200 text-sm cursor-pointer hover:border-em/40 focus:outline-none focus:border-em/50 transition-colors"
          >
            {selectedTender ? (
              <span className="flex-1 truncate">{selectedTender.title}</span>
            ) : (
              <span className="flex-1 text-slate-500">Wybierz przetarg…</span>
            )}
            <ChevronRight
              className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${dropOpen ? 'rotate-90' : ''}`}
            />
          </div>

          {/* Dropdown */}
          <AnimatePresence>
            {dropOpen && (
              <motion.div
                initial={{ opacity: 0, y: -6, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -6, scale: 0.98 }}
                transition={{ duration: 0.14 }}
                className="absolute z-30 top-full mt-1.5 left-0 right-0 bg-ink-900 border border-ink-700/60 rounded-xl shadow-xl overflow-hidden"
              >
                <div className="p-2 border-b border-ink-800/60">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
                    <input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      autoFocus
                      placeholder="Szukaj przetargu…"
                      className="input-base w-full pl-8 text-xs"
                    />
                  </div>
                </div>
                <div className="overflow-y-auto max-h-56">
                  {loadingTenders ? (
                    <div className="flex items-center justify-center py-8 gap-2 text-slate-500 text-xs">
                      <Loader2 className="w-4 h-4 animate-spin" /> Ładowanie…
                    </div>
                  ) : filtered.length === 0 ? (
                    <div className="py-8 text-center text-slate-500 text-xs">
                      {query ? `Brak wyników dla "${query}"` : 'Brak dostępnych przetargów'}
                    </div>
                  ) : (
                    <ul>
                      {filtered.map((t) => (
                        <li
                          key={t.id}
                          onClick={() => selectTender(t)}
                          className={`px-3 py-2.5 cursor-pointer hover:bg-ink-800/40 transition-colors border-b border-ink-800/20 last:border-b-0 ${
                            t.id === selectedTenderId ? 'bg-em/10' : ''
                          }`}
                        >
                          <div className="text-xs font-medium text-slate-200 line-clamp-2 leading-snug">
                            {t.title}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                            <span className="text-slate-500 text-[10px] truncate max-w-[180px]">
                              {t.contracting_authority}
                            </span>
                            {t.value_pln != null && (
                              <>
                                <span className="text-slate-700">·</span>
                                <span className="text-em text-[10px] font-mono">
                                  {fmtPLN(t.value_pln)}
                                </span>
                              </>
                            )}
                            {t.deadline_date && (
                              <>
                                <span className="text-slate-700">·</span>
                                <span className="text-warn text-[10px]">
                                  {fmtDate(t.deadline_date)}
                                </span>
                              </>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Tender details card */}
      <AnimatePresence>
        {selectedTender && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <GlassCard className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Building2 className="w-4 h-4 text-em" />
                <span className="section-label">
                  Dane przetargu
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="text-slate-500 mb-0.5">Zamawiający</div>
                  <div className="text-slate-200 leading-snug">
                    {selectedTender.contracting_authority}
                  </div>
                </div>
                {selectedTender.value_pln != null && (
                  <div>
                    <div className="text-slate-500 mb-0.5">Wartość szacunkowa</div>
                    <div className="text-em font-mono font-semibold">
                      {fmtPLN(selectedTender.value_pln)}
                    </div>
                  </div>
                )}
                {selectedTender.cpv_code && (
                  <div>
                    <div className="text-slate-500 mb-0.5">Kod CPV</div>
                    <div className="text-slate-300 font-mono">{selectedTender.cpv_code}</div>
                  </div>
                )}
                {selectedTender.deadline_date && (
                  <div>
                    <div className="text-slate-500 mb-0.5">Termin składania</div>
                    <div className="text-warn flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {fmtDate(selectedTender.deadline_date)}
                    </div>
                  </div>
                )}
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Offer title */}
      <div>
        <label className="label-base">
          Tytuł oferty <span className="text-nogo">*</span>
        </label>
        <input
          value={offerTitle}
          onChange={(e) => setOfferTitle(e.target.value)}
          placeholder="np. Oferta nr 1/2026 – budowa drogi gminnej"
          className="input-base w-full"
        />
      </div>

      {/* Helper note when no tenders */}
      {!loadingTenders && tenders.length === 0 && (
        <div className="flex items-start gap-2 px-3 py-2.5 rounded-xl bg-warn/10 border border-warn/20 text-xs text-warn">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            Brak aktywnych przetargów. Możesz mimo to wpisać tytuł oferty ręcznie i przejść do
            kolejnego kroku.
          </span>
        </div>
      )}

      <div className="flex justify-end pt-2">
        <button type="button"
          onClick={onNext}
          disabled={!offerTitle.trim()}
          className="btn-primary flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Dalej — Kosztorys <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Step 2 – Kosztorys
// ═══════════════════════════════════════════════════════════════════════════════

interface Step2Props {
  items: EditableItem[];
  setItems: React.Dispatch<React.SetStateAction<EditableItem[]>>;
  vatPct: number;
  setVatPct: (v: number) => void;
  loadingItems: boolean;
  onNext: () => void;
  onBack: () => void;
}

function Step2Kosztorys({
  items,
  setItems,
  vatPct,
  setVatPct,
  loadingItems,
  onNext,
  onBack,
}: Step2Props) {
  const [editCell, setEditCell] = useState<{
    id: string;
    field: 'quantity' | 'unit_price';
  } | null>(null);
  const [editVal, setEditVal] = useState('');

  const netTotal = items.reduce((s, it) => s + it.quantity * it.unit_price, 0);
  const vatTotal = netTotal * (vatPct / 100);
  const grossTotal = netTotal + vatTotal;

  function startEdit(id: string, field: 'quantity' | 'unit_price', current: number) {
    setEditCell({ id, field });
    setEditVal(String(current));
  }

  function commitEdit() {
    if (!editCell) return;
    const val = parseFloat(editVal);
    if (!isNaN(val) && val >= 0) {
      setItems((prev) =>
        prev.map((it) => {
          if (it.id !== editCell.id) return it;
          const q = editCell.field === 'quantity' ? val : it.quantity;
          const p = editCell.field === 'unit_price' ? val : it.unit_price;
          return { ...it, [editCell.field]: val, line_total_pln: q * p, _edited: true };
        }),
      );
    }
    setEditCell(null);
  }

  function addRow() {
    const newItem: EditableItem = {
      id: `new-${Date.now()}`,
      description: 'Nowa pozycja',
      unit: 'szt.',
      quantity: 1,
      unit_price: 0,
      line_total_pln: 0,
      _edited: true,
    };
    setItems((prev) => [...prev, newItem]);
  }

  function removeRow(id: string) {
    setItems((prev) => prev.filter((it) => it.id !== id));
  }

  function updateDesc(id: string, val: string) {
    setItems((prev) =>
      prev.map((it) => (it.id === id ? { ...it, description: val, _edited: true } : it)),
    );
  }

  function updateUnit(id: string, val: string) {
    setItems((prev) =>
      prev.map((it) => (it.id === id ? { ...it, unit: val, _edited: true } : it)),
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Netto', value: fmtPLN(netTotal), color: 'text-slate-200' },
          { label: `VAT ${vatPct}%`, value: fmtPLN(vatTotal), color: 'text-warn' },
          { label: 'Brutto', value: fmtPLN(grossTotal), color: 'text-em' },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            className="card px-4 py-3 text-center"
          >
            <div className="text-xs text-slate-500 mb-0.5">{label}</div>
            <div className={`text-sm font-bold font-mono ${color}`}>{value}</div>
          </div>
        ))}
      </div>

      {/* VAT picker */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-slate-400 font-medium">Stawka VAT:</span>
        {[0, 8, 23].map((v) => (
          <button type="button"
            key={v}
            onClick={() => setVatPct(v)}
            className={`px-3 py-1 rounded-md text-xs font-semibold border transition-colors ${
              vatPct === v
                ? 'bg-em/20 text-em border-em/40'
                : 'text-slate-400 border-ink-700/40 hover:border-ink-600 hover:text-slate-200'
            }`}
          >
            {v}%
          </button>
        ))}
      </div>

      {/* Table */}
      <GlassCard className="overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-ink-800/60">
          <span className="section-label">
            {items.length} pozycji kosztorysu
          </span>
          <button type="button"
            onClick={addRow}
            className="btn-secondary flex items-center gap-1.5 !text-xs"
          >
            <Plus className="w-3.5 h-3.5" /> Dodaj pozycję
          </button>
        </div>

        {loadingItems ? (
          <div className="flex items-center justify-center py-10 gap-2 text-slate-500 text-sm">
            <Loader2 className="w-5 h-5 animate-spin text-em" />
            Pobieranie kosztorysu…
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2 text-slate-500">
            <Package className="w-8 h-8 opacity-30" />
            <p className="text-sm">Brak pozycji kosztorysu.</p>
            <button type="button" onClick={addRow} className="text-xs text-em hover:underline">
              Dodaj pierwszą pozycję
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-ink-800/50 bg-ink-900/50">
                  <th className="text-left px-3 py-2.5 text-slate-500 font-medium w-7">#</th>
                  <th className="text-left px-3 py-2.5 text-slate-500 font-medium">Opis</th>
                  <th className="text-right px-3 py-2.5 text-slate-500 font-medium w-14">Jm</th>
                  <th className="text-right px-3 py-2.5 text-slate-500 font-medium w-20">Ilość</th>
                  <th className="text-right px-3 py-2.5 text-slate-500 font-medium w-28">
                    Cena jdn.
                  </th>
                  <th className="text-right px-3 py-2.5 text-slate-500 font-medium w-28">
                    Wartość
                  </th>
                  <th className="w-8" />
                </tr>
              </thead>
              <tbody>
                {items.map((it, idx) => (
                  <tr
                    key={it.id}
                    className="border-b border-ink-800/20 hover:bg-ink-800/10 transition-colors group"
                  >
                    <td className="px-3 py-2 text-slate-600">{idx + 1}</td>
                    {/* Description */}
                    <td className="px-3 py-2">
                      <input
                        value={it.description}
                        onChange={(e) => updateDesc(it.id, e.target.value)}
                        className="w-full bg-transparent text-slate-200 focus:outline-none focus:bg-ink-800/30 rounded-md px-1 py-0.5 min-w-[120px]"
                      />
                    </td>
                    {/* Unit */}
                    <td className="px-3 py-2 text-right">
                      <input
                        value={it.unit}
                        onChange={(e) => updateUnit(it.id, e.target.value)}
                        className="w-full text-right bg-transparent text-slate-400 focus:outline-none focus:bg-ink-800/30 rounded-md px-1 py-0.5"
                      />
                    </td>
                    {/* Quantity */}
                    <td className="px-3 py-2 text-right">
                      {editCell?.id === it.id && editCell.field === 'quantity' ? (
                        <input
                          autoFocus
                          type="number"
                          value={editVal}
                          onChange={(e) => setEditVal(e.target.value)}
                          onBlur={commitEdit}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') commitEdit();
                            if (e.key === 'Escape') setEditCell(null);
                          }}
                          className="w-full text-right bg-ink-800 border border-em/40 rounded-md px-1 py-0.5 text-slate-100 focus:outline-none text-xs"
                        />
                      ) : (
                        <span
                          onClick={() => startEdit(it.id, 'quantity', it.quantity)}
                          className="cursor-text text-slate-300 hover:text-em px-1 transition-colors"
                        >
                          {it.quantity}
                        </span>
                      )}
                    </td>
                    {/* Unit price */}
                    <td className="px-3 py-2 text-right">
                      {editCell?.id === it.id && editCell.field === 'unit_price' ? (
                        <input
                          autoFocus
                          type="number"
                          value={editVal}
                          onChange={(e) => setEditVal(e.target.value)}
                          onBlur={commitEdit}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') commitEdit();
                            if (e.key === 'Escape') setEditCell(null);
                          }}
                          className="w-full text-right bg-ink-800 border border-em/40 rounded-md px-1 py-0.5 text-slate-100 focus:outline-none text-xs"
                        />
                      ) : (
                        <span
                          onClick={() => startEdit(it.id, 'unit_price', it.unit_price)}
                          className="cursor-text text-slate-300 hover:text-em font-mono px-1 transition-colors"
                        >
                          {it.unit_price.toLocaleString('pl-PL', { minimumFractionDigits: 2 })}
                        </span>
                      )}
                    </td>
                    {/* Line total */}
                    <td className="px-3 py-2 text-right text-slate-200 font-mono font-semibold">
                      {fmtPLN(it.quantity * it.unit_price)}
                    </td>
                    <td className="px-2 py-2">
                      <button type="button"
                        onClick={() => removeRow(it.id)}
                        className="btn-ghost opacity-0 group-hover:opacity-100 !p-1"
                        title="Usuń pozycję"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-nogo" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-ink-700/60 bg-ink-900/50">
                  <td
                    colSpan={5}
                    className="px-4 py-3 text-xs font-semibold text-slate-400 text-right"
                  >
                    RAZEM NETTO
                  </td>
                  <td className="px-3 py-3 text-right text-sm font-bold text-slate-200 font-mono">
                    {fmtPLN(netTotal)}
                  </td>
                  <td />
                </tr>
                <tr className="bg-ink-900/30">
                  <td colSpan={5} className="px-4 py-2 text-xs text-slate-500 text-right">
                    VAT {vatPct}%
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-warn font-mono">
                    {fmtPLN(vatTotal)}
                  </td>
                  <td />
                </tr>
                <tr className="bg-ink-900/50 border-t border-em/20">
                  <td
                    colSpan={5}
                    className="px-4 py-3 text-sm font-bold text-em text-right"
                  >
                    RAZEM BRUTTO
                  </td>
                  <td className="px-3 py-3 text-right text-base font-bold text-em font-mono">
                    {fmtPLN(grossTotal)}
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </GlassCard>

      <div className="flex justify-between pt-2">
        <button type="button"
          onClick={onBack}
          className="btn-secondary flex items-center gap-2"
        >
          <ChevronLeft className="w-4 h-4" /> Wstecz
        </button>
        <button type="button"
          onClick={onNext}
          className="btn-primary flex items-center gap-2"
        >
          Dalej — Finalizacja <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Step 3 – Finalizacja
// ═══════════════════════════════════════════════════════════════════════════════

const PAYMENT_TERMS_OPTIONS = [
  '30 dni od doręczenia faktury',
  '14 dni od doręczenia faktury',
  '60 dni od doręczenia faktury',
  'Zaliczka 30%, reszta po odbiorze',
  'Płatność po odbiorze końcowym',
];

const WARRANTY_OPTIONS = [12, 24, 36, 48, 60];

interface Step3Props {
  data: FinalizacjaData;
  setData: React.Dispatch<React.SetStateAction<FinalizacjaData>>;
  grossTotal: number;
  saving: boolean;
  onSaveDraft: () => void;
  onGeneratePDF: () => void;
  onBack: () => void;
}

function Step3Finalizacja({
  data,
  setData,
  grossTotal,
  saving,
  onSaveDraft,
  onGeneratePDF,
  onBack,
}: Step3Props) {
  function set<K extends keyof FinalizacjaData>(field: K, value: FinalizacjaData[K]) {
    setData((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <div className="space-y-5">
      {/* Gross total banner */}
      <div className="rounded-xl bg-em/10 border border-em/20 px-5 py-4 flex items-center justify-between">
        <div>
          <div className="text-xs text-em mb-0.5 font-medium">
            Wartość oferty brutto
          </div>
          <div className="text-2xl font-bold text-em font-mono">
            {fmtPLN(grossTotal)}
          </div>
        </div>
        <FileCheck className="w-9 h-9 text-em/30" />
      </div>

      {/* Contractor data */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="w-4 h-4 text-em" />
          <span className="section-label">
            Dane wykonawcy
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="sm:col-span-2">
            <label className="label-base">
              Nazwa firmy <span className="text-nogo">*</span>
            </label>
            <input
              value={data.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="Firma Budowlana Sp. z o.o."
              className="input-base w-full"
            />
          </div>
          <div>
            <label className="label-base">NIP</label>
            <input
              value={data.nip}
              onChange={(e) => set('nip', e.target.value)}
              placeholder="123-456-78-90"
              className="input-base w-full"
            />
          </div>
          <div>
            <label className="label-base">Adres</label>
            <input
              value={data.address}
              onChange={(e) => set('address', e.target.value)}
              placeholder="ul. Budowlana 1, 00-001 Warszawa"
              className="input-base w-full"
            />
          </div>
        </div>
      </div>

      {/* Offer terms */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <SlidersHorizontal className="w-4 h-4 text-em" />
          <span className="section-label">
            Warunki oferty
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Delivery slider */}
          <div className="sm:col-span-2">
            <div className="flex items-center justify-between mb-2">
              <label className="label-base mb-0">Termin realizacji</label>
              <span className="text-sm font-bold text-em tabular-nums">
                {data.delivery_days} dni
              </span>
            </div>
            <input
              type="range"
              min={30}
              max={365}
              step={5}
              value={data.delivery_days}
              onChange={(e) => set('delivery_days', parseInt(e.target.value))}
              className="w-full h-1.5 rounded-full em-500 bg-ink-700 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-600 mt-1">
              <span>30 dni</span>
              <span>180 dni</span>
              <span>365 dni</span>
            </div>
          </div>

          {/* Warranty */}
          <div>
            <label className="label-base">Gwarancja</label>
            <select
              value={data.warranty_months}
              onChange={(e) => set('warranty_months', parseInt(e.target.value))}
              className="input-base w-full cursor-pointer"
            >
              {WARRANTY_OPTIONS.map((m) => (
                <option key={m} value={m}>
                  {m} miesięcy
                </option>
              ))}
            </select>
          </div>

          {/* Payment terms */}
          <div>
            <label className="label-base">
              Warunki płatności
            </label>
            <select
              value={data.payment_terms}
              onChange={(e) => set('payment_terms', e.target.value)}
              className="input-base w-full cursor-pointer"
            >
              {PAYMENT_TERMS_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="label-base">
          Uwagi / notatki
        </label>
        <textarea
          value={data.notes}
          onChange={(e) => set('notes', e.target.value)}
          rows={3}
          placeholder="Dodatkowe informacje, zastrzeżenia, uwagi do oferty…"
          className="input-base w-full resize-none"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-2 gap-3 flex-wrap">
        <button type="button"
          onClick={onBack}
          className="btn-secondary flex items-center gap-2"
        >
          <ChevronLeft className="w-4 h-4" /> Wstecz
        </button>
        <div className="flex items-center gap-3">
          <button type="button"
            onClick={onSaveDraft}
            disabled={saving}
            className="btn-ghost flex items-center gap-2 disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Zapisz szkic
          </button>
          <button type="button"
            onClick={onGeneratePDF}
            disabled={saving || !data.name.trim()}
            className="btn-primary flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            Generuj PDF
          </button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Step 4 – PDF success screen
// ═══════════════════════════════════════════════════════════════════════════════

interface Step4Props {
  offerTitle: string;
  saving: boolean;
  onDownloadAgain: () => void;
  onNewOffer: () => void;
}

function Step4PDF({ offerTitle, saving, onDownloadAgain, onNewOffer }: Step4Props) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-5 text-center">
      <motion.div
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', damping: 14, stiffness: 200 }}
        className="w-16 h-16 rounded-full bg-em/20 border border-em/30 flex items-center justify-center shadow-md-glow"
      >
        <Check className="w-8 h-8 text-em" />
      </motion.div>
      <div>
        <h3 className="text-lg font-bold text-slate-100 mb-1">Oferta gotowa!</h3>
        <p className="text-sm text-slate-400">PDF wygenerowany i otwarty w nowej karcie przeglądarki.</p>
        <p className="text-xs text-slate-600 mt-1 font-mono">{offerTitle}</p>
      </div>
      <div className="flex items-center gap-3 flex-wrap justify-center">
        <button type="button"
          onClick={onDownloadAgain}
          disabled={saving}
          className="btn-secondary flex items-center gap-2 disabled:opacity-50"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          Pobierz ponownie
        </button>
        <button type="button"
          onClick={onNewOffer}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> Nowa oferta
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main OfertaPage
// ═══════════════════════════════════════════════════════════════════════════════

export function OfertaPage() {
  const authFetch = useAuthFetch();
  const { accessToken } = useStore();

  // ── Offers list ────────────────────────────────────────────────────────────
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loadingOffers, setLoadingOffers] = useState(true);
  const [offerSearch, setOfferSearch] = useState('');

  // ── Wizard state ───────────────────────────────────────────────────────────
  const [wizardOpen, setWizardOpen] = useState(false);
  const [editingOfferId, setEditingOfferId] = useState<string | null>(null);
  const [wizardStep, setWizardStep] = useState<WizardStep>(0);

  // Step 1
  const [tenders, setTenders] = useState<TenderOption[]>([]);
  const [loadingTenders, setLoadingTenders] = useState(false);
  const [selectedTenderId, setSelectedTenderId] = useState('');
  const [offerTitle, setOfferTitle] = useState('');

  // Step 2
  const [items, setItems] = useState<EditableItem[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [vatPct, setVatPct] = useState(23);

  // Step 3
  const [finData, setFinData] = useState<FinalizacjaData>({
    name: '',
    nip: '',
    address: '',
    delivery_days: 90,
    warranty_months: 36,
    payment_terms: PAYMENT_TERMS_OPTIONS[0],
    notes: '',
  });
  const [saving, setSaving] = useState(false);

  // ── Derived ────────────────────────────────────────────────────────────────
  const netTotal = items.reduce((s, it) => s + it.quantity * it.unit_price, 0);
  const grossTotal = netTotal * (1 + vatPct / 100);

  // ── Load offers ────────────────────────────────────────────────────────────
  const loadOffers = useCallback(async () => {
    setLoadingOffers(true);
    try {
      const data = (await authFetch('/api/v1/offers')) as
        | { items?: Offer[]; total?: number }
        | Offer[];
      const fetched = Array.isArray(data) ? data : (data.items ?? []);
      setOffers(fetched);
    } catch {
      setOffers([]);
    } finally {
      setLoadingOffers(false);
    }
  }, [authFetch]);

  useEffect(() => {
    loadOffers();
  }, [loadOffers]);

  // ── Load tenders when wizard opens ────────────────────────────────────────
  useEffect(() => {
    if (!wizardOpen) return;
    setLoadingTenders(true);
    authFetch('/api/v2/tenders?limit=20&status=new')
      .then((d: unknown) => {
        const data = d as { items?: TenderOption[] } | TenderOption[];
        setTenders(Array.isArray(data) ? data : (data.items ?? []));
      })
      .catch(() => setTenders([]))
      .finally(() => setLoadingTenders(false));
  }, [wizardOpen, authFetch]);

  // ── Load kosztorys when entering step 2 ───────────────────────────────────
  useEffect(() => {
    if (wizardStep !== 1 || !selectedTenderId) return;
    setLoadingItems(true);
    authFetch(`/api/v2/estimates?tender_id=${selectedTenderId}`)
      .then((d: unknown) => {
        const data = d as { items?: KosztorysItem[]; lines?: KosztorysItem[] } | null;
        setItems(data?.items ?? data?.lines ?? []);
      })
      .catch(() => setItems([]))
      .finally(() => setLoadingItems(false));
  }, [wizardStep, selectedTenderId, authFetch]);

  // ── Wizard open helpers ────────────────────────────────────────────────────
  function openNewWizard() {
    setEditingOfferId(null);
    setWizardStep(0);
    setSelectedTenderId('');
    setOfferTitle('');
    setItems([]);
    setVatPct(23);
    setFinData({
      name: '',
      nip: '',
      address: '',
      delivery_days: 90,
      warranty_months: 36,
      payment_terms: PAYMENT_TERMS_OPTIONS[0],
      notes: '',
    });
    setWizardOpen(true);
  }

  function openEditWizard(offer: Offer) {
    setEditingOfferId(offer.id);
    setSelectedTenderId(offer.tender_id ?? '');
    setOfferTitle(offer.title);
    setVatPct(offer.vat_pct ?? 23);
    setFinData({
      name: offer.contractor_name ?? '',
      nip: offer.contractor_nip ?? '',
      address: offer.contractor_address ?? '',
      delivery_days: offer.delivery_days ?? 90,
      warranty_months: offer.warranty_months ?? 36,
      payment_terms: offer.payment_terms ?? PAYMENT_TERMS_OPTIONS[0],
      notes: offer.notes ?? '',
    });
    setWizardStep(0);
    setItems([]);
    setWizardOpen(true);
  }

  // ── Build API payload ──────────────────────────────────────────────────────
  function buildPayload(status: Offer['status']) {
    return {
      title: offerTitle,
      status,
      tender_id: selectedTenderId || null,
      contractor_name: finData.name || null,
      contractor_nip: finData.nip || null,
      contractor_address: finData.address || null,
      delivery_days: finData.delivery_days,
      warranty_months: finData.warranty_months,
      payment_terms: finData.payment_terms,
      notes: finData.notes || null,
      price_gross_pln: grossTotal > 0 ? grossTotal : null,
      vat_pct: vatPct,
    };
  }

  // ── Save draft ─────────────────────────────────────────────────────────────
  async function saveDraft() {
    if (!offerTitle.trim()) {
      showToast('error', 'Tytuł oferty jest wymagany');
      return;
    }
    setSaving(true);
    try {
      if (editingOfferId) {
        await authFetch(`/api/v1/offers/${editingOfferId}`, {
          method: 'PATCH',
          body: JSON.stringify(buildPayload('draft')),
        });
        showToast('success', 'Szkic zaktualizowany');
      } else {
        const result = (await authFetch('/api/v1/offers', {
          method: 'POST',
          body: JSON.stringify(buildPayload('draft')),
        })) as { id: string };
        setEditingOfferId(result.id);
        showToast('success', 'Szkic zapisany');
      }
      await loadOffers();
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd zapisu oferty');
    } finally {
      setSaving(false);
    }
  }

  // ── Generate PDF ───────────────────────────────────────────────────────────
  async function generatePDF() {
    if (!finData.name.trim()) {
      showToast('error', 'Podaj nazwę firmy wykonawcy przed generowaniem PDF');
      return;
    }
    setSaving(true);
    try {
      // Save / update the offer first
      let offerId = editingOfferId;
      if (offerId) {
        await authFetch(`/api/v1/offers/${offerId}`, {
          method: 'PATCH',
          body: JSON.stringify(buildPayload('ready')),
        });
      } else {
        const result = (await authFetch('/api/v1/offers', {
          method: 'POST',
          body: JSON.stringify(buildPayload('ready')),
        })) as { id: string };
        offerId = result.id;
        setEditingOfferId(offerId);
      }

      // Fetch PDF blob via raw fetch (authFetch parses JSON)
      const res = await fetch(`/api/v1/offers/${offerId}/pdf`, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      });

      if (!res.ok) {
        showToast('error', `Błąd generowania PDF (${res.status})`);
        await loadOffers();
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
      showToast('success', 'PDF wygenerowany — sprawdź nową kartę');
      setWizardStep(3);
      await loadOffers();
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Błąd generowania PDF');
    } finally {
      setSaving(false);
    }
  }

  // ── Filtered offers ────────────────────────────────────────────────────────
  const filteredOffers = offerSearch
    ? offers.filter((o) =>
        o.title.toLowerCase().includes(offerSearch.toLowerCase()),
      )
    : offers;

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <PageShell
      title="Kreator Oferty"
      subtitle="Generowanie oferty PDF"
      noPadding
    >
      <div className="flex h-full min-h-[calc(100dvh-8rem)]">
        {/* ── Left panel — offer list ─────────────────────────────────────────── */}
        <div className="w-80 shrink-0 flex flex-col border-r border-ink-800/60 bg-ink-900/30 h-full">
          {/* Panel header */}
          <div className="px-4 pt-5 pb-3 border-b border-ink-800/60 shrink-0">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-em" />
                <h2 className="text-sm font-bold text-slate-100">Oferty</h2>
                <span className="px-1.5 py-0.5 rounded-full bg-ink-800 text-slate-500 text-xs tabular-nums">
                  {offers.length}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <button type="button"
                  onClick={loadOffers}
                  title="Odśwież"
                  className="btn-ghost !p-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
                <button type="button"
                  onClick={openNewWizard}
                  className="btn-primary flex items-center gap-1.5 !text-xs"
                >
                  <Plus className="w-3.5 h-3.5" /> Nowa
                </button>
              </div>
            </div>
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
              <input
                value={offerSearch}
                onChange={(e) => setOfferSearch(e.target.value)}
                placeholder="Szukaj oferty…"
                className="input-base w-full pl-8 text-xs"
              />
            </div>
          </div>

          {/* Status legend */}
          <div className="flex items-center gap-2 px-4 py-2 border-b border-ink-800/40 flex-wrap">
            {(Object.keys(STATUS_CONFIG) as Offer['status'][]).map((key) => {
              const cfg = STATUS_CONFIG[key];
              return (
                <span
                  key={key}
                  className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[9px] font-medium border ${cfg.color}`}
                >
                  {cfg.label}
                </span>
              );
            })}
          </div>

          {/* Offer cards */}
          <div className="flex-1 overflow-y-auto py-2 px-2">
            {loadingOffers ? (
              <div className="space-y-0">
                {[1, 2, 3].map((i) => (
                  <SkeletonOfferCard key={i} />
                ))}
              </div>
            ) : filteredOffers.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-600 px-4">
                <FileText className="w-10 h-10 opacity-20" />
                <p className="text-xs text-center leading-relaxed">
                  {offerSearch
                    ? `Brak wyników dla "${offerSearch}"`
                    : 'Brak ofert.\nUtwórz pierwszą ofertę przetargową.'}
                </p>
                {!offerSearch && (
                  <button type="button"
                    onClick={openNewWizard}
                    className="text-xs text-em hover:underline transition-colors"
                  >
                    Utwórz ofertę →
                  </button>
                )}
              </div>
            ) : (
              <AnimatePresence initial={false}>
                {filteredOffers.map((offer, i) => (
                  <motion.div
                    key={offer.id}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -12 }}
                    transition={{ delay: i * 0.03, duration: 0.18 }}
                    className={`group relative rounded-xl border p-3 mb-2 cursor-pointer transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200 ${
                      editingOfferId === offer.id
                        ? 'bg-em/10 border-em/30'
                        : 'bg-ink-900/40 border-ink-800/40 hover:bg-ink-800/30 hover:border-ink-700/50'
                    }`}
                    onClick={() => openEditWizard(offer)}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <p className="text-xs font-semibold text-slate-200 leading-snug line-clamp-2 flex-1 min-w-0">
                        {offer.title}
                      </p>
                      <OfferStatusBadge status={offer.status} />
                    </div>
                    {offer.contractor_name && (
                      <div className="flex items-center gap-1 mb-2">
                        <Building2 className="w-2.5 h-2.5 text-slate-500 shrink-0" />
                        <span className="text-[10px] text-slate-400 truncate">
                          {offer.contractor_name}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center justify-between gap-1">
                      {offer.price_gross_pln != null ? (
                        <span className="text-xs font-mono text-em font-semibold">
                          {fmtPLN(offer.price_gross_pln)}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                      <span className="text-[10px] text-slate-600 shrink-0">
                        {fmtDate(offer.created_at)}
                      </span>
                    </div>
                    {/* Hover edit icon */}
                    <button type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        openEditWizard(offer);
                      }}
                      title="Edytuj"
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 rounded-md bg-ink-700/80 text-slate-400 hover:text-slate-200 transition-[color,background-color,border-color,opacity,transform,box-shadow]"
                    >
                      <Edit2 className="w-3 h-3" />
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
            )}
          </div>
        </div>

        {/* ── Right panel — wizard or landing ──────────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0 overflow-auto">
          <AnimatePresence mode="wait">
            {!wizardOpen ? (
              /* Landing / empty state */
              <motion.div
                key="landing"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="flex-1 flex flex-col items-center justify-center p-8 text-slate-600"
              >
                <div className="w-24 h-24 rounded-2xl bg-ink-900/60 border border-ink-800/60 flex items-center justify-center mb-5">
                  <FileText className="w-10 h-10 opacity-25" />
                </div>
                <h3 className="text-base font-semibold text-slate-400 mb-2">
                  Kreator oferty PDF
                </h3>
                <p className="text-sm text-slate-600 text-center max-w-xs leading-relaxed mb-6">
                  Utwórz nową ofertę przetargową lub wybierz istniejącą z listy po lewej stronie.
                  Wizard poprowadzi Cię przez 3 kroki.
                </p>
                <button type="button"
                  onClick={openNewWizard}
                  className="btn-primary flex items-center gap-2 shadow-md-glow"
                >
                  <Plus className="w-4 h-4" /> Nowa oferta
                </button>

                {/* Quick stats */}
                {offers.length > 0 && (
                  <div className="mt-10 grid grid-cols-3 gap-4 max-w-sm w-full">
                    {(
                      [
                        {
                          label: 'Szkice',
                          count: offers.filter((o) => o.status === 'draft').length,
                          color: 'text-slate-400',
                        },
                        {
                          label: 'Złożone',
                          count: offers.filter((o) => o.status === 'submitted').length,
                          color: 'text-indigo-400',
                        },
                        {
                          label: 'Wygrane',
                          count: offers.filter((o) => o.status === 'won').length,
                          color: 'text-em',
                        },
                      ] as const
                    ).map(({ label, count, color }) => (
                      <div
                        key={label}
                        className="card px-3 py-3 text-center"
                      >
                        <div className={`text-xl font-bold tabular-nums ${color}`}>{count}</div>
                        <div className="text-[10px] text-slate-600 mt-0.5">{label}</div>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            ) : (
              /* Wizard */
              <motion.div
                key="wizard"
                initial={{ opacity: 0, x: 24 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 24 }}
                transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
                className="flex-1 flex flex-col p-6"
              >
                {/* Wizard header */}
                <div className="flex items-start justify-between mb-4 gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <ClipboardList className="w-4 h-4 text-em" />
                      <h2 className="text-base font-bold text-slate-100">
                        {editingOfferId ? 'Edytuj ofertę' : 'Nowa oferta przetargowa'}
                      </h2>
                    </div>
                    <p className="text-xs text-slate-500">
                      {editingOfferId
                        ? offerTitle
                        : 'Wypełnij 3 kroki, aby wygenerować ofertę PDF'}
                    </p>
                  </div>
                  <button type="button"
                    onClick={() => setWizardOpen(false)}
                    className="btn-ghost !p-2 shrink-0"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Stepper */}
                <StepperBar step={wizardStep} setStep={setWizardStep} />

                {/* Step content */}
                <GlassCard className="p-6 flex-1 max-w-3xl w-full">
                  <AnimatePresence mode="wait">
                    {wizardStep === 0 && (
                      <motion.div
                        key="s0"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.18 }}
                      >
                        <Step1Przetarg
                          tenders={tenders}
                          loadingTenders={loadingTenders}
                          selectedTenderId={selectedTenderId}
                          setSelectedTenderId={setSelectedTenderId}
                          offerTitle={offerTitle}
                          setOfferTitle={setOfferTitle}
                          onNext={() => setWizardStep(1)}
                        />
                      </motion.div>
                    )}

                    {wizardStep === 1 && (
                      <motion.div
                        key="s1"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.18 }}
                      >
                        <Step2Kosztorys
                          items={items}
                          setItems={setItems}
                          vatPct={vatPct}
                          setVatPct={setVatPct}
                          loadingItems={loadingItems}
                          onNext={() => setWizardStep(2)}
                          onBack={() => setWizardStep(0)}
                        />
                      </motion.div>
                    )}

                    {wizardStep === 2 && (
                      <motion.div
                        key="s2"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.18 }}
                      >
                        <Step3Finalizacja
                          data={finData}
                          setData={setFinData}
                          grossTotal={grossTotal}
                          saving={saving}
                          onSaveDraft={saveDraft}
                          onGeneratePDF={generatePDF}
                          onBack={() => setWizardStep(1)}
                        />
                      </motion.div>
                    )}

                    {wizardStep === 3 && (
                      <motion.div
                        key="s3"
                        initial={{ opacity: 0, scale: 0.96 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.22 }}
                      >
                        <Step4PDF
                          offerTitle={offerTitle}
                          saving={saving}
                          onDownloadAgain={generatePDF}
                          onNewOffer={openNewWizard}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </GlassCard>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </PageShell>
  );
}
