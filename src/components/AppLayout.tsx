'use client';

import dynamic from 'next/dynamic';
import { useStore } from '@/store/useStore';
import { Sidebar } from './Sidebar';
import { DashboardPage } from './pages/DashboardPage';
import { KosztorysPage } from './pages/KosztorysPage';
import { SilnikPage } from './pages/SilnikPage';
import { DecyzjaPage } from './pages/DecyzjaPage';

// Dynamic import to avoid SSR issues with motion
const MotionDiv = dynamic(() => import('motion/react').then((m) => m.motion.div), { ssr: false });

export function AppLayout() {
  const currentModule = useStore((state) => state.currentModule);

  const renderPage = () => {
    switch (currentModule) {
      case 'zwiad':
        return <DashboardPage />;
      case 'kosztorys':
        return <KosztorysPage />;
      case 'silnik':
        return <SilnikPage />;
      case 'decyzja':
        return <DecyzjaPage />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <div className="flex min-h-screen bg-[#0A0A0A] text-[#F4F4F0] font-sans">
      <Sidebar />
      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        <MotionDiv
          key={currentModule}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {renderPage()}
        </MotionDiv>
      </main>
    </div>
  );
}
