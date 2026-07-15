'use client';

import { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { LoginForm } from '@/components/LoginForm';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { AnalyticsPage } from '@/components/pages/AnalyticsPage';
import { DashboardPage } from '@/components/pages/DashboardPage';
import { ZwiadPage } from '@/components/pages/ZwiadPage';
import { KosztorysPage } from '@/components/pages/KosztorysPage';
import { SilnikPage } from '@/components/pages/SilnikPage';
import { DecyzjaPage } from '@/components/pages/DecyzjaPage';
import { LogistykaPage } from '@/components/pages/LogistykaPage';
import { RfqPage } from '@/components/pages/RfqPage';
import { PipelinePage } from '@/components/pages/PipelinePage';
import { SystemPage } from '@/components/pages/SystemPage';
import { SettingsPage } from '@/components/pages/SettingsPage';
import { ImportPage } from '@/components/pages/ImportPage';
import { PogodaPage } from '@/components/pages/PogodaPage';
import { MarketIntelPage } from '@/components/pages/MarketIntelPage';
import { ProactivePage } from '@/components/pages/ProactivePage';
import { DocumentsPage } from '@/components/pages/DocumentsPage';
import { CompetitorPage } from '@/components/pages/CompetitorPage';
import { BookmarksBoardPage } from '@/components/pages/BookmarksBoardPage';
import { BuyerCRMPage } from '@/components/pages/BuyerCRMPage';
import { NotificationsPage } from '@/components/pages/NotificationsPage';
import ExportPage from '@/components/pages/ExportPage';
import { OfertaPage } from '@/components/pages/OfertaPage';
import AutomationPage from '@/components/pages/AutomationPage';
import { ResourcesPage } from '@/components/pages/ResourcesPage';
import { ContractsPage } from '@/components/pages/ContractsPage';
import { TeamPage } from '@/components/pages/TeamPage';
import { ReportsPage } from '@/components/pages/ReportsPage';
import { ICBPage } from '@/components/pages/ICBPage';
import { AlertsPage } from '@/components/pages/AlertsPage';
import AxiomEnginePage from '@/components/pages/AxiomEnginePage';
import BidIntelligencePage from '@/components/pages/BidIntelligencePage';
import WebhooksPage from '@/components/pages/WebhooksPage';
import { PricingPage } from '@/components/pages/PricingPage';
import { Sidebar } from '@/components/Sidebar';
import { MarketBar } from '@/components/widgets/MarketBar';
import { ChatWidget } from '@/components/ChatWidget';
import { CommandMenu } from '@/components/CommandMenu';
import { ToastContainer } from '@/components/Toast';
import { OnboardingWizard } from '@/components/OnboardingWizard';
import { useStore } from '@/store/useStore';



function ActivePage() {
  const { currentModule } = useStore();
  switch (currentModule) {
    case 'dashboard':     return <DashboardPage />;
    case 'zwiad':         return <ZwiadPage />;
    case 'kosztorys':     return <KosztorysPage />;
    case 'silnik':        return <SilnikPage />;
    case 'decyzja':       return <DecyzjaPage />;
    case 'analytics':     return <AnalyticsPage />;
    case 'logistyka':     return <LogistykaPage />;
    case 'rfq':           return <RfqPage />;
    case 'pipeline':      return <PipelinePage />;
    case 'system':        return <SystemPage />;
    case 'settings':      return <SettingsPage />;
    case 'pogoda':        return <PogodaPage />;
    case 'market-intel':  return <MarketIntelPage />;
    case 'proactive':     return <ProactivePage />;
    case 'documents':     return <DocumentsPage />;
    case 'competitors':   return <CompetitorPage />;
    case 'bookmarks':     return <BookmarksBoardPage />;
    case 'buyer-crm':     return <BuyerCRMPage />;
    case 'notifications': return <NotificationsPage />;
    case 'export':        return <ExportPage />;
    case 'oferta':        return <OfertaPage />;
    case 'automations':   return <AutomationPage />;
    case 'resources':     return <ResourcesPage />;
    case 'contracts':     return <ContractsPage />;
    case 'team':          return <TeamPage />;
    case 'reports':       return <ReportsPage />;
    case 'icb':             return <ICBPage />;
    case 'import':          return <ImportPage />;
    case 'alerts':          return <AlertsPage />;
    case 'axiom':           return <AxiomEnginePage />;
    case 'bid-intelligence':return <BidIntelligencePage />;
    case 'webhooks':        return <WebhooksPage />;
    case 'pricing':         return <PricingPage />;
    default:              return <DashboardPage />;
  }
}

export default function Home() {
  const { user, accessToken, currentModule } = useStore();
  const isAuthenticated = !!(user && accessToken);
  const [commandOpen, setCommandOpen] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  // Show onboarding if user has no org_id
  useEffect(() => {
    if (isAuthenticated && user && !user.org_id) {
      const dismissed = localStorage.getItem('terra-onboarding-dismissed');
      if (!dismissed) setShowOnboarding(true);
    }
  }, [isAuthenticated, user]);

  // Global keyboard shortcuts
  useEffect(() => {
    if (!isAuthenticated) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        setCommandOpen(true);
        e.preventDefault();
      }
      if (e.key === 'Escape') setCommandOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <ErrorBoundary resetKey={currentModule}>
        <LoginForm onSuccess={() => {}} />
        <ToastContainer />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary resetKey={currentModule}>
      <div className="flex min-h-[100dvh] bg-earth-950">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <MarketBar />
          <main className="flex-1 overflow-auto bg-earth-950">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentModule}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.15, ease: 'easeOut' }}
                className="h-full"
              >
                <ActivePage />
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
        <ChatWidget />
      </div>
      <CommandMenu open={commandOpen} onClose={() => setCommandOpen(false)} />
      <ToastContainer />
      {showOnboarding && (
        <OnboardingWizard onComplete={() => {
          setShowOnboarding(false);
          localStorage.setItem('terra-onboarding-dismissed', '1');
        }} />
      )}
    </ErrorBoundary>
  );
}
