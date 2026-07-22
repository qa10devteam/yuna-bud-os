'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import DOMPurify from 'dompurify';
import { useStore } from '@/store/useStore';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';
import type { Tender } from '@/types';
import {
  Scale, CheckCircle, XCircle, AlertCircle, Loader2,
  Clock, Building2, Hash, Brain, PlayCircle,
  ThumbsUp, ThumbsDown, FileText, History, RefreshCw,
} from 'lucide-react';

// ── Local API types ────────────────────────────────────────────────────────────

interface ApiTender {
  id: string;
  title: string;
  buyer: string | null;
  cpv: string[] | null;
  value_pln: number | string | null;
  match_score: number | null;
  deadline_at: string | null;
  pipeline_status: string;
}

interface TenderAnalysis {
  id: string;
  tender_id: string;
  summary: string | null;
  go_nogo: 'GO' | 'NO-GO' | null;
  decision_brief: string | null;
  created_at: string;
}

interface EngineResult {
  feasible: boolean;
  violations: { severity: string; message: string }[];
  risk?: {
    margin_p10: number;
    margin_p50: number;
    margin_p90: number;
  } | null;
}

interface CompareResult {
  doc_total: string | number;
  owner_total: string | number;
  delta_pln: string | number;
  margin_headroom_pct: string | number;
}

// ── Progress steps ─────────────────────────────────────────────────────────────

type ProgressStep =
  | 'fetching'
  | 'analyzing'
  | 'scoring'
  | 'icb_estimate'
  | 'ahp_eval'
  | 'generating_brief'
  | 'done';

const PROGRESS_STEPS: ProgressStep[] = [
  'fetching',
  'analyzing',
  'scoring',
  'icb_estimate',
  'ahp_eval',
  'generating_brief',
  'done',
];

const STEP_LABELS: Record<ProgressStep, string> = {
  fetching:         'Pobieranie danych',
  analyzing:        'Analiza dokumentów',
  scoring:          'Obliczanie Score',
  icb_estimate:     'Szacowanie ICB',
  ahp_eval:         'Ewaluacja AHP',
  generating_brief: 'Generowanie briefu',
  done:             'Ukończono',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtPLN(v: number | string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = typeof v === 'string' ? parseFloat(v) : v;
  if (isNaN(n)) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + ' M zł';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + ' tys. zł';
  return n.toFixed(0) + ' zł';
}

function daysUntil(deadline: string | null): number | null {
  if (!deadline) return null;
  return Math.ceil((new Date(deadline).getTime() - Date.now()) / 86_400_000);
}

function renderMarkdown(md: string): string {
  if (!md) return '';
  return md
    .replace(/^### (.+)$/gm, '<h3 style="font-size:0.875rem;font-weight:700;color:#f1f5f9;margin-top:1rem;margin-bottom:0.25rem;">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 style="font-size:1rem;font-weight:700;color:#f1f5f9;margin-top:1.25rem;margin-bottom:0.5rem;">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 style="font-size:1.125rem;font-weight:700;color:#f1f5f9;margin-top:1.5rem;margin-bottom:0.5rem;">$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong style="color:#e2e8f0;font-weight:600;">$1</strong>')
    .replace(/^- (.+)$/gm, '<li style="color:#94a3b8;font-size:0.8125rem;margin-left:1rem;list-style-type:disc;">$1</li>')
    .replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul style="margin:0.5rem 0;">$&</ul>')
    .replace(/\n\n/g, '<br/>')
    .replace(/^(?!<[hul])(.+)$/gm, '<p style="color:#94a3b8;font-size:0.8125rem;line-height:1.6;margin:0.25rem 0;">$1</p>');
}

// ── Sub-components ────────────────────────────────────────────────────────────

function DeadlineBadge({ deadline }: { deadline: string | null }) {
  const days = daysUntil(deadline);
  if (days === null) return <span className="text-slate-600 text-xs">—</span>;
  const cls =
    days < 0   ? 'text-nogo bg-nogo/15 border-nogo/30' :
    days <= 3  ? 'text-nogo bg-nogo/15 border-nogo/30' :
    days <= 7  ? 'text-orange-400 bg-orange-500/15 border-orange-500/30' :
    days <= 14 ? 'text-warn bg-warn/15 border-warn/30' :
    'text-slate-400 bg-ink-800/60 border-ink-700/40';
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${cls}`}>
      {days < 0 ? 'po terminie' : days === 0 ? 'dziś' : `${days}d`}
    </span>
  );
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-slate-600 text-xs">—</span>;
  const pct = Math.round(score * 100);
  const cls =
    score >= 0.75 ? 'text-em bg-em/15 border-em/30' :
    score >= 0.5  ? 'text-warn bg-warn/15 border-warn/30' :
    'text-nogo bg-nogo/15 border-nogo/30';
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-bold border ${cls}`}>
      {pct}%
    </span>
  );
}

