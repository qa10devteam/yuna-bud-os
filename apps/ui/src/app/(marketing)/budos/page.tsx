'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion, AnimatePresence, useScroll, useTransform } from 'motion/react';
import {
  ArrowLeft, ArrowRight, ChevronDown, CheckCircle2,
  Satellite, Brain, Calculator, Hexagon,
  ChevronRight, Plus, Minus,
} from 'lucide-react';

// ─── Data ─────────────────────────────────────────────────────────────────────

const PILLARS = [
  {
    icon: Satellite,
    title: 'Zwiad Przetargowy',
    desc: 'Monitoring BZP i TED w czasie rzeczywistym. AI dopasowuje ogłoszenia do profilu Twojej firmy i wysyła alerty natychmiast.',
    href: '#zwiad',
    label: 'Dowiedz się więcej',
  },
  {
    icon: Brain,
    title: 'Silnik Decyzyjny AI',
    desc: 'Pełna analiza SWZ w 30 sekund. GO / NO-GO z uzasadnieniem, listą ryzyk i oceną dopasowania do Twojego profilu.',
    href: '#silnik',
    label: 'Dowiedz się więcej',
  },
  {
    icon: Calculator,
    title: 'Kosztorys AI',
    desc: 'Automatyczna wycena z dokumentacji przetargowej. Format ATH/PDF, baza materiałów, wersjonowanie i eksport KNR.',
    href: '#kosztorys',
    label: 'Dowiedz się więcej',
  },
];

const ZWIAD_FEATURES = [
  'BZP + TED w jednym miejscu',
  'Matching AI z profilem firmy',
  'Alerty push i email',
  'Historia wszystkich ogłoszeń',
  'Filtrowanie branż i kwot',
];

const SILNIK_FEATURES = [
  'Analiza ryzyk kontraktowych',
  'Wymagania techniczne SWZ',
  'Ocena dopasowania 0–100',
  'Historia decyzji GO/NO-GO',
  'Raport PDF jednym kliknięciem',
];

const KOSZTORYS_FEATURES = [
  'Generowanie z dokumentacji SWZ',
  'Format ATH / PDF gotowy do złożenia',
  'Baza materiałów zawsze aktualna',
  'Wersjonowanie kosztorysów',
  'Eksport KNR i ICB',
];

const PRICING = [
  {
    name: 'Starter',
    price: 'Bezpłatny',
    period: '14 dni próby',
    desc: 'Dla pojedynczego estimatora',
    features: ['5 przetargów miesięcznie', 'Podstawowa analiza AI', 'Alerty email', 'BZP Sync', '1 użytkownik'],
    cta: 'Zacznij za darmo',
    href: '/signup',
    highlight: false,
    badge: null,
  },
  {
    name: 'Professional',
    price: '499 zł',
    period: '/mies.',
    desc: 'Dla aktywnego zespołu ofertowego',
    features: [
      'Nielimitowane przetargi',
      'Pełny Silnik Decyzyjny AI',
      'Kosztorys AI (ATH/PDF/KNR)',
      'Alerty push i email',
      'Do 5 użytkowników',
      'Priorytetowy support',
    ],
    cta: 'Wybierz Professional',
    href: '/signup',
    highlight: true,
    badge: 'Najczęściej wybierany',
  },
  {
    name: 'Enterprise',
    price: 'Wycena',
    period: 'indywidualna',
    desc: 'Dla firm z dużym portfolio',
    features: [
      'Wszystko z Professional',
      'Nielimitowani użytkownicy',
      'Dedykowany model AI',
      'SLA 99,9%',
      'Wdrożenie i integracje',
      'Analiza konkurencji premium',
    ],
    cta: 'Porozmawiajmy',
    href: '/contact',
    highlight: false,
    badge: null,
  },
];

