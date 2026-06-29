'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

export function OpeningView({ onStart }: { onStart: () => void }) {
  const [phase, setPhase] = useState<'intro' | 'shovel' | 'ready'>('intro');
  
  useEffect(() => {
    const t1 = setTimeout(() => setPhase('shovel'), 800);
    const t2 = setTimeout(() => setPhase('ready'), 2000);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 1.1, transition: { duration: 0.5 } }}
      className="h-screen w-full flex flex-col items-center justify-center bg-earth-950 text-earth-100 overflow-hidden"
    >
      {/* Hero background image */}
      <div className="absolute inset-0 z-0 opacity-40">
        <img
          src="/assets/illustrations/shovel-hero.png"
          alt="Terra.OS"
          className="w-full h-full object-cover"
        />
      </div>
      
      {/* Dark overlay */}
      <div className="absolute inset-0 z-0 bg-gradient-to-t from-earth-950 via-earth-950/80 to-transparent" />
      
      {/* Shovel animation */}
      <AnimatePresence mode="wait">
        {phase === 'shovel' && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="relative z-10 mb-8"
          >
            <img
              src="/assets/logo/logo.svg"
              alt="Terra.OS"
              className="w-64 h-auto mx-auto"
            />
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Title */}
      <AnimatePresence mode="wait">
        {phase !== 'intro' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center z-10"
          >
            <h1 className="text-6xl font-bold mb-2 tracking-tight">
              Terra<span className="text-accent-success">.OS</span>
            </h1>
            <p className="text-xl text-earth-400 mb-2">System Zarządzania Przetargami i Budową</p>
            <p className="text-sm text-earth-500 mb-12">v2.1 — Dla firmy Macieka (Dzierżoniów)</p>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Tooltip hints */}
      {phase === 'shovel' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="absolute bottom-32 flex gap-6 text-earth-500 text-sm"
        >
          <span>Zwiad</span>
          <span>•</span>
          <span>Kosztorys</span>
          <span>•</span>
          <span>Silnik</span>
          <span>•</span>
          <span>Decyzja</span>
        </motion.div>
      )}
      
      {/* Launch button */}
      {phase === 'ready' && (
        <motion.button
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onStart}
          className="group flex items-center gap-3 px-8 py-4 bg-accent-success text-earth-950 rounded-xl font-semibold text-lg shadow-lg shadow-accent-success/20 hover:shadow-accent-success/40 transition-shadow z-10"
        >
          Uruchom system
          <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </motion.button>
      )}
      
      {/* Bottom info */}
      {phase === 'ready' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="absolute bottom-8 text-earth-600 text-xs"
        >
          © 2026 QA10 — Terra.OS | Dzierżoniów, Dolnośląskie
        </motion.div>
      )}
    </motion.div>
  );
}
