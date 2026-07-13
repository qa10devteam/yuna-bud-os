'use client';

import { useState, useEffect, DragEvent } from 'react';
import { useAuthFetch } from '@/hooks/useAuthFetch';

type Status = 'new' | 'qualifying' | 'bid_prep' | 'submitted' | 'won' | 'lost';

interface Tender {
  id: string;
  title: string;
  value_pln: number;
  deadline_at: string;
  match_score: number;
  status: Status;
}

const COLUMNS: { key: Status; label: string; color: string }[] = [
  { key: 'new', label: 'Nowe', color: '#6B7280' },
  { key: 'qualifying', label: 'Kwalifikacja', color: '#8B5CF6' },
  { key: 'bid_prep', label: 'Przygotowanie oferty', color: '#F59E0B' },
  { key: 'submitted', label: 'Złożone', color: '#3B82F6' },
  { key: 'won', label: 'Wygrane', color: '#10B981' },
  { key: 'lost', label: 'Przegrane', color: '#EF4444' },
];

export default function PipelinePage() {
  const authFetch = useAuthFetch();
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(true);
  const [draggedId, setDraggedId] = useState<string | null>(null);

  useEffect(() => {
    fetchTenders();
  }, []);

  const fetchTenders = async () => {
    try {
      const data = await authFetch('/api/v2/tenders');
      setTenders(data.results || data);
    } catch (err) {
      console.error('Failed to fetch tenders:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDragStart = (e: DragEvent, tenderId: string) => {
    setDraggedId(tenderId);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', tenderId);
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e: DragEvent, newStatus: Status) => {
    e.preventDefault();
    const tenderId = e.dataTransfer.getData('text/plain') || draggedId;
    if (!tenderId) return;

    const tender = tenders.find((t) => t.id === tenderId);
    if (!tender || tender.status === newStatus) {
      setDraggedId(null);
      return;
    }

    // Optimistic update
    setTenders((prev) =>
      prev.map((t) => (t.id === tenderId ? { ...t, status: newStatus } : t))
    );
    setDraggedId(null);

    try {
      await authFetch(`/api/v2/tenders/${tenderId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
    } catch (err) {
      console.error('Failed to update status:', err);
      // Revert on failure
      setTenders((prev) =>
        prev.map((t) => (t.id === tenderId ? { ...t, status: tender.status } : t))
      );
    }
  };

  const formatPLN = (value: number) =>
    new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(value);

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });

  const getTendersByStatus = (status: Status) => tenders.filter((t) => t.status === status);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#0A1628' }}>
        <p className="text-white text-xl">Ładowanie pipeline...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: '#0A1628' }}>
      <h1 className="text-3xl font-bold text-white mb-6">📊 Pipeline Przetargów</h1>

      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((col) => (
          <div
            key={col.key}
            className="flex-shrink-0 w-72 rounded-xl p-4"
            style={{ backgroundColor: '#1E293B' }}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, col.key)}
          >
            {/* Column Header */}
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: col.color }} />
              <h2 className="text-white font-semibold">{col.label}</h2>
              <span className="ml-auto text-gray-400 text-sm">
                {getTendersByStatus(col.key).length}
              </span>
            </div>

            {/* Cards */}
            <div className="space-y-3 min-h-[200px]">
              {getTendersByStatus(col.key).map((tender) => (
                <div
                  key={tender.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, tender.id)}
                  className={`rounded-lg p-3 border border-gray-600 cursor-grab active:cursor-grabbing hover:border-[#3B82F6] transition-all ${
                    draggedId === tender.id ? 'opacity-50' : ''
                  }`}
                  style={{ backgroundColor: '#0A1628' }}
                >
                  <h3 className="text-white text-sm font-medium line-clamp-2 mb-2">
                    {tender.title}
                  </h3>
                  <p className="text-gray-300 text-xs">💰 {formatPLN(tender.value_pln)}</p>
                  <p className="text-gray-300 text-xs">📅 {formatDate(tender.deadline_at)}</p>
                  <div className="mt-2">
                    <span
                      className="text-xs px-2 py-0.5 rounded"
                      style={{
                        backgroundColor:
                          tender.match_score >= 0.8
                            ? '#065F46'
                            : tender.match_score >= 0.5
                            ? '#92400E'
                            : '#7F1D1D',
                        color: '#FFF',
                      }}
                    >
                      {(tender.match_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
