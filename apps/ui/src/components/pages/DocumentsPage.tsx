'use client';
import { useCallback, useEffect, useState } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';
import { motion } from 'motion/react';
import {
  Upload, FileText, FileSpreadsheet, Cpu, Calculator,
  CheckCircle, AlertCircle, Loader2, CloudUpload,
} from 'lucide-react';

interface Document {
  document_id: string;
  filename: string;
  size_bytes: number;
  status: string;
  has_text: boolean;
  has_analysis: boolean;
  has_estimate: boolean;
  uploaded_at: string;
}

interface EstimateItem {
  category: string;
  min_pln: number;
  max_pln: number;
  avg_pln: number;
  icb_backed: boolean;
}

interface Estimate {
  document_id: string;
  items: EstimateItem[];
  total: { min_pln: number; max_pln: number; mid_pln: number; confidence: string };
  disclaimer: string;
}



// ─── Helpers ─────────────────────────────────────────────────────────────────
function getFileExt(filename: string) {
  return filename.split('.').pop()?.toLowerCase() ?? '';
}

function FileTypeIcon({ filename, size = 16 }: { filename: string; size?: number }) {
  const ext = getFileExt(filename);
  if (ext === 'xlsx' || ext === 'xls' || ext === 'csv') {
    return <FileSpreadsheet size={size} className="text-emerald-400 shrink-0" />;
  }
  if (ext === 'docx' || ext === 'doc') {
    return <FileText size={size} className="text-blue-400 shrink-0" />;
  }
  // pdf and others
  return <FileText size={size} className="text-red-400 shrink-0" />;
}

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { label: string; className: string }> = {
    uploaded:  { label: 'Przesłany',        className: 'bg-slate-800 text-slate-400 border border-slate-700' },
    analyzed:  { label: 'Przeanalizowany',  className: 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/30' },
    analyzing: { label: 'Analizuję…',       className: 'bg-amber-500/10 text-amber-300 border border-amber-500/30' },
    estimated: { label: 'Wyceniony',        className: 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30' },
  };
  const { label, className } = cfg[status] ?? cfg.uploaded;
  return (
    <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${className}`}>
      {status === 'analyzing' && <Loader2 size={10} className="inline animate-spin mr-1" />}
      {label}
    </span>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────
export function DocumentsPage() {
  const authFetch = useAuthFetch();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await authFetch('/api/v2/documents');
        if (!cancelled && res.ok) {
          const json = await res.json();
          setDocuments(Array.isArray(json) ? json : json.documents ?? []);
        }
      } catch { /* ignore */ } finally {
        if (!cancelled) setDocsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [authFetch]);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const formatSize = (bytes: number) =>
    bytes >= 1_000_000
      ? `${(bytes / 1_000_000).toFixed(1)} MB`
      : `${(bytes / 1_000).toFixed(0)} KB`;

  const formatPLN = (v: number) =>
    v.toLocaleString('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 });

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: '2-digit' });

  const statusConfig: Record<string, { icon: typeof FileText; color: string; label: string }> = {
    uploaded:  { icon: FileText,   color: 'text-slate-400',   label: 'Przesłany' },
    analyzed:  { icon: Cpu,        color: 'text-indigo-300',  label: 'Przeanalizowany' },
    analyzing: { icon: Loader2,    color: 'text-amber-300',   label: 'Analizuję…' },
    estimated: { icon: Calculator, color: 'text-emerald-400', label: 'Wyceniony' },
  };

  const handleUpload = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/v2/documents/upload', { method: 'POST', body: formData });
      if (res.ok) {
        const data = await res.json();
        const doc: Document = {
          document_id: data.document_id,
          filename: data.filename,
          size_bytes: data.size_bytes,
          status: 'uploaded',
          has_text: false,
          has_analysis: false,
          has_estimate: false,
          uploaded_at: new Date().toISOString(),
        };
        setDocuments(prev => [doc, ...prev]);
        setSelectedDoc(doc);
      }
    } catch {}
    setUploading(false);
  }, []);

  const analyzeDoc = useCallback(async (docId: string) => {
    setAnalyzing(true);
    try {
      await authFetch(`/api/v2/documents/${docId}/analyze`, { method: 'POST' });
      const updated = await authFetch(`/api/v2/documents/${docId}`);
      setSelectedDoc(updated);
      setDocuments(prev => prev.map(d => d.document_id === docId ? { ...d, ...updated } : d));
    } catch {}
    setAnalyzing(false);
  }, [authFetch]);

  const getEstimate = useCallback(async (docId: string) => {
    try {
      const data = await authFetch(`/api/v2/documents/${docId}/estimate`);
      setEstimate(data);
    } catch { setEstimate(null); }
  }, [authFetch]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  }, [handleUpload]);

  return (
    <PageShell title="Dokumenty" subtitle="SWZ, SIWZ, umowy i załączniki">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-6xl">
        {/* ── Left column: upload + list ─────────────────────────────── */}
        <div className="space-y-4">

          {/* ── Premium drop zone ──────────────────────────────────── */}
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={`relative rounded-2xl border-2 border-dashed p-8 text-center
              transition-all duration-200 group cursor-default
              ${dragOver
                ? 'border-emerald-400/60 bg-emerald-500/5 shadow-[0_0_24px_0_rgba(52,211,153,0.08)]'
                : 'border-slate-700/60 hover:border-slate-600/70 bg-slate-900/30 hover:bg-slate-900/50'
              }`}
          >
            {/* Icon wrapper */}
            <div className={`mx-auto mb-4 w-14 h-14 rounded-xl flex items-center justify-center transition-colors
              ${dragOver
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-slate-800/70 text-slate-400 group-hover:bg-slate-800 group-hover:text-slate-300'
              }`}>
              {dragOver
                ? <CloudUpload size={28} />
                : <Upload size={26} />
              }
            </div>

            <p className="text-slate-200 text-sm font-semibold">
              {dragOver ? 'Upuść plik tutaj' : 'Przeciągnij plik tutaj'}
            </p>
            <p className="text-slate-500 text-xs mt-1 mb-1">
              lub kliknij, aby wybrać z dysku
            </p>
            <p className="text-slate-600 text-[11px] mb-4">
              Akceptowane formaty: <span className="text-slate-500">PDF, DOCX, XLSX</span>
            </p>

            <label className="inline-block cursor-pointer">
              <span className="btn-primary px-5 py-2 text-sm inline-flex items-center gap-2 rounded-lg font-medium">
                {uploading ? (
                  <><Loader2 size={14} className="animate-spin" /> Przesyłanie…</>
                ) : (
                  <><Upload size={14} /> Wybierz plik</>
                )}
              </span>
              <input
                type="file"
                accept=".pdf,.docx,.xlsx"
                className="hidden"
                onChange={e => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }}
              />
            </label>
          </div>

          {/* ── Document list ──────────────────────────────────────── */}
          <div className="space-y-1.5">
            <p className="text-slate-500 text-xs font-medium uppercase tracking-wider px-1 mb-2">
              Dokumenty ({documents.length})
            </p>
            {docsLoading ? (
              <div className="space-y-2">
                {[1,2,3].map(i => (
                  <div key={i} className="h-16 rounded-xl bg-slate-800/50 animate-pulse" />
                ))}
              </div>
            ) : documents.length === 0 ? (
              <p className="text-slate-500 text-sm px-1">Brak dokumentów. Prześlij plik PDF aby rozpocząć.</p>
            ) : documents.map(doc => (
              <div
                key={doc.document_id}
                onClick={() => {
                  setSelectedDoc(doc);
                  if (doc.has_estimate) getEstimate(doc.document_id);
                }}
                className={`group flex items-center gap-3 p-3 rounded-xl cursor-pointer
                  transition-all duration-150 border
                  ${selectedDoc?.document_id === doc.document_id
                    ? 'bg-emerald-500/8 border-emerald-500/25 shadow-sm'
                    : 'bg-slate-900/40 border-transparent hover:bg-slate-800/50 hover:border-slate-700/40'
                  }`}
              >
                {/* File type icon */}
                <div className="shrink-0 w-8 h-8 rounded-lg bg-slate-800/80 flex items-center justify-center">
                  <FileTypeIcon filename={doc.filename} size={15} />
                </div>

                {/* Name + meta */}
                <div className="flex-1 min-w-0">
                  <div className="text-slate-200 text-sm truncate font-medium leading-tight">
                    {doc.filename}
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-slate-500 text-[11px]">{formatSize(doc.size_bytes)}</span>
                    <span className="text-slate-700 text-[11px]">·</span>
                    <span className="text-slate-600 text-[11px]">{formatDate(doc.uploaded_at)}</span>
                  </div>
                </div>

                {/* Status badge */}
                <StatusBadge status={doc.status} />
              </div>
            ))}
          </div>
        </div>

        {/* ── Right panel: detail ────────────────────────────────────────── */}
        <div className="lg:col-span-2">
          {!selectedDoc ? (
            <GlassCard className="p-12 text-center">
              <div className="mx-auto w-16 h-16 rounded-2xl bg-slate-800/70 flex items-center justify-center mb-4">
                <FileText size={32} className="text-slate-600" />
              </div>
              <p className="text-slate-400 font-semibold">Wybierz lub prześlij dokument</p>
              <p className="text-slate-600 text-sm mt-1">
                Upload PDF → Analiza AI → Automatyczny kosztorys z ICB
              </p>
            </GlassCard>
          ) : (
            <div className="space-y-4">
              {/* Status pipeline */}
              <GlassCard className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileTypeIcon filename={selectedDoc.filename} size={18} />
                    <h3 className="text-slate-100 font-semibold truncate">{selectedDoc.filename}</h3>
                  </div>
                  <StatusBadge status={selectedDoc.status} />
                </div>
                <div className="text-slate-500 text-xs mt-1 ml-6">
                  {formatSize(selectedDoc.size_bytes)} · przesłany {formatDate(selectedDoc.uploaded_at)}
                </div>

                {/* Pipeline steps */}
                <div className="flex items-center gap-2 mt-5">
                  {(['Upload', 'Analiza', 'Kosztorys'] as const).map((step, i) => {
                    const done = i === 0
                      || (i === 1 && selectedDoc.has_analysis)
                      || (i === 2 && selectedDoc.has_estimate);
                    return (
                      <div key={step} className="flex items-center gap-2 flex-1">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                          done ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-500'
                        }`}>
                          {done ? <CheckCircle size={16} /> : <span className="text-xs">{i + 1}</span>}
                        </div>
                        <span className={`text-xs ${done ? 'text-emerald-400' : 'text-slate-500'}`}>{step}</span>
                        {i < 2 && (
                          <div className={`flex-1 h-0.5 ${done ? 'bg-emerald-500/30' : 'bg-slate-800'}`} />
                        )}
                      </div>
                    );
                  })}
                </div>
              </GlassCard>

              {/* Actions */}
              {!selectedDoc.has_analysis && (
                <button type="button"
                  onClick={() => analyzeDoc(selectedDoc.document_id)}
                  disabled={analyzing}
                  className="btn-primary w-full px-4 py-3 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {analyzing ? <Loader2 size={16} className="animate-spin" /> : <Cpu size={16} />}
                  {analyzing ? 'Analizuję PDF…' : 'Uruchom analizę AI'}
                </button>
              )}

              {selectedDoc.has_analysis && !selectedDoc.has_estimate && (
                <button type="button"
                  onClick={() => getEstimate(selectedDoc.document_id)}
                  className="w-full px-4 py-3 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/25 rounded-xl font-medium flex items-center justify-center gap-2 transition-colors"
                >
                  <Calculator size={16} />
                  Generuj kosztorys z ICB
                </button>
              )}

              {/* Estimate results */}
              {estimate && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <GlassCard className="p-4">
                    <h3 className="text-slate-100 font-semibold mb-3">Kosztorys wstępny</h3>

                    {/* Summary */}
                    <div className="grid grid-cols-3 gap-3 mb-4">
                      <div className="bg-slate-900/60 rounded-xl p-3 text-center">
                        <div className="text-slate-500 text-xs mb-1">Minimum</div>
                        <div className="text-slate-100 font-bold text-sm">{formatPLN(estimate.total.min_pln)}</div>
                      </div>
                      <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-3 text-center">
                        <div className="text-indigo-300 text-xs mb-1">Środek</div>
                        <div className="text-indigo-300 font-bold text-lg">{formatPLN(estimate.total.mid_pln)}</div>
                      </div>
                      <div className="bg-slate-900/60 rounded-xl p-3 text-center">
                        <div className="text-slate-500 text-xs mb-1">Maksimum</div>
                        <div className="text-slate-100 font-bold text-sm">{formatPLN(estimate.total.max_pln)}</div>
                      </div>
                    </div>

                    {/* Items */}
                    <div className="space-y-2">
                      {estimate.items.map((item, i) => (
                        <div key={i} className="flex items-center justify-between p-2 bg-slate-900/40 rounded-md">
                          <div className="flex items-center gap-2">
                            {item.icb_backed ? (
                              <CheckCircle size={12} className="text-emerald-400" />
                            ) : (
                              <AlertCircle size={12} className="text-amber-400" />
                            )}
                            <span className="text-slate-200 text-sm">{item.category}</span>
                          </div>
                          <span className="text-slate-300 text-sm">
                            {formatPLN(item.min_pln)} – {formatPLN(item.max_pln)}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Confidence */}
                    <div className="mt-3 flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-md ${
                        estimate.total.confidence === 'medium'
                          ? 'bg-amber-500/10 text-amber-300'
                          : 'bg-red-500/10 text-red-300'
                      }`}>
                        Pewność: {estimate.total.confidence}
                      </span>
                    </div>

                    <p className="text-slate-600 text-xs mt-3 italic">{estimate.disclaimer}</p>
                  </GlassCard>
                </motion.div>
              )}
            </div>
          )}
        </div>
      </div>
    </PageShell>
  );
}
