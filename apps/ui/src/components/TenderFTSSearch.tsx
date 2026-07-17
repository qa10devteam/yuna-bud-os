'use client';

import { useState, useCallback } from 'react';
import { motion } from 'motion/react';
import DOMPurify from 'dompurify';
import { Search, FileText, MapPin, Calendar, DollarSign } from 'lucide-react';
import { useAuthFetch } from '@/lib/api-v2';

interface FTSResult {
  id: string;
  title: string;
  description: string | null;
  buyer_name: string | null;
  province: string | null;
  value_pln: number | null;
  published_at: string | null;
  cpv_code: string | null;
  headline: string | null;
}

function fmtPLN(v: number): string {
  const n = v ?? 0;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M PLN`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k PLN`;
  return `${n.toFixed(0)} PLN`;
}

export default function TenderFTSSearch() {
  const authFetch = useAuthFetch();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<FTSResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [searched, setSearched] = useState(false);

  const search = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await authFetch(
        `/api/v2/intelligence/fts?q=${encodeURIComponent(query)}&limit=20`
      );
      setResults(data?.results || data?.items || data?.data || []);
      setTotal(data?.total || 0);
    } catch { }
    setLoading(false);
  }, [authFetch, query]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="card"
    >
      <div className="flex items-center gap-2 mb-4">
        <FileText className="w-4 h-4 text-accent-primary" />
        <h3 className="section-label">Wyszukiwarka przetargów</h3>
        <span className="text-xs text-earth-500 ml-auto">1.4M rekordów · full-text + GIN</span>
      </div>

      {/* Search */}
      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Szukaj w 1.4M przetargów: 'budowa drogi', 'remont szkoły'..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            className="input-base pl-9"
          />
        </div>
        <button
          onClick={search}
          disabled={loading}
          className="btn-primary px-4 py-2 text-sm disabled:opacity-50"
        >
          {loading ? '...' : 'Szukaj'}
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div>
          <p className="text-xs text-earth-500 mb-2">{total.toLocaleString()} wyników</p>
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {results.map((r, i) => (
              <div key={r.id || i} className="p-3 rounded-token bg-earth-800/50 hover:bg-earth-800 transition-colors">
                <p className="text-sm text-earth-100 font-medium line-clamp-2">
                  {r.headline ? (
                    <span dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(r.headline) }} />
                  ) : r.title}
                </p>
                <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-earth-500">
                  {r.buyer_name && (
                    <span className="flex items-center gap-0.5">
                      <MapPin className="w-3 h-3" />{r.buyer_name}
                    </span>
                  )}
                  {r.province && <span>{r.province}</span>}
                  {r.value_pln && (
                    <span className="text-accent-primary flex items-center gap-0.5">
                      <DollarSign className="w-3 h-3" />{fmtPLN(r.value_pln)}
                    </span>
                  )}
                  {r.published_at && (
                    <span className="flex items-center gap-0.5">
                      <Calendar className="w-3 h-3" />{r.published_at.slice(0, 10)}
                    </span>
                  )}
                  {r.cpv_code && <span className="font-mono">{r.cpv_code}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {searched && results.length === 0 && !loading && (
        <p className="text-xs text-earth-500 text-center py-4">Brak wyników</p>
      )}
    </motion.div>
  );
}
