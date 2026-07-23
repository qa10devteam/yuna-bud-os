'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { motion, useReducedMotion } from 'motion/react';
import { useStore } from '@/store/useStore';
import {
  ArrowRight, Bell, LogOut, TrendingUp, Activity, FileText,
  Zap, BarChart3, ChevronRight,
} from 'lucide-react';

// ── YU-NA Hub v3 ─────────────────────────────────────────────────────────────
// Bud.OS: hero card z żywym screenshotem + metrykami.
// Infra.OS / Dev.OS: pełne karty z opisem — widoczne nazwy, bez "in shadow".

export default function YunaHubPage() {
  const user        = useStore((s) => s.user);
  const accessToken = useStore((s) => s.accessToken);
  const logout      = useStore((s) => s.clearAuth);
  const router      = useRouter();
  const reduce      = useReducedMotion();
  const isAuth      = !!(user && accessToken);

  const [hydrated, setHydrated] = useState(() => {
    if (typeof window === 'undefined') return false;
    try {
      const raw = localStorage.getItem('yuna-store');
      if (!raw) return false;
      const parsed = JSON.parse(raw);
      return !!(parsed?.state?.accessToken && parsed?.state?.user);
    } catch { return false; }
  });

  useEffect(() => { setHydrated(true); }, []);
  useEffect(() => {
    if (hydrated && !isAuth) router.replace('/login');
  }, [hydrated, isAuth, router]);

  if (!hydrated || !isAuth) return null;

  const firstName = user?.name?.split(' ')[0] || 'użytkowniku';
  const initials  = user?.name?.slice(0, 2).toUpperCase() || 'U';

  return (
    <div
      className="min-h-screen font-display"
      style={{
        background: '#f8f9fb',
        backgroundImage: 'radial-gradient(circle, #d1d5db 1px, transparent 1px)',
        backgroundSize: '22px 22px',
      }}
    >
      {/* ─── Nav ─────────────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-white/90 border-b border-zinc-100 shadow-sm">
        <div className="max-w-5xl mx-auto px-6 h-[60px] flex items-center justify-between">
          <Link href="/app" className="flex items-center gap-2.5">
            <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={26} height={26} className="rounded-lg" />
            <span className="font-semibold text-[13.5px] tracking-tight text-zinc-900">YU-NA</span>
          </Link>
          <div className="flex items-center gap-1.5">
            <button type="button" className="p-2 rounded-full hover:bg-zinc-100 transition-colors" title="Powiadomienia">
              <Bell className="w-4 h-4 text-zinc-400" />
            </button>
            <div className="flex items-center gap-2 pl-3 border-l border-zinc-200 ml-1">
              <div className="w-7 h-7 rounded-full bg-zinc-900 flex items-center justify-center text-white text-[11px] font-semibold shrink-0">
                {initials}
              </div>
              <span className="text-[13px] text-zinc-600 font-medium hidden sm:block">{user?.name}</span>
              <button
                type="button"
                onClick={() => { logout(); router.push('/login'); }}
                className="p-2 rounded-full hover:bg-zinc-100 transition-colors"
                title="Wyloguj"
              >
                <LogOut className="w-4 h-4 text-zinc-400" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* ─── Main ────────────────────────────────────────────────────────────── */}
      <main className="max-w-5xl mx-auto px-6 py-12">

        {/* Welcome row */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="flex items-center justify-between mb-8"
        >
          <div>
            <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">
              Witaj, {firstName}.
            </h1>
            <p className="mt-1 text-[13.5px] text-zinc-400">
              YU-NA Intelligence Platform
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-zinc-500 bg-white border border-zinc-200 rounded-full px-3 py-1.5 shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
            Wszystkie systemy online
          </div>
        </motion.div>

        {/* ─── Bud.OS hero card ──────────────────────────────────────────────── */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
          className="mb-4"
        >
          <Link
            href="/app/zwiad"
            className="group relative block rounded-2xl bg-zinc-950 overflow-hidden hover:ring-1 hover:ring-white/10 transition-all shadow-2xl shadow-zinc-900/30"
          >
            {/* Ambient glow */}
            <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-emerald-500/6 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-20 left-40 w-64 h-64 bg-emerald-500/4 rounded-full blur-3xl pointer-events-none" />

            {/* Header row */}
            <div className="relative z-10 flex items-center justify-between px-7 pt-6 pb-5">
              <div className="flex items-center gap-3.5">
                <Image src="/brand/B01-app-icon-budos.png" alt="Bud.OS" width={40} height={40} className="rounded-xl shrink-0" />
                <div>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-[10px] font-bold text-emerald-400 tracking-[0.14em] uppercase">Professional</span>
                  </div>
                  <h2 className="text-[18px] font-bold text-white leading-none tracking-tight">Bud.OS</h2>
                </div>
              </div>

              {/* Metrics */}
              <div className="flex items-center gap-2.5 shrink-0">
                {[
                  { icon: Activity,   value: '14',  label: 'nowych dziś' },
                  { icon: FileText,   value: '3',   label: 'w analizie' },
                  { icon: TrendingUp, value: '—',   label: 'win rate', accent: true },
                ].map((m) => (
                  <div key={m.label} className="flex flex-col items-center px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.07] min-w-[76px]">
                    <m.icon className={`w-3.5 h-3.5 mb-1.5 ${m.accent ? 'text-emerald-400' : 'text-zinc-500'}`} />
                    <div className={`text-[1.35rem] font-bold leading-none tabular-nums ${m.accent ? 'text-emerald-400' : 'text-white'}`}>
                      {m.value}
                    </div>
                    <div className="text-[9.5px] text-zinc-500 mt-1 text-center leading-tight">{m.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Screenshot */}
            <div className="relative z-10 mx-4 mb-0 rounded-t-xl overflow-hidden border border-white/[0.07] border-b-0">
              {/* Browser chrome */}
              <div className="flex items-center gap-1.5 px-3.5 py-2.5 bg-zinc-900/90 border-b border-white/[0.05]">
                <span className="w-2 h-2 rounded-full bg-red-500/50" />
                <span className="w-2 h-2 rounded-full bg-amber-400/50" />
                <span className="w-2 h-2 rounded-full bg-emerald-500/50" />
                <div className="flex-1 mx-2.5 bg-zinc-800/70 rounded h-4 flex items-center px-2">
                  <span className="text-[9.5px] text-zinc-500 font-mono">app.yu-na.io/zwiad</span>
                </div>
              </div>
              <Image
                src="/brand/live-zwiad.png"
                alt="BudOS Zwiad Przetargowy"
                width={1440}
                height={900}
                className="w-full h-auto block"
                priority
              />
            </div>

            {/* Footer CTA */}
            <div className="relative z-10 px-7 py-4 flex items-center justify-between border-t border-white/[0.05]">
              <p className="text-[12.5px] text-zinc-500 max-w-[48ch]">
                Przetargi z BZP i TED, scoring GO/NO-GO, kosztorysy KNR/ICB, analiza konkurencji.
              </p>
              <div className="flex items-center gap-1.5 text-[13px] font-semibold text-emerald-400 group-hover:gap-2.5 transition-all shrink-0">
                Otwórz Bud.OS <ArrowRight className="w-3.5 h-3.5" />
              </div>
            </div>
          </Link>
        </motion.div>

        {/* ─── Infra.OS + Dev.OS ─────────────────────────────────────────────── */}
        <div className="grid md:grid-cols-2 gap-4">
          {[
            {
              id: 'infra',
              icon: Zap,
              name: 'Infra.OS',
              tagline: 'Zarządzanie infrastrukturą budowy',
              desc: 'Harmonogramy, zasoby, logistyka placu budowy i monitoring postępów — wszystko w jednym miejscu.',
              eta: 'Q3 2026',
              color: 'amber' as const,
              delay: 0.12,
            },
            {
              id: 'dev',
              icon: BarChart3,
              name: 'Dev.OS',
              tagline: 'Analiza rynku nieruchomości',
              desc: 'Feasibility studies, ROI inwestycji, analiza lokalizacji i wyceny rynkowe dla deweloperów.',
              eta: 'Q4 2026',
              color: 'blue' as const,
              delay: 0.18,
            },
          ].map((p) => {
            const colorMap = {
              amber: {
                bg: 'from-amber-500/[0.06] to-orange-500/[0.03]',
                border: 'border-amber-200/60 hover:border-amber-300/80',
                iconBg: 'bg-amber-100',
                iconFg: 'text-amber-600',
                badge: 'text-amber-600 bg-amber-50 border border-amber-200',
                title: 'text-zinc-900',
                cta: 'text-amber-600 bg-amber-50 hover:bg-amber-100 border border-amber-200',
              },
              blue: {
                bg: 'from-blue-500/[0.06] to-indigo-500/[0.03]',
                border: 'border-blue-200/60 hover:border-blue-300/80',
                iconBg: 'bg-blue-100',
                iconFg: 'text-blue-600',
                badge: 'text-blue-600 bg-blue-50 border border-blue-200',
                title: 'text-zinc-900',
                cta: 'text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-200',
              },
            };
            const c = colorMap[p.color];

            return (
              <motion.div
                key={p.id}
                initial={reduce ? false : { opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.45, delay: p.delay, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className={`relative h-full p-6 rounded-2xl bg-gradient-to-br ${c.bg} border ${c.border} bg-white transition-all shadow-sm`}>
                  {/* Header */}
                  <div className="flex items-start justify-between mb-5">
                    <div className={`w-10 h-10 rounded-xl ${c.iconBg} flex items-center justify-center shrink-0`}>
                      <p.icon className={`w-5 h-5 ${c.iconFg}`} />
                    </div>
                    <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${c.badge}`}>
                      Wkrótce · {p.eta}
                    </span>
                  </div>

                  {/* Name + tagline */}
                  <h3 className={`text-[17px] font-bold ${c.title} leading-tight mb-1`}>{p.name}</h3>
                  <p className="text-[12px] font-medium text-zinc-500 mb-3">{p.tagline}</p>
                  <p className="text-[13px] text-zinc-500 leading-relaxed mb-6">{p.desc}</p>

                  {/* CTA */}
                  <button
                    type="button"
                    className={`inline-flex items-center gap-1.5 text-[12.5px] font-semibold px-3.5 py-2 rounded-lg transition-colors ${c.cta}`}
                  >
                    Powiadom mnie <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>

      </main>
    </div>
  );
}
