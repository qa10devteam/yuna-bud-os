'use client';

import { useState, useEffect } from 'react';
import {
  X, FileText, BarChart3, Shield, Scale, History,
  MapPin, Calendar, DollarSign, Building2, AlertTriangle,
  CheckCircle, XCircle,
} from 'lucide-react';
import { GlassCard }   from '@/components/ui/GlassCard';
import { SkeletonCard } from '@/components/ui/SkeletonLoader';
import { StatusBadge }  from '@/components/ui/StatusBadge';
import { useStore }     from '@/store/useStore';
import { DocumentViewer } from '@/components/DocumentViewer';
import { motion, AnimatePresence } from 'motion/react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface TenderItem {
  id:           string;
  title:        string;
  buyer:        string | null;
  cpv:          string[];
  voivodeship:  string | null;
  value_pln:    number | string | null;
  deadline_at:  string | null;
  status:       string;
  match_score:  number | null;
  match_reason: string | null;
  source:       string | null;
}

interface TenderDetailProps {
  tender:  TenderItem | null;
  onClose: () => void;
}

const TABS = [
  { id: 'overview',  label: 'Przegląd',  icon: FileText  },
  { id: 'docs',      label: 'Dokumenty', icon: FileText  },
  { id: 'estimate',  label: 'Kosztorys', icon: BarChart3 },
  { id: 'risk',      label: 'Ryzyko',    icon: Shield    },
  { id: 'decision',  label: 'Decyzja',   icon: Scale     },
  { id: 'history',   label: 'Historia',  icon: History   },
] as const;

type TabId = typeof TABS[number]['id'];

const AHP_CRITERIA = [
  'Wartość przetargu',
  'Doświadczenie w branży',
  'Dostępność zasobów',
  'Ryzyko techniczne',
  'Konkurencja rynkowa',
  'Termin realizacji',
  'Warunki płatności',
];

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmtPLN(v: number | string | null | undefined) {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'string' ? parseFloat(v) : v;
  if (isNaN(n)) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace('.', ',') + ' M PLN';
  if (n >= 1_000)     return Math.round(n / 1_000) + ' tys. PLN';
  return Math.round(n) + ' PLN';
}

function fmtDate(s: string | null | undefined) {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('pl-PL', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  });
}

// ── Score arc ─────────────────────────────────────────────────────────────────

function ScoreArc({ score }: { score: number }) {
  const pct    = score / 100;
  const r      = 28;
  const circ   = 2 * Math.PI * r;
  const dash   = circ * pct;
  const isGo   = score >= 70;
  const color  = isGo ? '#10b981' : score >= 50 ? '#818cf8' : '#ef4444';

  return (
    <div className="flex flex-col items-center gap-0.5">
      <svg width="72" height="72" viewBox="0 0 72 72" className="-rotate-90">
        <circle cx="36" cy="36" r={r} fill="none" stroke="#1a1a28" strokeWidth="5" />
        <circle
          cx="36" cy="36" r={r} fill="none"
          stroke={color} strokeWidth="5"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          className="transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-700"
        />
      </svg>
      <div className="absolute flex flex-col items-center pointer-events-none" style={{ marginTop: 12 }}>
        <span className="font-mono text-lg font-bold" style={{ color }}>{score}</span>
        <span className="text-[10px] text-slate-600 font-mono">/100</span>
      </div>
    </div>
  );
}


