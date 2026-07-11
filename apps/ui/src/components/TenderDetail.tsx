'use client';

import { useState, useEffect } from 'react';
import { X, FileText, BarChart3, Shield, Scale, History, MapPin, Calendar, DollarSign, Building2, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { SkeletonCard } from '@/components/ui/SkeletonLoader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { useStore } from '@/store/useStore';
import { DocumentViewer } from '@/components/DocumentViewer';

interface TenderItem {
  id: string;
  title: string;
  buyer: string | null;
  cpv: string[];
  voivodeship: string | null;
  value_pln: number | string | null;
  deadline_at: string | null;
  status: string;
  match_score: number | null;
  match_reason: string | null;
  source: string | null;
}

interface TenderDetailProps {
  tender: TenderItem | null;
  onClose: () => void;
}

const TABS = [
  { id: 'overview', label: 'Przegląd', icon: FileText },
  { id: 'docs', label: 'Dokumenty', icon: FileText },
  { id: 'estimate', label: 'Kosztorys', icon: BarChart3 },
  { id: 'risk', label: 'Ryzyko', icon: Shield },
  { id: 'decision', label: 'Decyzja', icon: Scale },
  { id: 'history', label: 'Historia', icon: History },
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

function fmtPLN(v: number | string | null | undefined) {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'string' ? parseFloat(v) : v;
  if (isNaN(n)) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace('.', ',') + ' M zł';
  if (n >= 1_000) return Math.round(n / 1_000) + ' tys. zł';
  return Math.round(n) + ' zł';
}
function fmtDate(s: string | null | undefined) {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

const MOCK_RED_FLAGS = [
  { id: '1', text: 'Krótki termin realizacji — 3 miesiące', severity: 'high' },
  { id: '2', text: 'Kary umowne 1% za każdy dzień zwłoki', severity: 'medium' },
  { id: '3', text: 'Wymagane polskie referencje z ostatnich 5 lat', severity: 'low' },
];

const MOCK_HISTORY = [
  { id: '1', action: 'Przetarg dodany do systemu', ts: new Date(Date.now() - 7*86400000).toISOString() },
  { id: '2', action: 'Dopasowany do profilu (95%)', ts: new Date(Date.now() - 5*86400000).toISOString() },
  { id: '3', action: 'Pobrano dokumentację SIWZ', ts: new Date(Date.now() - 2*86400000).toISOString() },
];

interface AuditEntry {
  id: string;
  at: string;
  actor: string;
  action: string;
  entity: string;
  detail?: Record<string, unknown>;
}

export function TenderDetail({ tender, onClose }: TenderDetailProps) {
  const { accessToken } = useStore();
  const [tab, setTab] = useState<TabId>('overview');
  const [ahpScores, setAhpScores] = useState<Record<string, number>>({});
  const [decision, setDecision] = useState<'go' | 'nogo' | null>(null);
  const [auditLog, setAuditLog] = useState<AuditEntry[] | null>(null);
  const [loading] = useState(false);
  const [engineData, setEngineData] = useState<{
    feasible?: boolean;
    violations?: Array<{severity:string; message:string; axiom_code?:string}>;
    risk?: { margin_p50?: number; margin_p10?: number; margin_p90?: number } | null;
    explanation_md?: string;
  } | null>(null);

  useEffect(() => {
    if (!tender || !accessToken) return;
    setEngineData(null);
    setAuditLog(null); // reset on tender change
    fetch(`/api/v1/tenders/${tender.id}/engine`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setEngineData(d); })
      .catch(() => {});
  }, [tender?.id, accessToken]);

  // Fetch audit log when history tab is opened
  useEffect(() => {
    if (tab !== 'history' || !tender || !accessToken) return;
    if (auditLog !== null) return; // already loaded
    fetch(`/api/v2/audit?tender_id=${tender.id}&limit=30`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(d => { setAuditLog(d?.items ?? MOCK_HISTORY.map(h => ({ id: h.id, at: h.ts, actor: 'system', action: h.action, entity: 'tender' }))); })
      .catch(() => { setAuditLog(MOCK_HISTORY.map(h => ({ id: h.id, at: h.ts, actor: 'system', action: h.action, entity: 'tender' }))); });
  }, [tab, tender?.id, accessToken, auditLog]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  async function submitDecision(d: 'go' | 'nogo') {
    setDecision(d);
    if (!tender || !accessToken) return;
    try {
      await fetch(`/api/v1/tenders/${tender.id}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: d === 'go' ? 'decided_go' : 'decided_nogo' }),
      });
    } catch {}
  }

  const ahpTotal = Object.values(ahpScores).reduce((s, v) => s + v, 0);
  const ahpAvg = Object.keys(ahpScores).length > 0 ? (ahpTotal / Object.keys(ahpScores).length).toFixed(1) : '—';

  return (
    <>
      {tender ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-earth-950/80 backdrop-blur-sm"
            onClick={onClose}
          />
          <div
            className="relative z-10 w-full max-w-3xl bg-earth-900 border border-earth-700/60 rounded-2xl shadow-2xl shadow-black/60 flex flex-col max-h-[90vh]"
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between p-5 border-b border-earth-800/60 shrink-0">
              <div className="flex-1 min-w-0 pr-4">
                <div className="flex items-center gap-2 mb-1">
                  <StatusBadge status={tender.status} />
                  {(tender.match_score ?? 0) > 0 && (
                    <span className="text-xs font-bold text-emerald-400 bg-emerald-500/15 px-2 py-0.5 rounded-full">
                      {Math.round((tender.match_score ?? 0) * 100)}%
                    </span>
                  )}
                </div>
                <h2 className="text-sm font-semibold text-earth-100 line-clamp-2">{tender.title}</h2>
              </div>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-earth-800 text-earth-500 hover:text-earth-200 transition-colors shrink-0">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-earth-800/60 shrink-0 overflow-x-auto">
              {TABS.map(t => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-4 py-2.5 text-xs font-medium whitespace-nowrap transition-colors border-b-2 ${tab === t.id ? 'border-accent-primary text-accent-primary' : 'border-transparent text-earth-500 hover:text-earth-200'}`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5">
              {loading ? (
                <div className="space-y-3">
                  <SkeletonCard lines={4} />
                  <SkeletonCard lines={3} />
                </div>
              ) : (
                <>
                  {tab === 'overview' && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        <GlassCard className="p-3">
                          <div className="flex items-center gap-2 mb-1 text-earth-500">
                            <Building2 className="w-3.5 h-3.5" />
                            <span className="text-xs">Zamawiający</span>
                          </div>
                          <p className="text-sm text-earth-200">{tender.buyer ?? '—'}</p>
                        </GlassCard>
                        <GlassCard className="p-3">
                          <div className="flex items-center gap-2 mb-1 text-earth-500">
                            <DollarSign className="w-3.5 h-3.5" />
                            <span className="text-xs">Wartość</span>
                          </div>
                          <p className="text-sm font-mono text-earth-200">{fmtPLN(tender.value_pln)}</p>
                        </GlassCard>
                        <GlassCard className="p-3">
                          <div className="flex items-center gap-2 mb-1 text-earth-500">
                            <Calendar className="w-3.5 h-3.5" />
                            <span className="text-xs">Termin składania</span>
                          </div>
                          <p className="text-sm text-earth-200">{fmtDate(tender.deadline_at)}</p>
                        </GlassCard>
                        <GlassCard className="p-3">
                          <div className="flex items-center gap-2 mb-1 text-earth-500">
                            <MapPin className="w-3.5 h-3.5" />
                            <span className="text-xs">Region</span>
                          </div>
                          <p className="text-sm text-earth-200">{tender.voivodeship ?? '—'}</p>
                        </GlassCard>
                      </div>
                      {tender.cpv.length > 0 && (
                        <GlassCard className="p-3">
                          <p className="text-xs text-earth-500 mb-2">Kody CPV</p>
                          <div className="flex flex-wrap gap-1.5">
                            {tender.cpv.map(c => (
                              <span key={c} className="text-xs bg-earth-800 text-earth-300 px-2 py-0.5 rounded font-mono">{c}</span>
                            ))}
                          </div>
                        </GlassCard>
                      )}
                      {tender.match_reason && (
                        <GlassCard className="p-3">
                          <p className="text-xs text-earth-500 mb-2">Powód dopasowania AI</p>
                          <p className="text-sm text-earth-300">{tender.match_reason}</p>
                        </GlassCard>
                      )}
                      <GlassCard className="p-3">
                        <p className="text-xs text-earth-500 mb-2">Analiza Silnika</p>
                        {engineData ? (
                          <div className="space-y-2">
                            {engineData.explanation_md ? (
                              <p className="text-sm text-earth-300 whitespace-pre-line">
                                {engineData.explanation_md.slice(0, 400)}{engineData.explanation_md.length > 400 ? '…' : ''}
                              </p>
                            ) : (
                              <div className="flex flex-wrap gap-1.5">
                                {(engineData.violations ?? []).slice(0, 3).map((v, i) => (
                                  <span key={i} className={`text-xs px-2 py-0.5 rounded border ${
                                    v.severity === 'block' ? 'bg-red-500/10 border-red-500/30 text-red-400'
                                    : v.severity === 'warn' ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                                    : 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                                  }`}>{v.message}</span>
                                ))}
                                {(engineData.violations ?? []).length === 0 && (
                                  <span className="text-xs text-emerald-400">✓ Brak naruszeń PZP</span>
                                )}
                              </div>
                            )}
                            {engineData.risk?.margin_p50 != null && (
                              <p className="text-xs text-earth-500 mt-1">
                                Marża P50: <span className="text-emerald-400 font-semibold">{(engineData.risk.margin_p50 * 100).toFixed(1)}%</span>
                              </p>
                            )}
                          </div>
                        ) : (
                          <p className="text-sm text-earth-400 italic">Otwórz moduł Silnik → Analizuj, aby wygenerować analizę ryzyka dla tego przetargu.</p>
                        )}
                      </GlassCard>
                    </div>
                  )}

                  {tab === 'docs' && (
                    <DocumentViewer
                      pdfUrl={tender.source ?? undefined}
                      tenderTitle={tender.title}
                      tenderId={tender.id}
                    />
                  )}

                  {tab === 'estimate' && (
                    <div className="text-center py-8 text-earth-600">
                      <BarChart3 className="w-10 h-10 mx-auto mb-3 opacity-40" />
                      <p className="text-sm">Przejdź do modułu Kosztorys aby stworzyć wycenę</p>
                    </div>
                  )}

                  {tab === 'risk' && (
                    <div className="space-y-3">
                      <p className="text-xs text-earth-500 font-semibold uppercase tracking-wide">Analiza ryzyka PZP</p>
                      {engineData?.violations && engineData.violations.length > 0 ? (
                        engineData.violations.map((v, i) => (
                          <GlassCard key={i} className="p-3 flex items-start gap-3">
                            <AlertTriangle className={`w-4 h-4 shrink-0 mt-0.5 ${v.severity === 'error' ? 'text-red-400' : v.severity === 'warn' ? 'text-yellow-400' : 'text-green-400'}`} />
                            <div>
                              <p className="text-sm text-earth-200">{v.message}</p>
                              <span className={`text-xs px-1.5 py-0.5 rounded-full mt-1 inline-block ${v.severity === 'error' ? 'bg-red-500/15 text-red-400' : v.severity === 'warn' ? 'bg-yellow-500/15 text-yellow-400' : 'bg-green-500/15 text-green-400'}`}>
                                {v.severity === 'error' ? 'Wysokie' : v.severity === 'warn' ? 'Średnie' : 'Niskie'}
                              </span>
                            </div>
                          </GlassCard>
                        ))
                      ) : MOCK_RED_FLAGS.map(flag => (
                        <GlassCard key={flag.id} className="p-3 flex items-start gap-3">
                          <AlertTriangle className={`w-4 h-4 shrink-0 mt-0.5 ${flag.severity === 'high' ? 'text-red-400' : flag.severity === 'medium' ? 'text-yellow-400' : 'text-green-400'}`} />
                          <div>
                            <p className="text-sm text-earth-200">{flag.text}</p>
                            <span className={`text-xs px-1.5 py-0.5 rounded-full mt-1 inline-block ${flag.severity === 'high' ? 'bg-red-500/15 text-red-400' : flag.severity === 'medium' ? 'bg-yellow-500/15 text-yellow-400' : 'bg-green-500/15 text-green-400'}`}>
                              {flag.severity === 'high' ? 'Wysokie' : flag.severity === 'medium' ? 'Średnie' : 'Niskie'}
                            </span>
                          </div>
                        </GlassCard>
                      ))}
                      {engineData?.risk && (
                        <div className="mt-2 p-3 rounded-xl bg-earth-800/40 border border-earth-700/40">
                          <p className="text-xs text-earth-500 font-semibold uppercase tracking-wide mb-1">Ogólna ocena ryzyka</p>
                          {typeof engineData.risk === 'string' ? (
                            <p className="text-sm text-earth-200">{engineData.risk}</p>
                          ) : (
                            <p className="text-sm text-earth-200">
                              Marża P10/P50/P90: {' '}
                              <span className="text-red-400">{engineData.risk.margin_p10 != null ? (engineData.risk.margin_p10*100).toFixed(1)+'%' : '—'}</span>
                              {' / '}
                              <span className="text-emerald-400">{engineData.risk.margin_p50 != null ? (engineData.risk.margin_p50*100).toFixed(1)+'%' : '—'}</span>
                              {' / '}
                              <span className="text-blue-400">{engineData.risk.margin_p90 != null ? (engineData.risk.margin_p90*100).toFixed(1)+'%' : '—'}</span>
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {tab === 'decision' && (
                    <div className="space-y-4">
                      <GlassCard className="p-4">
                        <p className="text-xs text-earth-500 font-semibold uppercase tracking-wide mb-3">Ocena kryteriów AHP (1-10)</p>
                        <div className="space-y-2">
                          {AHP_CRITERIA.map(c => (
                            <div key={c} className="flex items-center gap-3">
                              <span className="text-xs text-earth-400 w-44 shrink-0">{c}</span>
                              <input
                                type="range" min={1} max={10}
                                value={ahpScores[c] ?? 5}
                                onChange={e => setAhpScores(s => ({ ...s, [c]: Number(e.target.value) }))}
                                className="flex-1"
                              />
                              <span className="text-xs font-mono text-earth-300 w-5 text-right">{ahpScores[c] ?? 5}</span>
                            </div>
                          ))}
                        </div>
                        <div className="mt-3 pt-3 border-t border-earth-800/60 flex items-center justify-between">
                          <span className="text-xs text-earth-500">Wynik AHP</span>
                          <span className="text-lg font-bold text-accent-primary">{ahpAvg}</span>
                        </div>
                      </GlassCard>
                      <div className="flex gap-3">
                        <button
                          onClick={() => submitDecision('go')}
                          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all ${decision === 'go' ? 'bg-emerald-500 text-white' : 'bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25'}`}
                        >
                          <CheckCircle className="w-4 h-4" /> GO ✓
                        </button>
                        <button
                          onClick={() => submitDecision('nogo')}
                          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all ${decision === 'nogo' ? 'bg-red-500 text-white' : 'bg-red-500/15 text-red-400 hover:bg-red-500/25'}`}
                        >
                          <XCircle className="w-4 h-4" /> NO-GO ✗
                        </button>
                      </div>
                    </div>
                  )}

                  {tab === 'history' && (
                    <div className="space-y-3">
                      {auditLog === null ? (
                        <div className="flex items-center gap-2 text-earth-500 text-sm py-4">
                          <div className="w-4 h-4 border-2 border-earth-600 border-t-accent-primary rounded-full animate-spin" />
                          Ładowanie historii…
                        </div>
                      ) : auditLog.length === 0 ? (
                        <p className="text-sm text-earth-500 text-center py-6">Brak wpisów historii dla tego przetargu.</p>
                      ) : (
                        auditLog.map((h, i) => (
                          <div key={h.id} className="flex gap-3">
                            <div className="flex flex-col items-center">
                              <div className="w-2 h-2 rounded-full bg-accent-primary mt-1.5 shrink-0" />
                              {i < auditLog.length - 1 && <div className="w-px flex-1 bg-earth-800 mt-1" />}
                            </div>
                            <div className="pb-3 min-w-0">
                              <p className="text-sm text-earth-200 break-words">{h.action}</p>
                              <div className="flex items-center gap-2 mt-0.5">
                                <p className="text-xs text-earth-600">{new Date(h.at).toLocaleString('pl-PL')}</p>
                                {h.actor && h.actor !== 'system' && (
                                  <span className="text-xs text-earth-500 truncate max-w-[120px]">{h.actor}</span>
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
          </div>
        </div>
      ) : null}
    </>
  );
}
