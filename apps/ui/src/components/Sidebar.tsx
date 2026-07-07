'use client';

import { useStore } from '@/store/useStore';
import { NotificationsBell } from '@/components/NotificationsBell';
import {
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Radar,
  Calculator,
  Brain,
  BarChart3,
  TrendingUp,
  Users,
  Bookmark as BookmarkIcon,
  Scale,
  Truck,
  ShieldCheck,
  GitBranch,
  Settings,
  CloudSun,
  LogOut,
  Upload,
  Menu,
  X,
  Building2,
  Bell,
  Download,
  FileText,
} from 'lucide-react';
import { useState } from 'react';

const modules = [
  { id: 'dashboard' as const, icon: LayoutDashboard, name: 'Dashboard',  desc: 'Panel główny' },
  { id: 'zwiad'     as const, icon: Radar,           name: 'Zwiad',      desc: 'Zwiad przetargowy' },
  { id: 'kosztorys' as const, icon: Calculator,      name: 'Kosztorys',  desc: 'Wycena i kosztorysy' },
  { id: 'silnik'    as const, icon: Brain,           name: 'Silnik',     desc: 'Silnik decyzyjny AI' },
  { id: 'analytics'    as const, icon: BarChart3,    name: 'Analityka',   desc: 'AHP, Friedman, Ryzyko' },
  { id: 'market-intel' as const, icon: TrendingUp,  name: 'Rynek',       desc: 'Trendy, CPV, benchmarki' },
  { id: 'competitors'  as const, icon: Users,        name: 'Konkurenci',  desc: 'Obserwowani wykonawcy' },
  { id: 'bookmarks'    as const, icon: BookmarkIcon, name: 'Zakładki',    desc: 'Kanban + alerty' },
  { id: 'buyer-crm'    as const, icon: Building2,    name: 'CRM',          desc: 'Zamawiajacy i kontakty' },
  { id: 'notifications' as const, icon: Bell,        name: 'Powiadomienia', desc: 'Alerty i zdarzenia' },
  { id: 'export'       as const, icon: Download,     name: 'Eksport',      desc: 'Pobierz dane' },
  { id: 'settings'     as const, icon: Settings,     name: 'Ustawienia',   desc: 'Organizacja i konto' },
  { id: 'decyzja'      as const, icon: Scale,        name: 'Decyzja',     desc: 'Rekomendacje i decyzje' },
  { id: 'logistyka'    as const, icon: Truck,        name: 'Logistyka',   desc: 'Sprzęt i pracownicy' },
  { id: 'oferta'       as const, icon: FileText,     name: 'Oferta',      desc: 'Kreator oferty PDF' },
  { id: 'rfq'          as const, icon: ShieldCheck,  name: 'RFQ',         desc: 'Zapytania ofertowe' },
  { id: 'pipeline'     as const, icon: GitBranch,    name: 'Pipeline',    desc: 'Nadzór procesów' },
  { id: 'pogoda'       as const, icon: CloudSun,     name: 'Pogoda',      desc: 'Prognoza 14 dni' },
  { id: 'system'       as const, icon: Settings,     name: 'Ustawienia',  desc: 'Konfiguracja systemu' },
];

