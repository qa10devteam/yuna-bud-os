'use client';

import { useState } from 'react';
import { useAuthFetch } from '@/hooks/useAuthFetch';

interface Tender {
  id: string;
  title: string;
  buyer: string;
  value_pln: number;
  match_score: number;
  deadline_at: string;
}

export default function ZwiadPage() {
  const authFetch = useAuthFetch();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await authFetch(`/api/v2/semantic-search/tenders?q=${encodeURIComponent(query)}`);
      setResults(data.results || data);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async (tenderId: string) => {
    setAnalyzingId(tenderId);
    try {
      await authFetch(`/api/v2/agent/analyze/${tenderId}`, { method: 'POST' });
      alert('Analiza rozpoczęta');
    } catch (err) {
      console.error('Analysis failed:', err);
      alert('Błąd analizy');
    } finally {
      setAnalyzingId(null);
    }
  };

  const formatPLN = (value: number) =>
    new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(value);

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: '#0A1628' }}>
      <h1 className="text-3xl font-bold text-white mb-6">🔍 Zwiad — Wyszukiwanie Przetargów</h1>

      {/* Search Bar */}
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Szukaj przetargów..."
          className="flex-1 px-4 py-3 rounded-lg text-white placeholder-gray-400 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-[#3B82F6]"
          style={{ backgroundColor: '#1E293B' }}
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-6 py-3 rounded-lg font-semibold text-white transition-colors hover:opacity-90 disabled:opacity-50"
          style={{ backgroundColor: '#3B82F6' }}
        >
          {loading ? 'Szukam...' : 'Szukaj'}
        </button>
      </div>

      {/* Results */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {results.map((tender) => (
          <div
            key={tender.id}
            className="rounded-xl p-5 border border-gray-700 hover:border-[#3B82F6] transition-colors"
            style={{ backgroundColor: '#1E293B' }}
          >
            <h3 className="text-white font-semibold text-lg mb-2 line-clamp-2">{tender.title}</h3>
            <p className="text-gray-400 text-sm mb-1">🏢 {tender.buyer}</p>
            <p className="text-gray-300 text-sm mb-1">💰 {formatPLN(tender.value_pln)}</p>
            <p className="text-gray-300 text-sm mb-1">📅 Termin: {formatDate(tender.deadline_at)}</p>
            <div className="flex items-center justify-between mt-3">
              <span
                className="text-sm font-medium px-2 py-1 rounded"
                style={{
                  backgroundColor: tender.match_score >= 0.8 ? '#065F46' : tender.match_score >= 0.5 ? '#92400E' : '#7F1D1D',
                  color: '#FFF',
                }}
              >
                Dopasowanie: {(tender.match_score * 100).toFixed(0)}%
              </span>
              <button
                onClick={() => handleAnalyze(tender.id)}
                disabled={analyzingId === tender.id}
                className="px-4 py-2 rounded-lg text-sm font-semibold text-white transition-colors hover:opacity-90 disabled:opacity-50"
                style={{ backgroundColor: '#3B82F6' }}
              >
                {analyzingId === tender.id ? 'Analizuję...' : 'Analizuj'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {results.length === 0 && !loading && (
        <p className="text-gray-500 text-center mt-12">Wpisz zapytanie i naciśnij Szukaj</p>
      )}
    </div>
  );
}
