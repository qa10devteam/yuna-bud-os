'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ArrowRight } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

type Phase = 'intro' | 'logo' | 'ready';

interface OpeningViewProps {
  onStart: () => void;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function OpeningView({ onStart }: OpeningViewProps) {
  const [phase, setPhase] = useState<Phase>('intro');

  useEffect(() => {
    // Respect reduced motion — skip straight to ready
    const prefersReduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReduced) {
      setPhase('ready');
      return;
    }

    const t1 = setTimeout(() => setPhase('logo'),  600);
    const t2 = setTimeout(() => setPhase('ready'), 1800);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  // Auto-skip if user already visited (returning user)
  useEffect(() => {
    const visited = sessionStorage.getItem('yu-na-opened');
    if (visited) {
      setPhase('ready');
      return;
    }
    const t = setTimeout(() => sessionStorage.setItem('yu-na-opened', '1'), 2000);
    return () => clearTimeout(t);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-[100dvh] w-full flex flex-col items-center justify-center bg-earth-950 text-earth-100 overflow-hidden relative"
    >
      {/* Background texture */}
      <div
        className="absolute inset-0 z-0 opacity-[0.025]"
        aria-hidden="true"
        style={{
          backgroundImage:
            'repeating-linear-gradient(0deg,#fff 0px,#fff 1px,transparent 1px,transparent 60px),' +
            'repeating-linear-gradient(90deg,#fff 0px,#fff 1px,transparent 1px,transparent 60px)',
        }}
      />

      {/* BG image */}
      <div className="absolute inset-0 z-0 opacity-25">
        <img
          src="/assets/illustrations/shovel-hero.png"
          alt=""
          aria-hidden="true"
          className="w-full h-full object-cover"
        />
      </div>
      <div className="absolute inset-0 z-0 bg-gradient-to-t from-earth-950 via-earth-950/70 to-transparent" />

      {/* ── Content ──────────────────────────────────────────────────── */}

      {/* Logo */}
      <AnimatePresence>
        {phase !== 'intro' && (
          <motion.div
            key="logo"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="z-10 mb-8"
          >
            <img
              src="/assets/logo/logo.svg"
              alt="YU-NA"
              className="w-52 h-auto mx-auto drop-shadow-2xl"
              onError={(e) => {
                // Fallback if SVG missing
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Title */}
      <AnimatePresence>
        {phase !== 'intro' && (
          <motion.div
            key="title"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5, delay: 0.1, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="text-center z-10 px-6"
          >
            <h1 className="text-6xl md:text-7xl font-bold mb-3 tracking-tighter leading-none">
              YU-NA
            </h1>
            <p className="text-xl text-earth-400 mb-2 font-light">
              Platforma zarządzania przetargami budowlanymi
            </p>
            <p className="text-sm text-earth-700 mb-12 font-mono tracking-wide">
              budos v2.1
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Module pills */}
      <AnimatePresence>
        {phase === 'logo' && (
          <motion.div
            key="pills"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ delay: 0.5 }}
            className="absolute bottom-28 flex items-center gap-4 text-earth-700 text-xs z-10 tracking-widest uppercase"
          >
            {['Zwiad', 'Kosztorys', 'Silnik AI', 'Decyzja'].map((m) => (
              <span key={m}>{m}</span>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* CTA */}
      <AnimatePresence>
        {phase === 'ready' && (
          <motion.button
            key="cta"
            initial={{ opacity: 0, scale: 0.9, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0 }}
            whileHover={{ scale: 1.03, y: -2 }}
            whileTap={{ scale: 0.97 }}
            transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
            onClick={onStart}
            className="group relative flex items-center gap-3 px-9 py-4 bg-accent-primary text-earth-950 rounded-token-lg font-bold text-lg shadow-token-glow hover:shadow-lg transition-shadow z-10 cursor-pointer"
          >
            <span className="absolute inset-0 rounded-token-lg bg-accent-primary/20 blur-xl -z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            Wejdź do systemu
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform duration-200" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Skip hint — shown immediately for accessibility */}
      <AnimatePresence>
        {phase === 'ready' && (
          <motion.div
            key="footer"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.45 }}
            exit={{ opacity: 0 }}
            transition={{ delay: 0.6 }}
            className="absolute bottom-6 text-earth-700 text-xs z-10"
          >
            QA10 Labs &copy; 2026
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