const FAQ_ITEMS = [
  {
    q: 'Jak działa dopasowanie AI?',
    a: 'Silnik porównuje pełną treść ogłoszenia przetargowego z profilem Twojej firmy — branżą, kodami CPV, historią wygranych i deklarowanymi kompetencjami. Wynik dopasowania 0–100 jest generowany automatycznie i możesz go dostosować własną wagą kryteriów.',
  },
  {
    q: 'Czy można eksportować kosztorys do ATH?',
    a: 'Tak. BudOS obsługuje natywny eksport do formatu ATH (Norma Pro / Zuzia), PDF oraz XLSX. Wszystkie pozycje kosztorysowe są zgodne z katalogami KNR i bazą InterCenBud.',
  },
  {
    q: 'Jakie bazy przetargów są monitorowane?',
    a: 'BudOS monitoruje Biuletyn Zamówień Publicznych (BZP), Dziennik Urzędowy UE (TED/eTendering) oraz wybrane platformy e-zamówienia.gov.pl. Synchronizacja odbywa się co godzinę.',
  },
  {
    q: 'Czy jest integracja z innymi systemami?',
    a: 'Plan Professional i Enterprise obsługują eksport do Excel / PDF / DOCX. Enterprise zawiera pełne API REST, umożliwiające integrację z systemami ERP, CRM i własnymi narzędziami biurowymi.',
  },
  {
    q: 'Ile kosztuje plan Enterprise?',
    a: 'Enterprise wyceniamy indywidualnie na podstawie liczby użytkowników, wolumenu przetargów i wymaganych integracji. Skontaktuj się z nami — zazwyczaj odpowiadamy w ciągu 24 godzin roboczych.',
  },
];

// ─── Navbar ───────────────────────────────────────────────────────────────────
function Navbar() {
  return (
    <nav className="fixed top-0 inset-x-0 z-50 glass-nav border-b border-white/[0.07] py-3">
      <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
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
        <div className="hidden md:flex items-center gap-6">
          <a href="#zwiad" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">Zwiad</a>
          <a href="#silnik" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">Silnik AI</a>
          <a href="#kosztorys" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">Kosztorys</a>
          <a href="#pricing" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">Cennik</a>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/signup"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-em text-ink-950 text-xs font-bold hover:bg-em/90 transition-[color,background-color,border-color,opacity,transform,box-shadow] glow-em-xs"
          >
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
  const imgY = useTransform(scrollYProgress, [0, 1], [0, 60]);
  const opacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);

  return (
    <section ref={ref} className="relative min-h-screen flex flex-col items-center justify-start overflow-hidden px-6 pt-28 pb-0">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[600px]"
          style={{ background: 'radial-gradient(ellipse at center top, rgba(16,185,129,0.11) 0%, transparent 65%)' }}
        />
        <div
          className="absolute inset-0 opacity-[0.018]"
          style={{
            backgroundImage: 'linear-gradient(rgba(16,185,129,.8) 1px,transparent 1px),linear-gradient(90deg,rgba(16,185,129,.8) 1px,transparent 1px)',
            backgroundSize: '64px 64px',
          }}
        />
      </div>

      {/* Text content */}
      <motion.div style={{ opacity }} className="relative z-10 text-center max-w-4xl mx-auto mb-16">
        {/* Eyebrow */}
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="eyebrow text-em mb-6"
        >
          BudOS
        </motion.p>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="display text-gradient-white mb-6"
          style={{ fontFamily: 'var(--font-space)' }}
        >
          Twoja przewaga<br />w przetargach.
        </motion.h1>

        {/* Subline */}
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="text-lg text-white/40 max-w-xl mx-auto leading-relaxed"
        >
          Jeden system który monitoruje BZP/TED, analizuje SWZ i generuje kosztorysy — od znalezienia przetargu do podpisanej umowy.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.38 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-10"
        >
          <Link
            href="/signup"
            className="group flex items-center gap-2 px-8 py-3.5 rounded-full bg-em text-ink-950 font-bold text-sm hover:bg-em/90 transition-[color,background-color,border-color,opacity,transform,box-shadow] glow-em shadow-lg shadow-em/20"
          >
            Zacznij za darmo <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
          <a
            href="#zwiad"
            className="flex items-center gap-2 px-7 py-3.5 rounded-full border border-white/10 text-slate-300 font-medium text-sm hover:border-white/20 hover:bg-white/[0.04] transition-[color,background-color,border-color,opacity,transform,box-shadow]"
          >
            Poznaj moduły <ChevronDown className="w-4 h-4 text-slate-500" />
          </a>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.55 }}
          className="text-[11px] text-slate-700 mt-5"
        >
          14 dni za darmo · Bez karty kredytowej · Anuluj kiedy chcesz
        </motion.p>
      </motion.div>

      {/* Hero screenshot in glass frame */}
      <motion.div
        style={{ y: imgY }}
        initial={{ opacity: 0, y: 48 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 w-full max-w-6xl"
      >
        {/* Glow below frame */}
        <div className="absolute inset-x-24 bottom-0 h-24 rounded-full blur-3xl bg-em/10 pointer-events-none" />

        {/* Glass frame */}
        <div
          className="glass-card rounded-2xl overflow-hidden"
          style={{ boxShadow: '0 40px 100px rgba(0,0,0,.75), 0 0 0 1px rgba(16,185,129,.09), inset 0 1px 0 rgba(255,255,255,0.10)' }}
        >
          {/* Fake browser bar */}
          <div className="flex items-center gap-2 px-4 py-3 bg-ink-900/80 border-b border-white/[0.06]">
            <span className="w-2.5 h-2.5 rounded-full bg-nogo/50" />
            <span className="w-2.5 h-2.5 rounded-full bg-warn/50" />
            <span className="w-2.5 h-2.5 rounded-full bg-go/50" />
            <div className="flex-1 mx-3 bg-ink-800/80 rounded h-5 flex items-center px-2.5">
              <span className="text-[10px] text-slate-600 font-mono">app.yu-na.io/budos/dashboard</span>
            </div>
          </div>
          <Image
            src="/screenshots/live-dashboard.png"
            alt="BudOS dashboard"
            width={1440}
            height={900}
            className="w-full h-auto block"
            priority
          />
        </div>
      </motion.div>
    </section>
  );
}

