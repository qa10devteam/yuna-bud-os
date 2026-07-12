'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  FileText, DollarSign, Clock, AlertCircle, TrendingUp, Plus, Filter, RefreshCw,
} from 'lucide-react';
import { useAuthFetch } from '@/lib/api-v2';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Contract {
  id: string;
  title: string;
  client: string;
  value_pln: number;
  paid_pln: number;
  status: 'active' | 'completed' | 'overdue' | 'draft';
  start_date: string;
  end_date: string;
  progress_pct: number;
  // backend fields
  tender_id?: string;
  contractor_name?: string;
  total_value?: number;
  contract_number?: string;
  execution_status?: string;
  signed_at?: string;
  deadline_at?: string;
}

const STATUS_META: Record<string, { label: string; bg: string }> = {
  active:    { label: 'Aktywny',          bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  completed: { label: 'Zakończony',       bg: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  overdue:   { label: 'Opóźniony',        bg: 'bg-red-500/10 text-red-400 border-red-500/20' },
  draft:     { label: 'Wersja robocza',   bg: 'bg-earth-700/30 text-earth-400 border-earth-700/40' },
  BEFORE:    { label: 'Przed realizacją', bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  IN_PROGRESS:{ label: 'W trakcie',       bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  DONE:      { label: 'Zakończony',       bg: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  DISPUTED:  { label: 'Sporny',           bg: 'bg-red-500/10 text-red-400 border-red-500/20' },
};

function fmtPLN(v: number) {
  return new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 }).format(v);
}

function mapBackendContract(c: Record<string, unknown>, idx: number): Contract {
  const execStatus = (c.execution_status as string) ?? 'active';
  const statusMap: Record<string, Contract['status']> = {
    BEFORE: 'draft', IN_PROGRESS: 'active', DONE: 'completed', DISPUTED: 'overdue',
    active: 'active', completed: 'completed', overdue: 'overdue', draft: 'draft',
  };
  const totalVal = (c.total_value as number) ?? (c.value_pln as number) ?? 0;
  const paidVal  = (c.paid_pln as number) ?? 0;
  const prog     = (c.progress_pct as number) ?? (totalVal > 0 && paidVal > 0 ? Math.round((paidVal / totalVal) * 100) : 0);
  return {
    id:           (c.id as string) ?? String(idx),
    title:        (c.title as string) ?? (c.contract_number as string) ?? `Kontrakt #${idx + 1}`,
    client:       (c.client as string) ?? (c.contractor_name as string) ?? '—',
    value_pln:    totalVal,
    paid_pln:     paidVal,
    status:       statusMap[execStatus] ?? 'active',
    start_date:   ((c.signed_at as string) ?? (c.start_date as string) ?? '').slice(0, 10),
    end_date:     ((c.deadline_at as string) ?? (c.end_date as string) ?? '').slice(0, 10),
    progress_pct: prog,
    tender_id:    c.tender_id as string | undefined,
    contract_number: c.contract_number as string | undefined,
  };
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const itemVar   = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.3 } } };

export function ContractsPage() {
  const authFetch = useAuthFetch();
  const [contracts, setContracts]   = useState<Contract[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const [filter, setFilter]         = useState<'all' | 'active' | 'completed' | 'overdue' | 'draft'>('all');

  const fetchContracts = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await authFetch('/api/v1/contracts') as { items?: Record<string, unknown>[]; contracts?: Record<string, unknown>[] } | Record<string, unknown>[];
      const raw: Record<string, unknown>[] = Array.isArray(data)
        ? data
        : (data as { items?: Record<string, unknown>[]; contracts?: Record<string, unknown>[] }).items
          ?? (data as { items?: Record<string, unknown>[]; contracts?: Record<string, unknown>[] }).contracts
          ?? [];
      setContracts(raw.map(mapBackendContract));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { fetchContracts(); }, [fetchContracts]);

  const displayed = contracts.filter(c => filter === 'all' || c.status === filter);

  const totals = {
    value:   contracts.reduce((s, c) => s + c.value_pln, 0),
    paid:    contracts.reduce((s, c) => s + c.paid_pln, 0),
    active:  contracts.filter(c => c.status === 'active').length,
    overdue: contracts.filter(c => c.status === 'overdue').length,
  };

  return (
    <motion.div className="flex flex-col gap-6 p-6 h-full overflow-y-auto" variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={itemVar} className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-earth-100">Kontrakty</h2>
          <p className="text-earth-500 text-sm mt-0.5">Tracker kontraktów i cashflow</p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchContracts} className="p-2 rounded-xl border border-earth-800/60 text-earth-500 hover:text-earth-300 transition-colors">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary text-earth-950 font-semibold text-sm hover:bg-emerald-400 transition-colors">
            <Plus className="w-4 h-4" /> Nowy kontrakt
          </button>
        </div>
      </motion.div>

      {/* Stats */}
      <motion.div variants={itemVar} className="grid grid-cols-4 gap-3">
        {[
          { label: 'Wartość kontraktów', value: fmtPLN(totals.value),     icon: DollarSign, color: 'text-accent-primary' },
          { label: 'Zapłacono',          value: fmtPLN(totals.paid),       icon: TrendingUp,  color: 'text-emerald-400' },
          { label: 'Aktywne',            value: String(totals.active),     icon: Clock,       color: 'text-amber-400' },
          { label: 'Opóźnione',          value: String(totals.overdue),    icon: AlertCircle, color: 'text-red-400' },
        ].map(s => (
          <div key={s.label} className="glass-card rounded-xl p-4 border border-earth-800/40">
            <div className="flex items-center gap-2 text-earth-500 text-xs mb-2">
              <s.icon className="w-3.5 h-3.5" />{s.label}
            </div>
            <p className={`text-xl font-bold ${s.color}`}>{loading ? '—' : s.value}</p>
          </div>
        ))}
      </motion.div>

      {/* Filter tabs */}
      <motion.div variants={itemVar} className="flex items-center gap-3">
        <Filter className="w-4 h-4 text-earth-600" />
        <div className="flex gap-1 p-1 rounded-lg bg-earth-900 border border-earth-800/60">
          {([['all', 'Wszystkie'], ['active', 'Aktywne'], ['completed', 'Zakończone'], ['overdue', 'Opóźnione'], ['draft', 'Robocze']] as const).map(([key, label]) => (
            <button key={key} onClick={() => setFilter(key)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${filter === key ? 'bg-earth-800 text-earth-100' : 'text-earth-500 hover:text-earth-300'}`}>
              {label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* States */}
      {error && (
        <motion.div variants={itemVar} className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </motion.div>
      )}

      {loading && !error && (
        <motion.div variants={itemVar} className="space-y-3">
          {[1,2,3].map(i => (
            <div key={i} className="h-28 rounded-xl bg-earth-900/50 border border-earth-800/40 animate-pulse" />
          ))}
        </motion.div>
      )}

      {!loading && !error && displayed.length === 0 && (
        <motion.div variants={itemVar} className="flex flex-col items-center justify-center py-16 text-center">
          <FileText className="w-10 h-10 text-earth-600 mb-3" />
          <p className="text-earth-400 text-sm font-medium">Brak kontraktów</p>
          <p className="text-earth-600 text-xs mt-1">Zmień filtr lub dodaj nowy kontrakt</p>
        </motion.div>
      )}

      {/* Contract cards */}
      {!loading && !error && displayed.length > 0 && (
        <motion.div variants={itemVar} className="space-y-3">
          {displayed.map(c => {
            const meta    = STATUS_META[c.status] ?? STATUS_META.active;
            const cashPct = c.value_pln > 0 ? Math.round((c.paid_pln / c.value_pln) * 100) : 0;
            return (
              <div key={c.id} className="glass-card rounded-xl p-5 border border-earth-800/40 hover:border-earth-700/60 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-earth-800 flex items-center justify-center border border-earth-700/40 shrink-0">
                      <FileText className="w-5 h-5 text-earth-500" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-earth-200 truncate">{c.title}</h3>
                      <p className="text-xs text-earth-500 mt-0.5">{c.client}{c.contract_number ? ` · ${c.contract_number}` : ''}</p>
                    </div>
                  </div>
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium border ${meta.bg}`}>{meta.label}</span>
                </div>

                <div className="mt-4 grid grid-cols-4 gap-4 text-xs">
                  <div><p className="text-earth-600">Wartość</p><p className="text-earth-200 font-mono font-semibold mt-0.5">{fmtPLN(c.value_pln)}</p></div>
                  <div><p className="text-earth-600">Zapłacono</p><p className="text-earth-200 font-mono font-semibold mt-0.5">{fmtPLN(c.paid_pln)}</p></div>
                  <div><p className="text-earth-600">Termin</p><p className="text-earth-200 mt-0.5">{c.start_date || '—'} → {c.end_date || '—'}</p></div>
                  <div><p className="text-earth-600">Postęp</p><p className="text-earth-200 font-semibold mt-0.5">{c.progress_pct}%</p></div>
                </div>

                <div className="mt-3 space-y-2">
                  <div>
                    <div className="flex justify-between text-xs text-earth-600 mb-1"><span>Postęp prac</span><span>{c.progress_pct}%</span></div>
                    <div className="h-1.5 bg-earth-800 rounded-full overflow-hidden">
                      <div className="h-full bg-accent-primary rounded-full transition-all" style={{ width: `${c.progress_pct}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs text-earth-600 mb-1"><span>Cashflow</span><span>{cashPct}%</span></div>
                    <div className="h-1.5 bg-earth-800 rounded-full overflow-hidden">
                      <div className="h-full bg-amber-400 rounded-full transition-all" style={{ width: `${cashPct}%` }} />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </motion.div>
      )}
    </motion.div>
  );
}
