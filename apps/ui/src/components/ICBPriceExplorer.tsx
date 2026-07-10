'use client';

import { useState, useCallback } from 'react';
import { motion } from 'motion/react';
import { Search, DollarSign, Tag, TrendingUp, ArrowUpDown } from 'lucide-react';
import { useAuthFetch } from '@/lib/api-v2';

interface ICBItem {
  symbol: string;
  nazwa: string;
  jm: string;
  cena_netto: number;
  kategoria: string | null;
  region: string | null;
  kwartal: string | null;
}

export default function ICBPriceExplorer() {
  const authFetch = useAuthFetch();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ICBItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [sortBy, setSortBy] = useState<'cena_netto' | 'nazwa'>('nazwa');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const search = useCallback(async (q?: string) => {
    const searchQ = q ?? query;
    if (!searchQ.trim()) return;
    setLoading(true);
    try {
      const data = await authFetch(
        `/api/v2/intelligence/prices/icb?q=${encodeURIComponent(searchQ)}&limit=50&sort=${sortBy}&dir=${sortDir}`
      );
      setResults(data?.items || data?.data || []);
      setTotal(data?.total || data?.items?.length || 0);
    } catch { }
    setLoading(false);
  }, [authFetch, query, sortBy, sortDir]);

  const toggleSort = (field: 'cena_netto' | 'nazwa') => {
    if (sortBy === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortDir('asc');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="bg-zinc-900/80 border border-zinc-800 rounded-xl p-4"
    >
      <div className="flex items-center gap-2 mb-4">
        <DollarSign className="w-4 h-4 text-emerald-400" />
        <h3 className="text-sm font-medium text-zinc-200">Eksplorator cen ICB</h3>
        <span className="text-xs text-zinc-500 ml-auto">784 685 pozycji</span>
      </div>

      {/* Search */}
      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Szukaj materiału, np. 'beton C25', 'kabel', 'rura PE'..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            className="w-full pl-9 pr-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-emerald-600"
          />
        </div>
        <button
          onClick={() => search()}
          disabled={loading}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg text-sm text-white font-medium transition-colors"
        >
          {loading ? '...' : 'Szukaj'}
        </button>
      </div>

      {/* Quick filters */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {['robocizna', 'beton', 'stal', 'kabel', 'rura', 'izolacja', 'farba'].map(tag => (
          <button
            key={tag}
            onClick={() => { setQuery(tag); search(tag); }}
            className="text-xs px-2 py-1 bg-zinc-800 hover:bg-zinc-700 rounded-md text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <Tag className="w-3 h-3 inline mr-1" />{tag}
          </button>
        ))}
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-zinc-500">{total} wyników</span>
            <div className="flex gap-2">
              <button
                onClick={() => toggleSort('nazwa')}
                className={`text-xs px-2 py-0.5 rounded ${sortBy === 'nazwa' ? 'bg-emerald-900/50 text-emerald-400' : 'text-zinc-500 hover:text-zinc-300'}`}
              >
                Nazwa {sortBy === 'nazwa' && (sortDir === 'asc' ? '↑' : '↓')}
              </button>
              <button
                onClick={() => toggleSort('cena_netto')}
                className={`text-xs px-2 py-0.5 rounded ${sortBy === 'cena_netto' ? 'bg-emerald-900/50 text-emerald-400' : 'text-zinc-500 hover:text-zinc-300'}`}
              >
                Cena {sortBy === 'cena_netto' && (sortDir === 'asc' ? '↑' : '↓')}
              </button>
            </div>
          </div>

          <div className="space-y-1 max-h-[400px] overflow-y-auto">
            {results.map((item, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-800/50 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-zinc-200 truncate">{item.nazwa}</p>
                  <div className="flex items-center gap-2 text-xs text-zinc-500 mt-0.5">
                    <span className="font-mono">{item.symbol}</span>
                    {item.kategoria && <span>· {item.kategoria}</span>}
                    {item.kwartal && <span>· {item.kwartal}</span>}
                  </div>
                </div>
                <div className="text-right ml-3">
                  <p className="text-sm font-medium text-emerald-400">
                    {item.cena_netto?.toFixed(2)} PLN
                  </p>
                  <p className="text-xs text-zinc-500">/{item.jm}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {results.length === 0 && !loading && query && (
        <p className="text-xs text-zinc-500 text-center py-4">Brak wyników dla "{query}"</p>
      )}
    </motion.div>
  );
}