export function Sidebar() {
  const { currentModule, setCurrentModule, isMenuOpen, toggleMenu, user, clearAuth } = useStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  const initials = user
    ? user.name
        ? user.name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
        : user.email.slice(0, 2).toUpperCase()
    : 'T';
  const displayName = user?.name || user?.email || 'Użytkownik';

  const sidebarContent = (
    <div
      className={`relative flex flex-col bg-earth-900/50 border-r border-earth-800/80 backdrop-blur-xl transition-all duration-300 ease-in-out h-full ${
        isMenuOpen ? 'w-60' : 'w-[68px]'
      }`}
    >
      {/* ── Logo / Header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 h-16 border-b border-earth-800/60">
        {isMenuOpen ? (
          <span className="text-base font-bold text-earth-100 tracking-tight select-none">
            Terra<span className="text-accent-primary">.OS</span>
          </span>
        ) : (
          <div className="w-8 h-8 rounded-full bg-accent-primary/10 border border-accent-primary/30 flex items-center justify-center mx-auto">
            <span className="text-accent-primary text-sm font-bold leading-none select-none">T</span>
          </div>
        )}

        {/* Notifications bell — only in expanded sidebar */}
        {isMenuOpen && <NotificationsBell />}

        <button
          onClick={toggleMenu}
          aria-label={isMenuOpen ? 'Zwiń menu' : 'Rozwiń menu'}
          className="p-1.5 rounded-md hover:bg-earth-800 text-earth-500 hover:text-earth-200 transition-colors duration-200 ml-1 flex-shrink-0"
        >
          {isMenuOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {/* ── Navigation ────────────────────────────────────────────────── */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {modules.map(({ id, icon: Icon, name, desc }) => {
          const isActive = currentModule === id;
          return (
            <div key={id} className="relative group/item">
              <button
                onClick={() => { setCurrentModule(id); setMobileOpen(false); }}
                className={`relative w-full flex items-center gap-3 rounded-lg px-3 py-2.5 transition-all duration-200 ${
                  isActive
                    ? 'bg-accent-primary/15 text-accent-primary border-l-[3px] border-accent-primary shadow-sm'
                    : 'text-earth-400 hover:text-earth-200 hover:bg-earth-800/60 border-l-[3px] border-transparent'
                }`}
              >
                <Icon
                  className={`w-[18px] h-[18px] flex-shrink-0 transition-colors duration-200 ${
                    isActive ? 'text-accent-primary' : 'text-earth-500 group-hover/item:text-earth-300'
                  }`}
                />
                {isMenuOpen && (
                  <span
                    className={`text-sm font-medium truncate transition-colors duration-200 ${
                      isActive ? 'text-accent-primary' : 'text-earth-300 group-hover/item:text-earth-100'
                    }`}
                  >
                    {name}
                  </span>
                )}
              </button>

              {!isMenuOpen && (
                <div className="pointer-events-none absolute left-full top-1/2 -translate-y-1/2 ml-3 z-50 px-3 py-2 bg-earth-800 border border-earth-700/50 rounded-lg shadow-xl shadow-black/40 whitespace-nowrap opacity-0 scale-95 group-hover/item:opacity-100 group-hover/item:scale-100 transition-all duration-150 ease-out">
                  <div className="text-sm font-semibold text-earth-100">{name}</div>
                  <div className="text-xs text-earth-400 mt-0.5">{desc}</div>
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-earth-700/50" />
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <div className="p-3 border-t border-earth-800/60 space-y-2">
        {isMenuOpen ? (
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-earth-800/40 transition-colors cursor-pointer">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-primary/30 to-accent-primary/10 border border-accent-primary/20 flex items-center justify-center text-xs font-bold text-accent-primary flex-shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-earth-200 truncate">{displayName}</div>
              <div className="text-xs text-earth-500 capitalize">{user?.role || 'Gość'}</div>
            </div>
            <button
              onClick={clearAuth}
              title="Wyloguj"
              className="p-1.5 rounded-md hover:bg-earth-700 text-earth-500 hover:text-red-400 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="relative group/logout">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-primary/30 to-accent-primary/10 border border-accent-primary/20 flex items-center justify-center text-xs font-bold text-accent-primary mx-auto cursor-pointer">
              {initials}
            </div>
            <button
              onClick={clearAuth}
              title="Wyloguj"
              className="absolute -top-1 -right-1 opacity-0 group-hover/logout:opacity-100 w-4 h-4 bg-red-500/80 rounded-full flex items-center justify-center transition-opacity"
            >
              <LogOut className="w-2.5 h-2.5 text-white" />
            </button>
          </div>
        )}

        {isMenuOpen ? (
          <div className="flex items-center justify-between px-2 py-1">
            <span className="text-[10px] text-earth-600 font-mono tracking-wide">v2.0.0</span>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-accent-primary animate-pulse" />
              <span className="text-[10px] text-earth-600">API</span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-primary animate-pulse" />
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="md:hidden fixed top-4 left-4 z-40 p-2 bg-earth-900/80 rounded-xl border border-earth-800/60 text-earth-400"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Desktop sidebar */}
      <div className="hidden md:block h-screen sticky top-0">
        {sidebarContent}
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-earth-950/80" onClick={() => setMobileOpen(false)} />
          <div className="relative h-full">
            {sidebarContent}
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            className="absolute top-4 right-4 p-2 text-earth-500 hover:text-earth-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}
    </>
  );
}