// ─── Three Pillars ────────────────────────────────────────────────────────────
function ThreePillars() {
  return (
    <section className="px-6 py-24">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-3 gap-4">
          {PILLARS.map((p, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
            >
              <a
                href={p.href}
                className="glass-card-hover rounded-2xl p-7 flex flex-col h-full group"
              >
                {/* Icon */}
                <div className="w-11 h-11 rounded-xl bg-em/10 border border-em/20 flex items-center justify-center mb-5">
                  <p.icon className="w-5 h-5 text-em" />
                </div>

                {/* Content */}
                <h3 className="text-[17px] font-bold text-slate-100 mb-2.5" style={{ fontFamily: 'var(--font-space)' }}>
                  {p.title}
                </h3>
                <p className="text-sm text-slate-500 leading-relaxed flex-1">{p.desc}</p>

                {/* Link */}
                <div className="flex items-center gap-1.5 mt-6 text-xs text-em font-semibold group-hover:gap-2.5 transition-[color,background-color,border-color,opacity,transform,box-shadow]">
                  {p.label} <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </a>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Feature Section ──────────────────────────────────────────────────────────
interface FeatureSectionProps {
  id: string;
  eyebrow: string;
  headline: string;
  subline: string;
  screenshot: string;
  screenshotAlt: string;
  features: string[];
  reverse?: boolean;
}

function FeatureSection({
  id, eyebrow, headline, subline, screenshot, screenshotAlt, features, reverse = false,
}: FeatureSectionProps) {
  return (
    <section id={id} className="px-6 py-28 scroll-mt-20">
      <div className="max-w-6xl mx-auto">
        <div className={`grid lg:grid-cols-2 gap-16 items-center ${reverse ? 'lg:[&>*:first-child]:order-2' : ''}`}>

          {/* Text */}
          <motion.div
            initial={{ opacity: 0, x: reverse ? 24 : -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
          >
            <p className="eyebrow text-em mb-4">{eyebrow}</p>
            <h2
              className="h2 text-gradient-white mb-5 whitespace-pre-line"
              style={{ fontFamily: 'var(--font-space)' }}
            >
              {headline}
            </h2>
            <p className="text-[15px] text-white/40 leading-relaxed mb-8">{subline}</p>

            <ul className="space-y-3">
              {features.map((f, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.1 + i * 0.07, ease: [0.16, 1, 0.3, 1] }}
                  className="flex items-center gap-3 text-sm text-slate-300"
                >
                  <CheckCircle2 className="w-4 h-4 text-em shrink-0" />
                  {f}
                </motion.li>
              ))}
            </ul>
          </motion.div>

          {/* Screenshot */}
          <motion.div
            initial={{ opacity: 0, x: reverse ? -24 : 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.65, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="relative">
              {/* Ambient glow */}
              <div className="absolute inset-4 rounded-2xl blur-2xl bg-em/6 pointer-events-none" />
              {/* Glass frame */}
              <div
                className="glass-card rounded-2xl overflow-hidden relative"
                style={{ boxShadow: '0 32px 80px rgba(0,0,0,.6), 0 0 0 1px rgba(16,185,129,.08), inset 0 1px 0 rgba(255,255,255,0.10)' }}
              >
                <Image
                  src={screenshot}
                  alt={screenshotAlt}
                  width={800}
                  height={560}
                  className="w-full h-auto block"
                />
              </div>
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  );
}

// ─── Pricing ──────────────────────────────────────────────────────────────────
function PricingSection() {
  return (
    <section id="pricing" className="px-6 py-28 scroll-mt-16">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <p className="eyebrow text-em mb-4">Cennik</p>
          <h2 className="h2 text-gradient-white" style={{ fontFamily: 'var(--font-space)' }}>
            Prosty i transparentny.
          </h2>
          <p className="text-[15px] text-white/40 mt-4">Bez ukrytych opłat. Anuluj kiedy chcesz.</p>
        </motion.div>

        {/* Cards */}
        <div className="grid md:grid-cols-3 gap-4">
          {PRICING.map((plan, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="relative"
            >
              {/* Badge */}
              {plan.badge && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 z-10">
                  <span className="text-[10px] font-bold text-ink-950 bg-em px-3 py-1 rounded-full whitespace-nowrap">
                    {plan.badge}
                  </span>
                </div>
              )}

              <div
                className={`glass-card rounded-2xl p-7 flex flex-col h-full ${
                  plan.highlight
                    ? 'border-em/30 animate-glow-pulse ring-1 ring-em/10'
                    : ''
                }`}
                style={plan.highlight ? { borderColor: 'rgba(16,185,129,0.30)' } : undefined}
              >
                {/* Plan name */}
                <h3 className="text-[17px] font-bold text-slate-100 mb-1" style={{ fontFamily: 'var(--font-space)' }}>
                  {plan.name}
                </h3>
                <p className="text-xs text-slate-600 mb-6">{plan.desc}</p>

                {/* Price */}
                <div className="mb-7">
                  <span className="text-3xl font-bold text-slate-100 font-mono">{plan.price}</span>
                  {plan.period && (
                    <span className="text-sm text-slate-500 ml-1.5">{plan.period}</span>
                  )}
                </div>

                {/* Features */}
                <ul className="space-y-2.5 mb-8 flex-1">
                  {plan.features.map((f, fi) => (
                    <li key={fi} className="flex items-start gap-2.5 text-sm text-slate-400">
                      <CheckCircle2 className="w-3.5 h-3.5 text-em shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <Link
                  href={plan.href}
                  className={`w-full text-center py-3 rounded-full text-sm font-bold transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
                    plan.highlight
                      ? 'bg-em text-ink-950 hover:bg-em/90 shadow-lg shadow-em/20'
                      : 'border border-white/10 text-slate-300 hover:border-white/20 hover:bg-white/[0.04]'
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── FAQ ──────────────────────────────────────────────────────────────────────
function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="glass-card rounded-xl overflow-hidden"
    >
      <button type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-6 py-5 text-left hover:bg-white/[0.02] transition-colors"
      >
        <span className="text-sm font-semibold text-slate-200 pr-4">{q}</span>
        <motion.div
          animate={{ rotate: open ? 45 : 0 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="shrink-0"
        >
          {open ? (
            <Minus className="w-4 h-4 text-em" />
          ) : (
            <Plus className="w-4 h-4 text-slate-500" />
          )}
        </motion.div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="answer"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="px-6 pb-5 pt-0 border-t border-white/[0.06]">
              <p className="text-sm text-slate-500 leading-relaxed pt-4">{a}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function FAQSection() {
  return (
    <section className="px-6 py-24 border-t border-white/[0.05]">
      <div className="max-w-2xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <p className="eyebrow text-em mb-4">FAQ</p>
          <h2 className="h2 text-gradient-white" style={{ fontFamily: 'var(--font-space)' }}>
            Pytania i odpowiedzi.
          </h2>
        </motion.div>

        <div className="space-y-2">
          {FAQ_ITEMS.map((item, i) => (
            <FAQItem key={i} q={item.q} a={item.a} />
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Final CTA ────────────────────────────────────────────────────────────────
function FinalCTA() {
  return (
    <section className="px-6 py-28 border-t border-white/[0.05]">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ ease: [0.16, 1, 0.3, 1] }}
        className="max-w-3xl mx-auto text-center"
      >
        {/* Ambient */}
        <div
          className="absolute left-1/2 -translate-x-1/2 w-[500px] h-[300px] pointer-events-none"
          style={{ background: 'radial-gradient(ellipse, rgba(16,185,129,0.08) 0%, transparent 65%)' }}
        />

        <p className="eyebrow text-em mb-6 relative z-10">BudOS</p>
        <h2
          className="h1 text-gradient-white mb-6 relative z-10"
          style={{ fontFamily: 'var(--font-space)' }}
        >
          Wygrywaj więcej przetargów.
        </h2>
        <p className="text-[15px] text-white/40 mb-10 relative z-10">
          14 dni za darmo. Bez karty kredytowej. Anuluj kiedy chcesz.
        </p>

        <Link
          href="/signup"
          className="relative z-10 inline-flex items-center gap-2.5 px-10 py-4 rounded-full bg-white text-ink-950 font-bold text-sm hover:bg-white/90 transition-[color,background-color,border-color,opacity,transform,box-shadow] shadow-xl shadow-white/10"
        >
          Zacznij za darmo
        </Link>
      </motion.div>
    </section>
  );
}

// ─── Footer ───────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="border-t border-white/[0.05] px-6 py-8">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Hexagon className="w-4 h-4 text-em/60" strokeWidth={1.5} />
          <span className="text-xs text-slate-600" style={{ fontFamily: 'var(--font-space)' }}>
            YU-NA / <span className="text-slate-500">BudOS</span>
          </span>
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
      <ThreePillars />

      <FeatureSection
        id="zwiad"
        eyebrow="Zwiad Przetargowy"
        headline={'Monitoring\nnon-stop.'}
        subline="BZP i TED w jednym miejscu. AI dopasowuje ogłoszenia do profilu Twojej firmy i wysyła alerty natychmiast po publikacji."
        screenshot="/screenshots/live-zwiad.png"
        screenshotAlt="BudOS Zwiad Przetargowy"
        features={ZWIAD_FEATURES}
      />

      <FeatureSection
        id="silnik"
        eyebrow="Silnik Decyzyjny AI"
        headline={'GO / NO-GO\nw 30 sekund.'}
        subline="AI czyta pełną dokumentację SWZ, ocenia ryzyko kontraktowe i generuje rekomendację z uzasadnieniem — zanim Ty zdążysz otworzyć PDF."
        screenshot="/screenshots/live-silnik.png"
        screenshotAlt="BudOS Silnik Decyzyjny AI"
        features={SILNIK_FEATURES}
        reverse
      />

      <FeatureSection
        id="kosztorys"
        eyebrow="Kosztorys AI"
        headline={'Wycena\nautomatyczna.'}
        subline="Prześlij dokumentację przetargową — BudOS wygeneruje kosztorys w formacie ATH lub PDF, gotowy do złożenia oferty."
        screenshot="/screenshots/live-kosztorys.png"
        screenshotAlt="BudOS Kosztorys AI"
        features={KOSZTORYS_FEATURES}
      />

      <PricingSection />
      <FAQSection />
      <FinalCTA />
      <Footer />
    </main>
  );
}
