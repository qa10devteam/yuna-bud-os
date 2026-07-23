'use client';

import Image from 'next/image';
import Link from 'next/link';
import { motion, useReducedMotion } from 'motion/react';
import { ArrowRight, Search, BarChart3, FileText, Zap, Shield, Brain } from 'lucide-react';

// ── YU-NA Landing — Light Theme ─────────────────────────────────────────────────
// Design Read: B2B SaaS platform landing for construction industry buyers.
// Dials: VARIANCE 7 / MOTION 5 / DENSITY 4
// Accent: emerald (single). Font: Space Grotesk (display) + system (body).

export default function LandingPage() {
  const reduce = useReducedMotion();

  return (
    <div className="min-h-screen bg-[#fafbfc] text-zinc-900 antialiased overflow-x-hidden">
      {/* ─── Nav ─────────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 backdrop-blur-xl bg-white/80 border-b border-zinc-100">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <Image
              src="/brand/01-logo-concept.png"
              alt="YU-NA"
              width={28}
              height={28}
              className="rounded-lg"
            />
            <span className="font-semibold text-[15px] tracking-tight">YU-NA</span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-[13px] text-zinc-500 font-medium">
            <Link href="#products" className="hover:text-zinc-900 transition-colors">Produkty</Link>
            <Link href="#how" className="hover:text-zinc-900 transition-colors">Jak działa</Link>
            <Link href="/budos" className="hover:text-zinc-900 transition-colors">Bud.OS</Link>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-[13px] text-zinc-500 hover:text-zinc-900 transition-colors px-3 py-2 font-medium"
            >
              Zaloguj się
            </Link>
            <Link
              href="/signup"
              className="text-[13px] font-medium bg-zinc-900 text-white px-4 py-2 rounded-full hover:bg-zinc-800 transition-colors"
            >
              Wypróbuj
            </Link>
          </div>
        </div>
      </nav>

      {/* ─── Hero — Asymmetric Split ─────────────────────────────────────────── */}
      <section className="pt-28 pb-20 px-6">
        <div className="max-w-7xl mx-auto grid lg:grid-cols-12 gap-12 lg:gap-6 items-center min-h-[70dvh]">
          {/* Left — copy (7 cols) */}
          <div className="lg:col-span-7 max-w-xl">
            <motion.div
              initial={reduce ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <h1 className="text-4xl md:text-5xl lg:text-[3.5rem] font-bold tracking-tight leading-[1.08]">
                Przetargi budowlane.
                <br />
                <span className="text-emerald-600">Opanowane.</span>
              </h1>

              <p className="mt-6 text-zinc-500 text-lg leading-relaxed max-w-[50ch]">
                AI analizuje przetargi z BZP i TED, ocenia szanse i generuje kosztorysy. Decyzja GO/NO-GO w minuty zamiast godzin.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  href="/signup"
                  className="inline-flex items-center gap-2 bg-zinc-900 text-white px-6 py-3.5 rounded-full text-sm font-medium hover:bg-zinc-800 transition-all active:scale-[0.98] shadow-lg shadow-zinc-900/10"
                >
                  Załóż konto
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/budos"
                  className="inline-flex items-center gap-2 text-zinc-600 px-6 py-3.5 rounded-full text-sm font-medium border border-zinc-200 hover:border-zinc-300 hover:bg-white transition-all"
                >
                  Poznaj Bud.OS
                </Link>
              </div>
            </motion.div>
          </div>

          {/* Right — platform preview (5 cols) */}
          <motion.div
            className="lg:col-span-5"
            initial={reduce ? false : { opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="relative rounded-2xl bg-white border border-zinc-200/80 shadow-xl shadow-zinc-200/40 p-6 space-y-4">
              {/* Mini dashboard header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span className="text-xs font-medium text-zinc-400">Zwiad aktywny</span>
                </div>
                <span className="text-[11px] text-zinc-300 font-mono">BZP + TED</span>
              </div>

              {/* Fake tender rows — minimal, NOT a full screenshot */}
              <div className="space-y-2.5">
                {[
                  { score: 87, title: 'Budowa drogi S7 odc. Kraków-Nowy Targ', value: '42M PLN' },
                  { score: 72, title: 'Termomodernizacja ZS nr 4 w Katowicach', value: '8.2M PLN' },
                  { score: 64, title: 'Remont mostu na rzece Wisła km 341', value: '15M PLN' },
                ].map((t) => (
                  <div key={t.title} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-50 border border-zinc-100">
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold text-white ${
                      t.score >= 80 ? 'bg-emerald-500' : t.score >= 70 ? 'bg-amber-500' : 'bg-zinc-400'
                    }`}>
                      {t.score}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-medium text-zinc-700 truncate">{t.title}</div>
                      <div className="text-[11px] text-zinc-400">{t.value}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Bottom metric strip */}
              <div className="flex items-center justify-between pt-3 border-t border-zinc-100">
                <div className="text-center">
                  <div className="text-lg font-bold text-zinc-900">14</div>
                  <div className="text-[10px] text-zinc-400">Nowe dziś</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-emerald-600">67%</div>
                  <div className="text-[10px] text-zinc-400">Win rate</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-zinc-900">2.1s</div>
                  <div className="text-[10px] text-zinc-400">Avg analiza</div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── Products — Bento (2+1 asymmetric) ───────────────────────────────── */}
      <section id="products" className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
            Ekosystem YU-NA
          </h2>
          <p className="text-zinc-500 text-lg max-w-[55ch] mb-12">
            Trzy produkty. Jeden cel: dane zamiast domysłów w budownictwie.
          </p>

          <div className="grid md:grid-cols-5 gap-4">
            {/* Bud.OS — takes 3 cols (hero card) */}
            <div className="md:col-span-3 group relative p-8 rounded-2xl bg-zinc-900 text-white overflow-hidden">
              <div className="relative z-10">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-medium mb-6 border border-emerald-500/30">
                  Dostępny
                </div>
                <h3 className="text-2xl font-bold mb-3">Bud.OS</h3>
                <p className="text-zinc-400 leading-relaxed max-w-[40ch] mb-6">
                  System decyzyjny AI. Monitoring przetargów z BZP i TED, scoring GO/NO-GO, kosztorysy KNR, analiza konkurencji.
                </p>
                <Link
                  href="/budos"
                  className="inline-flex items-center gap-2 text-sm font-medium text-white hover:text-emerald-300 transition-colors"
                >
                  Dowiedz się więcej <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
              {/* Decorative gradient blob */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl" />
            </div>

            {/* Infra.OS + Dev.OS — stacked in 2 cols */}
            <div className="md:col-span-2 flex flex-col gap-4">
              <div className="flex-1 p-6 rounded-2xl bg-white border border-zinc-200 hover:border-zinc-300 hover:shadow-md transition-all">
                <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center mb-4">
                  <Shield className="w-5 h-5 text-amber-600" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Infra.OS</h3>
                <p className="text-zinc-500 text-sm leading-relaxed">
                  Zarządzanie infrastrukturą. Logistyka, zasoby, harmonogramy.
                </p>
                <span className="inline-block mt-4 text-xs text-amber-600 font-medium">Wkrótce</span>
              </div>

              <div className="flex-1 p-6 rounded-2xl bg-white border border-zinc-200 hover:border-zinc-300 hover:shadow-md transition-all">
                <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center mb-4">
                  <Brain className="w-5 h-5 text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Dev.OS</h3>
                <p className="text-zinc-500 text-sm leading-relaxed">
                  Analiza rynku nieruchomości. Feasibility studies, ROI.
                </p>
                <span className="inline-block mt-4 text-xs text-blue-600 font-medium">Wkrótce</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── How it works — vertical steps, no numbering ─────────────────────── */}
      <section id="how" className="py-24 px-6 bg-white">
        <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
          {/* Left — explanation */}
          <div>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6">
              Od danych do decyzji
            </h2>
            <p className="text-zinc-500 text-lg leading-relaxed mb-10 max-w-[50ch]">
              Połącz źródła przetargowe, pozwól AI ocenić i przygotować dokumentację.
            </p>

            <div className="space-y-8">
              {[
                {
                  icon: Search,
                  title: 'Monitoring',
                  desc: 'BZP, TED, e-Zamówienia. Nowe ogłoszenia trafiają do Ciebie w sekundy.',
                },
                {
                  icon: BarChart3,
                  title: 'Analiza AI',
                  desc: 'Scoring trafności, analiza ryzyka, weryfikacja warunków udziału.',
                },
                {
                  icon: FileText,
                  title: 'Dokumentacja',
                  desc: 'Kosztorysy KNR/ICB, harmonogramy, pełna oferta w godziny.',
                },
              ].map((item) => (
                <div key={item.title} className="flex gap-4">
                  <div className="w-10 h-10 shrink-0 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center">
                    <item.icon className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-zinc-900 mb-1">{item.title}</h3>
                    <p className="text-zinc-500 text-sm leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right — visual metric card */}
          <div className="relative">
            <div className="rounded-2xl bg-zinc-50 border border-zinc-200 p-8">
              <div className="grid grid-cols-2 gap-6">
                <div className="p-5 rounded-xl bg-white border border-zinc-100 shadow-sm">
                  <Zap className="w-5 h-5 text-emerald-600 mb-3" />
                  <div className="text-2xl font-bold text-zinc-900">2.1s</div>
                  <div className="text-xs text-zinc-400 mt-1">Czas analizy jednego przetargu</div>
                </div>
                <div className="p-5 rounded-xl bg-white border border-zinc-100 shadow-sm">
                  <Search className="w-5 h-5 text-emerald-600 mb-3" />
                  <div className="text-2xl font-bold text-zinc-900">24/7</div>
                  <div className="text-xs text-zinc-400 mt-1">Monitoring BZP i TED</div>
                </div>
                <div className="p-5 rounded-xl bg-white border border-zinc-100 shadow-sm">
                  <BarChart3 className="w-5 h-5 text-emerald-600 mb-3" />
                  <div className="text-2xl font-bold text-emerald-600">67%</div>
                  <div className="text-xs text-zinc-400 mt-1">Avg win rate klientów</div>
                </div>
                <div className="p-5 rounded-xl bg-white border border-zinc-100 shadow-sm">
                  <FileText className="w-5 h-5 text-emerald-600 mb-3" />
                  <div className="text-2xl font-bold text-zinc-900">3h</div>
                  <div className="text-xs text-zinc-400 mt-1">Oferta zamiast 3 dni</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── CTA — single dark band (one theme switch, justified as strong CTA) */}
      <section className="py-20 px-6 bg-zinc-900">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            Gotowy na przewagę?
          </h2>
          <p className="mt-4 text-zinc-400 text-lg max-w-[45ch] mx-auto">
            Dołącz do firm, które wygrywają przetargi dzięki danym i AI.
          </p>
          <Link
            href="/signup"
            className="mt-8 inline-flex items-center gap-2 bg-white text-zinc-900 px-7 py-3.5 rounded-full text-sm font-semibold hover:bg-zinc-100 transition-all active:scale-[0.98]"
          >
            Załóż konto
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ─── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="py-10 px-6 border-t border-zinc-100 bg-[#fafbfc]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <Image
              src="/brand/01-logo-concept.png"
              alt="YU-NA"
              width={20}
              height={20}
              className="rounded-md"
            />
            <span className="text-xs text-zinc-400">© 2026 YU-NA Intelligence</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-zinc-400">
            <Link href="/terms" className="hover:text-zinc-600 transition-colors">Regulamin</Link>
            <Link href="/privacy" className="hover:text-zinc-600 transition-colors">Prywatność</Link>
            <Link href="/budos" className="hover:text-zinc-600 transition-colors">Bud.OS</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
