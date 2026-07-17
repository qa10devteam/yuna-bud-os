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
  Scale,
  GitBranch,
  Settings,
  LogOut,
  Menu,
  X,
  FileText,
  Target,
  Hammer,
  Wrench,
  PackageSearch,
  Users,
} from 'lucide-react';
import { useState } from 'react';

// ── Module groups ──────────────────────────────────────────────────────────────

type ModuleGroup = {
  label:     string;
  GroupIcon: React.ElementType;
  items:     { id: string; icon: React.ElementType; name: string; desc: string }[];
};

const moduleGroups: ModuleGroup[] = [
  {
    label:     'Przetargi',
    GroupIcon: Target,
    items: [
      { id: 'zwiad',    icon: Radar,     name: 'Zwiad',      desc: 'Zwiad przetargowy BZP/TED' },
      { id: 'pipeline', icon: GitBranch, name: 'Lejek',      desc: 'Kanban przetargów' },
      { id: 'silnik',   icon: Brain,     name: 'Silnik AI',  desc: 'Analiza AHP + Friedman' },
      { id: 'decyzja',  icon: Scale,     name: 'Decyzja',    desc: 'Rekomendacje AI' },
    ],
  },
  {
    label:     'Realizacja',
    GroupIcon: Hammer,
    items: [
      { id: 'kosztorys', icon: Calculator, name: 'Kosztorys', desc: 'Wycena KNR i materiały' },
      { id: 'oferta',    icon: FileText,   name: 'Oferta',    desc: 'Kreator oferty PDF' },
      { id: 'contracts', icon: FileText,   name: 'Kontrakty', desc: 'Tracker + cashflow' },
      { id: 'logistyka', icon: Wrench,     name: 'Logistyka', desc: 'Zasoby, sprzęt, harmonogram' },
      { id: 'resources', icon: Users,      name: 'Zasoby',    desc: 'Pracownicy i maszyny' },
    ],
  },
  {
    label:     'Inteligencja',
    GroupIcon: BarChart3,
    items: [
      { id: 'dashboard',    icon: LayoutDashboard, name: 'Dashboard',  desc: 'Panel główny' },
      { id: 'analytics',    icon: BarChart3,       name: 'Analityka',  desc: 'AHP, Friedman, Ryzyko' },
      { id: 'icb',          icon: PackageSearch,   name: 'Cennik ICB', desc: 'Baza cen InterCenBud' },
      { id: 'market-intel', icon: TrendingUp,      name: 'Rynek',      desc: 'Trendy i benchmarki CPV' },
      { id: 'rynek',        icon: BarChart3,        name: 'Rynek S6',   desc: 'Dashboard BZP · TED · GUS' },
    ],
  },
  {
    label:     'System',
    GroupIcon: Settings,
    items: [
      { id: 'settings', icon: Settings, name: 'Ustawienia', desc: 'Organizacja i konto' },
      { id: 'system',   icon: Wrench,   name: 'System',     desc: 'Parametry systemu' },
    ],
  },
];

// ── Inner content ──────────────────────────────────────────────────────────────

