'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Search, LayoutDashboard, Radar, GitBranch, Calculator, Settings,
  Upload, X, Bell, Bookmark, BarChart2, Users, Loader2,
  FileText, ExternalLink,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import type { ModuleName } from '@/store/useStore';

// ── Types ─────────────────────────────────────────────────────────────────────

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  action: () => void;
  group?: 'page' | 'tender' | 'document';
  href?: string;
}

interface TenderSearchResult {
  id: string;
  title: string;
  status?: string;
  cpv_code?: string;
  value_pln?: number | null;
  source?: string;
}

interface CommandMenuProps {
  open: boolean;
  onClose: () => void;
}

// ── Static page nav items ─────────────────────────────────────────────────────

const PAGE_ITEMS = (navigate: (m: ModuleName) => void): CommandItem[] => [
  { id: 'dashboard', label: 'Dashboard', description: 'Panel główny', icon: <LayoutDashboard className="w-4 h-4" />, action: () => navigate('dashboard'), group: 'page' },
  { id: 'zwiad',     label: 'Zwiad przetargowy', description: 'Lista przetargów z BZP/TED/BIP', icon: <Radar className="w-4 h-4" />, action: () => navigate('zwiad'), group: 'page' },
  { id: 'pipeline',  label: 'Pipeline / Kanban', description: 'Tablica statusów przetargów', icon: <GitBranch className="w-4 h-4" />, action: () => navigate('pipeline'), group: 'page' },
  { id: 'bookmarks', label: 'Zakładki', description: 'Obserwowane przetargi', icon: <Bookmark className="w-4 h-4" />, action: () => navigate('bookmarks'), group: 'page' },
  { id: 'alerts',    label: 'Alerty', description: 'Konfiguracja alertów', icon: <Bell className="w-4 h-4" />, action: () => navigate('alerts'), group: 'page' },
  { id: 'notifications', label: 'Powiadomienia', description: 'Centrum powiadomień', icon: <Bell className="w-4 h-4" />, action: () => navigate('notifications'), group: 'page' },
  { id: 'analytics', label: 'Analityka', description: 'Wykresy i statystyki', icon: <BarChart2 className="w-4 h-4" />, action: () => navigate('analytics'), group: 'page' },
  { id: 'kosztorys', label: 'Kosztorys', description: 'Wycena i kosztorysy', icon: <Calculator className="w-4 h-4" />, action: () => navigate('kosztorys'), group: 'page' },
  { id: 'team',      label: 'Zespół', description: 'Zarządzanie zespołem', icon: <Users className="w-4 h-4" />, action: () => navigate('team'), group: 'page' },
  { id: 'settings',  label: 'Ustawienia', description: 'Profil, billing, API', icon: <Settings className="w-4 h-4" />, action: () => navigate('settings'), group: 'page' },
  { id: 'import',    label: 'Import danych', description: 'Importuj dane CSV', icon: <Upload className="w-4 h-4" />, action: () => navigate('system'), group: 'page' },
];

