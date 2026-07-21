'use client';

import { useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion, useScroll, useTransform } from 'motion/react';
import {
  ArrowLeft, ArrowRight, ChevronRight, CheckCircle2,
  RefreshCw, Brain, Calculator, GitBranch,
  BarChart3, Shield, FileText, Target,
  Clock, TrendingUp, Award, Zap, Hexagon,
} from 'lucide-react';

// ─── Data ─────────────────────────────────────────────────────────────────────
const STATS = [
  { icon: Clock,      value: '< 3 min', label: 'analiza SWZ' },
  { icon: TrendingUp, value: '94%',     label: 'trafność GO/NO-GO' },
  { icon: Award,      value: '+23%',    label: 'skuteczność ofert' },
  { icon: RefreshCw,  value: '2 137',   label: 'przetargów live' },
];

const FEATURES = [
  { icon: RefreshCw,   title: 'BZP/TED Sync',        desc: 'Nowe przetargi co godzinę. Filtry CPV, region, wartość.',           tag: 'Monitorowanie' },
  { icon: Brain,       title: 'Silnik GO/NO-GO',      desc: 'AI czyta SWZ, scoring AHP 0–100, rekomendacja w 3 min.',            tag: 'Analiza AI' },
  { icon: Calculator,  title: 'Kosztorysy KNR/ICB',   desc: 'Baza InterCenBud. Monte Carlo dla marży. Excel/PDF gotowy.',        tag: 'Wyceny' },
  { icon: GitBranch,   title: 'Pipeline Kanban',      desc: 'Cykl życia przetargu od zidentyfikowania do podpisanej umowy.',     tag: 'Zarządzanie' },
  { icon: BarChart3,   title: 'Raporty Win/Loss',      desc: 'Analiza skuteczności, porównanie z konkurencją, rekomendacje.',     tag: 'Analityka' },
  { icon: FileText,    title: 'Generator Ofert',      desc: 'Formularz ofertowy z danymi systemu. PDF/DOCX do podpisu.',         tag: 'Generowanie' },
  { icon: Target,      title: 'Analiza Konkurencji',  desc: 'Historia wyników BZP. Kto startuje i za ile.',                     tag: 'Wywiad' },
  { icon: Shield,      title: 'Alerty i Powiadomienia',desc: 'Push/email dla deadlinów, nowych przetargów, zmian warunków.',     tag: 'Alerty' },
];

const PRICING = [
  {
    name: 'Starter', price: '299', period: 'zł/mies.',
    desc: 'Dla pojedynczego estimatora',
    features: ['Do 50 przetargów/mies.', 'Silnik GO/NO-GO', 'BZP Sync', 'Alerty email', '1 użytkownik'],
    cta: 'Zacznij za darmo', highlight: false, badge: null,
  },
  {
    name: 'Pro', price: '799', period: 'zł/mies.',
    desc: 'Dla zespołu ofertowego',
    features: ['Nieograniczone przetargi', 'Kosztorysy KNR/ICB', 'Pipeline Kanban', 'Raporty Win/Loss', 'Generator ofert', 'Do 5 użytkowników', 'Priorytetowy support'],
    cta: 'Wybierz Pro', highlight: true, badge: 'Najczęściej wybierany',
  },
  {
    name: 'Enterprise', price: 'Kontakt', period: '',
    desc: 'Dla firm z dużym portfolio',
    features: ['Wszystko z Pro', 'Nielimitowani użytkownicy', 'API dostęp', 'Dedykowane wdrożenie', 'SLA 99.9%', 'Analiza konkurencji premium'],
    cta: 'Porozmawiajmy', highlight: false, badge: null,
  },
];

