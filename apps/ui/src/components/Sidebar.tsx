'use client';

import { useState } from 'react';
import { useStore } from '@/store/useStore';
import { ChevronLeft, ChevronRight } from 'lucide-react';

// Custom SVG Icons
const ShovelIcon = ({ className }: { className?: string }) => (
  <img src="/assets/icons/shovel.svg" alt="Zwiad" className={className} />
);
const CalcIcon = ({ className }: { className?: string }) => (
  <img src="/assets/icons/calculator.svg" alt="Kosztorys" className={className} />
);
const BrainIcon = ({ className }: { className?: string }) => (
  <img src="/assets/icons/brain.svg" alt="Silnik" className={className} />
);
const ClipboardIcon = ({ className }: { className?: string }) => (
  <img src="/assets/icons/clipboard.svg" alt="Decyzja" className={className} />
);
const TruckIcon = ({ className }: { className?: string }) => (
  <img src="/assets/icons/truck.svg" alt="Logistyka" className={className} />
);
const DashboardIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
  </svg>
);

const modules = [
  { id: 'dashboard' as const, icon: DashboardIcon, name: 'DASHBOARD', desc: 'Panel główny', color: 'text-earth-100' },
  { id: 'zwiad' as const, icon: ShovelIcon, name: 'ZWIAD', desc: 'Zwiad przetargowy', color: 'text-accent-success' },
  { id: 'kosztorys' as const, icon: CalcIcon, name: 'KOSZTORYS', desc: 'Kosztorys 2 warianty', color: 'text-accent-info' },
  { id: 'silnik' as const, icon: BrainIcon, name: 'SILNIK', desc: 'Silnik decyzyjny', color: 'text-accent-warning' },
  { id: 'decyzja' as const, icon: ClipboardIcon, name: 'DECYZJA', desc: 'Rekomendacje', color: 'text-accent-violet' },
  { id: 'logistyka' as const, icon: TruckIcon, name: 'MÓZG', desc: 'Logistyka', color: 'text-earth-400' },
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
            <img src="/assets/logo/logo.svg" alt="Terra.OS" className="h-10 w-auto" />
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
            <Icon className={`w-8 h-8 flex-shrink-0 ${currentModule === id ? color : 'text-earth-400'}`} />
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
              <div className="text-sm font-medium text-earth-200">Maciek K.</div>
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