function fmtMln(v: number | null | undefined): string {
  if (!v) return '';
  return v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)} mln zł` : `${Math.round(v / 1000)} tys. zł`;
}

// ── CommandMenu ───────────────────────────────────────────────────────────────

export function CommandMenu({ open, onClose }: CommandMenuProps) {
  const { setCurrentModule, accessToken } = useStore();
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const [apiResults, setApiResults] = useState<TenderSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function navigate(module: ModuleName) {
    setCurrentModule(module);
    onClose();
  }

  // ── Debounced API search ───────────────────────────────────────────────────

  const searchAPI = useCallback(async (q: string) => {
    if (!q.trim() || !accessToken) { setApiResults([]); return; }
    setSearching(true);
    try {
      const res = await fetch(`/api/v2/search?q=${encodeURIComponent(q)}&limit=8&type=tenders`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) { setApiResults([]); return; }
      const data = await res.json() as { tenders?: TenderSearchResult[]; results?: TenderSearchResult[]; items?: TenderSearchResult[] } | TenderSearchResult[];
      const items = Array.isArray(data) ? data : (data?.tenders ?? data?.results ?? data?.items ?? []);
      setApiResults(items.slice(0, 8));
    } catch {
      setApiResults([]);
    } finally {
      setSearching(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (!open) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.length >= 2) {
      debounceRef.current = setTimeout(() => searchAPI(query), 400);
    } else {
      setApiResults([]);
    }
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, open, searchAPI]);

  // ── Build combined item list ───────────────────────────────────────────────

  const pageItems = PAGE_ITEMS(navigate);
  const filteredPages = query
    ? pageItems.filter(i => i.label.toLowerCase().includes(query.toLowerCase()) || i.description?.toLowerCase().includes(query.toLowerCase()))
    : pageItems;

  const tenderItems: CommandItem[] = apiResults.map(t => ({
    id: `tender:${t.id}`,
    label: t.title,
    description: [t.cpv_code, t.status, fmtMln(t.value_pln), t.source].filter(Boolean).join(' · '),
    icon: <FileText className="w-4 h-4" />,
    action: () => { setCurrentModule('zwiad'); onClose(); },
    group: 'tender' as const,
  }));

  const allItems: CommandItem[] = [...tenderItems, ...filteredPages];

  // Reset selection on results change
  useEffect(() => { setSelected(0); }, [query, apiResults]);

  // Focus on open
  useEffect(() => {
    if (open) {
      setQuery('');
      setApiResults([]);
      setSelected(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose(); return; }
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(s => Math.min(s + 1, allItems.length - 1)); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)); return; }
      if (e.key === 'Enter') { e.preventDefault(); allItems[selected]?.action(); return; }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, allItems, selected, onClose]);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] px-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-earth-950/70 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
            className="relative w-full max-w-lg bg-earth-900 border border-earth-700/60 rounded-2xl shadow-2xl shadow-black/60 overflow-hidden"
          >
            {/* Search input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-earth-800/60">
              {searching
                ? <Loader2 className="w-4 h-4 text-accent-primary shrink-0 animate-spin" />
                : <Search className="w-4 h-4 text-earth-500 shrink-0" />
              }
              <input
                ref={inputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Szukaj modułu, przetargu lub akcji… (⌘K)"
                className="flex-1 bg-transparent text-earth-100 placeholder-earth-600 text-sm outline-none"
              />
              {query && (
                <button onClick={() => setQuery('')} className="text-earth-600 hover:text-earth-300 transition-colors">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
              <button onClick={onClose} className="text-earth-600 hover:text-earth-300 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Results */}
            <div className="py-2 max-h-96 overflow-y-auto">
              {/* Tender results section */}
              {tenderItems.length > 0 && (
                <>
                  <div className="px-4 py-1.5 text-[10px] font-semibold text-earth-600 uppercase tracking-wider">Przetargi</div>
                  {tenderItems.map((item, idx) => (
                    <button
                      key={item.id}
                      onClick={item.action}
                      onMouseEnter={() => setSelected(idx)}
                      className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${idx === selected ? 'bg-accent-primary/10 text-accent-primary' : 'text-earth-300 hover:bg-earth-800/60'}`}
                    >
                      <span className={idx === selected ? 'text-accent-primary' : 'text-earth-500'}>{item.icon}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{item.label}</p>
                        {item.description && <p className="text-xs text-earth-600 truncate">{item.description}</p>}
                      </div>
                      <ExternalLink className="w-3 h-3 text-earth-700 shrink-0" />
                    </button>
                  ))}
                </>
              )}

              {/* Page / module navigation */}
              {filteredPages.length > 0 && (
                <>
                  {(tenderItems.length > 0 || query) && (
                    <div className="px-4 py-1.5 text-[10px] font-semibold text-earth-600 uppercase tracking-wider mt-1">
                      {query ? 'Strony' : 'Nawigacja'}
                    </div>
                  )}
                  {filteredPages.map((item, i) => {
                    const idx = tenderItems.length + i;
                    return (
                      <button
                        key={item.id}
                        onClick={item.action}
                        onMouseEnter={() => setSelected(idx)}
                        className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${idx === selected ? 'bg-accent-primary/10 text-accent-primary' : 'text-earth-300 hover:bg-earth-800/60'}`}
                      >
                        <span className={idx === selected ? 'text-accent-primary' : 'text-earth-500'}>{item.icon}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium">{item.label}</p>
                          {item.description && <p className="text-xs text-earth-600">{item.description}</p>}
                        </div>
                      </button>
                    );
                  })}
                </>
              )}

              {/* Empty */}
              {allItems.length === 0 && !searching && (
                <p className="px-4 py-6 text-center text-earth-600 text-sm">
                  Brak wyników dla &ldquo;{query}&rdquo;
                </p>
              )}
              {searching && apiResults.length === 0 && (
                <p className="px-4 py-4 text-center text-earth-600 text-sm flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" /> Szukam…
                </p>
              )}
            </div>

            {/* Footer hint */}
            <div className="px-4 py-2 border-t border-earth-800/60 flex items-center gap-3 text-xs text-earth-700">
              <span>↑↓ nawigacja</span>
              <span>↵ wybierz</span>
              <span>Esc zamknij</span>
              {query.length >= 2 && <span className="ml-auto text-earth-800">szukam w API…</span>}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
