'use client';

import { useStore } from '@/store/useStore';
import { Shovel, Map, Calculator, Flag, Brain, X, User, Settings } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useState, useEffect } from 'react';

// Dynamic imports to avoid SSR issues with motion
const MotionButton = dynamic(() => import('motion/react').then((m) => m.motion.button), { ssr: false });
const MotionAside = dynamic(() => import('motion/react').then((m) => m.motion.aside), { ssr: false });

export function Sidebar() {
  const { currentModule, setCurrentModule, isMenuOpen, toggleMenu, selectedTenderData } = useStore();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    setIsMobile(window.innerWidth < 768);
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const navItems = [
    { key: 'zwiad' as const, name: 'ZWIAD', icon: Map, desc: 'Trzonek' },
    { key: 'kosztorys' as const, name: 'KOSZTORYS', icon: Calculator, desc: 'Kij' },
    { key: 'silnik' as const, name: 'SILNIK', icon: Flag, desc: 'Przetwarzanie' },
    { key: 'decyzja' as const, name: 'DECYZJA', icon: Brain, desc: 'Łyżka' },
  ];

  return (
    <>
      {/* Mobile menu button */}
      <MotionButton
        onClick={toggleMenu}
        className="fixed top-4 left-4 z-50 md:hidden p-2 rounded-lg bg-[#1A1A1A] border border-neutral-200"
        whileTap={{ scale: 0.9 }}
      >
        {isMenuOpen ? <X className="w-6 h-6" /> : <Shovel className="w-6 h-6" />}
      </MotionButton>

      {/* Sidebar */}
      <MotionAside
        className={`fixed md:relative z-40 h-screen w-64 bg-[#1A1A1A] text-[#F4F4F0] flex flex-col items-start p-4 border-r border-neutral-200 transform transition-transform duration-300 ${
          isMenuOpen ? 'translate-x-0' : isMobile ? '-translate-x-full' : 'translate-x-0'
        }`}
        initial={false}
        animate={{ x: isMenuOpen ? 0 : isMobile ? -256 : 0 }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8 w-full">
          <div className="w-10 h-10 rounded-lg bg-[#00FF94]/20 flex items-center justify-center">
            <Shovel className="w-6 h-6 text-[#00FF94]" />
          </div>
          <div>
            <div className="font-display font-bold text-xl text-[#F4F4F0]">Terra.OS</div>
            <div className="text-xs text-neutral-400">v1.0.0</div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-2 w-full flex-1">
          {navItems.map((item) => (
            <MotionButton
              key={item.key}
              onClick={() => setCurrentModule(item.key)}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors group w-full text-left ${
                currentModule === item.key
                  ? 'bg-[#00FF94]/20 text-[#00FF94]'
                  : 'hover:bg-[#3D3D3C]'
              }`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <item.icon className="w-5 h-5" />
              <div>
                <div className="font-display font-bold text-sm">{item.name}</div>
                <div className="text-xs text-neutral-400">{item.desc}</div>
              </div>
            </MotionButton>
          ))}
        </nav>

        {/* User info */}
        <div className="w-full mt-auto">
          <div className="p-3 rounded-lg bg-[#3D3D3C]/50">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-full bg-[#00FF94] flex items-center justify-center text-[#1A1A1A] font-bold">
                M
              </div>
              <div>
                <div className="font-display font-bold text-sm">Maciek K.</div>
                <div className="text-xs text-neutral-400">Firma Robót Ziemnych</div>
              </div>
            </div>
            <div className="flex gap-2 mt-2">
              <button className="flex-1 p-2 rounded bg-[#1A1A1A] hover:bg-[#6B6B68] transition-colors">
                <User className="w-4 h-4 mx-auto" />
              </button>
              <button className="flex-1 p-2 rounded bg-[#1A1A1A] hover:bg-[#6B6B68] transition-colors">
                <Settings className="w-4 h-4 mx-auto" />
              </button>
            </div>
          </div>
        </div>
      </MotionAside>

      {/* Overlay for mobile */}
      {isMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={toggleMenu}
        />
      )}
    </>
  );
}
