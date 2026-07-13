'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { motion, AnimatePresence } from 'motion/react';
import {
  CheckCircle2, XCircle, Loader2, AlertTriangle,
  Calendar, Info, RefreshCw, ClipboardList,
} from 'lucide-react';
import { PageShell } from '@/components/PageShell';
import { StatusBadge } from '@/components/ui/StatusBadge';

// ── Typy ──────────────────────────────────────────────────────────────────────
interface RfqItem {
  id: string;
  title: string;
  status: string;
  tender_id: string | null;
  created_at: string;
  deadline_at: string | null;
  responses_count: number;
}

type Decision = 'decided_go' | 'decided_nogo';

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtDate(s: string | null | undefined) {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('pl-PL');
}

// ── Modal potwierdzenia ────────────────────────────────────────────────────────
function ConfirmDialog({
  tender, decision, onConfirm, onCancel, loading,
}: {
  tender: RfqItem;
  decision: Decision;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const isGo = decision === 'decided_go';
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-earth-950/80 backdrop-blur-sm p-4"
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="card rounded-token-xl p-6 max-w-md w-full shadow-token-lg"
      >
        <div className="flex items-center gap-3 mb-4">
          {isGo
            ? <CheckCircle2 className="w-6 h-6 text-accent-primary shrink-0" />
            : <XCircle className="w-6 h-6 text-accent-danger shrink-0" />
          }
          <h3 className="text-earth-100 font-semibold text-base">
            {isGo ? 'Potwierdzenie decyzji GO' : 'Potwierdzenie decyzji NO-GO'}
          </h3>
        </div>

        <p className="section-label mb-1">Zapytanie ofertowe:</p>
        <p className="text-earth-200 text-sm font-medium line-clamp-2 mb-4">{tender.title}</p>

        <div className="flex items-center gap-3 p-3 rounded-token bg-earth-800/40 mb-5">
          <Calendar className="w-4 h-4 text-earth-500 shrink-0" />
          <span className="text-earth-400 text-sm">Termin: {fmtDate(tender.deadline_at)}</span>
        </div>

        <div className={`p-3 rounded-token mb-5 text-sm ${
          isGo
            ? 'bg-accent-primary/8 border border-accent-primary/20 text-accent-primary'
            : 'bg-accent-danger/8 border border-accent-danger/20 text-accent-danger'
        }`}>
          {isGo
            ? '✓ Zapytanie zostanie przeniesione do etapu GO. Oferta zostanie przygotowana do złożenia.'
            : '✗ Zapytanie zostanie odrzucone. Decyzja NO-GO jest ostateczna i nie można jej cofnąć.'}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="btn-secondary flex-1 py-3 text-sm disabled:opacity-50"
          >
            Anuluj
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`flex-1 py-3 rounded-token text-sm font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 ${
              isGo
                ? 'btn-primary'
                : 'bg-accent-danger/15 text-accent-danger border border-accent-danger/30 hover:bg-accent-danger/25'
            }`}
          >
            {loading
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : isGo
                ? <><CheckCircle2 className="w-4 h-4" /> Potwierdź GO — złóż ofertę</>
                : <><XCircle className="w-4 h-4" /> Odrzuć — decyzja NO-GO</>
            }
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function SkeletonRow() {
  return (
    <div className="card rounded-token-xl p-4 animate-pulse-soft">
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="h-4 bg-earth-800 rounded w-3/4 mb-2" />
          <div className="h-3 bg-earth-800 rounded w-1/2 mb-3" />
          <div className="flex gap-4">
            <div className="h-3 bg-earth-800 rounded w-24" />
            <div className="h-3 bg-earth-800 rounded w-20" />
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          <div className="h-10 w-28 bg-earth-800 rounded-token" />
          <div className="h-10 w-28 bg-earth-800 rounded-token" />
        </div>
      </div>
    </div>
  );
}

// ── Komponent główny ──────────────────────────────────────────────────────────
export function RfqPage() {
  const [tenders, setTenders] = useState<RfqItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ tender: RfqItem; decision: Decision } | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [justDecided, setJustDecided] = useState<Record<string, Decision>>({});

  const authFetch = useAuthFetch();

  const fetchTenders = useCallback(() => {
    setLoading(true);
    setError(null);
    authFetch('/api/v2/rfq')
      .then((data: RfqItem[]) => { setTenders(data ?? []); setLoading(false); })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, [authFetch]);

  useEffect(() => { fetchTenders(); }, [fetchTenders]);

  const handleConfirm = async () => {
    if (!confirm) return;
    setConfirming(true);
    try {
      await authFetch(`/api/v2/rfq/${confirm.tender.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: confirm.decision }),
      });
      setJustDecided(prev => ({ ...prev, [confirm.tender.id]: confirm.decision }));
      setTimeout(() => {
        setTenders(prev => prev.filter(t => t.id !== confirm.tender.id));
        setJustDecided(prev => { const n = { ...prev }; delete n[confirm.tender.id]; return n; });
      }, 800);
    } catch (e: unknown) {
      console.error(e);
    } finally {
      setConfirming(false);
      setConfirm(null);
    }
  };

  return (
    <PageShell
      title="Zapytania Ofertowe"
      subtitle="RFQ i wyceny podwykonawców"
      actions={
        <div className="flex items-center gap-3">
          {tenders.length > 0 && (
            <StatusBadge status="warning" label={`${tenders.length} w analizie`} />
          )}
          <button
            onClick={fetchTenders}
            disabled={loading}
            title="Odśwież listę"
            className="btn-ghost p-2 disabled:opacity-40"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      }
    >
      {/* Modal potwierdzenia */}
      <AnimatePresence>
        {confirm ? (
          <ConfirmDialog
            tender={confirm.tender}
            decision={confirm.decision}
            onConfirm={handleConfirm}
            onCancel={() => setConfirm(null)}
            loading={confirming}
          />
        ) : null}
      </AnimatePresence>

      <div className="flex flex-col gap-5 max-w-5xl">
        {/* Pasek informacyjny */}
        <div className="flex items-start gap-2 px-4 py-3 bg-accent-info/8 border border-accent-info/20 rounded-token-lg text-accent-info text-xs leading-relaxed">
          <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>
            Przetargi z etapu <span className="font-semibold">Analiza</span> oczekują na Twoją decyzję.
            Kliknij <span className="font-semibold">GO</span>, aby przejść do składania oferty,
            lub <span className="font-semibold">NO-GO</span>, aby zrezygnować z przetargu.
          </span>
        </div>

        {/* Błąd */}
        {error && (
          <div className="flex items-center gap-2 p-4 rounded-token-lg bg-accent-danger/10 border border-accent-danger/20 text-accent-danger text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Błąd ładowania danych: {error}</span>
          </div>
        )}

        {/* Zawartość */}
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} />)}
          </div>
        ) : tenders.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="card rounded-token-xl p-14 text-center"
          >
            <ClipboardList className="w-12 h-12 text-earth-700 mx-auto mb-4" />
            <p className="text-earth-300 font-semibold mb-1">Brak aktywnych zapytań ofertowych</p>
            <p className="text-earth-600 text-sm">Wszystkie zapytania zostały już rozpatrzone</p>
          </motion.div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence mode="popLayout">
              {tenders.map((t) => {
                const decided = justDecided[t.id];
                const isGo   = decided === 'decided_go';
                const isNogo = decided === 'decided_nogo';

                return (
                  <motion.div
                    key={t.id}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{
                      opacity: decided ? 0.4 : 1,
                      scale:   decided ? 0.98 : 1,
                      y: 0,
                    }}
                    exit={{ opacity: 0, x: isGo ? 60 : -60, scale: 0.95 }}
                    transition={{ duration: 0.3 }}
                    className={`card rounded-token-xl p-5 ${decided ? 'pointer-events-none' : 'card-hover'}`}
                  >
                    <div className="flex items-start gap-4">
                      <div className="flex-1 min-w-0">
                        {/* Tytuł */}
                        <p className="text-earth-100 font-semibold text-sm line-clamp-2 mb-1">{t.title}</p>
                        <p className="text-earth-500 text-xs mb-3 truncate">Status: {t.status}</p>

                        {/* Meta: termin, odpowiedzi */}
                        <div className="flex items-center gap-4 flex-wrap">
                          <span className="flex items-center gap-1.5 text-xs text-earth-500">
                            <Calendar className="w-3.5 h-3.5" />
                            Termin: {fmtDate(t.deadline_at)}
                          </span>
                          <span className="flex items-center gap-1.5 text-xs text-earth-400">
                            <ClipboardList className="w-3.5 h-3.5" />
                            Odpowiedzi: {t.responses_count}
                          </span>
                        </div>
                      </div>

                      {/* Przyciski decyzji */}
                      {decided ? (
                        <div className={`flex items-center gap-2 px-4 py-2.5 rounded-token text-sm font-bold ${
                          isGo ? 'bg-accent-primary/15 text-accent-primary' : 'bg-accent-danger/15 text-accent-danger'
                        }`}>
                          {isGo ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                          {isGo ? 'GO — zatwierdzono' : 'NO-GO — odrzucono'}
                        </div>
                      ) : (
                        <div className="flex flex-col gap-2 shrink-0">
                          <button
                            onClick={() => setConfirm({ tender: t, decision: 'decided_go' })}
                            className="flex items-center gap-2 px-5 py-2.5 rounded-token bg-accent-primary/15 text-accent-primary text-sm font-bold hover:bg-accent-primary/25 transition-colors border border-accent-primary/30 min-w-[130px] justify-center"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                            GO — złóż ofertę
                          </button>
                          <button
                            onClick={() => setConfirm({ tender: t, decision: 'decided_nogo' })}
                            className="flex items-center gap-2 px-5 py-2.5 rounded-token bg-accent-danger/10 text-accent-danger text-sm font-bold hover:bg-accent-danger/20 transition-colors border border-accent-danger/25 min-w-[130px] justify-center"
                          >
                            <XCircle className="w-4 h-4" />
                            NO-GO — odrzuć
                          </button>
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </PageShell>
  );
}