// ─── Navbar ───────────────────────────────────────────────────────────────────
function Navbar() {
  return (
    <nav className="fixed top-0 inset-x-0 z-50 glass-2 border-b border-ink-800/60 py-3">
      <div className="max-w-5xl mx-auto px-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300 transition-colors text-xs">
            <ArrowLeft className="w-3.5 h-3.5" /> YU-NA
          </Link>
          <span className="text-slate-700">|</span>
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded-lg bg-em/10 border border-em/20 flex items-center justify-center">
              <span className="text-[9px] font-bold text-em" style={{ fontFamily: 'var(--font-space)' }}>b</span>
            </div>
            <span className="text-sm font-bold text-slate-200" style={{ fontFamily: 'var(--font-space)' }}>BudOS</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a href="#pricing" className="text-xs text-slate-500 hover:text-slate-300 transition-colors px-3 py-2">Cennik</a>
          <Link href="/signup" className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-em text-ink-950 text-xs font-bold hover:bg-em/90 transition-all glow-em-xs">
            Zacznij za darmo <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </nav>
  );
}

// ─── Hero ─────────────────────────────────────────────────────────────────────
function Hero() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const imgY = useTransform(scrollYProgress, [0, 1], [0, 50]);

  return (
    <section ref={ref} className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-6 pt-20">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[450px]"
          style={{ background: 'radial-gradient(ellipse at center top, rgba(16,185,129,0.09) 0%, transparent 65%)' }} />
      </div>
      <div className="absolute inset-0 pointer-events-none opacity-[0.025]"
        style={{ backgroundImage: 'linear-gradient(rgba(16,185,129,.9) 1px,transparent 1px),linear-gradient(90deg,rgba(16,185,129,.9) 1px,transparent 1px)', backgroundSize: '60px 60px' }} />

      <div className="relative z-10 text-center max-w-3xl mb-12">
        <motion.div initial={{ opacity: 0, scale: .9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: .4 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-em/20 bg-em/5 text-em text-[11px] font-semibold mb-8">
          <Zap className="w-3 h-3" /> Produkt YU-NA — Dostępny teraz
        </motion.div>
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .6, delay: .1 }}
          className="text-[clamp(2.4rem,7vw,4.5rem)] font-bold tracking-[-0.03em] leading-[1.07]" style={{ fontFamily: 'var(--font-space)' }}>
          <span className="text-gradient-white">Przetargi budowlane.</span><br />
          <span className="text-gradient-em">Opanowane.</span>
        </motion.h1>
        <motion.p initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5, delay: .22 }}
          className="mt-6 text-[1.05rem] text-slate-500 max-w-xl mx-auto leading-relaxed">
          System AI który monitoruje BZP/TED, analizuje SWZ w 3 minuty, generuje kosztorysy i prowadzi od znalezienia przetargu do podpisanej umowy.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .35 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-10">
          <Link href="/signup" className="group flex items-center gap-2 px-8 py-3.5 rounded-xl bg-em text-ink-950 font-bold text-sm hover:bg-em/90 transition-all glow-em shadow-lg shadow-em/20">
            Zacznij za darmo <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
          <a href="#pricing" className="flex items-center gap-2 px-7 py-3.5 rounded-xl border border-ink-700 text-slate-300 font-medium text-sm hover:border-em/30 hover:bg-ink-900/40 transition-all">
            Cennik <ChevronRight className="w-4 h-4 text-slate-500" />
          </a>
        </motion.div>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .55 }} className="text-[11px] text-slate-700 mt-5">
          14 dni za darmo · Bez karty kredytowej · Anuluj kiedy chcesz
        </motion.p>
      </div>

      {/* Hero product screenshot */}
      <motion.div style={{ y: imgY }} initial={{ opacity: 0, y: 32 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: .8, delay: .45, ease: [.16, 1, .3, 1] }}
        className="relative z-10 w-full max-w-5xl">
        <div className="absolute inset-x-16 bottom-0 h-20 rounded-full blur-3xl bg-em/10 pointer-events-none" />
        <div className="relative rounded-2xl overflow-hidden border border-ink-700/50"
          style={{ boxShadow: '0 32px 80px rgba(0,0,0,.65), 0 0 0 1px rgba(16,185,129,.07)' }}>
          <div className="flex items-center gap-2 px-4 py-3 bg-ink-900 border-b border-ink-800/80">
            <span className="w-2.5 h-2.5 rounded-full bg-nogo/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-warn/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-go/60" />
            <div className="flex-1 mx-3 bg-ink-800 rounded h-5 flex items-center px-2.5">
              <span className="text-[10px] text-slate-600 font-mono">app.yu-na.io/app/budos</span>
            </div>
          </div>
          <Image src="/brand/B09-dashboard-preview.png" alt="BudOS dashboard" width={1200} height={750} className="w-full h-auto block" priority />
        </div>
      </motion.div>
    </section>
  );
}

