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
      { id: 'rynek',        icon: BarChart3,       name: 'Rynek S6',   desc: 'Dashboard BZP · TED · GUS' },
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
  const planName = user?.plan ?? 'Fundament';

  return (
    <div
      className={[
        'relative flex flex-col h-full',
        'bg-ink-950 border-r border-ink-line',
        'transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-300 ease-in-out',
        isMenuOpen ? 'w-60' : 'w-[68px]',
      ].join(' ')}
    >
      {/* ── Logo / Header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 h-16 border-b border-ink-line shrink-0">
        {isMenuOpen ? (
          /* Full logo */
          <div className="flex items-center gap-2.5 select-none">
            <img
              src="/brand/B01-app-icon-budos.png"
              alt="BudOS"
              className="w-7 h-7 rounded-md object-cover shrink-0"
            />
            <div className="flex flex-col leading-none">
              <div className="flex items-center gap-1.5">
                <span className="text-[13px] font-bold text-white tracking-tight">YU-NA</span>
                <span className="text-[#10b981] font-light text-[13px]">|</span>
                <span className="text-[13px] font-bold text-white tracking-tight">BudOS</span>
              </div>
              <span className="text-[9px] uppercase tracking-[0.12em] text-slate-600 mt-0.5">System Decyzyjny</span>
            </div>
          </div>
        ) : (
          /* Signet icon — SVG logo */
          <img
            src="/brand/B01-app-icon-budos.png"
            alt="BudOS"
            className="w-8 h-8 rounded-lg object-cover"
          />
        )}

        {isMenuOpen && <NotificationsBell />}

        <button type="button"
          onClick={toggleMenu}
          aria-label={isMenuOpen ? 'Zwiń menu' : 'Rozwiń menu'}
          className="p-1.5 rounded-md hover:bg-ink-800 text-slate-600 hover:text-slate-200 transition-colors duration-150 ml-1 shrink-0"
        >
          {isMenuOpen
            ? <ChevronLeft  className="w-4 h-4" />
            : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {/* ── Navigation ─────────────────────────────────────────────────── */}
      <nav className="flex-1 py-2 px-2 overflow-y-auto">
        {moduleGroups.map(({ label, GroupIcon, items }, groupIndex) => (
          <div key={label} className="mb-1">
            {/* Separator line before every group except the first */}
            {groupIndex > 0 && (
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', marginBottom: '6px', marginTop: '4px' }} />
            )}

            {/* Group header — label only, no icon */}
            {isMenuOpen ? (
              <div className="px-2 py-1 mb-0.5">
                <span className="text-[9px] font-semibold text-slate-700 uppercase tracking-[0.12em] truncate">
                  {label}
                </span>
              </div>
            ) : (
              /* In collapsed mode: small dot as visual spacer instead of icon */
              <div className="flex justify-center py-1 mb-0.5">
                <div className="w-1 h-1 rounded-full bg-slate-800" />
              </div>
            )}

            {/* Items */}
            <div className="space-y-0.5">
              {items.map(({ id, icon: Icon, name, desc }) => {
                const isActive = currentModule === id;
                return (
                  <div key={id} className="relative group/item">
                    <button type="button"
                      onClick={() => {
                        setCurrentModule(id as Parameters<typeof setCurrentModule>[0]);
                        onItemClick?.();
                      }}
                      aria-current={isActive ? 'page' : undefined}
                      style={
                        isActive
                          ? {
                              background: 'rgba(16,185,129,0.1)',
                              borderLeft: '2px solid #10b981',
                              color: '#e8edf5',
                            }
                          : { paddingLeft: '2px' }
                      }
                      className={[
                        'relative w-full flex items-center gap-3',
                        'rounded-lg px-3 py-1.5',
                        'transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150',
                        isActive
                          ? ''
                          : 'text-slate-500 hover:text-slate-200',
                      ].join(' ')}
                      onMouseEnter={(e) => {
                        if (!isActive) {
                          (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.04)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) {
                          (e.currentTarget as HTMLButtonElement).style.background = '';
                        }
                      }}
                    >
                      <Icon
                        className={[
                          'w-[18px] h-[18px] shrink-0 transition-colors duration-150',
                          isActive ? 'text-em' : 'text-slate-600 group-hover/item:text-slate-300',
                        ].join(' ')}
                      />
                      {isMenuOpen && (
                        <span
                          className={[
                            'text-sm font-medium truncate transition-colors duration-150',
                            isActive ? 'text-slate-100' : 'text-slate-400 group-hover/item:text-slate-100',
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
                          'px-3 py-2 bg-ink-800 border border-ink-line rounded-xl shadow-lg',
                          'whitespace-nowrap',
                          'opacity-0 scale-95 group-hover/item:opacity-100 group-hover/item:scale-100',
                          'transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-150 ease-out',
                        ].join(' ')}
                      >
                        <div className="text-sm font-semibold text-slate-100">{name}</div>
                        <div className="text-xs text-slate-500 mt-0.5">{desc}</div>
                        {/* Arrow */}
                        <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-ink-line" />
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
      <div className="p-3 border-t border-ink-line shrink-0">
        {isMenuOpen ? (
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-ink-800 transition-colors cursor-default">
            <div className="w-8 h-8 rounded-full bg-ink-800 border border-ink-line flex items-center justify-center text-xs font-bold text-em shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-200 truncate">{displayName}</div>
              <div className="text-xs text-slate-600 capitalize">{user?.role || 'Użytkownik'}</div>
              {/* Plan badge */}
              <span
                style={{
                  color: '#10b981',
                  fontSize: '10px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  lineHeight: '1.2',
                }}
              >
                {planName}
              </span>
            </div>
            <button type="button"
              onClick={clearAuth}
              title="Wyloguj się"
              aria-label="Wyloguj się"
              className="p-1.5 rounded-md hover:bg-ink-700 text-slate-600 hover:text-nogo transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="relative group/logout">
            <div className="w-8 h-8 rounded-full bg-ink-800 border border-ink-line flex items-center justify-center text-xs font-bold text-em mx-auto cursor-default">
              {initials}
            </div>
            <button type="button"
              onClick={clearAuth}
              title="Wyloguj się"
              className="absolute -top-1 -right-1 opacity-0 group-hover/logout:opacity-100 w-4 h-4 bg-nogo/80 rounded-full flex items-center justify-center transition-opacity"
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
      <button type="button"
        onClick={() => setMobileOpen(true)}
        aria-label="Otwórz menu"
        className="md:hidden fixed top-4 left-4 z-40 p-2 bg-ink-900 rounded-xl border border-ink-line text-slate-500 hover:text-slate-200 transition-colors shadow-md"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Desktop sidebar */}
      <div className="hidden md:block h-screen sticky top-0 shrink-0">
        <SidebarContent />
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-ink-950/80 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          {/* Drawer */}
          <div className="relative h-full shrink-0">
            <SidebarContent onItemClick={() => setMobileOpen(false)} />
          </div>
          {/* Close button */}
          <button type="button"
            onClick={() => setMobileOpen(false)}
            aria-label="Zamknij menu"
            className="absolute top-4 right-4 p-2 text-slate-500 hover:text-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}
    </>
  );
}
