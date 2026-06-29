'use client';

import { decisions } from '@/lib/mockData';
import {
  ClipboardCheck,
  Check,
  X,
  MessageSquare,
  TrendingUp,
  AlertTriangle,
  Brain,
  FileText,
  Download,
  Share2,
  ArrowRight,
} from 'lucide-react';
import dynamic from 'next/dynamic';

export function DecyzjaPage() {
  const decision = decisions['tender-1'];
  
  const getRecommendationBadge = (rec: string) => {
    switch (rec) {
      case 'offer':
        return <span className="badge-success">Złóż ofertę</span>;
      case 'reject':
        return <span className="badge-danger">Odrzuć</span>;
      case 'negotiate':
        return <span className="badge-warning">Negocjuj</span>;
      default:
        return <span className="badge-info">Analityzuj</span>;
    }
  };
  
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-accent-success';
    if (confidence >= 0.6) return 'text-accent-warning';
    return 'text-accent-danger';
  };
  
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold text-earth-100">DECYZJA</h1>
          <span className="badge-info">Rekomendacje decyzji</span>
        </div>
        <p className="text-earth-400">
          Systemowe rekomendacje na podstawie analizy silnika — startuj lub odpuść
        </p>
      </div>
      
      {/* Main Decision Card */}
      <div className="card p-6 mb-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-earth-100 mb-2">Budowa drogi gminnej nr 1234B</h2>
            <div className="flex flex-wrap gap-4 text-sm text-earth-400">
              <span>BZP-2026-001</span>
              <span>dolnośląskie</span>
              <span>2 850 000 zł</span>
            </div>
          </div>
          <div className="text-right">
            {getRecommendationBadge(decision.recommendation)}
            <div className={`text-sm mt-2 ${getConfidenceColor(decision.confidence)}`}>
              Pewność: {(decision.confidence * 100).toFixed(0)}%
            </div>
          </div>
        </div>
        
        {/* Key Factors */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-earth-100 mb-3 flex items-center gap-2">
            <Brain className="w-5 h-5 text-accent-violet" />
            Kluczowe czynniki
          </h3>
          <div className="space-y-2">
            {decision.keyFactors.map((factor, i) => (
              <div key={i} className="flex items-start gap-2 p-3 bg-earth-800 rounded-lg">
                <AlertTriangle className="w-4 h-4 text-accent-warning mt-1 flex-shrink-0" />
                <span className="text-earth-200 text-sm">{factor}</span>
              </div>
            ))}
          </div>
        </div>
        
        {/* Reasoning */}
        <div className="mb-6 p-4 bg-earth-800 rounded-lg">
          <h3 className="text-lg font-semibold text-earth-100 mb-2 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-accent-info" />
            Uzasadnienie
          </h3>
          <p className="text-earth-200">{decision.reasoning}</p>
        </div>
        
        {/* Actions */}
        <div className="flex flex-wrap gap-3">
          <button className="btn-primary flex items-center gap-2">
            <Check className="w-4 h-4" />
            Akceptuj rekomendację
          </button>
          <button className="btn-danger flex items-center gap-2">
            <X className="w-4 h-4" />
            Odrzuć
          </button>
          <button className="btn-secondary flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            Dopytaj o szczegóły
          </button>
          <button className="btn-secondary flex items-center gap-2">
            <Download className="w-4 h-4" />
            Eksportuj raport
          </button>
        </div>
      </div>
      
      {/* Alternative Scenarios */}
      <div className="card p-6 mb-6">
        <h3 className="text-lg font-semibold text-earth-100 mb-4">Alternatywne warianty</h3>
        <div className="space-y-4">
          <div className="p-4 bg-earth-800 rounded-lg border border-earth-700">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-earth-100">Wariant 1 — Zgłoś rozbieżność</h4>
              <span className="badge-success">+15% szans</span>
            </div>
            <p className="text-sm text-earth-400 mb-3">
              Zgłoś rozbieżność między przedmiarem a projektem. Oczekuj korekty przedmiaru przed złożeniem oferty.
            </p>
            <div className="flex items-center gap-4 text-sm">
              <span className="text-earth-300">Szansa na wygraną: 45%</span>
              <span className="text-earth-300">Marża szacowana: 22%</span>
            </div>
          </div>
          
          <div className="p-4 bg-earth-800 rounded-lg border border-earth-700">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-earth-100">Wariant 2 — Korekta kosztorysu</h4>
              <span className="badge-warning">+8% szans</span>
            </div>
            <p className="text-sm text-earth-400 mb-3">
              Skoryguj kosztorys o dodatkowe pozycje (odwódrenie, dodatkowy wykop). Złóż ofertę z wyższą ceną.
            </p>
            <div className="flex items-center gap-4 text-sm">
              <span className="text-earth-300">Szansa na wygraną: 35%</span>
              <span className="text-earth-300">Marża szacowana: 8%</span>
            </div>
          </div>
          
          <div className="p-4 bg-earth-800 rounded-lg border border-earth-700">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-earth-100">Wariant 3 — Odrzuć</h4>
              <span className="badge-danger">-20% szans</span>
            </div>
            <p className="text-sm text-earth-400 mb-3">
              Obecne założenia generują zbyt wysokie ryzyko. Odrzuć przetarg i czekaj na lepsze możliwości.
            </p>
            <div className="flex items-center gap-4 text-sm">
              <span className="text-earth-300">Szansa na wygraną: 0%</span>
              <span className="text-earth-300">Zmarnowany czas analizy</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Second Decision */}
      <div className="card p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-earth-100 mb-2">Przebudowa placu zabaw</h2>
            <div className="flex flex-wrap gap-4 text-sm text-earth-400">
              <span>BZP-2026-002</span>
              <span>485 000 zł</span>
            </div>
          </div>
          <div className="text-right">
            {getRecommendationBadge(decisions['tender-2'].recommendation)}
            <div className={`text-sm mt-2 ${getConfidenceColor(decisions['tender-2'].confidence)}`}>
              Pewność: {(decisions['tender-2'].confidence * 100).toFixed(0)}%
            </div>
          </div>
        </div>
        
        <p className="text-earth-200 text-sm mb-4">{decisions['tender-2'].reasoning}</p>
        
        <div className="flex flex-wrap gap-3">
          <button className="btn-primary flex items-center gap-2 text-sm">
            <Check className="w-4 h-4" />
            Złóż ofertę
          </button>
          <button className="btn-secondary flex items-center gap-2 text-sm">
            <Download className="w-4 h-4" />
            Eksportuj
          </button>
        </div>
      </div>
    </div>
  );
}