interface AuditEntry {
  id:      string;
  at:      string;
  actor:   string;
  action:  string;
  entity:  string;
  detail?: Record<string, unknown>;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function TenderDetail({ tender, onClose }: TenderDetailProps) {
  const { accessToken } = useStore();
  const [tab,       setTab]       = useState<TabId>('overview');
  const [ahpScores, setAhpScores] = useState<Record<string, number>>({});
  const [decision,  setDecision]  = useState<'go' | 'nogo' | null>(null);
  const [auditLog,  setAuditLog]  = useState<AuditEntry[] | null>(null);
  const [loading]                 = useState(false);
  const [engineData, setEngineData] = useState<{
    feasible?:      boolean;
    violations?:    Array<{ severity: string; message: string; axiom_code?: string }>;
    risk?:          { margin_p50?: number; margin_p10?: number; margin_p90?: number } | null;
    explanation_md?: string;
  } | null>(null);

  // Engine data
  useEffect(() => {
    if (!tender || !accessToken) return;
    setEngineData(null);
    setAuditLog(null);
    fetch(`/api/v1/tenders/${tender.id}/engine`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setEngineData(d); })
      .catch(() => {});
  }, [tender?.id, accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  // Audit log
  useEffect(() => {
    if (tab !== 'history' || !tender || !accessToken) return;
    if (auditLog !== null) return;
    fetch(`/api/v2/audit?tender_id=${tender.id}&limit=30`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        setAuditLog(d?.items ?? []);
      })
      .catch(() => {
        setAuditLog([]);
      });
  }, [tab, tender?.id, accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  // Keyboard escape
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose]);

  async function submitDecision(d: 'go' | 'nogo') {
    setDecision(d);
    if (!tender || !accessToken) return;
    try {
      await fetch(`/api/v1/tenders/${tender.id}`, {
        method:  'PATCH',
        headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
        body:    JSON.stringify({ status: d === 'go' ? 'decided_go' : 'decided_nogo' }),
      });
    } catch {}
  }

  const ahpTotal = Object.values(ahpScores).reduce((s, v) => s + v, 0);
  const ahpAvg   = Object.keys(ahpScores).length > 0
    ? (ahpTotal / Object.keys(ahpScores).length).toFixed(1)
    : '—';

  const scoreVal = tender?.match_score != null ? Math.round((tender.match_score ?? 0) * 100) : null;

  return (
    <AnimatePresence>
      {tender && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-ink-950/85 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="relative z-10 w-full max-w-3xl bg-ink-900 border border-ink-line rounded-2xl shadow-2xl flex flex-col max-h-[90vh]"
            onClick={e => e.stopPropagation()}
          >
            {/* ── Header ──────────────────────────────────────────────── */}
            <div className="flex items-start justify-between p-5 border-b border-ink-line shrink-0">
              <div className="flex-1 min-w-0 pr-4">
                {/* Score + status row */}
                <div className="flex items-center gap-2 mb-2">
                  <StatusBadge status={tender.status} />
                  {scoreVal !== null && scoreVal > 0 && (
                    <span className={[
                      'text-xs font-mono font-bold px-2 py-0.5 rounded-md border',
                      scoreVal >= 70
                        ? 'bg-em-bg border-em-brd text-em'
                        : scoreVal >= 50
                        ? 'bg-indigo/10 border-indigo/25 text-indigo-400'
                        : 'bg-nogo-bg border-nogo-brd text-nogo',
                    ].join(' ')}>
                      {scoreVal}/100
                    </span>
                  )}
                  {/* GO/NO-GO from engine */}
                  {engineData?.feasible !== undefined && (
                    <span className={[
                      'text-xs font-mono font-bold tracking-wider px-2.5 py-0.5 rounded-md border',
                      engineData.feasible
                        ? 'bg-em-bg border-em-brd text-em'
                        : 'bg-nogo-bg border-nogo-brd text-nogo',
                    ].join(' ')}>
                      {engineData.feasible ? 'GO' : 'NO-GO'}
                    </span>
                  )}
                </div>
                <h2 className="text-sm font-semibold text-slate-100 leading-snug line-clamp-2">
                  {tender.title}
                </h2>
                {/* Key meta */}
                <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                  {tender.buyer && (
                    <span className="flex items-center gap-1">
                      <Building2 className="w-3 h-3" />
                      <span className="truncate max-w-[180px]">{tender.buyer}</span>
                    </span>
                  )}
                  {tender.value_pln && (
                    <span className="flex items-center gap-1">
                      <DollarSign className="w-3 h-3" />
                      <span className="font-mono text-slate-300">{fmtPLN(tender.value_pln)}</span>
                    </span>
                  )}
                  {tender.deadline_at && (
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {fmtDate(tender.deadline_at)}
                    </span>
                  )}
                </div>
              </div>
              <button type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg hover:bg-ink-800 text-slate-500 hover:text-slate-200 transition-colors shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* ── Tabs ──────────────────────────────────────────────────── */}
            <div className="flex border-b border-ink-line shrink-0 overflow-x-auto">
              {TABS.map(t => (
                <button type="button"
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={[
                    'px-4 py-2.5 text-xs font-medium whitespace-nowrap transition-colors border-b-2',
                    tab === t.id
                      ? 'border-em text-em'
                      : 'border-transparent text-slate-500 hover:text-slate-200',
                  ].join(' ')}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* ── Content ───────────────────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto p-5">
              {loading ? (
                <div className="space-y-3">
                  <SkeletonCard lines={4} />
                  <SkeletonCard lines={3} />
                </div>
              ) : (
                <>
                  {/* OVERVIEW */}
                  {tab === 'overview' && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        <GlassCard className="p-3">
                          <div className="flex items-center gap-2 mb-1.5 text-slate-600">
                            <Building2 className="w-3.5 h-3.5" />
                            <span className="text-[11px] uppercase tracking-widest font-semibold">
                              Zamawiający
                            </span>
                          </div>
                          <p className="text-sm text-slate-200">{tender.buyer ?? '—'}</p>
                        </GlassCard>

                        <GlassCard className="p-3">
                          <div className="flex items-center gap-2 mb-1.5 text-slate-600">
                            <DollarSign className="w-3.5 h-3.5" />
                            <span className="text-[11px] uppercase tracking-widest font-semibold">
                              Wartość
                            </span>
                          </div>
                          <p className="text-sm font-mono text-slate-100 font-semibold">
                            {fmtPLN(tender.value_pln)}
                          </p>
                        </GlassCard>

                        <GlassCard className="p-3">
                          <div className="flex items-center gap-2 mb-1.5 text-slate-600">
                            <Calendar className="w-3.5 h-3.5" />
                            <span className="text-[11px] uppercase tracking-widest font-semibold">
                              Termin składania
                            </span>
                          </div>
                          <p className="text-sm font-mono text-slate-200">
                            {fmtDate(tender.deadline_at)}
                          </p>
                        </GlassCard>

                        <GlassCard className="p-3">
                          <div className="flex items-center gap-2 mb-1.5 text-slate-600">
                            <MapPin className="w-3.5 h-3.5" />
                            <span className="text-[11px] uppercase tracking-widest font-semibold">
                              Region
                            </span>
                          </div>
                          <p className="text-sm text-slate-200">{tender.voivodeship ?? '—'}</p>
                        </GlassCard>
                      </div>

                      {tender.cpv.length > 0 && (
                        <GlassCard className="p-3">
                          <p className="text-[11px] uppercase tracking-widest font-semibold text-slate-600 mb-2">
                            Kody CPV
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {tender.cpv.map(c => (
                              <span
                                key={c}
                                className="text-xs bg-ink-800 border border-ink-line text-slate-400 px-2 py-0.5 rounded font-mono"
                              >
                                {c}
                              </span>
                            ))}
                          </div>
                        </GlassCard>
                      )}

                      {tender.match_reason && (
                        <GlassCard className="p-3">
                          <p className="text-[11px] uppercase tracking-widest font-semibold text-slate-600 mb-2">
                            Uzasadnienie AI
                          </p>
                          <p className="text-sm text-slate-300 leading-relaxed">
                            {tender.match_reason}
                          </p>
                        </GlassCard>
                      )}

                      <GlassCard className="p-3">
                        <p className="text-[11px] uppercase tracking-widest font-semibold text-slate-600 mb-2">
                          Analiza Silnika
                        </p>
                        {engineData ? (
                          <div className="space-y-2">
                            {engineData.explanation_md ? (
                              <p className="text-sm text-slate-300 whitespace-pre-line leading-relaxed">
                                {engineData.explanation_md.slice(0, 400)}
                                {engineData.explanation_md.length > 400 ? '…' : ''}
                              </p>
                            ) : (
                              <div className="flex flex-wrap gap-1.5">
                                {(engineData.violations ?? []).slice(0, 3).map((v, i) => (
                                  <span
                                    key={i}
                                    className={`text-xs px-2 py-0.5 rounded border ${
                                      v.severity === 'block'
                                        ? 'bg-nogo/10 border-nogo-brd text-nogo'
                                        : v.severity === 'warn'
                                        ? 'bg-warn-bg border-warn-brd text-warn'
                                        : 'bg-indigo/10 border-indigo/30 text-indigo-400'
                                    }`}
                                  >
                                    {v.message}
                                  </span>
                                ))}
                                {(engineData.violations ?? []).length === 0 && (
                                  <span className="text-xs text-em">✓ Brak naruszeń PZP</span>
                                )}
                              </div>
                            )}
                            {engineData.risk?.margin_p50 != null && (
                              <p className="text-xs text-slate-600 mt-1">
                                Marża P50:{' '}
                                <span className="text-em font-semibold font-mono">
                                  {(engineData.risk.margin_p50 * 100).toFixed(1)}%
                                </span>
                              </p>
                            )}
                          </div>
                        ) : (
                          <p className="text-sm text-slate-500 italic">
                            Otwórz moduł Silnik → Analizuj, aby wygenerować analizę ryzyka dla tego przetargu.
                          </p>
                        )}
                      </GlassCard>
                    </div>
                  )}

                  {/* DOCS */}
                  {tab === 'docs' && (
                    <DocumentViewer
                      pdfUrl={tender.source ?? undefined}
                      tenderTitle={tender.title}
                      tenderId={tender.id}
                    />
                  )}

                  {/* ESTIMATE */}
                  {tab === 'estimate' && (
                    <div className="text-center py-12 text-slate-600">
                      <BarChart3 className="w-10 h-10 mx-auto mb-3 opacity-30" />
                      <p className="text-sm">
                        Przejdź do modułu Kosztorys aby stworzyć wycenę
                      </p>
                    </div>
                  )}

                  {/* RISK */}
                  {tab === 'risk' && (
                    <div className="space-y-3">
                      <p className="text-[11px] font-semibold text-slate-600 uppercase tracking-widest">
                        Analiza ryzyka PZP
                      </p>
                      {(engineData?.violations && engineData.violations.length > 0
                        ? engineData.violations
                        : []
                      ).map((v, i) => (
                        <GlassCard key={i} className="p-3 flex items-start gap-3">
                          <AlertTriangle
                            className={`w-4 h-4 shrink-0 mt-0.5 ${
                              v.severity === 'error' ? 'text-nogo'
                              : v.severity === 'warn' ? 'text-warn'
                              : 'text-em'
                            }`}
                          />
                          <div>
                            <p className="text-sm text-slate-200">{v.message}</p>
                            <span
                              className={`text-xs px-1.5 py-0.5 rounded-full mt-1 inline-block ${
                                v.severity === 'error' ? 'bg-nogo/15 text-nogo'
                                : v.severity === 'warn' ? 'bg-warn-bg text-warn'
                                : 'bg-em-bg text-em'
                              }`}
                            >
                              {v.severity === 'error' ? 'Wysokie'
                               : v.severity === 'warn' ? 'Średnie'
                               : 'Niskie'}
                            </span>
                          </div>
                        </GlassCard>
                      ))}
                      {engineData?.risk && typeof engineData.risk !== 'string' && (
                        <div className="p-3 rounded-xl bg-ink-800 border border-ink-line">
                          <p className="text-[11px] font-semibold text-slate-600 uppercase tracking-widest mb-2">
                            Rozkład marży
                          </p>
                          <div className="flex items-center gap-4 font-mono text-sm">
                            <div>
                              <span className="text-slate-600 text-xs">P10 </span>
                              <span className="text-nogo">
                                {engineData.risk.margin_p10 != null
                                  ? (engineData.risk.margin_p10 * 100).toFixed(1) + '%'
                                  : '—'}
                              </span>
                            </div>
                            <div>
                              <span className="text-slate-600 text-xs">P50 </span>
                              <span className="text-em font-bold">
                                {engineData.risk.margin_p50 != null
                                  ? (engineData.risk.margin_p50 * 100).toFixed(1) + '%'
                                  : '—'}
                              </span>
                            </div>
                            <div>
                              <span className="text-slate-600 text-xs">P90 </span>
                              <span className="text-indigo-400">
                                {engineData.risk.margin_p90 != null
                                  ? (engineData.risk.margin_p90 * 100).toFixed(1) + '%'
                                  : '—'}
                              </span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* DECISION */}
                  {tab === 'decision' && (
                    <div className="space-y-4">
                      <GlassCard className="p-4">
                        <p className="text-[11px] font-semibold text-slate-600 uppercase tracking-widest mb-4">
                          Ocena kryteriów AHP (1–10)
                        </p>
                        <div className="space-y-3">
                          {AHP_CRITERIA.map(c => (
                            <div key={c} className="flex items-center gap-3">
                              <span className="text-xs text-slate-400 w-48 shrink-0">{c}</span>
                              <input
                                type="range" min={1} max={10}
                                value={ahpScores[c] ?? 5}
                                onChange={e =>
                                  setAhpScores(s => ({ ...s, [c]: Number(e.target.value) }))
                                }
                                className="flex-1 accent-[#10b981]"
                              />
                              <span className="text-xs font-mono text-em w-5 text-right font-bold">
                                {ahpScores[c] ?? 5}
                              </span>
                            </div>
                          ))}
                        </div>
                        <div className="mt-4 pt-3 border-t border-ink-line flex items-center justify-between">
                          <span className="text-xs text-slate-500">Wynik AHP</span>
                          <span className="text-2xl font-bold font-mono text-em">{ahpAvg}</span>
                        </div>
                      </GlassCard>

                      {/* GO / NO-GO buttons — Brand Bible primary CTAs */}
                      <div className="flex gap-3">
                        <button type="button"
                          onClick={() => submitDecision('go')}
                          className={[
                            'flex-1 flex items-center justify-center gap-2',
                            'py-3.5 rounded-xl font-mono font-bold text-sm tracking-wider',
                            'border transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200',
                            decision === 'go'
                              ? 'bg-em text-ink-950 border-em shadow-lg shadow-em/20'
                              : 'bg-em-bg border-em-brd text-em hover:bg-em/20',
                          ].join(' ')}
                        >
                          <CheckCircle className="w-4 h-4" />
                          GO
                        </button>
                        <button type="button"
                          onClick={() => submitDecision('nogo')}
                          className={[
                            'flex-1 flex items-center justify-center gap-2',
                            'py-3.5 rounded-xl font-mono font-bold text-sm tracking-wider',
                            'border transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200',
                            decision === 'nogo'
                              ? 'bg-nogo text-white border-nogo'
                              : 'bg-nogo-bg border-nogo-brd text-nogo hover:bg-nogo/20',
                          ].join(' ')}
                        >
                          <XCircle className="w-4 h-4" />
                          NO-GO
                        </button>
                      </div>
                    </div>
                  )}

                  {/* HISTORY */}
                  {tab === 'history' && (
                    <div className="space-y-3">
                      {auditLog === null ? (
                        <div className="flex items-center gap-2 text-slate-500 text-sm py-4">
                          <div className="w-4 h-4 border-2 border-ink-line border-t-em rounded-full animate-spin" />
                          Ładowanie historii…
                        </div>
                      ) : auditLog.length === 0 ? (
                        <p className="text-sm text-slate-500 text-center py-8">
                          Brak wpisów historii dla tego przetargu.
                        </p>
                      ) : (
                        auditLog.map((h, i) => (
                          <div key={h.id} className="flex gap-3">
                            <div className="flex flex-col items-center">
                              <div className="w-2 h-2 rounded-full bg-em mt-1.5 shrink-0" />
                              {i < auditLog.length - 1 && (
                                <div className="w-px flex-1 bg-ink-line mt-1" />
                              )}
                            </div>
                            <div className="pb-3 min-w-0">
                              <p className="text-sm text-slate-200 break-words">{h.action}</p>
                              <div className="flex items-center gap-2 mt-0.5">
                                <p className="text-xs font-mono text-slate-600">
                                  {new Date(h.at).toLocaleString('pl-PL')}
                                </p>
                                {h.actor && h.actor !== 'system' && (
                                  <span className="text-xs text-slate-500 truncate max-w-[120px]">
                                    {h.actor}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
