'use client';

import { useState } from 'react';
import { FileText, ExternalLink, Search, X, Download, Loader2 } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { useStore } from '@/store/useStore';

interface DocumentViewerProps {
  pdfUrl?: string;
  tenderTitle?: string;
  tenderId?: string;
}

interface DocItem {
  id: string;
  name: string;
  filename?: string;
  type: string;
  doc_type?: string;
  size_bytes?: number;
  url?: string;
}

export function DocumentViewer({ pdfUrl, tenderTitle, tenderId }: DocumentViewerProps) {
  const { accessToken } = useStore();
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedText, setSelectedText] = useState('');
  const [menuPos, setMenuPos] = useState<{ x: number; y: number } | null>(null);
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [fetching, setFetching] = useState(false);
  const [fetched, setFetched] = useState(false);

  async function fetchDocuments() {
    if (!tenderId || !accessToken) return;
    setFetching(true);
    try {
      // First trigger document fetch from BZP
      await fetch(`/api/v1/bzp/documents/${tenderId}/fetch`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      // Wait a moment for background task to complete
      await new Promise(r => setTimeout(r, 2000));
      // Then get documents list
      const res = await fetch(`/api/v1/bzp/documents/${tenderId}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        const raw = Array.isArray(data) ? data : data.documents ?? [];
        // Map API fields to component fields
        setDocs(raw.map((d: any) => ({
          id: d.id,
          name: d.filename || d.name || 'Dokument',
          type: d.doc_type || d.type || 'PDF',
          size_bytes: d.size_bytes,
          url: d.url,
        })));
      }
    } catch {} finally {
      setFetching(false);
      setFetched(true);
    }
  }

  function handleTextSelect() {
    const sel = window.getSelection()?.toString().trim();
    if (sel && sel.length > 3) {
      const range = window.getSelection()?.getRangeAt(0);
      if (range) {
        const rect = range.getBoundingClientRect();
        setSelectedText(sel);
        setMenuPos({ x: rect.left, y: rect.top - 40 });
      }
    } else {
      setMenuPos(null);
    }
  }

  function analyzeFragment() {
    const event = new CustomEvent('terra:analyze-fragment', { detail: { text: selectedText } });
    window.dispatchEvent(event);
    setMenuPos(null);
  }

  if (!pdfUrl && !fetched) {
    return (
      <GlassCard className="p-6 text-center">
        <FileText className="w-10 h-10 text-slate-700 mx-auto mb-3" />
        <p className="text-sm text-slate-500">Brak pobranych dokumentów</p>
        <p className="text-xs text-slate-700 mt-2">Kliknij aby pobrać dokumentację przetargową (SWZ, przedmiar, specyfikacja)</p>
        <button type="button"
          onClick={fetchDocuments}
          disabled={fetching}
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-em/15 text-em border border-em/30 rounded-xl text-sm font-semibold hover:bg-em/25 transition-colors disabled:opacity-50"
        >
          {fetching ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Pobieranie z BZP...</>
          ) : (
            <><Download className="w-4 h-4" /> Pobierz dokumenty z BZP</>
          )}
        </button>
      </GlassCard>
    );
  }

  if (fetched && docs.length === 0 && !pdfUrl) {
    return (
      <GlassCard className="p-6 text-center">
        <FileText className="w-10 h-10 text-warn/50 mx-auto mb-3" />
        <p className="text-sm text-slate-400">Dokumenty nie są jeszcze dostępne w API BZP</p>
        <p className="text-xs text-slate-600 mt-1">Spróbuj ponownie później lub dodaj dokumenty ręcznie</p>
        <button type="button"
          onClick={fetchDocuments}
          disabled={fetching}
          className="mt-3 text-xs text-em hover:underline"
        >
          Ponów pobieranie
        </button>
      </GlassCard>
    );
  }

  if (docs.length > 0) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-300">{docs.length} dokumentów</h3>
          <button type="button"
            onClick={fetchDocuments}
            disabled={fetching}
            className="text-xs text-em hover:underline"
          >
            Odśwież
          </button>
        </div>
        {docs.map(doc => (
          <GlassCard key={doc.id} className="p-3 flex items-center gap-3 hover:bg-ink-800/40 transition-colors cursor-pointer">
            <FileText className="w-5 h-5 text-em shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-200 truncate">{doc.name}</p>
              <p className="text-xs text-slate-600">{doc.type}{doc.size_bytes ? ` • ${(doc.size_bytes / 1024 / 1024).toFixed(1)} MB` : ''}</p>
            </div>
            {doc.url && (
              <a href={doc.url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg hover:bg-ink-700 text-slate-500 hover:text-slate-200">
                <Download className="w-4 h-4" />
              </a>
            )}
          </GlassCard>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-300">{tenderTitle ?? 'Dokument przetargu'}</h3>
        <div className="flex items-center gap-2">
          <button type="button"
            onClick={() => setShowSearch(s => !s)}
            className="p-1.5 rounded-lg hover:bg-ink-800 text-slate-500 hover:text-slate-200 transition-colors"
            title="Szukaj w dokumencie (Ctrl+F)"
          >
            <Search className="w-4 h-4" />
          </button>
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-lg hover:bg-ink-800 text-slate-500 hover:text-slate-200 transition-colors"
            title="Otwórz PDF w nowej karcie"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {showSearch && (
        <div className="flex items-center gap-2 bg-ink-800/60 border border-ink-700/40 rounded-xl px-3 py-2">
          <Search className="w-3.5 h-3.5 text-slate-500" />
          <input
            autoFocus
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Szukaj w dokumencie..."
            className="flex-1 bg-transparent text-sm text-slate-200 placeholder-ink-600 outline-none"
          />
          <button type="button" onClick={() => { setShowSearch(false); setSearchQuery(''); }}>
            <X className="w-3.5 h-3.5 text-slate-600 hover:text-slate-300" />
          </button>
        </div>
      )}

      <div className="relative" onMouseUp={handleTextSelect}>
        <iframe
          src={pdfUrl}
          sandbox="allow-same-origin allow-scripts"
          className="w-full h-[500px] rounded-xl border border-ink-800/60 bg-white"
          title="Dokument przetargu"
        />
        {menuPos && (
          <div
            className="fixed z-50 bg-ink-800 border border-ink-700/60 rounded-lg shadow-xl px-3 py-1.5"
            style={{ left: menuPos.x, top: menuPos.y }}
          >
            <button type="button"
              onClick={analyzeFragment}
              className="text-xs text-em hover:text-em whitespace-nowrap"
            >
              🤖 Analizuj ten fragment
            </button>
          </div>
        )}
      </div>

      <p className="text-xs text-slate-700 text-center">
        Zaznacz tekst aby go przeanalizować • <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="text-em hover:underline">Kliknij aby otworzyć PDF</a>
      </p>
    </div>
  );
}
