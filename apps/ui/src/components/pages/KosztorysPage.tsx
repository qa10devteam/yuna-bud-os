'use client';

import { useState } from 'react';
import { useStore } from '@/store/useStore';
import { estimateA, estimateB } from '@/lib/mockData';
import {
  Calculator,
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Upload,
  Download,
  Edit3,
  TrendingUp,
  TrendingDown,
  Info,
} from 'lucide-react';
import dynamic from 'next/dynamic';

interface PieSegment {
  name: string;
  value: number;
  color: string;
  percent: number;
  cumulative: number;
}

function PieChart({ data, label }: { data: { name: string; value: number; color: string }[]; label: string }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const [hovered, setHovered] = useState<number | null>(null);
  
  const segments: PieSegment[] = data.reduce((acc, d, i) => {
    const percent = d.value / total;
    acc.push({
      ...d,
      percent,
      cumulative: acc.length > 0 ? acc[acc.length - 1].cumulative + acc[acc.length - 1].percent : 0,
    });
    return acc;
  }, [] as PieSegment[]);
  
  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-earth-100 mb-4">{label}</h3>
      <div className="flex items-center gap-6">
        <div className="relative w-32 h-32 flex-shrink-0">
          <svg viewBox="0 0 32 32" className="w-full h-full -rotate-90">
            {segments.map((seg, i) => (
              <circle
                key={i}
                cx="16"
                cy="16"
                r="12"
                fill="transparent"
                stroke={seg.color}
                strokeWidth="8"
                strokeDasharray={`${seg.percent * 75.4} 75.4`}
                strokeDashoffset={-seg.cumulative * 75.4}
                className="transition-all duration-200"
                opacity={hovered === i ? 1 : 0.7}
              />
            ))}
          </svg>
        </div>
        <div className="flex-1 space-y-2">
          {segments.map((seg, i) => (
            <div
              key={i}
              className="flex items-center justify-between cursor-pointer"
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: seg.color }} />
                <span className="text-sm text-earth-200">{seg.name}</span>
              </div>
              <span className="text-sm font-semibold text-earth-100">
                {((seg.percent * 100)).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function KosztorysPage() {
  const { selectedTender } = useStore();
  const [activeTab, setActiveTab] = useState<'A' | 'B' | 'compare'>('compare');
  
  const delta = estimateB.totals.gross - estimateA.totals.gross;
  const deltaPercent = ((delta / estimateA.totals.gross) * 100).toFixed(1);
  
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold text-earth-100">KOSZTORYS</h1>
          <span className="badge-info">Kosztorys w 2 wariantach</span>
        </div>
        <p className="text-earth-400">
          Porównanie kosztorysu z dokumentacji (Variant A) vs. kosztorys Pana stawkami (Variant B)
        </p>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="card p-4">
          <div className="text-sm text-earth-400 mb-1">Wariant A (dokumentacja)</div>
          <div className="text-2xl font-bold text-earth-100">{(estimateA.totals.gross / 1000).toFixed(0)}k zł</div>
          <div className="text-xs text-earth-400">Netto: {(estimateA.totals.net / 1000).toFixed(0)}k zł</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-earth-400 mb-1">Wariant B (Pan)</div>
          <div className="text-2xl font-bold text-earth-100">{(estimateB.totals.gross / 1000).toFixed(0)}k zł</div>
          <div className="text-xs text-earth-400">Netto: {(estimateB.totals.net / 1000).toFixed(0)}k zł</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-earth-400 mb-1">Różnica</div>
          <div className="text-2xl font-bold text-accent-danger">+{deltaPercent}%</div>
          <div className="text-xs text-earth-400">
            +{(delta / 1000).toFixed(0)}k zł
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-earth-400 mb-1">Marża szacowana</div>
          <div className="text-2xl font-bold text-accent-success">18%</div>
          <div className="text-xs text-earth-400">Na wariantach</div>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'compare' ? 'bg-accent-success text-earth-950' : 'bg-earth-800 text-earth-300 hover:bg-earth-700'
          }`}
          onClick={() => setActiveTab('compare')}
        >
          Porównanie
        </button>
        <button
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'A' ? 'bg-accent-info text-earth-950' : 'bg-earth-800 text-earth-300 hover:bg-earth-700'
          }`}
          onClick={() => setActiveTab('A')}
        >
          Wariant A - z dokumentacji
        </button>
        <button
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'B' ? 'bg-accent-warning text-earth-950' : 'bg-earth-800 text-earth-300 hover:bg-earth-700'
          }`}
          onClick={() => setActiveTab('B')}
        >
          Wariant B - Pan
        </button>
      </div>
      
      {/* Compare View */}
      {activeTab === 'compare' && (
        <div className="space-y-6">
          {/* Delta Alert */}
          <div className="p-4 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <AlertTriangle className="w-5 h-5 text-accent-danger" />
              <h3 className="font-semibold text-accent-danger">Krytyczna różnica między wariantami</h3>
            </div>
            <p className="text-sm text-earth-200">
              Wariant B (Pan) jest droższy o {deltaPercent}% (+{(delta / 1000).toFixed(0)}k zł) niż wariant A z dokumentacji.
              To oznacza, że Pana rzeczywiste koszty są wyższe niż szacowane w przedmiarze.
              <span className="block mt-2 font-medium">
                Rekomendacja: Skoryguj ofertę lub negocjuj przedmiar.
              </span>
            </p>
          </div>
          
          {/* Charts */}
          <div className="grid grid-cols-2 gap-6">
            <PieChart
              data={[
                { name: 'Robocizna', value: estimateA.totals.labor, color: '#22C55E' },
                { name: 'Sprzęt', value: estimateA.totals.equipment, color: '#3B82F6' },
                { name: 'Materiały', value: estimateA.totals.materials, color: '#F59E0B' },
                { name: 'Nakład', value: estimateA.totals.overhead, color: '#8B5CF6' },
              ]}
              label="Wariant A — Struktura kosztów"
            />
            <PieChart
              data={[
                { name: 'Robocizna', value: estimateB.totals.labor, color: '#22C55E' },
                { name: 'Sprzęt', value: estimateB.totals.equipment, color: '#3B82F6' },
                { name: 'Materiały', value: estimateB.totals.materials, color: '#F59E0B' },
                { name: 'Nakład', value: estimateB.totals.overhead, color: '#8B5CF6' },
              ]}
              label="Wariant B — Struktura kosztów"
            />
          </div>
          
          {/* Comparison Table */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-earth-100 mb-4">Porównanie pozycji</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="table-header">Pozycja</th>
                    <th className="table-header">Jedn.</th>
                    <th className="table-header text-accent-info">A - Ilość</th>
                    <th className="table-header text-accent-info">A - Cena</th>
                    <th className="table-header text-accent-warning">B - Ilość</th>
                    <th className="table-header text-accent-warning">B - Cena</th>
                    <th className="table-header">Różnica</th>
                  </tr>
                </thead>
                <tbody>
                  {estimateA.lines.map((lineA, i) => {
                    const lineB = estimateB.lines[i];
                    if (!lineB) return null;
                    const diff = lineB.totalPrice - lineA.totalPrice;
                    return (
                      <tr key={lineA.id}>
                        <td className="table-cell font-medium text-earth-100">{lineA.description}</td>
                        <td className="table-cell text-earth-300">{lineA.unit}</td>
                        <td className="table-cell text-accent-info">{lineA.quantity.toLocaleString('pl-PL')}</td>
                        <td className="table-cell text-accent-info">{lineA.unitPrice.toFixed(2)} zł</td>
                        <td className="table-cell text-accent-warning">{lineB.quantity.toLocaleString('pl-PL')}</td>
                        <td className="table-cell text-accent-warning">{lineB.unitPrice.toFixed(2)} zł</td>
                        <td className={`table-cell ${diff > 0 ? 'text-accent-danger' : 'text-accent-success'}`}>
                          {diff > 0 ? '+' : ''}{diff.toLocaleString('pl-PL')} zł
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
      
      {/* Variant A View */}
      {activeTab === 'A' && (
        <div className="space-y-6">
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-earth-100 mb-4">Wariant A — z dokumentacji</h3>
            <div className="text-sm text-earth-400 mb-4">
              Kalkulacja uproszczona zgodna z Rozp. MRiT z 20.12.2021, oparta o przedmiar i ceny rynkowe (KNR).
              Tak liczy zamawiający.
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="table-header">Pozycja</th>
                    <th className="table-header">Opis</th>
                    <th className="table-header">Jedn.</th>
                    <th className="table-header">Ilość</th>
                    <th className="table-header">Cena jedn.</th>
                    <th className="table-header text-right">Wartość</th>
                  </tr>
                </thead>
                <tbody>
                  {estimateA.lines.map((line) => (
                    <tr key={line.id}>
                      <td className="table-cell text-accent-info font-mono">{line.position}</td>
                      <td className="table-cell text-earth-200">{line.description}</td>
                      <td className="table-cell text-earth-300">{line.unit}</td>
                      <td className="table-cell text-earth-200">{line.quantity.toLocaleString('pl-PL')}</td>
                      <td className="table-cell text-earth-200">{line.unitPrice.toFixed(2)} zł</td>
                      <td className="table-cell text-earth-100 font-semibold text-right">
                        {line.totalPrice.toLocaleString('pl-PL')} zł
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 p-4 bg-earth-800 rounded-lg">
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-sm text-earth-400">Netto</div>
                  <div className="text-lg font-bold text-earth-100">{estimateA.totals.net.toLocaleString('pl-PL')} zł</div>
                </div>
                <div>
                  <div className="text-sm text-earth-400">VAT 23%</div>
                  <div className="text-lg font-bold text-earth-100">{estimateA.totals.vat.toLocaleString('pl-PL')} zł</div>
                </div>
                <div>
                  <div className="text-sm text-earth-400">Brutto</div>
                  <div className="text-lg font-bold text-accent-success">{estimateA.totals.gross.toLocaleString('pl-PL')} zł</div>
                </div>
                <div>
                  <div className="text-sm text-earth-400">Marża</div>
                  <div className="text-lg font-bold text-accent-warning">18%</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Variant B View */}
      {activeTab === 'B' && (
        <div className="space-y-6">
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-earth-100 mb-4">Wariant B — Pana stawkami</h3>
            <div className="text-sm text-earth-400 mb-4">
              Oparty na Pana własnym arkuszu Excel: realne ceny materiałów, robocizny, wydajności brygad.
              Tak naprawdę wygląda Pana koszt.
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="table-header">Pozycja</th>
                    <th className="table-header">Opis</th>
                    <th className="table-header">Jedn.</th>
                    <th className="table-header">Ilość</th>
                    <th className="table-header">Cena jedn.</th>
                    <th className="table-header text-right">Wartość</th>
                  </tr>
                </thead>
                <tbody>
                  {estimateB.lines.map((line) => (
                    <tr key={line.id}>
                      <td className="table-cell text-accent-warning font-mono">{line.position}</td>
                      <td className="table-cell text-earth-200">{line.description}</td>
                      <td className="table-cell text-earth-300">{line.unit}</td>
                      <td className="table-cell text-earth-200">{line.quantity.toLocaleString('pl-PL')}</td>
                      <td className="table-cell text-earth-200">{line.unitPrice.toFixed(2)} zł</td>
                      <td className="table-cell text-earth-100 font-semibold text-right">
                        {line.totalPrice.toLocaleString('pl-PL')} zł
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 p-4 bg-earth-800 rounded-lg">
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-sm text-earth-400">Netto</div>
                  <div className="text-lg font-bold text-earth-100">{estimateB.totals.net.toLocaleString('pl-PL')} zł</div>
                </div>
                <div>
                  <div className="text-sm text-earth-400">VAT 23%</div>
                  <div className="text-lg font-bold text-earth-100">{estimateB.totals.vat.toLocaleString('pl-PL')} zł</div>
                </div>
                <div>
                  <div className="text-sm text-earth-400">Brutto</div>
                  <div className="text-lg font-bold text-accent-danger">{estimateB.totals.gross.toLocaleString('pl-PL')} zł</div>
                </div>
                <div>
                  <div className="text-sm text-earth-400">Marża</div>
                  <div className="text-lg font-bold text-accent-warning">5%</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
