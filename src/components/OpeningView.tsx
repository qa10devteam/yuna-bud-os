'use client';

import { useStore } from '@/store/useStore';
import dynamic from 'next/dynamic';

// Dynamic imports to avoid SSR issues with motion
const MotionDiv = dynamic(() => import('motion/react').then((m) => m.motion.div), { ssr: false });
const MotionPath = dynamic(() => import('motion/react').then((m) => m.motion.path), { ssr: false });
const MotionCircle = dynamic(() => import('motion/react').then((m) => m.motion.circle), { ssr: false });
const MotionButton = dynamic(() => import('motion/react').then((m) => m.motion.button), { ssr: false });

interface OpeningViewProps {
  onEnter: () => void;
}

export function OpeningView({ onEnter }: OpeningViewProps) {
  const setCurrentModule = useStore((state) => state.setCurrentModule);

  const modules = [
    {
      key: 'zwiad' as const,
      name: 'ZWIAD',
      subtitle: 'Szukanie przetargów',
      description: 'Moduł 1: Trzonek — Analiza rynku i źródeł danych',
      color: '#00FF94',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
      )
    },
    {
      key: 'kosztorys' as const,
      name: 'KOSZTORYS',
      subtitle: 'Analiza kosztów',
      description: 'Moduł 2: Kij — Porównanie kosztów i marży',
      color: '#3B82F6',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
      )
    },
    {
      key: 'silnik' as const,
      name: 'SILNIK',
      subtitle: 'Ryzyka i analiZA',
      description: 'Moduł 2: Przetwarzanie — Wykrywanie zagrożeń',
      color: '#FF3300',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        </svg>
      )
    },
    {
      key: 'decyzja' as const,
      name: 'DECYZJA',
      subtitle: 'Mózg systemowy',
      description: 'Moduł 3: Łyżka — Rekomendacje i akcja',
      color: '#A855F7',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
        </svg>
      )
    }
  ];

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-[#F4F4F0] font-sans flex flex-col">
      {/* Hero Section */}
      <div className="flex-1 flex items-center justify-center p-8">
        <MotionDiv
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center max-w-4xl mx-auto"
        >
          <MotionDiv
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mb-8"
          >
            <svg viewBox="0 0 400 200" className="w-full max-w-2xl mx-auto">
              {/* Shovel Handle */}
              <MotionPath
                d="M 200 180 L 200 100"
                stroke="#00FF94"
                strokeWidth="8"
                fill="none"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1, delay: 0.5 }}
              />
              {/* Shovel Shaft */}
              <MotionPath
                d="M 200 100 L 200 50"
                stroke="#3B82F6"
                strokeWidth="6"
                fill="none"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1, delay: 1 }}
              />
              {/* Shovel Blade */}
              <MotionPath
                d="M 150 50 L 200 30 L 250 50 L 200 70 Z"
                stroke="#FF3300"
                strokeWidth="3"
                fill="none"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1, delay: 1.5 }}
              />
              {/* Connection points */}
              <MotionCircle
                cx="200"
                cy="100"
                r="8"
                fill="#00FF94"
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 1.5 }}
              />
              <MotionCircle
                cx="200"
                cy="50"
                r="6"
                fill="#3B82F6"
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 2 }}
              />
              <MotionCircle
                cx="200"
                cy="30"
                r="5"
                fill="#FF3300"
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 2.5 }}
              />
            </svg>
          </MotionDiv>

          <h1 className="text-6xl md:text-8xl font-display font-bold mb-4 bg-gradient-to-r from-[#00FF94] via-[#3B82F6] to-[#FF3300] bg-clip-text text-transparent">
            Terra.OS
          </h1>
          <p className="text-2xl text-neutral-400 mb-12">
            System zarządzania Ziemią dla firm budowlanych
          </p>

          {/* Module Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
            {modules.map((module, index) => (
              <MotionButton
                key={module.key}
                onClick={() => {
                  setCurrentModule(module.key);
                  onEnter();
                }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + index * 0.1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="p-6 rounded-xl border border-neutral-200 hover:border-[color:var(--accent)] bg-[#1A1A1A] transition-all"
                style={{ '--accent': module.color } as React.CSSProperties}
              >
                <div className="text-[color:var(--accent)] mb-4">
                  {module.icon}
                </div>
                <h3 className="text-xl font-display font-bold mb-2">{module.name}</h3>
                <p className="text-sm text-neutral-400 mb-2">{module.subtitle}</p>
                <p className="text-xs text-neutral-500">{module.description}</p>
              </MotionButton>
            ))}
          </div>
        </MotionDiv>
      </div>

      {/* Footer */}
      <MotionDiv
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2 }}
        className="p-4 text-center text-neutral-500 text-sm"
      >
        <p>© 2024 Terra.OS — Profesjonalne narzędzie do analizy przetargów budowlanych</p>
      </MotionDiv>
    </div>
  );
}
