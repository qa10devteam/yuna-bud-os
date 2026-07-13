'use client';
import { useEffect, useState, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';
import { motion } from 'motion/react';
import { Upload, FileText, Cpu, Calculator, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

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

export function DocumentsPage() {
  const authFetch = useAuthFetch();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const formatSize = (bytes: number) =>
    bytes > 1_000_000 ? `${(bytes / 1_000_000).toFixed(1)} MB` : `${(bytes / 1_000).toFixed(0)} KB`;
  const formatPLN = (v: number) =>
    v.toLocaleString('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 });

  const statusConfig: Record<string, { icon: typeof FileText; color: string; label: string }> = {
    uploaded: { icon: FileText,    color: 'text-earth-400',    label: 'Przesłany' },
    analyzed: { icon: Cpu,         color: 'text-accent-info',  label: 'Przeanalizowany' },
    estimated:{ icon: Calculator,  color: 'text-accent-primary', label: 'Wyceniony' },
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
        {/* Upload + list */}
        <div className="space-y-4">
          {/* Drop zone */}
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-token-xl p-8 text-center transition-all ${
              dragOver
                ? 'border-accent-primary/60 bg-accent-primary/5'
                : 'border-earth-700/60 hover:border-earth-600/80'
            }`}
          >
            <Upload
              size={32}
              className={`mx-auto mb-3 ${dragOver ? 'text-accent-primary' : 'text-earth-500'}`}
            />
            <p className="text-earth-300 text-sm font-medium">Przeciągnij PDF tutaj</p>
            <p className="text-earth-500 text-xs mt-1">SIWZ, rysunki techniczne, przedmiary</p>
            <label className="mt-3 inline-block cursor-pointer">
              <span className="btn-primary px-4 py-2 text-sm inline-flex items-center gap-2">
                {uploading ? (
                  <><Loader2 size={14} className="animate-spin" /> Przesyłanie...</>
                ) : (
                  'Wybierz plik'
                )}
              </span>
              <input
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={e => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }}
              />
            </label>
          </div>

          {/* Document list */}
          <div className="space-y-2">
            {documents.map(doc => {
              const cfg = statusConfig[doc.status] || statusConfig.uploaded;
              const Icon = cfg.icon;
              return (
                <div
                  key={doc.document_id}
                  onClick={() => { setSelectedDoc(doc); if (doc.has_estimate) getEstimate(doc.document_id); }}
                  className={`p-3 rounded-token cursor-pointer transition-colors ${
                    selectedDoc?.document_id === doc.document_id
                      ? 'bg-accent-primary/10 border border-accent-primary/30'
                      : 'bg-earth-900/40 hover:bg-earth-800/50 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon size={16} className={cfg.color} />
                    <div className="flex-1 min-w-0">
                      <div className="text-earth-200 text-sm truncate">{doc.filename}</div>
                      <div className="text-earth-500 text-xs">{formatSize(doc.size_bytes)} · {cfg.label}</div>
                    </div>
                  </div>
                </div>
              );
            })}
            {documents.length === 0 && (
              <p className="text-earth-600 text-sm text-center py-4">Brak dokumentów</p>
            )}
          </div>
        </div>

        {/* Detail panel */}
        <div className="lg:col-span-2">
          {!selectedDoc ? (
            <GlassCard className="p-12 text-center">
              <FileText size={48} className="mx-auto text-earth-700 mb-3" />
              <p className="text-earth-500 font-medium">Wybierz lub prześlij dokument</p>
              <p className="text-earth-700 text-sm mt-1">Upload PDF → Analiza AI → Automatyczny kosztorys z ICB</p>
            </GlassCard>
          ) : (
            <div className="space-y-4">
              {/* Status pipeline */}
              <GlassCard className="p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-earth-100 font-medium truncate">{selectedDoc.filename}</h3>
                  <span className={`text-xs px-2 py-1 rounded-token bg-earth-800 ${statusConfig[selectedDoc.status]?.color || 'text-earth-400'}`}>
                    {statusConfig[selectedDoc.status]?.label || selectedDoc.status}
                  </span>
                </div>
                {/* Pipeline steps */}
                <div className="flex items-center gap-2 mt-4">
                  {['Upload', 'Analiza', 'Kosztorys'].map((step, i) => {
                    const done = i === 0 || (i === 1 && selectedDoc.has_analysis) || (i === 2 && selectedDoc.has_estimate);
                    return (
                      <div key={step} className="flex items-center gap-2 flex-1">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          done ? 'bg-accent-primary/20 text-accent-primary' : 'bg-earth-800 text-earth-500'
                        }`}>
                          {done ? <CheckCircle size={16} /> : <span className="text-xs">{i + 1}</span>}
                        </div>
                        <span className={`text-xs ${done ? 'text-accent-primary' : 'text-earth-500'}`}>{step}</span>
                        {i < 2 && (
                          <div className={`flex-1 h-0.5 ${done ? 'bg-accent-primary/30' : 'bg-earth-800'}`} />
                        )}
                      </div>
                    );
                  })}
                </div>
              </GlassCard>

              {/* Actions */}
              {!selectedDoc.has_analysis && (
                <button
                  onClick={() => analyzeDoc(selectedDoc.document_id)}
                  disabled={analyzing}
                  className="btn-primary w-full px-4 py-3 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {analyzing ? <Loader2 size={16} className="animate-spin" /> : <Cpu size={16} />}
                  {analyzing ? 'Analizuję PDF...' : 'Uruchom analizę AI'}
                </button>
              )}

              {selectedDoc.has_analysis && !selectedDoc.has_estimate && (
                <button
                  onClick={() => getEstimate(selectedDoc.document_id)}
                  className="w-full px-4 py-3 bg-accent-success/15 hover:bg-accent-success/25 text-accent-success border border-accent-success/30 rounded-token font-medium flex items-center justify-center gap-2 transition-colors"
                >
                  <Calculator size={16} />
                  Generuj kosztorys z ICB
                </button>
              )}

              {/* Estimate results */}
              {estimate && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <GlassCard className="p-4">
                    <h3 className="text-earth-100 font-semibold mb-3">Kosztorys wstępny</h3>

                    {/* Summary */}
                    <div className="grid grid-cols-3 gap-3 mb-4">
                      <div className="bg-earth-900/60 rounded-token-lg p-3 text-center">
                        <div className="text-earth-500 text-xs mb-1">Minimum</div>
                        <div className="text-earth-100 font-bold text-sm">{formatPLN(estimate.total.min_pln)}</div>
                      </div>
                      <div className="bg-accent-info/10 border border-accent-info/20 rounded-token-lg p-3 text-center">
                        <div className="text-accent-info text-xs mb-1">Środek</div>
                        <div className="text-accent-info font-bold text-lg">{formatPLN(estimate.total.mid_pln)}</div>
                      </div>
                      <div className="bg-earth-900/60 rounded-token-lg p-3 text-center">
                        <div className="text-earth-500 text-xs mb-1">Maksimum</div>
                        <div className="text-earth-100 font-bold text-sm">{formatPLN(estimate.total.max_pln)}</div>
                      </div>
                    </div>

                    {/* Items */}
                    <div className="space-y-2">
                      {estimate.items.map((item, i) => (
                        <div key={i} className="flex items-center justify-between p-2 bg-earth-900/40 rounded-token">
                          <div className="flex items-center gap-2">
                            {item.icb_backed ? (
                              <CheckCircle size={12} className="text-accent-primary" />
                            ) : (
                              <AlertCircle size={12} className="text-accent-warning" />
                            )}
                            <span className="text-earth-200 text-sm">{item.category}</span>
                          </div>
                          <span className="text-earth-300 text-sm">
                            {formatPLN(item.min_pln)} – {formatPLN(item.max_pln)}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Confidence */}
                    <div className="mt-3 flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-token ${
                        estimate.total.confidence === 'medium'
                          ? 'bg-accent-warning/10 text-accent-warning'
                          : 'bg-accent-danger/10 text-accent-danger'
                      }`}>
                        Pewność: {estimate.total.confidence}
                      </span>
                    </div>

                    <p className="text-earth-600 text-xs mt-3 italic">{estimate.disclaimer}</p>
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
