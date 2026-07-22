'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { motion, useInView, useReducedMotion } from 'motion/react';
import {
  RefreshCw,
  Brain,
  Calculator,
  BarChart3,
  Shield,
  FileCheck,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Zap,
  Target,
  TrendingUp,
  Menu,
  X,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Reveal primitive
// ─────────────────────────────────────────────────────────────────────────────
function Reveal({
  children,
  delay = 0,
  className,
  y = 24,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  y?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.12 });
  const reduce = useReducedMotion();
  // Fallback: force visible after 1.2s in case IntersectionObserver doesn't fire (e.g. through tunnels/proxies)
  const [forceVisible, setForceVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setForceVisible(true), 1200);
    return () => clearTimeout(t);
  }, []);
  const visible = inView || forceVisible;

  return (
    <motion.div
      ref={ref}
      className={className}
      initial={reduce ? false : { opacity: 0, y }}
      animate={visible ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.55, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// NavBar
// ─────────────────────────────────────────────────────────────────────────────
function NavBar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handle = () => setScrolled(window.scrollY > 24);
    window.addEventListener('scroll', handle, { passive: true });
    handle();
    return () => window.removeEventListener('scroll', handle);
  }, []);

  return (
    <nav
      className={[
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-ink-950/95 backdrop-blur-xl border-b border-ink-700/50 shadow-xl shadow-black/40'
          : 'bg-transparent',
      ].join(' ')}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/landing" className="flex items-center gap-2.5 group">
          <div className="relative">
            <Image
              src="/brand/B01-app-icon-budos.png"
              alt="YU-NA BudOS"
              width={30}
              height={30}
              className="rounded-lg ring-1 ring-em/20 group-hover:ring-em/40 transition-all"
            />
          </div>
          <span className="font-bold text-slate-100 text-[15px] tracking-tight">
            YU-NA{' '}
            <span className="text-em/70 font-normal text-[13px]">BudOS</span>
          </span>
        </Link>

        {/* Desktop Links */}
        <div className="hidden md:flex items-center gap-7 text-sm text-slate-400">
          <a href="#features" className="hover:text-slate-200 transition-colors">Funkcje</a>
          <a href="#how" className="hover:text-slate-200 transition-colors">Jak działa</a>
          <a href="#pricing" className="hover:text-slate-200 transition-colors">Cennik</a>
          <Link href="/app" className="hover:text-slate-200 transition-colors">Demo</Link>
        </div>

        {/* CTAs */}
        <div className="flex items-center gap-3">
          <a
            href="mailto:demo@yu-na.io"
            className="hidden sm:inline-flex text-sm text-slate-400 hover:text-slate-200 transition-colors"
          >
            Umów demo
          </a>
          <Link
            href="/register"
            className="inline-flex items-center gap-1.5 bg-em hover:bg-em-light text-ink-950 font-bold text-sm px-4 py-2 rounded-lg transition-all duration-200 active:scale-[0.98]"
          >
            Zacznij za darmo
          </Link>
          {/* Mobile hamburger */}
          <button
            className="md:hidden p-2 text-slate-400 hover:text-slate-200 transition-colors"
            onClick={() => setOpen(o => !o)}
            aria-label="Toggle menu"
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-ink-950/98 backdrop-blur-xl border-b border-ink-700/50 px-6 py-4 space-y-1 text-sm text-slate-300">
          <a href="#features" className="block py-2 hover:text-slate-100 transition-colors" onClick={() => setOpen(false)}>Funkcje</a>
          <a href="#how" className="block py-2 hover:text-slate-100 transition-colors" onClick={() => setOpen(false)}>Jak działa</a>
          <a href="#pricing" className="block py-2 hover:text-slate-100 transition-colors" onClick={() => setOpen(false)}>Cennik</a>
          <Link href="/app" className="block py-2 hover:text-slate-100 transition-colors" onClick={() => setOpen(false)}>Demo</Link>
          <a href="mailto:demo@yu-na.io" className="block py-2 hover:text-slate-100 transition-colors">Umów demo</a>
        </div>
      )}
    </nav>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Hero