function QueueCard({
  t,
  isSelected,
  onClick,
}: {
  t: ApiTender;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      onClick={onClick}
      className={`p-3 rounded-xl border cursor-pointer transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200 ${
        isSelected
          ? 'bg-indigo/10 border-indigo/40 shadow-md-sm'
          : 'card-hover'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className={`text-xs font-medium line-clamp-2 leading-snug flex-1 ${isSelected ? 'text-slate-100' : 'text-slate-200'}`}>
          {t.title}
        </p>
        <ScoreBadge score={t.match_score} />
      </div>

      {t.buyer && (
        <p className="text-slate-500 text-xs mt-1.5 truncate flex items-center gap-1">
          <Building2 className="w-2.5 h-2.5 shrink-0 text-slate-600" />
          {t.buyer}
        </p>
      )}

      {t.cpv && t.cpv.length > 0 && (
        <p className="text-slate-600 text-xs mt-0.5 truncate flex items-center gap-1">
          <Hash className="w-2.5 h-2.5 shrink-0" />
          {t.cpv[0]}
        </p>
      )}

      <div className="flex items-center justify-between mt-2">
        <span className="text-slate-400 text-xs font-mono">{fmtPLN(t.value_pln)}</span>
        <DeadlineBadge deadline={t.deadline_at} />
      </div>
    </motion.div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function DecyzjaPage() {
  const { selectedTender, setSelectedTender, accessToken } = useStore();
  const authFetch = useAuthFetch();
  const tender = selectedTender as unknown as ApiTender | null;

  // Section A: Queue
  const [queue, setQueue] = useState<ApiTender[]>([]);
  const [queueLoading, setQueueLoading] = useState(true);

  // Section B: Analysis data
  const [analysis, setAnalysis] = useState<TenderAnalysis | null>(null);
  const [engine, setEngine] = useState<EngineResult | null>(null);
  const [compare, setCompare] = useState<CompareResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  // Section C: AI runner
  const [running, setRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState<ProgressStep | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Set<ProgressStep>>(new Set());
  const [brief, setBrief] = useState<string | null>(null);
  const [goNogo, setGoNogo] = useState<'GO' | 'NO-GO' | null>(null);
  const sseCleanup = useRef<(() => void) | null>(null);

  // Section D: Decision + history
  const [decisionStatus, setDecisionStatus] = useState<string | null>(null);
  const [historyGo, setHistoryGo] = useState<ApiTender[]>([]);
  const [historyNogo, setHistoryNogo] = useState<ApiTender[]>([]);

  // ── Fetch queue ────────────────────────────────────────────────────────────
  const fetchQueue = useCallback(async () => {
    setQueueLoading(true);
    try {
      const data = await authFetch('/api/v2/tenders?pipeline_status=ANALIZOWANY&limit=20');
      const items: ApiTender[] = data?.items ?? data ?? [];
      setQueue(items.filter((t) => (t.match_score ?? 0) > 0.5));
    } catch {
      // silently ignore
    } finally {
      setQueueLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  // ── Fetch decision history ─────────────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    try {
      const [go, nogo] = await Promise.all([
        authFetch('/api/v2/tenders?status=decided_go&limit=5').catch(() => null),
        authFetch('/api/v2/tenders?status=decided_nogo&limit=5').catch(() => null),
      ]);
      setHistoryGo((go?.items ?? go ?? []).slice(0, 5));
      setHistoryNogo((nogo?.items ?? nogo ?? []).slice(0, 5));
    } catch { /* ignore */ }
  }, [authFetch]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  // ── Load analysis when tender changes ─────────────────────────────────────
  useEffect(() => {
    if (!tender?.id) return;
    setAnalysisLoading(true);
    setAnalysis(null);
    setEngine(null);
    setCompare(null);
    setBrief(null);
    setGoNogo(null);
    setCompletedSteps(new Set());
    setCurrentStep(null);
    setDecisionStatus(null);
    setRunning(false);
    sseCleanup.current?.();

    Promise.all([
      authFetch(`/api/v2/tenders/${tender.id}/analysis`).catch(() => null),
      authFetch(`/api/v1/tenders/${tender.id}/engine`).catch(() => null),
      authFetch(`/api/v1/tenders/${tender.id}/estimate/compare`).catch(() => null),
    ]).then(([ana, eng, cmp]) => {
      if (ana) {
        setAnalysis(ana);
        if (ana.decision_brief) setBrief(ana.decision_brief);
        if (ana.go_nogo) setGoNogo(ana.go_nogo);
      }
      if (eng) setEngine(eng);
      if (cmp) setCompare(cmp);
    }).finally(() => setAnalysisLoading(false));
  }, [tender?.id, authFetch]);

  // ── Cleanup SSE on unmount ─────────────────────────────────────────────────
  useEffect(() => {
    return () => { sseCleanup.current?.(); };
  }, []);

  // ── AI Runner ─────────────────────────────────────────────────────────────
  const runAnalysis = useCallback(async () => {
    if (!tender?.id || running) return;

    sseCleanup.current?.();
    setRunning(true);
    setCompletedSteps(new Set());
    setCurrentStep('fetching');
    setBrief(null);
    setGoNogo(null);

    // Trigger POST
    try {
      await authFetch(`/api/v2/agent/analyze/${tender.id}`, { method: 'POST' });
    } catch {
      // OK to continue — might already be running
    }

    // SSE stream
    const token = accessToken;
    const url = `/api/v2/agent/analyze/${tender.id}/stream${token ? `?token=${encodeURIComponent(token)}` : ''}`;
    let es: EventSource | null = null;

    try {
      es = new EventSource(url);
      sseCleanup.current = () => { es?.close(); };

      es.onmessage = (evt: MessageEvent) => {
        try {
          const data = JSON.parse(evt.data as string) as {
            step?: string;
            decision_brief?: string;
            go_nogo?: 'GO' | 'NO-GO';
          };
          if (!data.step) return;

          const step = data.step as ProgressStep;

          if (step === 'done') {
            setCompletedSteps(new Set(PROGRESS_STEPS));
            setCurrentStep('done');
            setRunning(false);
            if (data.decision_brief) setBrief(data.decision_brief);
            if (data.go_nogo) setGoNogo(data.go_nogo);
            es?.close();
          } else {
            setCurrentStep(step);
            setCompletedSteps((prev) => {
              const next = new Set(prev);
              next.add(step);
              return next;
            });
          }
        } catch { /* ignore parse errors */ }
      };

      es.onerror = () => {
        es?.close();
        if (running) {
          setRunning(false);
          showToast('error', 'Błąd strumienia analizy SSE');
        }
      };
    } catch {
      setRunning(false);
      showToast('error', 'Nie można uruchomić analizy AI');
    }
  }, [tender?.id, running, authFetch, accessToken]);

  // ── Decision action ───────────────────────────────────────────────────────
  const takeDecision = useCallback(
    async (status: 'decided_go' | 'decided_nogo') => {
      if (!tender?.id) return;
      const previous = decisionStatus;
      setDecisionStatus(status); // optimistic
      try {
        await authFetch(`/api/v1/tenders/${tender.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ pipeline_status: status }),
        });
        showToast(
          'success',
          status === 'decided_go' ? '✅ Decyzja GO zapisana!' : '❌ Decyzja NO-GO zapisana',
        );
        fetchHistory();
        fetchQueue();
      } catch (e) {
        setDecisionStatus(previous);
        showToast('error', `Błąd zapisu decyzji: ${(e as Error).message}`);
      }
    },
    [tender?.id, decisionStatus, authFetch, fetchHistory, fetchQueue],
  );

  // ── Derived ───────────────────────────────────────────────────────────────
  const delta = compare != null ? parseFloat(String(compare.delta_pln)) : null;
  const headroom = compare != null ? parseFloat(String(compare.margin_headroom_pct)) : null;
  const blockCount = engine?.violations?.filter((v) => v.severity === 'block').length ?? 0;
  const warnCount = engine?.violations?.filter((v) => v.severity !== 'block').length ?? 0;

  // ── Queue panel ───────────────────────────────────────────────────────────
  const QueuePanel = (
    <div className="w-80 shrink-0 border-r border-ink-800/60 flex flex-col overflow-hidden bg-ink-950">
      <div className="px-4 py-3 border-b border-ink-800/60 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-200">Oczekuje na decyzję</h2>
          <p className="text-slate-500 text-xs mt-0.5">
            {queueLoading ? 'Ładowanie…' : `${queue.length} przetargów`}
          </p>
        </div>
        <button type="button"
          onClick={fetchQueue}
          aria-label="Odśwież kolejkę"
          className="btn-ghost p-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${queueLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {queueLoading
          ? Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="p-3 rounded-xl bg-ink-900/60 border border-ink-800/50 animate-pulse h-[80px]" />
            ))
          : queue.length === 0
            ? (
              <div className="py-10 text-center">
                <Scale className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                <p className="text-slate-500 text-xs">Brak przetargów w kolejce</p>
                <p className="text-slate-700 text-xs mt-1">Status: ANALIZOWANY, score &gt; 50%</p>
              </div>
            )
            : queue.map((t) => (
              <QueueCard
                key={t.id}
                t={t}
                isSelected={tender?.id === t.id}
                onClick={() => setSelectedTender(t as unknown as Tender)}
              />
            ))
        }
      </div>
    </div>
  );

  // ── Empty state ───────────────────────────────────────────────────────────
  if (!tender) {
    return (
      <PageShell title="Decyzja" subtitle="AI rekomendacja GO/NO-GO" noPadding>
        <div className="flex h-full overflow-hidden">
          {QueuePanel}
          <div className="flex-1 flex flex-col items-center justify-center gap-5 text-center p-8">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
              className="w-16 h-16 rounded-2xl bg-ink-800 flex items-center justify-center border border-ink-700/40"
            >
              <Scale className="w-8 h-8 text-slate-500" />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              <p className="text-slate-200 font-semibold text-lg">Wybierz przetarg z kolejki</p>
              <p className="text-slate-500 text-sm mt-1.5 max-w-xs leading-relaxed">
                Kliknij przetarg po lewej stronie, aby zobaczyć analizę AI i podjąć decyzję GO / NO-GO
              </p>
            </motion.div>
          </div>
        </div>
      </PageShell>
    );
  }

  // ── Full layout ───────────────────────────────────────────────────────────
  return (
    <PageShell title="Decyzja" subtitle="AI rekomendacja GO/NO-GO" noPadding>
      <div className="flex h-full overflow-hidden">
        {QueuePanel}

        {/* Right panel */}
        <div className="flex-1 overflow-y-auto bg-ink-950">
          <div className="p-5 space-y-5 max-w-3xl mx-auto pb-12">

            {/* ── Section B: Selected Tender ───────────────────── */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <FileText className="w-4 h-4 text-indigo" />
                <h3 className="section-label">Wybrany przetarg</h3>
              </div>

              <GlassCard className="p-4">
                <h2 className="text-slate-100 font-semibold text-sm leading-snug mb-3">{tender.title}</h2>
                <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                  <div>
                    <p className="text-slate-600 text-xs mb-0.5">Zamawiający</p>
                    <p className="text-slate-300 text-xs leading-snug flex items-start gap-1">
                      <Building2 className="w-3 h-3 shrink-0 mt-0.5 text-slate-600" />
                      <span className="truncate">{tender.buyer ?? '—'}</span>
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-600 text-xs mb-0.5">Kod CPV</p>
                    <p className="text-slate-300 text-xs font-mono flex items-center gap-1">
                      <Hash className="w-3 h-3 text-slate-600" />
                      {tender.cpv?.[0] ?? '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-600 text-xs mb-0.5">Wartość szacunkowa</p>
                    <p className="text-slate-300 text-sm font-mono font-semibold">{fmtPLN(tender.value_pln)}</p>
                  </div>
                  <div>
                    <p className="text-slate-600 text-xs mb-0.5">Termin składania</p>
                    <p className="text-slate-300 text-xs flex items-center gap-1.5">
                      <Clock className="w-3 h-3 text-slate-600" />
                      {tender.deadline_at
                        ? new Date(tender.deadline_at).toLocaleDateString('pl-PL')
                        : '—'}
                      <DeadlineBadge deadline={tender.deadline_at} />
                    </p>
                  </div>
                </div>
              </GlassCard>

              {/* Loading skeleton for analysis data */}
              {analysisLoading && (
                <div className="flex items-center gap-2 p-3 mt-3 text-slate-500 text-xs">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Ładowanie danych analizy…
                </div>
              )}

              {/* Existing analysis summary */}
              {!analysisLoading && analysis?.summary && (
                <GlassCard className="p-4 mt-3">
                  <p className="section-label mb-2">Istniejąca analiza</p>
                  <p className="text-slate-300 text-xs leading-relaxed">{analysis.summary}</p>
                  <p className="text-slate-600 text-xs mt-2">
                    {new Date(analysis.created_at).toLocaleString('pl-PL')}
                  </p>
                </GlassCard>
              )}

              {/* Engine result */}
              {!analysisLoading && engine && (
                <GlassCard className="p-4 mt-3">
                  <div className="flex items-center justify-between mb-3">
                    <p className="section-label">Silnik decyzyjny</p>
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full font-bold border ${
                        engine.feasible
                          ? 'bg-em/15 text-em border-em/30'
                          : 'bg-nogo/15 text-nogo border-nogo/30'
                      }`}
                    >
                      {engine.feasible ? '✓ Wykonalne' : '✗ Niewykonalne'}
                    </span>
                  </div>

                  {engine.violations.length > 0 ? (
                    <div className="space-y-1.5">
                      <div className="flex gap-3 mb-2">
                        {blockCount > 0 && (
                          <span className="text-xs text-nogo">
                            <span className="font-bold">{blockCount}</span> blokad
                          </span>
                        )}
                        {warnCount > 0 && (
                          <span className="text-xs text-warn">
                            <span className="font-bold">{warnCount}</span> ostrzeżeń
                          </span>
                        )}
                      </div>
                      {engine.violations.slice(0, 6).map((v, i) => (
                        <div
                          key={i}
                          className={`flex items-start gap-2 text-xs px-3 py-2 rounded-md ${
                            v.severity === 'block'
                              ? 'bg-nogo/10 text-nogo'
                              : 'bg-warn/10 text-warn'
                          }`}
                        >
                          {v.severity === 'block'
                            ? <XCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                            : <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                          }
                          {v.message}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-500 text-xs flex items-center gap-1.5">
                      <CheckCircle className="w-3.5 h-3.5 text-em" />
                      Brak naruszeń reguł
                    </p>
                  )}
                </GlassCard>
              )}

              {/* Compare */}
              {!analysisLoading && compare && (
                <GlassCard className="p-4 mt-3">
                  <p className="section-label mb-3">Porównanie kosztorysów</p>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-slate-600 text-xs mb-1">Dokumentacja</p>
                      <p className="text-slate-200 text-sm font-mono font-semibold">{fmtPLN(compare.doc_total)}</p>
                    </div>
                    <div>
                      <p className="text-slate-600 text-xs mb-1">Wycena własna</p>
                      <p className="text-slate-200 text-sm font-mono font-semibold">{fmtPLN(compare.owner_total)}</p>
                    </div>
                    <div>
                      <p className="text-slate-600 text-xs mb-1">Delta B − A</p>
                      <p className={`text-sm font-mono font-bold ${(delta ?? 0) > 0 ? 'text-nogo' : 'text-em'}`}>
                        {delta !== null ? `${delta > 0 ? '+' : ''}${fmtPLN(delta)}` : '—'}
                      </p>
                      {headroom !== null && (
                        <p className="text-xs text-slate-600 mt-0.5">
                          Marża:{' '}
                          <span className={headroom < 0 ? 'text-nogo' : 'text-em'}>
                            {(headroom ?? 0).toFixed(1)}%
                          </span>
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Visual delta bar */}
                  {delta !== null && (
                    <div className="mt-3">
                      <div className="h-1.5 bg-ink-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-700 ${delta > 0 ? 'bg-nogo' : 'bg-em'}`}
                          style={{
                            width: `${Math.min(Math.abs(delta) / Math.max(parseFloat(String(compare.doc_total)) || 1, 1) * 200, 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </GlassCard>
              )}
            </section>

            {/* ── Section C: AI Analysis Runner ─────────────────── */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-4 h-4 text-indigo" />
                <h3 className="section-label">AI Analiza</h3>
              </div>

              <GlassCard className="p-4">
                {/* Run button */}
                <button type="button"
                  onClick={runAnalysis}
                  disabled={running}
                  className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl
                             bg-indigo hover:bg-indigo/90
                             disabled:opacity-50 disabled:cursor-not-allowed
                             text-ink-950 font-semibold text-sm transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200
                             shadow-md-md"
                >
                  {running
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <PlayCircle className="w-4 h-4" />
                  }
                  {running ? 'Analiza w toku…' : 'Uruchom AI Analizę'}
                </button>

                {/* Progress steps */}
                <AnimatePresence>
                  {(running || currentStep === 'done') && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-4 space-y-1 overflow-hidden"
                    >
                      {PROGRESS_STEPS.map((step, idx) => {
                        const isDone = completedSteps.has(step);
                        const isCurrent = currentStep === step && !isDone;
                        return (
                          <motion.div
                            key={step}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.04 }}
                            className={`flex items-center gap-2 text-xs px-3 py-2 rounded-md transition-colors ${
                              isDone
                                ? 'bg-em/10 text-em'
                                : isCurrent
                                ? 'bg-indigo/10 text-indigo'
                                : 'text-slate-600'
                            }`}
                          >
                            {isDone ? (
                              <CheckCircle className="w-3.5 h-3.5 shrink-0" />
                            ) : isCurrent ? (
                              <Loader2 className="w-3.5 h-3.5 shrink-0 animate-spin" />
                            ) : (
                              <div className="w-3.5 h-3.5 shrink-0 rounded-full border border-ink-700" />
                            )}
                            <span className={isCurrent ? 'font-medium' : ''}>{STEP_LABELS[step]}</span>
                          </motion.div>
                        );
                      })}
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* GO/NO-GO verdict badge */}
                <AnimatePresence>
                  {goNogo && (
                    <motion.div
                      key="verdict"
                      initial={{ opacity: 0, scale: 0.9, y: 8 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                      className={`mt-4 flex items-center justify-center gap-4 py-6 rounded-2xl border-2 ${
                        goNogo === 'GO'
                          ? 'bg-em/10 border-em/40'
                          : 'bg-nogo/10 border-nogo/40'
                      }`}
                    >
                      {goNogo === 'GO' ? (
                        <CheckCircle className="w-7 h-7 text-em" />
                      ) : (
                        <XCircle className="w-7 h-7 text-nogo" />
                      )}
                      <span
                        className={`text-6xl font-black tracking-tight leading-none ${
                          goNogo === 'GO' ? 'text-em' : 'text-nogo'
                        }`}
                      >
                        {goNogo}
                      </span>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Decision brief markdown */}
                <AnimatePresence>
                  {brief && (
                    <motion.div
                      key="brief"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35 }}
                      className="mt-4 p-4 rounded-xl bg-ink-950 border border-ink-800/60"
                    >
                      <p className="section-label mb-3">Decision Brief</p>
                      <div
                        className="space-y-1"
                        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(renderMarkdown(brief)) }}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </GlassCard>
            </section>

            {/* ── Section D: Decision Actions ───────────────────── */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <Scale className="w-4 h-4 text-indigo" />
                <h3 className="section-label">Decyzja</h3>
              </div>

              <GlassCard className="p-4">
                <AnimatePresence mode="wait">
                  {decisionStatus === 'decided_go' ? (
                    <motion.div
                      key="confirmed-go"
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-3 p-4 rounded-xl bg-em/10 border border-em/30 text-em"
                    >
                      <CheckCircle className="w-5 h-5 shrink-0" />
                      <div>
                        <p className="font-semibold text-sm">Decyzja GO zapisana</p>
                        <p className="text-xs text-em/60 mt-0.5">
                          Przetarg przekazany do realizacji — pipeline_status: decided_go
                        </p>
                      </div>
                    </motion.div>
                  ) : decisionStatus === 'decided_nogo' ? (
                    <motion.div
                      key="confirmed-nogo"
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-3 p-4 rounded-xl bg-nogo/10 border border-nogo/30 text-nogo"
                    >
                      <XCircle className="w-5 h-5 shrink-0" />
                      <div>
                        <p className="font-semibold text-sm">Decyzja NO-GO zapisana</p>
                        <p className="text-xs text-nogo/60 mt-0.5">
                          Przetarg oznaczony jako odrzucony — pipeline_status: decided_nogo
                        </p>
                      </div>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="action-buttons"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex gap-3"
                    >
                      <button type="button"
                        onClick={() => takeDecision('decided_go')}
                        className="flex-1 flex items-center justify-center gap-2.5 py-4 rounded-xl
                                   bg-em hover:bg-em/90 active:bg-em/80
                                   text-ink-950 font-bold text-sm
                                   transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200 shadow-md-md"
                      >
                        <ThumbsUp className="w-4 h-4" />
                        GO — Złóż ofertę
                      </button>
                      <button type="button"
                        onClick={() => takeDecision('decided_nogo')}
                        className="flex-1 flex items-center justify-center gap-2.5 py-4 rounded-xl
                                   border border-nogo/30 bg-nogo/10
                                   hover:bg-nogo/20 hover:border-nogo/50
                                   text-nogo font-bold text-sm
                                   transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200"
                      >
                        <ThumbsDown className="w-4 h-4" />
                        NO-GO — Odrzuć
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* History */}
                {(historyGo.length > 0 || historyNogo.length > 0) && (
                  <div className="mt-4 pt-4 border-t border-ink-800/60">
                    <div className="flex items-center gap-1.5 mb-3">
                      <History className="w-3.5 h-3.5 text-slate-600" />
                      <p className="section-label">Historia decyzji</p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      {/* GO history */}
                      <div>
                        <p className="text-em text-xs font-semibold mb-2 flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-em inline-block" />
                          GO ({historyGo.length})
                        </p>
                        <div className="space-y-1">
                          {historyGo.map((t) => (
                            <p
                              key={t.id}
                              className="text-slate-500 text-xs truncate py-0.5 border-l-2 border-em/40 pl-2"
                            >
                              {t.title}
                            </p>
                          ))}
                        </div>
                      </div>
                      {/* NO-GO history */}
                      <div>
                        <p className="text-nogo text-xs font-semibold mb-2 flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-nogo inline-block" />
                          NO-GO ({historyNogo.length})
                        </p>
                        <div className="space-y-1">
                          {historyNogo.map((t) => (
                            <p
                              key={t.id}
                              className="text-slate-500 text-xs truncate py-0.5 border-l-2 border-nogo/40 pl-2"
                            >
                              {t.title}
                            </p>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </GlassCard>
            </section>

          </div>
        </div>
      </div>
    </PageShell>
  );
}
