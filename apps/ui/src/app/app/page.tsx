'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { motion, useReducedMotion } from 'motion/react';
import { useStore } from '@/store/useStore';
import { ArrowRight, Bell, LogOut, TrendingUp, Activity, FileText, Zap, BarChart3 } from 'lucide-react';

// ── YU-NA Hub v2 ─────────────────────────────────────────────────────────────
// Marketplace of purchased products. Entry point after login.
// Design: Bud.OS = dark premium card (hero). Infra/Dev = coloured teaser cards.

export default function YunaHubPage() {
  const user        = useStore((s) => s.user);
  const accessToken = useStore((s) => s.accessToken);
  const logout      = useStore((s) => s.clearAuth);
  const router      = useRouter();
  const reduce      = useReducedMotion();
  const isAuth      = !!(user && accessToken);

  const [hydrated, setHydrated] = useState(false);
  useEffect(() => { setHydrated(true); }, []);
  useEffect(() => {
    if (hydrated && !isAuth) router.replace('/login');
  }, [hydrated, isAuth, router]);

  if (!hydrated || !isAuth) return null;

  const firstName = user?.name?.split(' ')[0] || 'użytkowniku';
  const initials  = user?.name?.slice(0, 2).toUpperCase() || 'U';

  return (
    <div className="min-h-screen bg-[#fafbfc] font-display" style={{ backgroundImage: 'radial-gradient(circle, #d4d4d4 1px, transparent 1px)', backgroundSize: '24px 24px' }}>

      {/* ─── Nav ───────────────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-white/85 border-b border-zinc-100">
        <div className="max-w-5xl mx-auto px-6 h-[62px] flex items-center justify-between">
          <Link href="/app" className="flex items-center gap-2.5">
            <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={26} height={26} className="rounded-lg" />
            <span className="font-semibold text-[14px] tracking-tight text-zinc-900">YU-NA</span>
          </Link>
          <div className="flex items-center gap-2">
            <button className="p-2 rounded-full hover:bg-zinc-100 transition-colors" title="Powiadomienia">
              <Bell className="w-4 h-4 text-zinc-400" />
            </button>
            <div className="flex items-center gap-2.5 pl-3 border-l border-zinc-200">
              <div className="w-8 h-8 rounded-full bg-zinc-900 flex items-center justify-center text-white text-[11px] font-semibold shrink-0">
                {initials}
              </div>
              <span className="text-[13px] text-zinc-700 font-medium hidden sm:block">{user?.name}</span>
              <button
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

      {/* ─── Main ──────────────────────────────────────────────────────────────── */}
      <main className="max-w-5xl mx-auto px-6 py-14">

        {/* Welcome */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="mb-10"
        >
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-[1.75rem] md:text-3xl font-bold text-zinc-900 tracking-tight">
                Witaj, {firstName}.
              </h1>
              <p className="mt-1.5 text-zinc-400 text-[14px]">
                Twoje produkty YU-NA Intelligence.
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-zinc-400 bg-white border border-zinc-200 rounded-full px-3 py-1.5 shadow-sm shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
              Wszystkie systemy online
            </div>
          </div>
        </motion.div>

        {/* ─── Bud.OS — hero card (dark) ────────────────────────────────────────── */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
          className="mb-4"
        >
          <Link
            href="/app/zwiad"
            className="group relative block rounded-2xl bg-zinc-950 overflow-hidden p-8 hover:ring-1 hover:ring-white/10 transition-all shadow-xl shadow-zinc-900/20"
          >
            {/* Glows */}
            <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/8 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute bottom-0 left-32 w-48 h-48 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />
            {/* Subtle grid */}
            <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'linear-gradient(rgba(16,185,129,1) 1px,transparent 1px),linear-gradient(90deg,rgba(16,185,129,1) 1px,transparent 1px)', backgroundSize: '40px 40px' }} />

            <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-8">
              {/* Left */}
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-5">
                  <Image src="/brand/B01-app-icon-budos.png" alt="Bud.OS" width={44} height={44} className="rounded-xl" />
                  <div>
                    <div className="text-[11px] font-semibold text-emerald-400 tracking-widest uppercase flex items-center gap-1.5 mb-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Professional
                    </div>
                    <h2 className="text-lg font-bold text-white leading-none">Bud.OS</h2>
                  </div>
                </div>
                <p className="text-zinc-400 text-[13.5px] leading-relaxed max-w-[46ch]">
                  Przetargi z BZP i TED, scoring GO/NO-GO, kosztorysy KNR/ICB, analiza konkurencji i dokumentacja ofertowa.
                </p>

                <div className="mt-6 flex items-center gap-1.5 text-[13px] font-medium text-emerald-400 group-hover:gap-3 transition-all">
                  Otwórz Bud.OS
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </div>

              {/* Right — metrics */}
              <div className="flex gap-3 md:gap-4 shrink-0">
                {[
                  { icon: Activity,    value: '14',  label: 'nowych dziś',   accent: false },
                  { icon: FileText,    value: '3',   label: 'w analizie',    accent: false },
                  { icon: TrendingUp,  value: '67%', label: 'win rate',      accent: true  },
                ].map((m) => (
                  <div key={m.label} className="flex flex-col items-center p-4 rounded-xl bg-white/5 border border-white/8 min-w-[80px]">
                    <m.icon className={`w-4 h-4 mb-2 ${m.accent ? 'text-emerald-400' : 'text-zinc-500'}`} />
                    <div className={`text-[1.4rem] font-bold leading-none ${m.accent ? 'text-emerald-400' : 'text-white'}`}>
                      {m.value}
                    </div>
                    <div className="text-[10px] text-zinc-500 mt-1 text-center leading-tight">{m.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </Link>
        </motion.div>

        {/* ─── Coming soon — 2 cards ────────────────────────────────────────────── */}
        <div className="grid md:grid-cols-2 gap-4">
          {[
            {
              id: 'infra',
              name: 'Infra.OS',
              subtitle: 'Zarządzanie infrastrukturą',
              desc: 'Logistyka budowy, zasoby ludzkie, harmonogramy i monitoring postępów.',
              icon: Zap,
              colorBg: 'from-amber-50 to-orange-50/40',
              colorBorder: 'border-amber-100/80 hover:border-amber-200',
              colorIcon: 'bg-amber-100',
              colorIconFg: 'text-amber-600',
              colorBadge: 'text-amber-600 bg-amber-50 border-amber-100',
              eta: 'Q3 2025',
              delay: 0.1,
            },
            {
              id: 'dev',
              name: 'Dev.OS',
              subtitle: 'Analiza rynku nieruchomości',
              desc: 'Feasibility studies, ROI, analiza lokalizacji i wyceny rynkowe.',
              icon: BarChart3,
              colorBg: 'from-blue-50 to-indigo-50/40',
              colorBorder: 'border-blue-100/80 hover:border-blue-200',
              colorIcon: 'bg-blue-100',
              colorIconFg: 'text-blue-600',
              colorBadge: 'text-blue-600 bg-blue-50 border-blue-100',
              eta: 'Q4 2025',
              delay: 0.15,
            },
          ].map((p) => (
            <motion.div
              key={p.id}
              initial={reduce ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: p.delay, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className={`relative h-full p-6 rounded-2xl bg-gradient-to-br ${p.colorBg} border ${p.colorBorder} transition-all`}>
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-10 h-10 rounded-xl ${p.colorIcon} flex items-center justify-center`}>
                    <p.icon className={`w-4.5 h-4.5 ${p.colorIconFg}`} />
                  </div>
                  <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full border ${p.colorBadge}`}>
                    Wkrótce
                  </span>
                </div>
                <h3 className="text-[15px] font-semibold text-zinc-800 mb-1">{p.name}</h3>
                <p className="text-[12px] text-zinc-500 mb-1">{p.subtitle}</p>
                <p className="text-[12.5px] text-zinc-400 leading-relaxed">{p.desc}</p>
                <div className="mt-5 flex items-center justify-between">
                  <button className="flex items-center gap-1.5 text-[12px] text-zinc-400 hover:text-zinc-600 transition-colors font-medium">
                    <Bell className="w-3.5 h-3.5" />
                    Powiadom mnie
                  </button>
                  <span className="text-[10px] text-zinc-400 font-mono">{p.eta}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </main>
    </div>
  );
}
