'use client';

import { useState } from 'react';
import { useStore } from '@/store/useStore';
import {
  Shovel,
  Calculator,
  Brain,
  ClipboardCheck,
  Truck,
  LayoutDashboard,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

const modules = [
  { id: 'dashboard' as const, icon: LayoutDashboard, name: 'DASHBOARD', desc: 'Panel główny', color: 'text-earth-100' },
  { id: 'zwiad' as const, icon: Shovel, name: 'ZWIAD', desc: 'Zwiad przetargowy', color: 'text-accent-success' },
  { id: 'kosztorys' as const, icon: Calculator, name: 'KOSZTORYS', desc: 'Kosztorys 2 warianty', color: 'text-accent-info' },
  { id: 'silnik' as const, icon: Brain, name: 'SILNIK', desc: 'Silnik decyzyjny', color: 'text-accent-warning' },
  { id: 'decyzja' as const, icon: ClipboardCheck, name: 'DECYZJA', desc: 'Rekomendacje', color: 'text-accent-violet' },
  { id: 'logistyka' as const, icon: Truck, name: 'MÓZG', desc: 'Logistyka', color: 'text-earth-400' },
];

export function Sidebar() {
  const { currentModule, setCurrentModule, isMenuOpen, toggleMenu } = useStore();
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div
      className={`flex flex-col bg-earth-900 border-r border-earth-700 transition-all duration-300 ${
        isMenuOpen ? 'w-64' : 'w-20'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-earth-700">
        {isMenuOpen && (
          <div className="flex items-center gap-2">
            <Shovel className="w-6 h-6 text-accent-success" />
            <div>
              <h1 className="text-lg font-bold text-earth-100">Terra.OS</h1>
              <p className="text-xs text-earth-400">v2.0 — GRUNT</p>
            </div>
          </div>
        )}
        <button
          onClick={toggleMenu}
          className="p-2 rounded-lg hover:bg-earth-700 text-earth-400 hover:text-earth-100 transition-colors"
        >
          {isMenuOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        {modules.map(({ id, icon: Icon, name, desc, color }) => (
          <button
            key={id}
            onClick={() => setCurrentModule(id)}
            onMouseEnter={() => setHovered(id)}
            onMouseLeave={() => setHovered(null)}
            className={`w-full flex items-center gap-3 px-4 py-3 transition-colors ${
              currentModule === id
                ? 'bg-earth-800 border-l-4 border-accent-success'
                : 'hover:bg-earth-800/50'
            }`}
          >
            <Icon className={`w-5 h-5 flex-shrink-0 ${currentModule === id ? color : 'text-earth-400'}`} />
            {isMenuOpen && (
              <div className="flex-1 text-left">
                <div className="text-sm font-semibold text-earth-100">{name}</div>
                <div className="text-xs text-earth-400">{desc}</div>
              </div>
            )}
            {!isMenuOpen && hovered === id && (
              <div className="absolute left-20 ml-2 px-3 py-2 bg-earth-700 rounded-lg shadow-lg whitespace-nowrap z-50">
                <div className="text-sm font-semibold text-earth-100">{name}</div>
                <div className="text-xs text-earth-400">{desc}</div>
              </div>
            )}
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-earth-700">
        {isMenuOpen ? (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-earth-700 flex items-center justify-center text-sm font-bold text-earth-300">
              MK
            </div>
            <div>
              <div className="text-sm font-medium text-earth-200">Michał K.</div>
              <div className="text-xs text-earth-400">Operator</div>
            </div>
          </div>
        ) : (
          <div className="w-10 h-10 rounded-full bg-earth-700 flex items-center justify-center text-sm font-bold text-earth-300 mx-auto">
            MK
          </div>
        )}
      </div>
    </div>
  );
}
