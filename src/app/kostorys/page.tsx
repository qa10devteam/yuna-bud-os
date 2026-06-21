'use client';

import { Sidebar } from '@/components/Sidebar';
import { Calculator, ArrowDown, ArrowUp } from 'lucide-react';
import { motion } from 'motion/react';

const items = [
  { item: 'Wykopy ziemne powszechne', docCost: 15.50, yourCost: 18.20 },
  { item: 'Nasypy z gruntów naturalnych', docCost: 22.00, yourCost: 20.50 },
  { item: 'Odwodnienie wykopów', docCost: 0.00, yourCost: 12.50 },
  { item: 'Transport gruntu 15km', docCost: 45.00, yourCost: 42.00 },
  { item: 'Składowanie gruntu', docCost: 12.00, yourCost: 10.50 },
];

export default function KostorysPage() {
  const totalDoc = items.reduce((sum, i) => sum + i.docCost, 0);
  const totalYour = items.reduce((sum, i) => sum + i.yourCost, 0);
  const diff = totalYour - totalDoc;

  return (
    <div className="flex min-h-screen bg-surface-base text-text-primary font-body">
      <Sidebar />
      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        <div className="flex items-center gap-3 mb-8">
          <Calculator className="w-8 h-8 text-accent-success" />
          <div>
            <h1 className="text-3xl font-display font-bold text-neutral-600">
              KOSZTORYS — Moduł 2: Kij
            </h1>
            <p className="text-neutral-400">Porównanie kosztów z dokumentacji vs. Twoje realia.</p>
          </div>
        </div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card mb-8"
        >
          <div className="grid grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-sm text-neutral-400 mb-1">Koszt w dokumencie</div>
              <div className="text-2xl font-mono font-bold text-neutral-600">{totalDoc.toFixed(2)} zł</div>
            </div>
            <div>
              <div className="text-sm text-neutral-400 mb-1">Twój koszt</div>
              <div className="text-2xl font-mono font-bold text-accent-tech">{totalYour.toFixed(2)} zł</div>
            </div>
            <div>
              <div className="text-sm text-neutral-400 mb-1">Różnica</div>
              <div className={`text-2xl font-mono font-bold flex items-center justify-center gap-2 ${diff > 0 ? 'text-accent-warning' : 'text-accent-success'}`}>
                {diff > 0 ? <ArrowUp className="w-5 h-5" /> : <ArrowDown className="w-5 h-5" />}
                {Math.abs(diff).toFixed(2)} zł
              </div>
            </div>
          </div>
        </motion.div>

        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-neutral-100 dark:bg-neutral-700">
              <tr>
                <th className="text-left p-4 font-display font-bold text-sm">Pozycja</th>
                <th className="text-right p-4 font-display font-bold text-sm">Koszt dok.</th>
                <th className="text-right p-4 font-display font-bold text-sm">Twój koszt</th>
                <th className="text-right p-4 font-display font-bold text-sm">Różnica</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.item} className="border-t border-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-700/50">
                  <td className="p-4 font-mono text-sm">{item.item}</td>
                  <td className="p-4 text-right font-mono text-sm">{item.docCost.toFixed(2)}</td>
                  <td className="p-4 text-right font-mono text-sm">{item.yourCost.toFixed(2)}</td>
                  <td className={`p-4 text-right font-mono text-sm font-bold ${item.yourCost > item.docCost ? 'text-accent-warning' : 'text-accent-success'}`}>
                    {(item.yourCost - item.docCost).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-8 flex justify-end">
          <button className="btn-primary">
            PRZEJDŹ DO SILNIKA RYZYKA
          </button>
        </div>
      </main>
    </div>
  );
}
