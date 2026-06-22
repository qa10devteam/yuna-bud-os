'use client';

import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { OpeningView } from '@/components/OpeningView';
import { DashboardPage } from '@/components/pages/DashboardPage';
import { ZwiadPage } from '@/components/pages/ZwiadPage';
import { KosztorysPage } from '@/components/pages/KosztorysPage';
import { SilnikPage } from '@/components/pages/SilnikPage';
import { DecyzjaPage } from '@/components/pages/DecyzjaPage';
import { LogistykaPage } from '@/components/pages/LogistykaPage';
import { Sidebar } from '@/components/Sidebar';
import { ToastContainer } from '@/components/Toast';
import { useStore } from '@/store/useStore';

export default function Home() {
  const [showApp, setShowApp] = useState(false);
  const { currentModule } = useStore();
  
  if (!showApp) {
    return <OpeningView onStart={() => setShowApp(true)} />;
  }
  
  return (
    <div className="flex h-screen bg-earth-950">
      <Sidebar />
      <main className="flex-1 overflow-auto bg-earth-950">
        <AnimatePresence mode="wait">
          {currentModule === 'dashboard' && <DashboardPage key="dashboard" />}
          {currentModule === 'zwiad' && <ZwiadPage key="zwiad" />}
          {currentModule === 'kosztorys' && <KosztorysPage key="kosztorys" />}
          {currentModule === 'silnik' && <SilnikPage key="silnik" />}
          {currentModule === 'decyzja' && <DecyzjaPage key="decyzja" />}
          {currentModule === 'logistyka' && <LogistykaPage key="logistyka" />}
        </AnimatePresence>
      </main>
      <ToastContainer />
    </div>
  );
}