function SidebarContent({ onItemClick }: { onItemClick?: () => void }) {
  const { currentModule, setCurrentModule, isMenuOpen, toggleMenu, user, clearAuth } = useStore();

  const initials = user
    ? (user.name
        ? user.name.split(' ').map((p: string) => p[0]).slice(0, 2).join('').toUpperCase()
        : user.email.slice(0, 2).toUpperCase())
    : 'Y';

  const displayName = user?.name || user?.email || 'Użytkownik';

  return (
    <div
      className={[
        'relative flex flex-col h-full',
        'bg-earth-900/50 border-r border-earth-700/60',
        'backdrop-blur-xl',
        'transition-all duration-300 ease-in-out',
        isMenuOpen ? 'w-60' : 'w-[68px]',
      ].join(' ')}
    >
      {/* ── Logo / Header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 h-16 border-b border-earth-700/50 flex-shrink-0">
        {isMenuOpen ? (
          /* Full logo */
          <div className="flex flex-col leading-none select-none">
            <span className="text-base font-bold text-accent-primary tracking-tight leading-tight">
              budos
            </span>
            <span className="text-[10px] text-earth-600 font-normal leading-tight mt-0.5">
              Powered by YU‑NA Intelligence
            </span>
          </div>
        ) : (
          /* Signet icon */
          <div className="w-8 h-8 rounded-lg bg-accent-primary/10 border border-accent-primary/30 flex items-center justify-center mx-auto">
            <span className="text-accent-primary text-xs font-bold leading-none select-none">b</span>
          </div>
        )}

        {isMenuOpen && <NotificationsBell />}

        <button
          onClick={toggleMenu}
          aria-label={isMenuOpen ? 'Zwiń menu' : 'Rozwiń menu'}
          className="p-1.5 rounded-md hover:bg-earth-800 text-earth-500 hover:text-earth-200 transition-colors duration-200 ml-1 flex-shrink-0"
        >
          {isMenuOpen
            ? <ChevronLeft  className="w-4 h-4" />
            : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {/* ── Navigation ─────────────────────────────────────────────────── */}
      <nav className="flex-1 py-2 px-2 overflow-y-auto">
        {moduleGroups.map(({ label, GroupIcon, items }) => (
          <div key={label} className="mb-1">
            {/* Group header */}
            {isMenuOpen ? (
              <div className="flex items-center gap-1.5 px-2 py-1 mb-0.5">
                <GroupIcon className="w-3.5 h-3.5 text-earth-700 flex-shrink-0" />
                <span className="section-label truncate">{label}</span>
              </div>
            ) : (
              <div className="flex justify-center py-1 mb-0.5">
                <GroupIcon className="w-3.5 h-3.5 text-earth-700" />
              </div>
            )}

            {/* Items */}
            <div className="space-y-0.5">
              {items.map(({ id, icon: Icon, name, desc }) => {
                const isActive = currentModule === id;
                return (
                  <div key={id} className="relative group/item">
                    <button
                      onClick={() => {
                        setCurrentModule(id as Parameters<typeof setCurrentModule>[0]);
                        onItemClick?.();
                      }}
                      aria-current={isActive ? 'page' : undefined}
                      className={[
                        'relative w-full flex items-center gap-3',
                        'rounded-lg px-3 py-1.5',
                        'transition-all duration-150',
                        isActive
                          ? 'bg-accent-primary/[0.12] text-accent-primary border-l-2 border-accent-primary shadow-token-sm'
                          : 'text-earth-400 hover:text-earth-200 hover:bg-earth-800/60 border-l-2 border-transparent',
                      ].join(' ')}
                    >
                      <Icon
                        className={[
                          'w-[18px] h-[18px] flex-shrink-0 transition-colors duration-150',
                          isActive ? 'text-accent-primary' : 'text-earth-500 group-hover/item:text-earth-300',
                        ].join(' ')}
                      />
                      {isMenuOpen && (
                        <span
                          className={[
                            'text-sm font-medium truncate transition-colors duration-150',
                            isActive ? 'text-accent-primary' : 'text-earth-300 group-hover/item:text-earth-100',
                          ].join(' ')}
                        >
                          {name}
                        </span>
                      )}
                    </button>

                    {/* Tooltip for collapsed mode */}
                    {!isMenuOpen && (
                      <div
                        aria-hidden="true"
                        className={[
                          'pointer-events-none absolute left-full top-1/2 -translate-y-1/2 ml-3 z-50',
                          'px-3 py-2 bg-earth-800 border border-earth-700/60 rounded-token-lg shadow-token-lg',
                          'whitespace-nowrap',
                          'opacity-0 scale-95 group-hover/item:opacity-100 group-hover/item:scale-100',
                          'transition-all duration-150 ease-out',
                        ].join(' ')}
                      >
                        <div className="text-sm font-semibold text-earth-100">{name}</div>
                        <div className="text-xs text-earth-400 mt-0.5">{desc}</div>
                        {/* Arrow */}
                        <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-earth-700/60" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="mt-1.5" />
          </div>
        ))}
      </nav>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <div className="p-3 border-t border-earth-700/50 flex-shrink-0">
        {isMenuOpen ? (
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-earth-800/40 transition-colors cursor-default">
            <div className="w-8 h-8 rounded-full bg-earth-800 border border-earth-600/50 flex items-center justify-center text-xs font-bold text-accent-primary flex-shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-earth-200 truncate">{displayName}</div>
              <div className="text-xs text-earth-500 capitalize">{user?.role || 'Użytkownik'}</div>
            </div>
            <button
              onClick={clearAuth}
              title="Wyloguj się"
              aria-label="Wyloguj się"
              className="p-1.5 rounded-md hover:bg-earth-700 text-earth-500 hover:text-accent-danger transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="relative group/logout">
            <div className="w-8 h-8 rounded-full bg-earth-800 border border-earth-600/50 flex items-center justify-center text-xs font-bold text-accent-primary mx-auto cursor-default">
              {initials}
            </div>
            <button
              onClick={clearAuth}
              title="Wyloguj się"
              className="absolute -top-1 -right-1 opacity-0 group-hover/logout:opacity-100 w-4 h-4 bg-accent-danger/80 rounded-full flex items-center justify-center transition-opacity"
            >
              <LogOut className="w-2.5 h-2.5 text-white" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Public export ──────────────────────────────────────────────────────────────

export function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        aria-label="Otwórz menu"
        className="md:hidden fixed top-4 left-4 z-40 p-2 bg-earth-900/90 rounded-xl border border-earth-700/60 text-earth-400 hover:text-earth-200 transition-colors shadow-token-md"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Desktop sidebar */}
      <div className="hidden md:block h-screen sticky top-0 flex-shrink-0">
        <SidebarContent />
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-earth-950/80 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          {/* Drawer */}
          <div className="relative h-full flex-shrink-0">
            <SidebarContent onItemClick={() => setMobileOpen(false)} />
          </div>
          {/* Close button */}
          <button
            onClick={() => setMobileOpen(false)}
            aria-label="Zamknij menu"
            className="absolute top-4 right-4 p-2 text-earth-500 hover:text-earth-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}
    </>
  );
}
