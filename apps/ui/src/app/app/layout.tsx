'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'motion/react';
import {
  LayoutDashboard,
  Radar,
  Brain,
  Calculator,
  LogOut,
  Menu,
  GitBranch,
  Scale,
  FileText,
  BarChart2,
  Users,
  Truck,
  TrendingUp,
  Database,
  Swords,
  BookOpen,
  FolderOpen,
  Settings,
  Target,
  ChevronLeft,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { TopBar } from '@/components/TopBar';
import { PageTransition } from '@/components/ui/PageTransition';

// ── Nav config ─────────────────────────────────────────────────────────────────

interface NavItem {
  label: string;
  href:  string;
  icon:  React.ElementType;
}

interface NavSection {
  section: string;
  items:   NavItem[];
}

const NAV: NavSection[] = [
  {
    section: 'GŁÓWNE',
    items: [
      { label: 'Dashboard',      href: '/app',                    icon: LayoutDashboard },
    ],
  },
  {
    section: 'ZWIAD',
    items: [
      { label: 'Przetargi',      href: '/app/zwiad',              icon: Radar           },
      { label: 'Lejek',          href: '/app/pipeline',           icon: GitBranch       },
      { label: 'Bookmarki',      href: '/app/bookmarks',          icon: BookOpen        },
    ],
  },
  {
    section: 'ANALIZA',
    items: [
      { label: 'Silnik AI',      href: '/app/silnik',             icon: Brain           },
      { label: 'Decyzja',        href: '/app/decyzja',            icon: Scale           },
      { label: 'Kosztorys',      href: '/app/kosztorys',          icon: Calculator      },
      { label: 'Bid Intel',      href: '/app/bid-intelligence',   icon: Swords          },
    ],
  },
  {
    section: 'OFERTOWANIE',
    items: [
      { label: 'Oferta',         href: '/app/oferta',             icon: FileText        },
      { label: 'Kontrakty',      href: '/app/contracts',          icon: Target          },
      { label: 'Dokumenty',      href: '/app/documents',          icon: FolderOpen      },
    ],
  },
  {
    section: 'RYNEK',
    items: [
      { label: 'Zamawiający',    href: '/app/buyer-crm',          icon: Users           },
      { label: 'Konkurenci',     href: '/app/competitors',        icon: TrendingUp      },
      { label: 'Rynek',          href: '/app/market-intel',       icon: BarChart2       },
      { label: 'Ceny ICB',       href: '/app/icb',                icon: Database        },
    ],
  },
  {
    section: 'REALIZACJA',
    items: [
      { label: 'Logistyka',      href: '/app/logistyka',          icon: Truck           },
      { label: 'Zasoby',         href: '/app/resources',          icon: Users           },
      { label: 'Zespół',         href: '/app/team',               icon: Users           },
    ],
  },
  {
    section: 'RAPORTOWANIE',
    items: [
      { label: 'Analityka',      href: '/app/analytics',          icon: BarChart2       },
      { label: 'Raporty',        href: '/app/reports',            icon: FileText        },
    ],
  },
  {
    section: 'SYSTEM',
    items: [
      { label: 'Ustawienia',     href: '/app/settings',           icon: Settings        },
    ],
  },
];

// ── Sidebar item ───────────────────────────────────────────────────────────────

interface SidebarItemProps {
  item:      NavItem;
  active:    boolean;
  collapsed: boolean;
}

function SidebarItem({ item, active, collapsed }: SidebarItemProps) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      title={collapsed ? item.label : undefined}
      className={[
        'flex items-center py-2 rounded-xl text-sm font-medium transition-[color,background-color,border-color,opacity,transform,box-shadow]',
        collapsed ? 'justify-center px-0' : 'gap-3 px-3',
        active
          ? 'text-emerald-400 border-l-2 border-emerald-400'
          : 'text-slate-500 hover:text-slate-200 border-l-2 border-transparent',
      ].join(' ')}
      style={
        active
          ? {
              background:     'rgba(16,185,129,0.08)',
              backdropFilter: 'blur(8px)',
              paddingLeft:    collapsed ? undefined : '10px',
            }
          : undefined
      }
      onMouseEnter={(e) => {
        if (!active) {
          (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          (e.currentTarget as HTMLElement).style.background = '';
        }
      }}
    >
      <Icon
        className={['w-4 h-4 shrink-0', active ? 'text-emerald-400' : 'text-slate-600'].join(' ')}
        strokeWidth={1.75}
      />
      {!collapsed && <span className="leading-none">{item.label}</span>}
    </Link>
  );
}

// ── Shell ──────────────────────────────────────────────────────────────────────

