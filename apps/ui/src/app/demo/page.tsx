'use client';

import { useEffect, useState } from 'react';
import { AnalyticsPage } from '@/components/pages/AnalyticsPage';
import { DashboardPage } from '@/components/pages/DashboardPage';
import { ZwiadPage } from '@/components/pages/ZwiadPage';
import { KosztorysPage } from '@/components/pages/KosztorysPage';
import { SilnikPage } from '@/components/pages/SilnikPage';
import { DecyzjaPage } from '@/components/pages/DecyzjaPage';
import { LogistykaPage } from '@/components/pages/LogistykaPage';
import { RfqPage } from '@/components/pages/RfqPage';
import { OfertaPage } from '@/components/pages/OfertaPage';
import { PipelinePage } from '@/components/pages/PipelinePage';
import { SettingsPage } from '@/components/pages/SettingsPage';
import { PogodaPage } from '@/components/pages/PogodaPage';
import { MarketIntelPage } from '@/components/pages/MarketIntelPage';
import { CompetitorPage } from '@/components/pages/CompetitorPage';
import { BookmarksBoardPage } from '@/components/pages/BookmarksBoardPage';
import { BuyerCRMPage } from '@/components/pages/BuyerCRMPage';
import { NotificationsPage } from '@/components/pages/NotificationsPage';
import ExportPage from '@/components/pages/ExportPage';
import { Sidebar } from '@/components/Sidebar';
import { MarketBar } from '@/components/widgets/MarketBar';
import { ChatWidget } from '@/components/ChatWidget';
import { ToastContainer } from '@/components/Toast';
import { DemoTour } from '@/components/DemoTour';
import { useStore } from '@/store/useStore';

function ActivePage() {
  const { currentModule } = useStore();
  switch (currentModule) {
    case 'dashboard':  return <DashboardPage />;
    case 'zwiad':      return <ZwiadPage />;
    case 'kosztorys':  return <KosztorysPage />;
    case 'silnik':     return <SilnikPage />;
    case 'decyzja':    return <DecyzjaPage />;
    case 'analytics':     return <AnalyticsPage />;
    case 'market-intel':  return <MarketIntelPage />;
    case 'competitors':   return <CompetitorPage />;
    case 'bookmarks':     return <BookmarksBoardPage />;
    case 'buyer-crm':     return <BuyerCRMPage />;
    case 'notifications': return <NotificationsPage />;
    case 'export':        return <ExportPage />;
    case 'settings':      return <SettingsPage />;
    case 'logistyka':  return <LogistykaPage />;
    case 'oferta':     return <OfertaPage />;
    case 'rfq':        return <RfqPage />;
    case 'pipeline':   return <PipelinePage />;
    case 'system':     return <SettingsPage />;
    case 'pogoda':     return <PogodaPage />;
    default:           return <DashboardPage />;
  }
}

export default function DemoPage() {
  const { user, accessToken, setAuth } = useStore();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // If already authenticated, just show the app
    if (user && accessToken) {
      setReady(true);
      return;
    }

    // Auto-login with demo credentials
    async function autoLogin() {
      try {
        // First try to register demo user (ignore if already exists)
        await fetch('/api/v2/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: 'demo@yu-na.pl',
            password: 'demo2026!',
            name: 'Jan Kowalski',
          }),
        }).catch(() => {});

        // Login demo user
        const res = await fetch('/api/v2/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: 'demo@yu-na.pl',
            password: 'demo2026!',
          }),
        });

        if (!res.ok) {
          // Fallback: try existing test user
          const res2 = await fetch('/api/v2/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: 'mateusz@qa10.io',
              password: 'terra123',
            }),
          });
          if (!res2.ok) throw new Error('Login failed');
          const data = await res2.json();
          setAuth(data.user, data.access_token, data.refresh_token);
          setReady(true);
          return;
        }

        const data = await res.json();
        setAuth(data.user, data.access_token, data.refresh_token);
        setReady(true);
      } catch (e: unknown) {
        setError((e as Error).message || 'Błąd logowania demo');
      }
    }

    autoLogin();
  }, [user, accessToken, setAuth]);

  if (error) {
    return (
      <div className="min-h-screen bg-earth-950 flex items-center justify-center text-earth-100">
        <div className="text-center">
          <p className="text-red-400 mb-4">Błąd demo: {error}</p>
          <button onClick={() => window.location.reload()} className="px-4 py-2 bg-accent-primary text-earth-950 rounded-lg font-semibold">
            Spróbuj ponownie
          </button>
        </div>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="min-h-screen bg-earth-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-earth-400 text-sm">Ładowanie demo...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Demo banner */}
      <div className="fixed top-0 left-0 right-0 z-[100] bg-amber-500/90 text-earth-950 text-center py-1.5 text-xs font-bold tracking-wide backdrop-blur-sm">
        🚀 ŚRODOWISKO DEMO — eksploruj wszystkie funkcjonalności YU-NA
        <a href="https://yu-na.pl" className="ml-3 underline font-semibold hover:text-earth-800">
          Zamów dostęp →
        </a>
      </div>

      <div className="flex min-h-[100dvh] bg-earth-950 pt-8">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <MarketBar />
          <main className="flex-1 overflow-auto bg-earth-950">
            <ActivePage />
          </main>
        </div>
        <ChatWidget />
      </div>
      <ToastContainer />
      <DemoTour />
    </>
  );
}
