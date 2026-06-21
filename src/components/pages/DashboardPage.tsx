'use client';

import { Map, CheckCircle, AlertTriangle, ArrowUpRight } from 'lucide-react';
import { useStore } from '@/store/useStore';
import dynamic from 'next/dynamic';

// Dynamic import to avoid SSR issues with motion
const MotionDiv = dynamic(() => import('motion/react').then((m) => m.motion.div), { ssr: false });

export function DashboardPage() {
  const { tenders } = useStore();
  const totalValue = tenders.reduce((sum, t) => sum + t.value, 0);
  const totalRedFlags = tenders.reduce((sum, t) => sum + t.redFlags.length, 0);
  const avgRisk = tenders.reduce((sum, t) => sum + (t.redFlags.length * 10), 0) / tenders.length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#00FF94]/20 flex items-center justify-center">
            <Map className="w-6 h-6 text-[#00FF94]" />
          </div>
          <div>
            <h1 className="text-3xl font-display font-bold text-[#F4F4F0]">ZWIAD</h1>
            <p className="text-neutral-400">Moduł 1: Szukanie przetargów i analiza rynku</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn-primary text-sm">
            Nowy przetarg
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <MotionDiv
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-neutral-400 text-sm">Łączna wartość</span>
            <div className="p-2 rounded-lg bg-[#00FF94]/20 text-[#00FF94]">
              <ArrowUpRight className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-mono font-bold text-[#F4F4F0]">
            {totalValue.toLocaleString('pl-PL')} zł
          </div>
          <div className="text-sm text-[#00FF94] mt-1">+12% vs zeszły miesiąc</div>
        </MotionDiv>

        <MotionDiv
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-neutral-400 text-sm">Ryzyka wykryte</span>
            <div className="p-2 rounded-lg bg-[#FF3300]/20 text-[#FF3300]">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-mono font-bold text-[#F4F4F0]">{totalRedFlags}</div>
          <div className="text-sm text-[#FF3300] mt-1">-3 vs wczoraj</div>
        </MotionDiv>

        <MotionDiv
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-neutral-400 text-sm">Średnie ryzyko</span>
            <div className="p-2 rounded-lg bg-[#3B82F6]/20 text-[#3B82F6]">
              <CheckCircle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-mono font-bold text-[#F4F4F0]">{avgRisk.toFixed(0)}%</div>
          <div className="text-sm text-[#3B82F6] mt-1">-5% vs plan</div>
        </MotionDiv>
      </div>

      {/* Tender List */}
      <MotionDiv
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="card"
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-display font-bold text-lg flex items-center gap-2">
            <Map className="w-5 h-5 text-[#00FF94]" />
            Ostatnie przetargi
          </h3>
          <span className="badge-success">{tenders.length} aktywnych</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="text-left text-sm text-neutral-400">
              <tr>
                <th className="pb-4 font-display">Przetarg</th>
                <th className="pb-4 font-display">Wartość</th>
                <th className="pb-4 font-display">Lokalizacja</th>
                <th className="pb-4 font-display">Termin</th>
                <th className="pb-4 font-display">Źródło</th>
                <th className="pb-4 font-display">Ryzyka</th>
                <th className="pb-4 font-display">Akcja</th>
              </tr>
            </thead>
            <tbody>
              {tenders.map((tender) => (
                <tr key={tender.id} className="border-t border-[#3D3D3C] hover:bg-[#1A1A1A] transition-colors">
                  <td className="py-4 font-display">{tender.title}</td>
                  <td className="py-4 font-mono">{tender.value.toLocaleString('pl-PL')} zł</td>
                  <td className="py-4">{tender.location}</td>
                  <td className="py-4 font-mono">{new Date(tender.deadline).toLocaleDateString('pl-PL')}</td>
                  <td className="py-4">
                    <span className="badge-tech">{tender.source}</span>
                  </td>
                  <td className="py-4">
                    {tender.redFlags.length > 0 ? (
                      <span className="badge-warning">{tender.redFlags.length} flagi</span>
                    ) : (
                      <span className="text-neutral-400">Brak</span>
                    )}
                  </td>
                  <td className="py-4">
                    <button className="btn-primary text-sm px-4 py-2">
                      ANALIZUJ
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </MotionDiv>
    </div>
  );
}
