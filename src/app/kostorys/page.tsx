'use client';

import { Sidebar } from '@/components/Sidebar';
import { Calculator, ArrowDown, ArrowUp, FileText } from 'lucide-react';
import dynamic from 'next/dynamic';
import { costItems } from '@/lib/mockData';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';

// Dynamic import to avoid SSR issues with motion
const MotionDiv = dynamic(() => import('motion/react').then((m) => m.motion.div), { ssr: false });

const costComparison = costItems.map((item) => ({
  name: item.item,
  doc: item.docCost,
  your: item.yourCost,
}));

// RechartsChart component wrapper
function RechartsChart() {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={costComparison}>
        <XAxis dataKey="name" stroke="#6B6B68" fontSize={12} tick={{ fill: '#6B6B68' }} />
        <YAxis stroke="#6B6B68" fontSize={12} tick={{ fill: '#6B6B68' }} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1A1A1A',
            border: '1px solid #3D3D3C',
            borderRadius: '8px',
          }}
        />
        <Legend />
        <Bar dataKey="doc" fill="#6B6B68" name="Koszt dokumentu" radius={[4, 4, 0, 0]} />
        <Bar dataKey="your" fill="#00FF94" name="Twój koszt" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

const DynamicRechartsChart = dynamic(() => Promise.resolve(RechartsChart), { ssr: false });

export default function KostorysPage() {
  const totalDoc = costItems.reduce((sum, i) => sum + i.docCost, 0);
  const totalYour = costItems.reduce((sum, i) => sum + i.yourCost, 0);
  const diff = totalYour - totalDoc;

  return (
    <div className="flex min-h-screen bg-[#0A0A0A] text-[#F4F4F0] font-sans">
      <Sidebar />
      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#00FF94]/20 flex items-center justify-center">
              <Calculator className="w-6 h-6 text-[#00FF94]" />
            </div>
            <div>
              <h1 className="text-3xl font-display font-bold text-[#F4F4F0]">
                KOSZTORYS
              </h1>
              <p className="text-neutral-400">Porównanie kosztów z dokumentacji vs. Twoje realia.</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="btn-secondary text-sm">
              <FileText className="w-4 h-4 mr-2 inline" />
              Zaimportuj PDF
            </button>
            <button className="btn-primary text-sm">
              Eksportuj
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <MotionDiv
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="card"
          >
            <div className="text-sm text-neutral-400 mb-1">Koszt w dokumencie</div>
            <div className="text-2xl font-mono font-bold text-[#F4F4F0]">{totalDoc.toFixed(2)} zł</div>
          </MotionDiv>
          <MotionDiv
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="card"
          >
            <div className="text-sm text-neutral-400 mb-1">Twój koszt</div>
            <div className="text-2xl font-mono font-bold text-[#3B82F6]">{totalYour.toFixed(2)} zł</div>
          </MotionDiv>
          <MotionDiv
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="card"
          >
            <div className="text-sm text-neutral-400 mb-1">Różnica</div>
            <div className={`text-2xl font-mono font-bold flex items-center gap-2 ${diff > 0 ? 'text-[#FF3300]' : 'text-[#00FF94]'}`}>
              {diff > 0 ? <ArrowUp className="w-5 h-5" /> : <ArrowDown className="w-5 h-5" />}
              {Math.abs(diff).toFixed(2)} zł
            </div>
          </MotionDiv>
        </div>

        {/* Chart */}
        <MotionDiv
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="card mb-8"
        >
          <h3 className="font-display font-bold text-lg mb-4">Porównanie kosztów jednostkowych</h3>
          <div className="h-80">
            <DynamicRechartsChart />
          </div>
        </MotionDiv>

        {/* Table */}
        <MotionDiv
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <table className="w-full">
            <thead className="text-left text-sm text-neutral-400">
              <tr>
                <th className="pb-4 font-display">Pozycja</th>
                <th className="pb-4 font-display">Koszt dok.</th>
                <th className="pb-4 font-display">Twój koszt</th>
                <th className="pb-4 font-display">Różnica</th>
                <th className="pb-4 font-display">Status</th>
              </tr>
            </thead>
            <tbody>
              {costItems.map((item) => (
                <tr key={item.id} className="border-t border-[#3D3D3C] hover:bg-[#1A1A1A] transition-colors">
                  <td className="py-4 font-display">{item.item}</td>
                  <td className="py-4 font-mono">{item.docCost.toFixed(2)} zł</td>
                  <td className="py-4 font-mono">{item.yourCost.toFixed(2)} zł</td>
                  <td className={`py-4 font-mono font-bold ${item.yourCost > item.docCost ? 'text-[#FF3300]' : 'text-[#00FF94]'}`}>
                    {(item.yourCost - item.docCost).toFixed(2)} zł
                  </td>
                  <td className="py-4">
                    {item.yourCost > item.docCost ? (
                      <span className="badge-warning">Przewyższony</span>
                    ) : (
                      <span className="badge-success">OK</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </MotionDiv>
      </main>
    </div>
  );
}
