'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Upload, ChevronRight, ChevronLeft, Check, AlertTriangle, Loader2, FileSpreadsheet, Clock, FileText } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';
import { showToast } from '@/components/Toast';
import { useStore } from '@/store/useStore';

type Step = 0 | 1 | 2 | 3;

interface ParsedRow {
  [key: string]: string;
}

interface ImportJob {
  id: string | number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  processed: number;
  total: number;
  filename?: string;
  created_at?: string;
}

const TARGET_FIELDS = [
  { key: 'project_name', label: 'Nazwa projektu', required: true },
  { key: 'cpv', label: 'Kod CPV', required: false },
  { key: 'value', label: 'Wartość oferty (PLN)', required: true },
  { key: 'actual_cost', label: 'Koszt rzeczywisty (PLN)', required: false },
  { key: 'won', label: 'Wygrany (true/false)', required: true },
  { key: 'n_competitors', label: 'Liczba konkurentów', required: false },
];

function parseCSV(text: string): { headers: string[]; rows: ParsedRow[] } {
  const lines = text.split('\n').filter(l => l.trim());
  if (lines.length === 0) return { headers: [], rows: [] };
  const sep = lines[0].includes(';') ? ';' : ',';
  const headers = lines[0].split(sep).map(h => h.trim().replace(/^[\"']|[\"']$/g, ''));
  const rows = lines.slice(1, 6).map(line => {
    const vals = line.split(sep).map(v => v.trim().replace(/^[\"']|[\"']$/g, ''));
    return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? '']));
  });
  return { headers, rows };
}

function formatDate(iso?: string): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pl-PL', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

function statusLabel(status: string): { text: string; cls: string } {
  switch (status) {
    case 'completed': return { text: 'Zakończony', cls: 'text-accent-primary' };
    case 'processing': return { text: 'W trakcie', cls: 'text-accent-warning' };
    case 'pending':    return { text: 'Oczekuje', cls: 'text-earth-400' };
    case 'failed':     return { text: 'Błąd', cls: 'text-accent-danger' };
    default:           return { text: status, cls: 'text-earth-500' };
  }
}

export function ImportPage() {
  const { accessToken } = useStore();
  const [step, setStep] = useState<Step>(0);
  const [file, setFile] = useState<File | null>(null);
  const [csvData, setCsvData] = useState<{ headers: string[]; rows: ParsedRow[] } | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  // Progress polling state
  const [activeJob, setActiveJob] = useState<ImportJob | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Import history
  const [importHistory, setImportHistory] = useState<ImportJob[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const dropRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Fetch import history ───────────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    if (!accessToken) return;
    setHistoryLoading(true);
    try {
      const res = await fetch('/api/v1/excel/imports', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (res.ok) {
        const data: ImportJob[] = await res.json();
        setImportHistory(data.slice(0, 5));
      }
    } catch {
      // history is best-effort; do not block UI
    } finally {
      setHistoryLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // ── Polling ────────────────────────────────────────────────────────────────
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const pollImports = useCallback(async () => {
    if (!accessToken) return;
    try {
      const res = await fetch('/api/v1/excel/imports', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) return;
      const jobs: ImportJob[] = await res.json();
      if (jobs.length === 0) return;
      const latest = jobs[0];
      setActiveJob(latest);

      if (latest.status === 'completed') {
        stopPolling();
        setDone(true);
        setStep(3);
        setLoading(false);
        showToast('success', 'Import zakończony pomyślnie!');
        loadHistory();
      } else if (latest.status === 'failed') {
        stopPolling();
        setLoading(false);
        setImportError('Import zakończył się błędem po stronie serwera.');
        showToast('error', 'Błąd importu danych');
      }
    } catch {
      // poll failure is transient — keep trying
    }
  }, [accessToken, stopPolling, loadHistory]);

  // cleanup on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

  // ── File handling ──────────────────────────────────────────────────────────
  function handleFile(f: File) {
    setFile(f);
    const reader = new FileReader();
    reader.onload = e => {
      const text = e.target?.result as string;
      const parsed = parseCSV(text);
      setCsvData(parsed);
      const autoMap: Record<string, string> = {};
      for (const tf of TARGET_FIELDS) {
        const match = parsed.headers.find(h =>
          h.toLowerCase().includes(tf.key.toLowerCase()) ||
          h.toLowerCase().includes(tf.label.toLowerCase().slice(0, 6))
        );
        if (match) autoMap[tf.key] = match;
      }
      setMapping(autoMap);
      setStep(1);
    };
    reader.readAsText(f, 'UTF-8');
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  function validate() {
    const errs: string[] = [];
    const warns: string[] = [];
    for (const tf of TARGET_FIELDS) {
      if (tf.required && !mapping[tf.key]) {
        errs.push(`Pole "${tf.label}" jest wymagane — przypisz kolumnę`);
      }
    }
    if (csvData && csvData.rows.length === 0) errs.push('Plik jest pusty');
    if (csvData && csvData.rows.length > 0 && !mapping['won']) warns.push('Pole "Wygrany" nie jest zmapowane — zostanie pominięte');
    setErrors(errs);
    setWarnings(warns);
    if (errs.length === 0) setStep(2);
  }

  // ── Submit ─────────────────────────────────────────────────────────────────
  async function submitImport() {
    setLoading(true);
    setImportError(null);
    setActiveJob(null);

    try {
      if (!accessToken || !file) {
        throw new Error('Brak tokenu autoryzacji lub pliku');
      }

      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/v1/excel/import/tenders', {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
        body: formData,
      });

      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const body = await res.json();
          if (body?.detail) detail = body.detail;
        } catch { /* ignore */ }
        throw new Error(detail);
      }

      // Start polling every 2 s for live progress
      stopPolling();
      pollTimerRef.current = setInterval(pollImports, 2000);
      // Immediate first poll
      pollImports();

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Błąd importu danych';
      setImportError(msg);
      showToast('error', msg);
      setLoading(false);
    }
  }

  // ── Progress % ─────────────────────────────────────────────────────────────
  const progressPct =
    activeJob && activeJob.total > 0
      ? Math.min(100, Math.round((activeJob.processed / activeJob.total) * 100))
      : null;

  const STEPS = ['Upload', 'Mapowanie', 'Walidacja', 'Import'];

  return (
    <PageShell title="Import Przetargów" subtitle="Import BZP/TED/XML">
      <div className="max-w-2xl">
        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-6">
          {STEPS.map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                i < step
                  ? 'bg-accent-primary text-earth-950'
                  : i === step
                    ? 'bg-accent-primary/20 text-accent-primary border border-accent-primary/60'
                    : 'bg-earth-800 text-earth-600'
              }`}>
                {i < step ? <Check className="w-3.5 h-3.5" /> : i + 1}
              </div>
              <span className={`text-xs ${i === step ? 'text-earth-200' : 'text-earth-600'}`}>{s}</span>
              {i < STEPS.length - 1 && (
                <div className={`h-px w-8 ${i < step ? 'bg-accent-primary' : 'bg-earth-800'}`} />
              )}
            </div>
          ))}
        </div>

        {/* ── Step 0: Upload ── */}
        {step === 0 && (
          <div
            ref={dropRef}
            onDrop={handleDrop}
            onDragOver={e => e.preventDefault()}
            onClick={() => inputRef.current?.click()}
            className="border-2 border-dashed border-earth-700/60 rounded-token-xl p-12 text-center cursor-pointer hover:border-accent-primary/40 hover:bg-accent-primary/5 transition-all group"
          >
            <input
              ref={inputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
            <FileSpreadsheet className="w-12 h-12 text-earth-700 group-hover:text-accent-primary/60 mx-auto mb-3 transition-colors" />
            <p className="text-sm font-medium text-earth-300">Upuść plik CSV lub Excel tutaj</p>
            <p className="text-xs text-earth-600 mt-1">lub kliknij aby wybrać</p>
            <p className="text-xs text-earth-700 mt-3">Obsługiwane formaty: .csv, .xlsx, .xls</p>
          </div>
        )}

        {/* ── Step 1: Mapping ── */}
        {step === 1 && csvData && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-earth-200">Mapowanie kolumn</h3>
            <p className="text-xs text-earth-500">
              Plik: <span className="text-earth-300">{file?.name}</span> • {csvData.rows.length} wierszy podglądu
            </p>

            {/* Preview table */}
            <GlassCard className="overflow-x-auto p-0">
              <table className="text-xs w-full">
                <thead>
                  <tr className="border-b border-earth-800/60">
                    {csvData.headers.map(h => (
                      <th key={h} className="px-3 py-2 text-left text-earth-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {csvData.rows.slice(0, 3).map((row, i) => (
                    <tr key={i} className="border-b border-earth-800/30">
                      {csvData.headers.map(h => (
                        <td key={h} className="px-3 py-2 text-earth-400">{row[h] ?? '—'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </GlassCard>

            {/* Mapping selects */}
            <GlassCard className="p-4 space-y-3">
              {TARGET_FIELDS.map(tf => (
                <div key={tf.key} className="flex items-center gap-3">
                  <span className="text-xs text-earth-400 w-44 shrink-0">
                    {tf.label}
                    {tf.required && <span className="text-accent-danger ml-0.5">*</span>}
                  </span>
                  <select
                    value={mapping[tf.key] ?? ''}
                    onChange={e => setMapping(m => ({ ...m, [tf.key]: e.target.value }))}
                    className="input-base flex-1 text-xs py-1.5"
                  >
                    <option value="">— Pomiń —</option>
                    {csvData.headers.map(h => <option key={h} value={h}>{h}</option>)}
                  </select>
                </div>
              ))}
            </GlassCard>

            <div className="flex gap-3">
              <button
                onClick={() => setStep(0)}
                className="btn-ghost flex items-center gap-1.5 px-4 py-2 text-sm"
              >
                <ChevronLeft className="w-4 h-4" /> Wstecz
              </button>
              <button
                onClick={validate}
                className="btn-primary flex items-center gap-1.5 px-5 py-2.5 text-sm"
              >
                Waliduj <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* ── Step 2: Validation + Import ── */}
        {step === 2 && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-earth-200">Wyniki walidacji</h3>

            {errors.length > 0 && (
              <GlassCard className="p-4 space-y-2 border-accent-danger/20">
                <p className="text-xs font-semibold text-accent-danger uppercase tracking-wide">Błędy ({errors.length})</p>
                {errors.map((e, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-accent-danger/80">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-accent-danger" /> {e}
                  </div>
                ))}
              </GlassCard>
            )}

            {warnings.length > 0 && (
              <GlassCard className="p-4 space-y-2 border-accent-warning/20">
                <p className="text-xs font-semibold text-accent-warning uppercase tracking-wide">Ostrzeżenia ({warnings.length})</p>
                {warnings.map((w, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-accent-warning/80">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-accent-warning" /> {w}
                  </div>
                ))}
              </GlassCard>
            )}

            {/* Import error */}
            {importError && (
              <GlassCard className="p-4 border-accent-danger/20">
                <div className="flex items-start gap-2 text-xs text-accent-danger/80">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-accent-danger" />
                  <span>{importError}</span>
                </div>
              </GlassCard>
            )}

            {errors.length === 0 && !importError && (
              <GlassCard className="p-4">
                <div className="flex items-center gap-2 text-accent-primary mb-2">
                  <Check className="w-4 h-4" />
                  <span className="text-sm font-semibold">Gotowe do importu</span>
                </div>
                <p className="text-xs text-earth-500">
                  {csvData?.rows.length ?? 0}+ wierszy danych historycznych zostanie zaimportowanych
                </p>
              </GlassCard>
            )}

            {/* Live progress bar */}
            {loading && (
              <GlassCard className="p-4 space-y-3">
                <div className="flex items-center gap-2 text-xs text-earth-300">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-primary" />
                  <span>
                    {activeJob
                      ? `Przetwarzanie… ${activeJob.processed} / ${activeJob.total > 0 ? activeJob.total : '?'} rekordów`
                      : 'Wysyłanie pliku…'}
                  </span>
                </div>
                <div className="w-full bg-earth-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-accent-primary h-2 rounded-full transition-all duration-500"
                    style={{
                      width: progressPct !== null ? `${progressPct}%` : '100%',
                      opacity: progressPct !== null ? 1 : 0.4,
                    }}
                  />
                </div>
                {progressPct !== null && (
                  <p className="text-xs text-earth-500 text-right">{progressPct}%</p>
                )}
              </GlassCard>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setStep(1)}
                disabled={loading}
                className="btn-ghost flex items-center gap-1.5 px-4 py-2 text-sm disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" /> Wstecz
              </button>
              {errors.length === 0 && (
                <button
                  onClick={submitImport}
                  disabled={loading}
                  className="btn-primary flex items-center gap-2 px-5 py-2.5 text-sm disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  {loading ? 'Importowanie…' : importError ? 'Spróbuj ponownie' : 'Importuj dane'}
                </button>
              )}
            </div>
          </div>
        )}

        {/* ── Step 3: Done ── */}
        {step === 3 && done && (
          <div className="text-center py-8">
            <div className="w-16 h-16 rounded-full bg-accent-primary/15 border border-accent-primary/30 flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-accent-primary" />
            </div>
            <h3 className="text-base font-bold text-earth-100 mb-2">Import zakończony!</h3>
            <p className="text-sm text-earth-500">
              Dane historyczne zostały zaimportowane. AI będzie mogło teraz uczyć się wzorców przetargów.
            </p>
            {activeJob && activeJob.total > 0 && (
              <p className="text-xs text-earth-600 mt-1">
                Zaimportowano {activeJob.processed} z {activeJob.total} rekordów.
              </p>
            )}
            <button
              onClick={() => {
                setStep(0); setFile(null); setCsvData(null);
                setDone(false); setActiveJob(null); setImportError(null);
              }}
              className="btn-secondary mt-4 px-5 py-2 text-sm"
            >
              Importuj kolejny plik
            </button>
          </div>
        )}

        {/* ── Import History ── */}
        <div className="mt-8 space-y-3">
          <h3 className="section-label flex items-center gap-2">
            <Clock className="w-3.5 h-3.5" /> Ostatnie importy
          </h3>

          {historyLoading ? (
            <p className="text-xs text-earth-600 flex items-center gap-2">
              <Loader2 className="w-3 h-3 animate-spin" /> Ładowanie historii…
            </p>
          ) : importHistory.length === 0 ? (
            <p className="text-xs text-earth-700">Brak historii importów.</p>
          ) : (
            <GlassCard className="p-0 overflow-hidden">
              <table className="text-xs w-full">
                <thead>
                  <tr className="border-b border-earth-800/60">
                    <th className="px-3 py-2 text-left text-earth-600 font-normal">Plik</th>
                    <th className="px-3 py-2 text-left text-earth-600 font-normal">Data</th>
                    <th className="px-3 py-2 text-right text-earth-600 font-normal">Rekordy</th>
                    <th className="px-3 py-2 text-left text-earth-600 font-normal">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {importHistory.map((job, i) => {
                    const { text, cls } = statusLabel(job.status);
                    return (
                      <tr key={job.id ?? i} className="border-b border-earth-800/20 last:border-0">
                        <td className="px-3 py-2 text-earth-300">
                          <span className="flex items-center gap-1.5">
                            <FileText className="w-3 h-3 text-earth-600 shrink-0" />
                            <span className="truncate max-w-[140px]">{job.filename ?? '—'}</span>
                          </span>
                        </td>
                        <td className="px-3 py-2 text-earth-500 whitespace-nowrap">{formatDate(job.created_at)}</td>
                        <td className="px-3 py-2 text-earth-400 text-right">
                          {job.total > 0 ? `${job.processed} / ${job.total}` : job.processed > 0 ? job.processed : '—'}
                        </td>
                        <td className={`px-3 py-2 font-medium ${cls}`}>{text}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </GlassCard>
          )}
        </div>
      </div>
    </PageShell>
  );
}