export default function AppShell({ children }: { children: React.ReactNode }) {
  const user        = useStore((s) => s.user);
  const accessToken = useStore((s) => s.accessToken);
  const clearAuth   = useStore((s) => s.clearAuth);
  const router      = useRouter();
  const pathname    = usePathname();
  const isAuth      = !!(user && accessToken);

  // Wait for Zustand persist rehydration before redirecting
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => { setHydrated(true); }, []);

  const [mobileOpen,  setMobileOpen]  = useState(false);
  const [collapsed,   setCollapsed]   = useState(false);

  useEffect(() => {
    if (hydrated && !isAuth) router.replace('/login');
  }, [hydrated, isAuth, router]);

  // Close mobile sidebar on navigation
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  if (!hydrated) return null;
  if (!isAuth) return null;

  const handleLogout = () => {
    clearAuth();
    router.push('/');
  };

  // User initials (reused in sidebar footer)
  const initials = (user?.name ?? 'U')
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();

  const SidebarContent = (
    <div className="flex flex-col h-full">
      {/* ── Logo + collapse toggle ── */}
      <div
        className={[
          'py-4 flex items-center shrink-0 border-b border-white/[0.06]',
          collapsed ? 'flex-col gap-2 px-0 justify-center' : 'gap-3 px-4 justify-between',
        ].join(' ')}
      >
        <div className="flex items-center gap-3">
          <img
            src="/brand/B01-app-icon-budos.png"
            alt="BudOS"
            className="w-8 h-8 rounded-lg object-cover shrink-0"
            style={{ boxShadow: '0 0 0 1px rgba(255,255,255,0.08)' }}
          />
          {!collapsed && (
            <div className="flex flex-col leading-none">
              <div className="flex items-center gap-1.5">
                <span className="text-[13px] font-bold text-white tracking-tight" style={{ fontFamily: 'var(--font-space)' }}>YU-NA</span>
                <span className="text-[#10b981] font-light text-[13px] leading-none">|</span>
                <span className="text-[13px] font-bold text-white tracking-tight" style={{ fontFamily: 'var(--font-space)' }}>BudOS</span>
              </div>
              <span className="text-[9px] uppercase tracking-[0.12em] text-slate-600 mt-0.5">System Decyzyjny</span>
            </div>
          )}
        </div>

        {/* Collapse / expand button */}
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          className="p-1 rounded-lg text-slate-600 hover:text-slate-400 hover:bg-white/[0.06] transition-[color,background-color,border-color,opacity,transform,box-shadow] shrink-0"
          title={collapsed ? 'Rozwiń sidebar' : 'Zwiń sidebar'}
        >
          {collapsed
            ? <Menu className="w-4 h-4" />
            : <ChevronLeft className="w-4 h-4" />
          }
        </button>
      </div>

      {/* ── Nav sections ── */}
      <nav className={['flex-1 py-2 overflow-y-auto space-y-5', collapsed ? 'px-1' : 'px-3'].join(' ')}>
        {NAV.map((section) => (
          <div key={section.section}>
            {/* Section label — only in expanded mode */}
            {!collapsed && (
              <p className="text-[10px] font-semibold tracking-widest text-slate-500 uppercase px-3 mb-2">
                {section.section}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <SidebarItem
                  key={item.href}
                  item={item}
                  collapsed={collapsed}
                  active={
                    item.href === '/app'
                      ? pathname === '/app'
                      : pathname === item.href || pathname.startsWith(item.href + '/')
                  }
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* ── Footer: user avatar ── */}
      <div className={['border-t border-white/[0.06] shrink-0', collapsed ? 'px-1 py-3' : 'px-3 pb-4 pt-3'].join(' ')}>
        {collapsed ? (
          /* Collapsed: just the initials circle + logout icon stacked */
          <div className="flex flex-col items-center gap-2">
            <div
              className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center text-[10px] font-bold text-emerald-400 shrink-0"
              title={user?.name ?? 'Użytkownik'}
            >
              {initials}
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-[color,background-color,border-color,opacity,transform,box-shadow]"
              title="Wyloguj"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          /* Expanded: circle + name/email + logout */
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 px-1 min-w-0">
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center text-[10px] font-bold text-emerald-400 shrink-0">
                {initials}
              </div>
              <div className="flex flex-col leading-tight min-w-0">
                <span className="text-[11px] font-semibold text-slate-300 truncate">
                  {user?.name?.split(' ')[0] ?? 'Użytkownik'}
                </span>
                <span className="text-[10px] text-slate-600 truncate max-w-[120px]">
                  {user?.email}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="p-2 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-[color,background-color,border-color,opacity,transform,box-shadow]"
              title="Wyloguj"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );

  const sidebarWidth = collapsed ? '56px' : '240px';

  return (
    <div className="min-h-screen flex" style={{ background: '#050508' }}>

      {/* ── Desktop sidebar ── */}
      <aside
        className="hidden lg:flex flex-col fixed top-0 left-0 h-screen z-30 transition-[width] duration-200"
        style={{
          width:               sidebarWidth,
          background:          'rgba(5,5,8,0.95)',
          borderRight:         '1px solid rgba(255,255,255,0.07)',
          backdropFilter:      'blur(32px)',
          WebkitBackdropFilter:'blur(32px)',
        }}
      >
        {SidebarContent}
      </aside>

      {/* ── Mobile sidebar backdrop ── */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              key="sidebar"
              initial={{ x: -260 }}
              animate={{ x: 0 }}
              exit={{ x: -260 }}
              transition={{ type: 'spring', damping: 28, stiffness: 300 }}
              className="fixed top-0 left-0 h-screen z-50 flex flex-col lg:hidden"
              style={{
                width:               '240px',
                background:          'rgba(5,5,8,0.98)',
                borderRight:         '1px solid rgba(255,255,255,0.08)',
                backdropFilter:      'blur(32px)',
                WebkitBackdropFilter:'blur(32px)',
              }}
            >
              {SidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* ── Main area ── */}
      <div
        className="flex-1 flex flex-col min-w-0 transition-[margin] duration-200"
        style={{ marginLeft: `var(--sidebar-offset, 0)` }}
      >
        {/* CSS var trick to apply dynamic margin on lg+ */}
        <style>{`@media (min-width: 1024px) { :root { --sidebar-offset: ${sidebarWidth}; } }`}</style>

        {/* Mobile topbar hamburger */}
        <div className="lg:hidden flex items-center px-4 py-3 border-b border-white/[0.06]">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="p-2 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-white/[0.06] transition-[color,background-color,border-color,opacity,transform,box-shadow]"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>

        {/* ── Topbar ── */}
        <TopBar />

        {/* ── Page content ── */}
        <main
          className="flex-1 overflow-y-auto"
          style={{ background: '#050508' }}
        >
          <PageTransition>
            {children}
          </PageTransition>
        </main>
      </div>
    </div>
  );
}