// ─────────────────────────────────────────────────────────────────────────────
function HeroSection() {
  return (
    <section className="min-h-[100dvh] flex items-center pt-16 pb-12 px-6 relative overflow-hidden">
      {/* Ambient glows */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden>
        <div className="absolute top-[-10%] left-[30%] w-[600px] h-[600px] bg-em/6 rounded-full blur-[140px]" />
        <div className="absolute bottom-[10%] right-[5%] w-[400px] h-[400px] bg-score/4 rounded-full blur-[120px]" />
      </div>

      <div className="max-w-6xl mx-auto w-full grid grid-cols-1 lg:grid-cols-[1fr_1.15fr] gap-12 lg:gap-10 items-center relative z-10">

        {/* ── Left ── */}
        <div className="space-y-7">
          {/* Eyebrow */}
          <div className="anim-hero-0">
            <span className="inline-flex items-center gap-2 bg-em/10 border border-em/25 text-em text-xs font-semibold px-3.5 py-1.5 rounded-full tracking-wide">
              <span className="w-1.5 h-1.5 rounded-full bg-em animate-pulse shrink-0" />
              Ponad 50 firm budowlanych wygrało więcej w 2025
            </span>
          </div>

          {/* H1 */}
          <h1
            className="anim-hero-1 text-[42px] md:text-5xl lg:text-[54px] font-extrabold text-slate-100 leading-[1.06] tracking-tight"
          >
            Wygrywaj przetargi{' '}
            <span className="text-em relative">
              3× szybciej
              <span className="absolute -bottom-1 left-0 right-0 h-px bg-gradient-to-r from-em/60 to-transparent" />
            </span>
            {' '}niż konkurencja
          </h1>

          {/* Subtext */}
          <p className="anim-hero-2 text-[17px] text-slate-400 leading-relaxed max-w-[46ch]">
            Automatyczny sync BZP, AI analiza ryzyka SWZ i silnik kosztorysowy KNR
            — w jednej platformie. Twój następny kontrakt jest już w systemie.
          </p>

          {/* CTAs */}
          <div className="anim-hero-3 flex flex-col sm:flex-row gap-3">
            <Link
              href="/register"
              className="inline-flex items-center justify-center gap-2 bg-em hover:bg-em-light text-ink-950 font-bold text-[15px] px-7 py-3.5 rounded-xl transition-all duration-200 active:scale-[0.98] shadow-[0_0_36px_rgba(16,185,129,0.32)]"
            >
              Zacznij za darmo
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="mailto:demo@yu-na.io"
              className="inline-flex items-center justify-center gap-2 border border-ink-700/60 hover:border-em/35 text-slate-300 hover:text-slate-100 font-semibold text-[15px] px-7 py-3.5 rounded-xl transition-all duration-200"
            >
              Umów demo
            </a>
          </div>

          {/* Trust micro */}
          <p className="anim-hero-4 text-slate-600 text-sm">
            Bez karty kredytowej &middot; 14 dni bezpłatnie &middot; Anuluj kiedy chcesz
          </p>
        </div>

        {/* ── Right — product screenshot ── */}
        <div className="anim-hero-right relative hidden lg:block">
          {/* Glow border */}
          <div className="absolute -inset-px rounded-2xl bg-gradient-to-br from-em/30 via-transparent to-em/10 blur-[2px]" />

          {/* Card */}
          <div className="relative rounded-2xl overflow-hidden border border-em/20 shadow-[0_0_80px_rgba(16,185,129,0.10),0_40px_100px_rgba(0,0,0,0.65)]">
            {/* Browser chrome */}
            <div className="bg-ink-800 border-b border-ink-700/60 px-4 py-2.5 flex items-center gap-3">
              <div className="flex gap-1.5 shrink-0">
                <span className="w-2.5 h-2.5 rounded-full bg-nogo/50" />
                <span className="w-2.5 h-2.5 rounded-full bg-warn/50" />
                <span className="w-2.5 h-2.5 rounded-full bg-go/50" />
              </div>
              <div className="flex-1 bg-ink-700/60 rounded px-3 py-1 text-[11px] text-slate-500 font-mono truncate">
                app.yu-na.io/app/pipeline
              </div>
            </div>
            <Image
              src="/brand/live-dashboard.png"
              alt="Panel zarządzania przetargami YU-NA BudOS"
              width={740}
              height={470}
              className="w-full object-cover"
              priority
              loading="eager"
            />
          </div>

          {/* Floating badge — nowe przetargi */}
          <div className="anim-hero-right absolute -bottom-4 -left-4 bg-ink-800/95 backdrop-blur border border-em/30 rounded-xl px-4 py-2.5 shadow-lg shadow-black/40">
            <div className="text-[11px] text-slate-500 mb-0.5 font-medium">Nowe przetargi dziś</div>
            <div className="text-2xl font-extrabold text-em tabular-nums leading-none">+24</div>
          </div>

          {/* Floating badge — wynik dopasowania */}
          <div className="anim-hero-right absolute -top-3 -right-3 bg-ink-800/95 backdrop-blur border border-score/25 rounded-xl px-3.5 py-2.5 shadow-lg shadow-black/40">
            <div className="text-[11px] text-slate-500 mb-0.5 font-medium">Wynik dopasowania</div>
            <div className="text-2xl font-extrabold text-score tabular-nums leading-none">92/100</div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Stats bar
// ─────────────────────────────────────────────────────────────────────────────
const stats = [
  { value: '47+',    label: 'firm budowlanych',     icon: Target },
  { value: '3×',     label: 'szybsza analiza SWZ',  icon: Zap },
  { value: '2 mies.',label: 'średni zwrot ROI',     icon: TrendingUp },
  { value: '8 h',    label: 'zaoszczędzone na ofercie', icon: RefreshCw },
];

function StatsBar() {
  return (
    <section className="py-10 px-6 border-y border-ink-700/40 bg-ink-900/60">
      <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((s, i) => (
          <Reveal key={s.label} delay={i * 0.07}>
            <div className="flex flex-col items-center text-center gap-1.5">
              <s.icon className="w-5 h-5 text-em/60 mb-0.5" />
              <div className="text-3xl font-extrabold text-em tabular-nums">{s.value}</div>
              <div className="text-xs text-slate-500 leading-snug">{s.label}</div>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Problem vs Solution
// ─────────────────────────────────────────────────────────────────────────────
const problems = [
  {
    before: 'Rano przeszukujesz BZP ręcznie, tracąc 2 h dziennie',
    after:  'Automatyczny sync co 30 minut, zero portali',
  },
  {
    before: 'Analiza SWZ trwa cały dzień — ryzyko przeoczenia klauzul',
    after:  'AI wskazuje ryzyka i klauzule karne w 3 minuty',
  },
  {
    before: 'Kosztorys KNR rozklejony na 12 arkuszy Excel',
    after:  'Silnik kosztorysowy jednym kliknięciem eksportuje PDF',
  },
];

function ProblemSection() {
  return (
    <section className="py-20 px-6">
      <div className="max-w-4xl mx-auto">
        <Reveal className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 leading-tight">
            Analiza przetargu zajmuje{' '}
            <span className="text-nogo">3 godziny</span>.{' '}
            YU-NA robi to w{' '}
            <span className="text-em">3 minuty</span>.
          </h2>
        </Reveal>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {problems.map((p, i) => (
            <Reveal key={i} delay={i * 0.09}>
              <div className="bg-ink-900/60 border border-ink-700/40 rounded-2xl p-5 space-y-3.5 hover:border-em/20 transition-colors duration-200 h-full">
                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 shrink-0 w-4 h-4 rounded-full bg-nogo/10 border border-nogo/30 flex items-center justify-center">
                    <div className="w-1.5 h-0.5 bg-nogo/60 rounded-full" />
                  </div>
                  <p className="text-slate-500 text-sm leading-snug line-through decoration-slate-600">{p.before}</p>
                </div>
                <div className="h-px bg-ink-700/50" />
                <div className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-em shrink-0 mt-0.5" />
                  <p className="text-slate-200 text-sm font-semibold leading-snug">{p.after}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Features bento
// ─────────────────────────────────────────────────────────────────────────────
const featuresLarge = [
  {
    Icon: RefreshCw,
    title: 'Automatyczny BZP Sync',
    desc:  'Nowe przetargi trafiają do systemu co 30 minut. Filtry branży, CPV, regionu i wartości działają od razu po konfiguracji.',
    img:   '/brand/live-zwiad.png',
    accent: 'em',
  },
  {
    Icon: Brain,
    title: 'AI Analiza Ryzyka SWZ',
    desc:  'Sztuczna inteligencja czyta Specyfikację Warunków Zamówienia i wskazuje klauzule karne, ryzyka i wymagania nierealistyczne.',
    img:   '/brand/live-silnik.png',
    accent: 'score',
  },
];

const featuresSmall = [
  {
    Icon: Calculator,
    title: 'Silnik Kosztorysowy KNR',
    desc:  'Automatyczne wyceny z bazy InterCenBud. Eksport PDF/Excel gotowy do podpisu.',
  },
  {
    Icon: FileCheck,
    title: 'Lejek Ofertowy Kanban',
    desc:  'Prowadź przetarg od rozpoznania przez wycenę po podpisaną umowę.',
  },
  {
    Icon: BarChart3,
    title: 'Raporty Win / Loss',
    desc:  'Analiza skuteczności ofert, porównanie z konkurencją, rekomendacje wzrostu marży.',
  },
  {
    Icon: Shield,
    title: 'Alerty o Terminach',
    desc:  'Powiadomienia gdy zbliża się deadline. Nigdy więcej spóźnionej oferty.',
  },
];

function FeaturesSection() {
  return (
    <section id="features" className="py-20 px-6 bg-ink-900/30 border-y border-ink-700/30">
      <div className="max-w-6xl mx-auto">
        <Reveal className="mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 leading-tight">
            Wszystko w jednym oknie
          </h2>
          <p className="text-slate-500 mt-3 max-w-[52ch] leading-relaxed">
            Jeden system zamiast pięciu arkuszy i trzech portali. Każda funkcja zaprojektowana pod realne procesy firmy budowlanej.
          </p>
        </Reveal>

        {/* Large bento — 2 wide cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
          {featuresLarge.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.1}>
              <div className="bg-ink-800/50 border border-ink-700/50 rounded-2xl overflow-hidden hover:border-em/25 transition-all duration-300 group">
                <div className="h-48 overflow-hidden border-b border-ink-700/40 relative">
                  <Image
                    src={f.img}
                    alt={f.title}
                    width={620}
                    height={240}
                    className="w-full h-full object-cover object-top group-hover:scale-[1.03] transition-transform duration-500"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-ink-800/60 to-transparent" />
                </div>
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-8 h-8 rounded-lg bg-em/10 border border-em/20 flex items-center justify-center shrink-0">
                      <f.Icon className="w-4 h-4 text-em" />
                    </div>
                    <h3 className="font-bold text-slate-100">{f.title}</h3>
                  </div>
                  <p className="text-slate-500 text-sm leading-relaxed">{f.desc}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>

        {/* Small bento — 4 cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {featuresSmall.map((f, i) => (
            <Reveal key={f.title} delay={0.1 + i * 0.07}>
              <div className="bg-ink-800/30 border border-ink-700/40 rounded-2xl p-5 hover:border-em/25 hover:bg-ink-800/50 transition-all duration-200 group h-full flex flex-col">
                <div className="w-9 h-9 rounded-lg bg-em/10 border border-em/20 flex items-center justify-center mb-4 group-hover:bg-em/15 transition-colors shrink-0">
                  <f.Icon className="w-4 h-4 text-em" />
                </div>
                <h3 className="font-bold text-slate-100 text-sm mb-2">{f.title}</h3>
                <p className="text-slate-500 text-xs leading-relaxed flex-1">{f.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// How it works
// ─────────────────────────────────────────────────────────────────────────────
const steps = [
  {
    num:   '01',
    title: 'Połącz z BZP',
    desc:  'Ustaw filtry branży, kody CPV, region i zakres wartości. System natychmiast importuje pasujące przetargi.',
  },
  {
    num:   '02',
    title: 'AI ocenia ryzyko',
    desc:  'Każdy przetarg otrzymuje wynik dopasowania 0–100 i listę ryzyk SWZ. Decyzja w 3 minuty.',
  },
  {
    num:   '03',
    title: 'Wyślij ofertę i wygrywaj',
    desc:  'Silnik KNR wycenia zakres automatycznie. Eksportuj kosztorys i ofertę gotową do podpisu.',
  },
];

function HowItWorksSection() {
  return (
    <section id="how" className="py-20 px-6">
      <div className="max-w-4xl mx-auto">
        <Reveal className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100">
            Od przetargu do oferty w 3 krokach
          </h2>
        </Reveal>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-6 relative">
          {/* Connector line — only desktop */}
          <div
            className="hidden md:block absolute top-8 left-[calc(16.7%+1px)] right-[calc(16.7%+1px)] h-px"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(16,185,129,0.4) 20%, rgba(16,185,129,0.4) 80%, transparent)',
            }}
          />

          {steps.map((s, i) => (
            <Reveal key={s.num} delay={i * 0.1} className="relative text-center md:text-left">
              <div className="inline-flex w-16 h-16 rounded-2xl bg-ink-800 border border-em/30 items-center justify-center mb-5 font-mono font-extrabold text-em text-xl shadow-[0_0_20px_rgba(16,185,129,0.1)]">
                {s.num}
              </div>
              <h3 className="font-bold text-slate-100 text-lg mb-2">{s.title}</h3>
              <p className="text-slate-500 text-sm leading-relaxed">{s.desc}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Product screenshots switcher
// ─────────────────────────────────────────────────────────────────────────────
const screenshots = [
  { src: '/brand/live-dashboard.png',  label: 'Dashboard',      slug: 'dashboard' },
  { src: '/brand/live-kosztorys.png',  label: 'Kosztorys KNR',  slug: 'kosztorys' },
  { src: '/brand/live-silnik.png',     label: 'Analiza SWZ',    slug: 'silnik' },
  { src: '/brand/live-zwiad.png',      label: 'Zwiad BZP',      slug: 'zwiad' },
];

function ScreenshotsSection() {
  const [active, setActive] = useState(0);

  return (
    <section className="py-20 px-6 bg-ink-900/40 border-y border-ink-700/30 overflow-hidden">
      <div className="max-w-5xl mx-auto">
        <Reveal className="text-center mb-10">
          <h2 className="text-2xl md:text-3xl font-bold text-slate-100 mb-3">
            Zaprojektowany dla budownictwa
          </h2>
          <p className="text-slate-500">Każdy moduł odzwierciedla realne procesy ofertowania</p>
        </Reveal>

        {/* Tab strip */}
        <div className="flex justify-center gap-2 mb-8 flex-wrap">
          {screenshots.map((s, i) => (
            <button
              key={s.label}
              onClick={() => setActive(i)}
              className={[
                'px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200',
                active === i
                  ? 'bg-em text-ink-950 shadow-[0_0_16px_rgba(16,185,129,0.3)]'
                  : 'bg-ink-800/60 text-slate-400 hover:text-slate-200 border border-ink-700/50',
              ].join(' ')}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Screenshot frame */}
        <motion.div
          key={active}
          className="screenshots-tab-content relative rounded-2xl overflow-hidden border border-ink-700/50 shadow-[0_40px_100px_rgba(0,0,0,0.55)]"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          style={{ willChange: 'opacity, transform' }}
        >
          {/* Browser chrome */}
          <div className="bg-ink-800 border-b border-ink-700/60 px-4 py-2.5 flex items-center gap-3">
            <div className="flex gap-1.5 shrink-0">
              <span className="w-2.5 h-2.5 rounded-full bg-nogo/40" />
              <span className="w-2.5 h-2.5 rounded-full bg-warn/40" />
              <span className="w-2.5 h-2.5 rounded-full bg-go/40" />
            </div>
            <div className="flex-1 mx-2 bg-ink-700/60 rounded px-3 py-1 text-[11px] text-slate-500 font-mono truncate">
              app.yu-na.io/app/{screenshots[active].slug}
            </div>
          </div>
          <Image
            src={screenshots[active].src}
            alt={screenshots[active].label}
            width={920}
            height={560}
            className="w-full object-cover"
          />
        </motion.div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Testimonials
// ─────────────────────────────────────────────────────────────────────────────
const testimonials = [
  {
    quote:   'YU-NA skróciła czas przygotowania oferty z 3 dni do 4 godzin. Wygrywamy o jedną trzecią więcej przetargów niż rok temu.',
    name:    'Piotr Malinowski',
    role:    'Dyrektor ds. ofertowania',
    company: 'BudMaster sp. z o.o.',
    initials:'PM',
  },
  {
    quote:   'Synchronizacja z BZP i automatyczna analiza ryzyka to zmiana, na którą czekaliśmy. Przestaliśmy tracić czas na nierentowne przetargi.',
    name:    'Katarzyna Wróbel',
    role:    'Prezes',
    company: 'Konstrukt Pro S.A.',
    initials:'KW',
  },
  {
    quote:   'ROI zwrócił się w niespełna 2 miesiące. Kosztorys, który zajmował nam 2 dni, teraz robi się w pół godziny.',
    name:    'Tomasz Nowicki',
    role:    'CEO',
    company: 'Inżbud Kielce sp. z o.o.',
    initials:'TN',
  },
];

function Stars() {
  return (
    <div className="flex gap-1 mb-4">
      {[...Array(5)].map((_, j) => (
        <svg key={j} className="w-3.5 h-3.5 text-gold" viewBox="0 0 20 20" fill="currentColor">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  );
}

function TestimonialsSection() {
  return (
    <section className="py-20 px-6">
      <div className="max-w-5xl mx-auto">
        <Reveal className="text-center mb-12">
          <h2 className="text-2xl md:text-3xl font-bold text-slate-100 mb-3">Co mówią nasi klienci</h2>
          <p className="text-slate-500">Firmy budowlane, które wygrywają więcej dzięki YU-NA</p>
        </Reveal>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {testimonials.map((t, i) => (
            <Reveal key={t.name} delay={i * 0.09}>
              <div className="bg-ink-900/60 border border-ink-700/40 rounded-2xl p-6 hover:border-em/20 transition-colors duration-200 flex flex-col h-full">
                <Stars />
                <p className="text-slate-300 text-sm leading-relaxed flex-1 mb-5">
                  &ldquo;{t.quote}&rdquo;
                </p>
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-em/15 border border-em/25 flex items-center justify-center text-xs font-bold text-em shrink-0">
                    {t.initials}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-slate-200">{t.name}</div>
                    <div className="text-xs text-slate-500">{t.role} - {t.company}</div>
                  </div>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Pricing
// ─────────────────────────────────────────────────────────────────────────────
const plans = [
  {
    name:    'Free',
    price:   '0 PLN',
    period:  'miesięcznie',
    note:    'Do 5 przetargów / mies.',
    features:['BZP sync co 6 h', 'Lejek Kanban (5 przetargów)', 'Eksport CSV'],
    popular: false,
    cta:     'Zacznij za darmo',
    href:    '/register',
  },
  {
    name:    'Pro',
    price:   '499 PLN',
    period:  'miesięcznie',
    note:    'Do 50 przetargów',
    features:['BZP sync co 30 min', 'AI analiza ryzyka SWZ', 'Silnik kosztorysowy KNR', 'Raporty Win / Loss', 'Alerty e-mail / SMS'],
    popular: true,
    cta:     'Zacznij Pro',
    href:    '/register?plan=pro',
  },
  {
    name:    'Business',
    price:   '1 499 PLN',
    period:  'miesięcznie',
    note:    'Bez limitu przetargów',
    features:['Wszystko z Pro', 'API integracja', 'Multi-user (10 kont)', 'Dedykowany opiekun'],
    popular: false,
    cta:     'Zacznij Business',
    href:    '/register?plan=business',
  },
  {
    name:    'Enterprise',
    price:   'Wycena',
    period:  'indywidualnie',
    note:    'On-premise lub chmura',
    features:['Wszystko z Business', 'SSO / LDAP', 'SLA 99.9%', 'Wdrożenie i szkolenia'],
    popular: false,
    cta:     'Skontaktuj się',
    href:    'mailto:enterprise@yu-na.io',
  },
];

function PricingSection() {
  return (
    <section id="pricing" className="py-20 px-6 bg-ink-900/30 border-y border-ink-700/30">
      <div className="max-w-5xl mx-auto">
        <Reveal className="text-center mb-12">
          <h2 className="text-2xl md:text-3xl font-bold text-slate-100 mb-3">Prosty cennik, bez gwiazdek</h2>
          <p className="text-slate-500">Od bezpłatnego startu do pełnoprawnego enterprise</p>
        </Reveal>

        <div className="flex flex-col md:flex-row gap-6 items-stretch">
          {plans.map((p, i) => (
            <Reveal key={p.name} delay={i * 0.08}>
              <div
                className={[
                  'rounded-2xl p-6 border flex flex-col flex-1 relative',
                  p.popular
                    ? 'border-em/50 bg-gradient-to-b from-em/8 to-ink-800/50 ring-1 ring-em/20 shadow-[0_0_40px_rgba(16,185,129,0.08)]'
                    : 'border-ink-700/50 bg-ink-800/30',
                ].join(' ')}
              >
                {p.popular && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-em text-ink-950 text-[11px] font-bold uppercase tracking-wider px-3.5 py-1 rounded-full whitespace-nowrap shadow-[0_0_16px_rgba(16,185,129,0.4)]">
                    Najpopularniejszy
                  </div>
                )}

                <div className="mb-4">
                  <div className={`font-bold text-sm mb-1 ${p.popular ? 'text-em' : 'text-slate-300'}`}>
                    {p.name}
                  </div>
                  <div className="text-2xl font-extrabold text-slate-100 tabular-nums">{p.price}</div>
                  <div className="text-xs text-slate-500 mb-1">/ {p.period}</div>
                  <div className="text-xs text-slate-400 font-medium">{p.note}</div>
                </div>

                <ul className="space-y-2.5 flex-1 mb-6">
                  {p.features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-xs text-slate-400 leading-snug">
                      <CheckCircle2 className="w-3.5 h-3.5 text-em shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>

                <a
                  href={p.href}
                  className={[
                    'inline-flex items-center justify-center gap-1.5 w-full py-2.5 rounded-xl text-sm font-semibold transition-all duration-200',
                    p.popular
                      ? 'bg-em hover:bg-em-light text-ink-950 active:scale-[0.98] shadow-[0_0_20px_rgba(16,185,129,0.25)]'
                      : 'bg-ink-700/50 hover:bg-ink-700 text-slate-300 border border-ink-600/40',
                  ].join(' ')}
                >
                  {p.cta}
                  <ChevronRight className="w-3.5 h-3.5" />
                </a>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Final CTA
// ─────────────────────────────────────────────────────────────────────────────
function FinalCTA() {
  return (
    <section className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden>
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] bg-em/5 rounded-full blur-[120px]" />
      </div>

      <Reveal className="max-w-2xl mx-auto text-center relative z-10">
        <h2 className="text-4xl md:text-5xl font-extrabold text-slate-100 leading-[1.05] tracking-tight mb-5">
          Twój następny przetarg<br />
          <span className="text-em">jest już w systemie</span>
        </h2>
        <p className="text-slate-400 text-lg mb-8 max-w-[44ch] mx-auto leading-relaxed">
          Zacznij bezpłatnie i przekonaj się, że wygrywanie przetargów może być prostsze.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/register"
            className="inline-flex items-center justify-center gap-2 bg-em hover:bg-em-light text-ink-950 font-bold text-lg px-10 py-4 rounded-xl transition-all duration-200 active:scale-[0.98] shadow-[0_0_48px_rgba(16,185,129,0.38)]"
          >
            Zacznij za darmo
            <ArrowRight className="w-5 h-5" />
          </Link>
          <a
            href="mailto:demo@yu-na.io"
            className="inline-flex items-center justify-center gap-2 border border-ink-700/60 hover:border-em/35 text-slate-300 hover:text-slate-100 font-semibold text-lg px-10 py-4 rounded-xl transition-all duration-200"
          >
            Umów demo
          </a>
        </div>
        <p className="text-slate-600 text-sm mt-6">
          Bez karty kredytowej &middot; 14 dni bezpłatnie &middot; Anuluj kiedy chcesz
        </p>
      </Reveal>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Footer
// ─────────────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="border-t border-ink-700/40 py-10 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between gap-8 mb-8">
          {/* Brand */}
          <div className="space-y-3">
            <div className="flex items-center gap-2.5">
              <Image
                src="/brand/B01-app-icon-budos.png"
                alt="YU-NA"
                width={24}
                height={24}
                className="rounded-md"
              />
              <span className="font-bold text-slate-300 text-sm">YU-NA BudOS</span>
            </div>
            <p className="text-slate-600 text-sm max-w-[28ch] leading-relaxed">
              System decyzyjny dla firm budowlanych.
            </p>
          </div>

          {/* Links */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-8 text-sm">
            <div className="space-y-2.5">
              <div className="text-slate-400 font-semibold text-xs uppercase tracking-wide">Produkt</div>
              <a href="#features" className="block text-slate-600 hover:text-slate-300 transition-colors">Funkcje</a>
              <a href="#pricing"  className="block text-slate-600 hover:text-slate-300 transition-colors">Cennik</a>
              <Link href="/app"   className="block text-slate-600 hover:text-slate-300 transition-colors">Panel demo</Link>
            </div>
            <div className="space-y-2.5">
              <div className="text-slate-400 font-semibold text-xs uppercase tracking-wide">Firma</div>
              <a href="mailto:kontakt@yu-na.io"    className="block text-slate-600 hover:text-slate-300 transition-colors">Kontakt</a>
              <a href="mailto:enterprise@yu-na.io" className="block text-slate-600 hover:text-slate-300 transition-colors">Enterprise</a>
            </div>
            <div className="space-y-2.5">
              <div className="text-slate-400 font-semibold text-xs uppercase tracking-wide">Prawo</div>
              <a href="#" className="block text-slate-600 hover:text-slate-300 transition-colors">Regulamin</a>
              <a href="#" className="block text-slate-600 hover:text-slate-300 transition-colors">Prywatność</a>
            </div>
          </div>
        </div>

        <div className="pt-6 border-t border-ink-700/30 flex flex-col sm:flex-row justify-between items-center gap-4">
          <span className="text-xs text-slate-600">© 2026 YU-NA sp. z o.o. Wszelkie prawa zastrzeżone.</span>
          <span className="text-xs text-em/40 font-mono tracking-widest">PRECYZJA · ZWIAD · PRZEWAGA</span>
        </div>
      </div>
    </footer>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Page root
// ─────────────────────────────────────────────────────────────────────────────
export default function LandingClient() {
  return (
    <div className="min-h-[100dvh] bg-ink-950 text-slate-100 font-sans">
      <NavBar />
      <HeroSection />
      <StatsBar />
      <ProblemSection />
      <FeaturesSection />
      <HowItWorksSection />
      <ScreenshotsSection />
      <TestimonialsSection />
      <PricingSection />
      <FinalCTA />
      <Footer />
    </div>
  );
}
