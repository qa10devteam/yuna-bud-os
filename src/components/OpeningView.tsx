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
      className="h-screen w-full flex flex-col items-center justify-center bg-earth-950 text-earth-100"
    >
      {/* Background grid effect */}
      <div className="absolute inset-0 opacity-5" style={{
        backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
        backgroundSize: '40px 40px'
      }} />
      
      {/* Shovel animation */}
      <AnimatePresence mode="wait">
        {phase === 'shovel' && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="relative z-10 mb-8"
          >
            <svg width="200" height="200" viewBox="0 0 200 200" fill="none" className="mx-auto">
              {/* Shovel handle */}
              <motion.line
                x1="100"
                y1="40"
                x2="100"
                y2="140"
                stroke="#F59E0B"
                strokeWidth="8"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1, ease: "easeInOut" }}
              />
              {/* Shovel head */}
              <motion.path
                d="M60 140 Q60 180 100 180 Q140 180 140 140"
                stroke="#22C55E"
                strokeWidth="8"
                fill="none"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1, ease: "easeInOut", delay: 0.5 }}
              />
              {/* Shovel blade */}
              <motion.rect
                x="50"
                y="130"
                width="100"
                height="20"
                rx="10"
                fill="#22C55E"
                opacity="0.3"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.3 }}
                transition={{ duration: 0.5, delay: 1 }}
              />
              {/* Glow effect */}
              <motion.circle
                cx="100"
                cy="100"
                r="60"
                fill="none"
                stroke="#22C55E"
                strokeWidth="2"
                opacity="0"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: [0, 0.5, 0], scale: [0.8, 1.2, 1.2] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </svg>
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
            <p className="text-sm text-earth-500 mb-12">v2.0 — Dla firm robót ziemnych</p>
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
          © 2026 QA10 — Terra.OS
        </motion.div>
      )}
    </motion.div>
  );
}
