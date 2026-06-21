'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { OpeningView } from '@/components/OpeningView';
import { AppLayout } from '@/components/AppLayout';

// Dynamic imports to avoid SSR issues with motion
const MotionDiv = dynamic(() => import('motion/react').then((m) => m.motion.div), { ssr: false });
const AnimatePresence = dynamic(() => import('motion/react').then((m) => m.AnimatePresence), { ssr: false });

export default function Home() {
  const [showApp, setShowApp] = useState(false);

  return (
    <AnimatePresence mode="wait">
      {!showApp ? (
        <MotionDiv
          key="opening"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5 }}
        >
          <OpeningView onEnter={() => setShowApp(true)} />
        </MotionDiv>
      ) : (
        <MotionDiv
          key="app"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <AppLayout />
        </MotionDiv>
      )}
    </AnimatePresence>
  );
}