// ─── Stats ────────────────────────────────────────────────────────────────────
function StatsSection() {
  return (
    <section className="border-y border-ink-800/50">
      <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4">
        {STATS.map((s, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .07 }}
            className={`flex flex-col items-center py-10 ${i < 3 ? 'border-r border-ink-800/50' : ''}`}>
            <s.icon className="w-4 h-4 text-em mb-3" />
            <span className="text-2xl md:text-3xl font-bold text-slate-100 font-mono tabular-nums">{s.value}</span>
            <span className="text-[11px] text-slate-600 mt-1">{s.label}</span>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

// ─── Feature rows ─────────────────────────────────────────────────────────────
function FeaturesVisual() {
  return (
    <section className="px-6 py-28">
      <div className="max-w-5xl mx-auto space-y-24">

        {/* Scoring */}
        <div className="flex flex-col lg:flex-row items-center gap-12">
          <motion.div initial={{ opacity: 0, x: -24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} className="flex-1">
            <span className="text-[10px] font-bold text-em/70 uppercase tracking-[.16em] mb-3 block">GO/NO-GO</span>
            <h3 className="text-2xl md:text-3xl font-bold text-slate-100 mb-4 leading-snug" style={{ fontFamily: 'var(--font-space)' }}>
              Decyzja w 3 minuty,<br />nie w 3 dni.
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed mb-6">
              AI analizuje pełną dokumentację SWZ, warunki udziału, kryteria oceny i profil Twojej firmy. Wynik 0–100 z uzasadnieniem i listą ryzyk.
            </p>
            <ul className="space-y-2.5">
              {['Scoring AHP z wagami branżowymi', 'Analiza warunków podmiotowych', 'Mapowanie kodów CPV', 'Rekomendacja GO/NO-GO z uzasadnieniem'].map((t, i) => (
                <li key={i} className="flex items-center gap-2.5 text-xs text-slate-400"><CheckCircle2 className="w-3.5 h-3.5 text-em shrink-0" />{t}</li>
              ))}
            </ul>
          </motion.div>
          <motion.div initial={{ opacity: 0, x: 24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: .1 }} className="flex-1 max-w-lg">
            <div className="rounded-2xl overflow-hidden border border-ink-700/50" style={{ boxShadow: '0 20px 60px rgba(0,0,0,.5), 0 0 0 1px rgba(16,185,129,.06)' }}>
              <Image src="/brand/B05-hero-score.png" alt="Scoring GO/NO-GO" width={800} height={520} className="w-full h-auto block" />
            </div>
          </motion.div>
        </div>

        {/* Silnik dark */}
        <div className="flex flex-col lg:flex-row-reverse items-center gap-12">
          <motion.div initial={{ opacity: 0, x: 24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} className="flex-1">
            <span className="text-[10px] font-bold text-em/70 uppercase tracking-[.16em] mb-3 block">Analiza AI</span>
            <h3 className="text-2xl md:text-3xl font-bold text-slate-100 mb-4 leading-snug" style={{ fontFamily: 'var(--font-space)' }}>
              200 stron SWZ.<br />Esencja w 3 minuty.
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed mb-6">
              Model wytrenowany na tysiącach polskich i europejskich postępowań. Rozumie kody CPV, warunki podmiotowe i kryteria. Nie musisz czytać — dostajesz co ważne.
            </p>
            <ul className="space-y-2.5">
              {['Ekstrakcja kryteriów oceny ofert', 'Wykrywanie klauzul ryzyka', 'Porównanie z profilem firmy', 'Historia postępowań tego zamawiającego'].map((t, i) => (
                <li key={i} className="flex items-center gap-2.5 text-xs text-slate-400"><CheckCircle2 className="w-3.5 h-3.5 text-em shrink-0" />{t}</li>
              ))}
            </ul>
          </motion.div>
          <motion.div initial={{ opacity: 0, x: -24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: .1 }} className="flex-1 max-w-lg">
            <div className="rounded-2xl overflow-hidden border border-ink-700/50" style={{ boxShadow: '0 20px 60px rgba(0,0,0,.5), 0 0 0 1px rgba(16,185,129,.06)' }}>
              <Image src="/brand/B03-feature-silnik-dark.png" alt="Silnik AI BudOS" width={800} height={520} className="w-full h-auto block" />
            </div>
          </motion.div>
        </div>

        {/* Kosztorysy */}
        <div className="flex flex-col lg:flex-row items-center gap-12">
          <motion.div initial={{ opacity: 0, x: -24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} className="flex-1">
            <span className="text-[10px] font-bold text-em/70 uppercase tracking-[.16em] mb-3 block">Kosztorysy KNR/ICB</span>
            <h3 className="text-2xl md:text-3xl font-bold text-slate-100 mb-4 leading-snug" style={{ fontFamily: 'var(--font-space)' }}>
              Wycena w 10 minut.<br />Nie w 3 dni.
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed mb-6">
              Baza InterCenBud z aktualnymi stawkami. Automatyczne pozycje KNR. Symulacja Monte Carlo dla marży. Eksport gotowy do złożenia.
            </p>
            <ul className="space-y-2.5">
              {['Baza KNR + ICB zawsze aktualna', 'Automatyczne pozycje kosztorysowe', 'Symulacja Monte Carlo marży', 'Eksport Excel / PDF / DOCX'].map((t, i) => (
                <li key={i} className="flex items-center gap-2.5 text-xs text-slate-400"><CheckCircle2 className="w-3.5 h-3.5 text-em shrink-0" />{t}</li>
              ))}
            </ul>
          </motion.div>
          <motion.div initial={{ opacity: 0, x: 24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: .1 }} className="flex-1 max-w-lg">
            <div className="rounded-2xl overflow-hidden border border-ink-700/50" style={{ boxShadow: '0 20px 60px rgba(0,0,0,.5), 0 0 0 1px rgba(16,185,129,.06)' }}>
              <Image src="/brand/B07-feature-kosztorys.png" alt="Kosztorysy KNR/ICB" width={800} height={520} className="w-full h-auto block" />
            </div>
          </motion.div>
        </div>

      </div>
    </section>
  );
}

// ─── Features grid ────────────────────────────────────────────────────────────
function FeaturesGrid() {
  return (
    <section className="px-6 py-20 bg-ink-900/15 border-y border-ink-800/40">
      <div className="max-w-5xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-14">
          <span className="text-[11px] text-em font-semibold uppercase tracking-[.16em]">Kompletny arsenał</span>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-100 mt-3" style={{ fontFamily: 'var(--font-space)' }}>8 modułów. Jeden system.</h2>
        </motion.div>
        <div className="grid md:grid-cols-2 gap-3">
          {FEATURES.map((f, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: (i % 2) * .07 }}
              className="flex gap-4 p-5 rounded-xl bg-ink-900/40 border border-ink-800/50 hover:border-ink-700/60 transition-colors">
              <div className="w-9 h-9 rounded-lg bg-em/8 border border-em/12 flex items-center justify-center shrink-0">
                <f.icon className="w-4 h-4 text-em" />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold text-slate-200">{f.title}</h3>
                  <span className="text-[9px] text-em/60 bg-em/6 border border-em/12 px-1.5 py-0.5 rounded-full font-medium">{f.tag}</span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">{f.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Pricing ──────────────────────────────────────────────────────────────────
function PricingSection() {
  return (
    <section id="pricing" className="px-6 py-28 scroll-mt-16">
      <div className="max-w-5xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-16">
          <span className="text-[11px] text-em font-semibold uppercase tracking-[.16em]">Cennik</span>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-100 mt-3" style={{ fontFamily: 'var(--font-space)' }}>Prosty i transparentny</h2>
          <p className="text-sm text-slate-500 mt-3">Bez ukrytych opłat. Anuluj kiedy chcesz.</p>
        </motion.div>
        <div className="grid md:grid-cols-3 gap-4">
          {PRICING.map((plan, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .1 }}
              className={`relative p-6 rounded-2xl border flex flex-col ${plan.highlight ? 'bg-ink-900/70 border-em/30 ring-1 ring-em/10 animate-glow-pulse' : 'bg-ink-900/30 border-ink-800/50'}`}>
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="text-[10px] font-bold text-ink-950 bg-em px-3 py-1 rounded-full whitespace-nowrap">{plan.badge}</span>
                </div>
              )}
              <h3 className="text-lg font-bold text-slate-100 mb-0.5" style={{ fontFamily: 'var(--font-space)' }}>{plan.name}</h3>
              <p className="text-xs text-slate-600 mb-5">{plan.desc}</p>
              <div className="mb-6">
                <span className="text-4xl font-bold text-slate-100 font-mono">{plan.price}</span>
                {plan.period && <span className="text-sm text-slate-500 ml-1">{plan.period}</span>}
              </div>
              <ul className="space-y-2.5 mb-8 flex-1">
                {plan.features.map((f, fi) => (
                  <li key={fi} className="flex items-start gap-2 text-xs text-slate-400">
                    <CheckCircle2 className="w-3.5 h-3.5 text-em shrink-0 mt-0.5" />{f}
                  </li>
                ))}
              </ul>
              <Link href="/signup" className={`w-full text-center py-3 rounded-xl text-sm font-bold transition-all ${plan.highlight ? 'bg-em text-ink-950 hover:bg-em/90 shadow-lg shadow-em/20' : 'border border-ink-700 text-slate-300 hover:border-em/25 hover:bg-ink-900/50'}`}>
                {plan.cta}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── CTA ─────────────────────────────────────────────────────────────────────
function CTA() {
  return (
    <section className="px-6 py-20 border-t border-ink-800/40">
      <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="max-w-2xl mx-auto text-center">
        <h2 className="text-3xl font-bold text-slate-100 mb-4" style={{ fontFamily: 'var(--font-space)' }}>Wygrywaj więcej przetargów.</h2>
        <p className="text-sm text-slate-500 mb-8">14 dni za darmo. Bez karty kredytowej.</p>
        <Link href="/signup" className="group inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-em text-ink-950 font-bold text-sm hover:bg-em/90 transition-all glow-em shadow-xl shadow-em/25">
          Zacznij za darmo <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      </motion.div>
    </section>
  );
}

// ─── Footer ───────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="border-t border-ink-800/40 px-6 py-8">
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Hexagon className="w-4 h-4 text-em/60" strokeWidth={1.5} />
          <span className="text-xs text-slate-600" style={{ fontFamily: 'var(--font-space)' }}>YU-NA / <span className="text-slate-500">BudOS</span></span>
        </div>
        <div className="flex gap-5 text-[11px] text-slate-700">
          <Link href="/" className="hover:text-slate-400 transition-colors">Platforma</Link>
          <Link href="/terms" className="hover:text-slate-400 transition-colors">Regulamin</Link>
          <Link href="/privacy" className="hover:text-slate-400 transition-colors">Prywatność</Link>
        </div>
      </div>
    </footer>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function BudosProductPage() {
  return (
    <main className="min-h-screen bg-ink-950 overflow-x-hidden">
      <Navbar />
      <Hero />
      <StatsSection />
      <FeaturesVisual />
      <FeaturesGrid />
      <PricingSection />
      <CTA />
      <Footer />
    </main>
  );
}
