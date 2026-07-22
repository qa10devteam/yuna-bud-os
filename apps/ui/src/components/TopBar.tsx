'use client';

import { useRef, useState, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { NotificationsBell } from '@/components/NotificationsBell';
import TenderFTSSearch from '@/components/TenderFTSSearch';
import { LogOut, ChevronDown } from 'lucide-react';

// ── Module display names ────────────────────────────────────────────────────

const MODULE_NAMES: Record<string, string> = {
  dashboard:    'Dashboard',
  zwiad:        'Przetargi',
  pipeline:     'Lejek',
  bookmarks:    'Bookmarki',
  silnik:       'Silnik AI',
  decyzja:      'Decyzja',
  kosztorys:    'Kosztorys',
  'bid-intelligence': 'Bid Intel',
  oferta:       'Oferta',
  contracts:    'Kontrakty',
  documents:    'Dokumenty',
  'buyer-crm':  'Zamawiający',
  competitors:  'Konkurenci',
  'market-intel': 'Rynek',
  icb:          'Cennik ICB',
  logistyka:    'Logistyka',
  resources:    'Zasoby',
  team:         'Zespół',
  analytics:    'Analityka',
  reports:      'Raporty',
  settings:     'Ustawienia',
  system:       'System',
};

// ── Derive module name from pathname ───────────────────────────────────────

function useModuleName(): string {
  const currentModule = useStore((s) => s.currentModule);
  // currentModule may be set from store; also derive from pathname as fallback
  if (currentModule && MODULE_NAMES[currentModule]) {
    return MODULE_NAMES[currentModule];
  }
  // Try to match the store key directly
  return MODULE_NAMES[currentModule] ?? currentModule ?? 'Dashboard';
}

// ── TopBar component ────────────────────────────────────────────────────────

export function TopBar() {
  const currentModule = useStore((s) => s.currentModule);
  const user          = useStore((s) => s.user);
  const clearAuth     = useStore((s) => s.clearAuth);

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!dropdownOpen) return;

    const handleOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, [dropdownOpen]);

  // Breadcrumb: map currentModule to display name
  const moduleName = MODULE_NAMES[currentModule] ?? currentModule ?? 'Dashboard';

  // User initials
  const initials = (user?.name ?? 'U')
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();

  const handleLogout = () => {
    setDropdownOpen(false);
    clearAuth();
  };

  return (
    <header
      className="sticky top-0 z-30 flex items-center px-6"
      style={{
        height:               '56px',
        background:           'rgba(8,12,23,0.95)',
        backdropFilter:       'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom:         '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* ── Left: breadcrumb ── */}
      <div className="flex items-center gap-2 min-w-[160px]">
        <span
          className="text-sm font-semibold"
          style={{ color: '#e8edf5' }}
        >
          BudOS
        </span>
        <span
          className="text-sm font-medium select-none"
          style={{ color: '#334155' }}
        >
          /
        </span>
        <span
          className="text-sm font-medium"
          style={{ color: '#64748b' }}
        >
          {moduleName}
        </span>
      </div>

      {/* ── Center: search with ⌘K badge ── */}
      <div className="flex-1 flex justify-center">
        <div className="relative w-full max-w-[400px]">
          <TenderFTSSearch />
          {/* ⌘K keyboard shortcut badge — overlaid in top-right of search container */}
          <div className="pointer-events-none absolute right-3 top-3 flex items-center">
            <span className="text-slate-500 text-xs bg-slate-800 px-1.5 py-0.5 rounded font-mono">
              ⌘K
            </span>
          </div>
        </div>
      </div>

      {/* ── Right: notifications + avatar ── */}
      <div className="flex items-center gap-2 min-w-[160px] justify-end">
        <NotificationsBell />

        {/* Avatar + dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setDropdownOpen((v) => !v)}
            className="flex items-center gap-1.5 rounded-xl px-1.5 py-1 transition-colors hover:bg-white/[0.06]"
            aria-label="Menu użytkownika"
          >
            {/* Avatar circle with emerald dot indicator */}
            <div className="relative">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold text-white shrink-0"
                style={{
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                }}
              >
                {initials}
              </div>
              {/* Emerald online dot */}
              <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-[#080c17]" />
            </div>
            <ChevronDown
              className="w-3 h-3 transition-transform"
              style={{
                color: '#64748b',
                transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
              }}
            />
          </button>

          {/* Dropdown menu */}
          {dropdownOpen && (
            <div
              className="absolute right-0 top-[calc(100%+8px)] w-56 rounded-xl overflow-hidden"
              style={{
                background:   '#1a2235',
                border:       '1px solid rgba(255,255,255,0.1)',
                boxShadow:    '0 16px 40px rgba(0,0,0,0.5)',
                zIndex:       50,
              }}
            >
              {/* User info row */}
              <div
                className="px-4 py-3 flex flex-col gap-0.5"
                style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
              >
                <span
                  className="text-[13px] font-semibold truncate"
                  style={{ color: '#e8edf5' }}
                >
                  {user?.name ?? 'Użytkownik'}
                </span>
                <span
                  className="text-[11px] truncate"
                  style={{ color: '#64748b' }}
                >
                  {user?.email ?? ''}
                </span>
              </div>

              {/* Separator */}
              <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)' }} />

              {/* Logout button */}
              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors hover:bg-white/[0.06]"
                style={{ color: '#e8edf5' }}
              >
                <LogOut className="w-4 h-4" style={{ color: '#64748b' }} />
                Wyloguj się
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
