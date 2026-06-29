'use client';

import { useMemo, useState } from 'react';
import { useStore } from '@/store/useStore';
import { tenders } from '@/lib/mockData';
import {
  Search,
  Filter,
  ExternalLink,
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  MapPin,
  Eye,
  Download,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import dynamic from 'next/dynamic';

export function ZwiadPage() {
  const { tenders: _storeTenders, selectedTender, setSelectedTender } = useStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  
  const filteredTenders = useMemo(() => {
    return tenders.filter((t) => {
      const matchesSearch = t.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           t.externalId.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesSource = sourceFilter === 'all' || t.source === sourceFilter;
      const matchesStatus = statusFilter === 'all' || t.status === statusFilter;
      return matchesSearch && matchesSource && matchesStatus;
    });
  }, [searchTerm, sourceFilter, statusFilter]);
  
  const getSourceBadge = (source: string) => {
    const colors: Record<string, string> = {
      BZP: 'badge-info',
      TED: 'badge-success',
      BK: 'badge-warning',
      BIP: 'badge-info',
    };
    return <span className={colors[source] || 'badge-info'}>{source}</span>;
  };
  
  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      new: 'badge-info',
      analyzing: 'badge-warning',
      ready: 'badge-success',
      accepted: 'badge-success',
      rejected: 'badge-danger',
      archived: 'badge-warning',
    };
    const labels: Record<string, string> = {
      new: 'Nowy',
      analyzing: 'W analizie',
      ready: 'Gotowy',
      accepted: 'Przyjęty',
      rejected: 'Odrzucony',
      archived: 'Archiwum',
    };
    return <span className={colors[status] || 'badge-info'}>{labels[status]}</span>;
  };
  
  const getScoreBadge = (score: number) => {
    if (score >= 80) return <span className="badge-success">{score}%</span>;
    if (score >= 60) return <span className="badge-warning">{score}%</span>;
    return <span className="badge-danger">{score}%</span>;
  };
  
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold text-earth-100">ZWIAD</h1>
          <span className="badge-info">Zwiad przetargowy</span>
        </div>
        <p className="text-earth-400">Znajdź i przeanalizuj przetargi z BZP, TED, Bazy Konkurencyjności i lokalnych BIP-ów</p>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-earth-400">Aktywne przetargi</span>
            <TrendingUp className="w-4 h-4 text-accent-success" />
          </div>
          <div className="text-2xl font-bold text-earth-100">{filteredTenders.length}</div>
        </div>
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-earth-400">Średni score</span>
            <CheckCircle className="w-4 h-4 text-accent-info" />
          </div>
          <div className="text-2xl font-bold text-earth-100">
            {filteredTenders.length > 0
              ? Math.round(filteredTenders.reduce((sum, t) => sum + t.matchScore, 0) / filteredTenders.length)
              : 0}%
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-earth-400">Wartość łącznie</span>
            <FileText className="w-4 h-4 text-accent-warning" />
          </div>
          <div className="text-2xl font-bold text-earth-100">
            {(filteredTenders.reduce((sum, t) => sum + t.estimatedValue, 0) / 1000000).toFixed(1)}M zł
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-earth-400">Czerwone flagi</span>
            <AlertTriangle className="w-4 h-4 text-accent-danger" />
          </div>
          <div className="text-2xl font-bold text-earth-100">
            {filteredTenders.reduce((sum, t) => sum + (t.redFlags?.length || 0), 0)}
          </div>
        </div>
      </div>
      
      {/* Filters */}
      <div className="card p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-400" />
              <input
                type="text"
                placeholder="Szukaj przetargów..."
                className="w-full input-field pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-earth-400" />
            <select
              className="input-field"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
            >
              <option value="all">Wszystkie źródła</option>
              <option value="BZP">BZP</option>
              <option value="TED">TED</option>
              <option value="BK">Baza Konkurencyjności</option>
              <option value="BIP">BIP</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <select
              className="input-field"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">Wszystkie statusy</option>
              <option value="new">Nowy</option>
              <option value="analyzing">W analizie</option>
              <option value="ready">Gotowy</option>
              <option value="accepted">Przyjęty</option>
              <option value="rejected">Odrzucony</option>
              <option value="archived">Archiwum</option>
            </select>
          </div>
          <button className="btn-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            Odśwież
          </button>
        </div>
      </div>
      
      {/* Tender List */}
      <div className="space-y-4">
        {filteredTenders.map((tender) => (
          <div key={tender.id} className="card-hover p-6 cursor-pointer" onClick={() => setSelectedTender(tender)}>
            <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  {getSourceBadge(tender.source)}
                  {getStatusBadge(tender.status)}
                  {getScoreBadge(tender.matchScore)}
                </div>
                <h3 className="text-lg font-semibold text-earth-100 mb-2">{tender.title}</h3>
                <div className="flex flex-wrap gap-4 text-sm text-earth-400">
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    {tender.voivodeship}
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Termin: {new Date(tender.deadline).toLocaleDateString('pl-PL')}
                  </div>
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    {tender.documents.length} dokumentów
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-earth-100">
                  {(tender.estimatedValue / 1000).toFixed(0)}k zł
                </div>
                <div className="text-xs text-earth-400">Szacowana wartość</div>
              </div>
            </div>
            
            {/* Red Flags */}
            {tender.redFlags && tender.redFlags.length > 0 && (
              <div className="mb-4 p-3 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-accent-danger" />
                  <span className="text-sm font-semibold text-accent-danger">
                    {tender.redFlags.length} czerwonych flag
                  </span>
                </div>
                {tender.redFlags.slice(0, 2).map((flag) => (
                  <div key={flag.id} className="text-xs text-earth-200 mb-1">
                    • {flag.description}
                  </div>
                ))}
              </div>
            )}
            
            {/* Actions */}
            <div className="flex flex-wrap gap-2">
              <button className="btn-primary flex items-center gap-2 text-sm">
                <Eye className="w-4 h-4" />
                Analizuj
              </button>
              <button className="btn-secondary flex items-center gap-2 text-sm">
                <Download className="w-4 h-4" />
                Pobierz dokumentację
              </button>
              <button className="btn-secondary flex items-center gap-2 text-sm">
                <ExternalLink className="w-4 h-4" />
                Otwórz w BZP
              </button>
            </div>
          </div>
        ))}
      </div>
      
      {filteredTenders.length === 0 && (
        <div className="text-center py-12">
          <p className="text-earth-400">Brak przetargów spełniających kryteria</p>
        </div>
      )}
    </div>
  );
}
