'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion, useScroll, useTransform } from 'motion/react';
import {
  ArrowRight, ChevronRight, CheckCircle2,
  Hexagon, Star, Quote, Zap, Play,
} from 'lucide-react';

// ─── Particle canvas ──────────────────────────────────────────────────────────
function ParticleField() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const ctx = c.getContext('2d'); if (!ctx) return;
    let raf: number;
    const pts: { x: number; y: number; vx: number; vy: number; a: number }[] = [];
    const resize = () => { c.width = c.offsetWidth; c.height = c.offsetHeight; };
    resize(); window.addEventListener('resize', resize);
    for (let i = 0; i < 55; i++) pts.push({ x: Math.random() * c.width, y: Math.random() * c.height, vx: (Math.random() - .5) * .25, vy: (Math.random() - .5) * .25, a: Math.random() * .4 + .05 });
    const draw = () => {
      ctx.clearRect(0, 0, c.width, c.height);
      for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
        const d = Math.hypot(pts[i].x - pts[j].x, pts[i].y - pts[j].y);
        if (d < 130) { ctx.beginPath(); ctx.strokeStyle = `rgba(16,185,129,${.07 * (1 - d / 130)})`; ctx.lineWidth = .5; ctx.moveTo(pts[i].x, pts[i].y); ctx.lineTo(pts[j].x, pts[j].y); ctx.stroke(); }
      }
      pts.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = c.width; if (p.x > c.width) p.x = 0;
        if (p.y < 0) p.y = c.height; if (p.y > c.height) p.y = 0;
        ctx.beginPath(); ctx.arc(p.x, p.y, 1.2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(16,185,129,${p.a})`; ctx.fill();
      });
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); };
  }, []);
  return <canvas ref={ref} className="absolute inset-0 w-full h-full pointer-events-none" style={{ opacity: .55 }} />;
}

// ─── Navbar ───────────────────────────────────────────────────────────────────
function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => { const fn = () => setScrolled(window.scrollY > 48); window.addEventListener('scroll', fn, { passive: true }); return () => window.removeEventListener('scroll', fn); }, []);
  return (
    <motion.nav initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .4 }}
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${scrolled ? 'glass-2 border-b border-ink-800/60 py-3' : 'py-5'}`}>
      <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="relative w-7 h-7">
            <Hexagon className="w-7 h-7 text-em" strokeWidth={1.5} />
            <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-em">YN</span>
          </div>
          <span className="text-sm font-bold tracking-wide text-slate-200" style={{ fontFamily: 'var(--font-space)' }}>YU-NA</span>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/login" className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors">Logowanie</Link>
          <Link href="/signup" className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-em text-ink-950 text-xs font-bold hover:bg-em/90 transition-all glow-em-xs">
            Zacznij za darmo <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </motion.nav>
  );
}

// ─── Hero ─────────────────────────────────────────────────────────────────────
function Hero() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const imgY = useTransform(scrollYProgress, [0, 1], [0, 60]);
  const textY = useTransform(scrollYProgress, [0, 1], [0, 40]);
  const opacity = useTransform(scrollYProgress, [0, .65], [1, 0]);

  return (
    <section ref={ref} className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden">
      <ParticleField />
      {/* radial glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[700px] rounded-full"
          style={{ background: 'radial-gradient(ellipse at center, rgba(16,185,129,0.07) 0%, transparent 60%)' }} />
      </div>

      <motion.div style={{ y: textY, opacity }} className="relative z-10 text-center max-w-4xl px-6 pt-24 pb-8">
        {/* pill badge */}
        <motion.div initial={{ opacity: 0, scale: .9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: .45 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-em/20 bg-em/5 text-em text-[11px] font-semibold mb-8 tracking-wide">
          <span className="w-1.5 h-1.5 rounded-full bg-em animate-pulse" />
          Platforma AI dla firm budowlanych — Premiera 2026
        </motion.div>

        {/* headline */}
        <motion.h1 initial={{ opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .65, delay: .08 }}
          className="text-[clamp(2.6rem,8vw,5rem)] font-bold tracking-[-0.03em] leading-[1.06]" style={{ fontFamily: 'var(--font-space)' }}>
          <span className="text-gradient-white">Przyszłość biznesu</span><br />
          <span className="text-gradient-em">budowlanego</span>
          <span className="text-gradient-white"> jest tutaj.</span>
        </motion.h1>

        <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .55, delay: .2 }}
          className="text-[1.05rem] text-slate-500 max-w-lg mx-auto mt-6 leading-relaxed">
          YU-NA to ekosystem narzędzi AI które zmieniają sposób w jaki firmy budowlane
          wygrywają przetargi, liczą koszty i zarządzają ofertami.
        </motion.p>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5, delay: .32 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-10">
          <Link href="/signup" className="group flex items-center gap-2 px-7 py-3.5 rounded-xl bg-em text-ink-950 font-bold text-sm hover:bg-em/90 transition-all glow-em shadow-lg shadow-em/20">
            Zacznij za darmo <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link href="/budos" className="flex items-center gap-2 px-7 py-3.5 rounded-xl border border-ink-700 text-slate-300 font-medium text-sm hover:border-em/30 hover:bg-ink-900/50 transition-all">
            Poznaj BudOS <ChevronRight className="w-4 h-4 text-slate-500" />
          </Link>
        </motion.div>

        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .55 }}
          className="text-[11px] text-slate-700 mt-5">
          14 dni za darmo · Bez karty kredytowej · Anuluj kiedy chcesz
        </motion.p>
      </motion.div>

      {/* ── HERO PRODUCT IMAGE ── */}
      <motion.div
        style={{ y: imgY }}
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: .8, delay: .5, ease: [.16, 1, .3, 1] }}
        className="relative z-10 w-full max-w-5xl px-6 pb-0"
      >
        {/* glow under image */}
        <div className="absolute inset-x-16 bottom-0 h-24 rounded-full blur-3xl bg-em/10 pointer-events-none" />
        <div className="relative rounded-2xl overflow-hidden border border-ink-700/60 shadow-2xl shadow-black/60"
          style={{ boxShadow: '0 32px 80px rgba(0,0,0,.7), 0 0 0 1px rgba(16,185,129,.08), inset 0 1px 0 rgba(255,255,255,.03)' }}>
          {/* browser chrome bar */}
          <div className="flex items-center gap-2 px-4 py-3 bg-ink-900 border-b border-ink-800/80">
            <span className="w-2.5 h-2.5 rounded-full bg-ink-700" />
            <span className="w-2.5 h-2.5 rounded-full bg-ink-700" />
            <span className="w-2.5 h-2.5 rounded-full bg-ink-700" />
            <div className="flex-1 mx-3 bg-ink-800 rounded-md h-5 flex items-center px-2.5">
              <span className="text-[10px] text-slate-600 font-mono">app.yu-na.io/budos</span>
            </div>
          </div>
          <Image
            src="/brand/B09-dashboard-preview.png"
            alt="BudOS — panel przetargowy"
            width={1200}
            height={750}
            className="w-full h-auto block"
            priority
          />
        </div>
      </motion.div>
    </section>
  );
}

// ─── Stats bar ────────────────────────────────────────────────────────────────
const STATS = [
  { value: '2 137', label: 'przetargów monitorowanych' },
  { value: '< 3 min', label: 'analiza SWZ' },
  { value: '94%', label: 'trafność GO/NO-GO' },
  { value: '+23%', label: 'skuteczność ofert' },
];

function StatsBar() {
  return (
    <section className="border-y border-ink-800/50 bg-ink-900/25">
      <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4">
        {STATS.map((s, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .07 }}
            className={`flex flex-col items-center py-8 px-4 ${i < 3 ? 'border-r border-ink-800/50' : ''}`}>
            <span className="text-2xl md:text-3xl font-bold text-slate-100 font-mono tabular-nums">{s.value}</span>
            <span className="text-[11px] text-slate-600 mt-1 text-center">{s.label}</span>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

// ─── Product section ──────────────────────────────────────────────────────────
function ProductSection() {
  return (
    <section className="px-6 py-28 overflow-hidden">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-20">
          <span className="text-[11px] text-em font-semibold uppercase tracking-[.16em]">Flagship — BudOS</span>
          <h2 className="text-[clamp(1.9rem,4vw,3rem)] font-bold text-slate-100 mt-3 tracking-tight" style={{ fontFamily: 'var(--font-space)' }}>
            Jeden system. Całe postępowanie.
          </h2>
          <p className="text-sm text-slate-500 mt-3 max-w-xl mx-auto leading-relaxed">
            Od znalezienia przetargu, przez analizę SWZ, wycenę KNR, aż po złożoną ofertę — BudOS prowadzi Cię przez każdy krok.
          </p>
        </motion.div>

        {/* Feature rows — alternating image + text */}

        {/* Row 1: Scoring GO/NO-GO */}
        <div className="flex flex-col lg:flex-row items-center gap-12 mb-24">
          <motion.div initial={{ opacity: 0, x: -32 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: .6 }}
            className="flex-1 min-w-0">
            <span className="text-[10px] font-bold text-em/70 uppercase tracking-[.16em] mb-3 block">Silnik decyzyjny</span>
            <h3 className="text-2xl md:text-3xl font-bold text-slate-100 mb-4 leading-snug" style={{ fontFamily: 'var(--font-space)' }}>
              GO lub NO-GO<br />w 3 minuty.
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed mb-6">
              Algorytm AHP analizuje SWZ, warunki udziału, wymagania finansowe i technikę. Dostaje scoring 0–100 z rekomendacją. Koniec z traceniem tygodnia na przetarg, którego nie wygrasz.
            </p>
            <ul className="space-y-2.5">
              {['Pełna analiza dokumentów SWZ', 'Scoring AHP z wagami branżowymi', 'Analiza ryzyka kontraktowego', 'Rekomendacja z uzasadnieniem'].map((item, i) => (
                <li key={i} className="flex items-center gap-2.5 text-xs text-slate-400">
                  <CheckCircle2 className="w-3.5 h-3.5 text-em shrink-0" /> {item}
                </li>
              ))}
            </ul>
          </motion.div>
          <motion.div initial={{ opacity: 0, x: 32 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: .6, delay: .1 }}
            className="flex-1 min-w-0 max-w-lg">
            <div className="relative rounded-2xl overflow-hidden border border-ink-700/50 shadow-xl shadow-black/40"
              style={{ boxShadow: '0 20px 60px rgba(0,0,0,.5), 0 0 0 1px rgba(16,185,129,.06)' }}>
              <Image src="/brand/B05-hero-score.png" alt="Scoring GO/NO-GO" width={800} height={500} className="w-full h-auto block" />
            </div>
          </motion.div>
        </div>

        {/* Row 2: Silnik AI dark */}
        <div className="flex flex-col lg:flex-row-reverse items-center gap-12 mb-24">
          <motion.div initial={{ opacity: 0, x: 32 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: .6 }}
            className="flex-1 min-w-0">
            <span className="text-[10px] font-bold text-em/70 uppercase tracking-[.16em] mb-3 block">Analiza AI</span>
            <h3 className="text-2xl md:text-3xl font-bold text-slate-100 mb-4 leading-snug" style={{ fontFamily: 'var(--font-space)' }}>
              AI czyta SWZ.<br />Ty podejmujesz decyzję.
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed mb-6">
              Model wytrenowany na tysiącach polskich i europejskich postępowań. Rozumie kody CPV, warunki podmiotowe i kryteria oceny. Nie musisz czytać 200 stron — dostajesz esencję.
            </p>
            <ul className="space-y-2.5">
              {['Ekstrakcja kryteriów oceny ofert', 'Mapowanie kodów CPV', 'Wykrywanie klauzul ryzyka', 'Porównanie z profilem firmy'].map((item, i) => (
                <li key={i} className="flex items-center gap-2.5 text-xs text-slate-400">
                  <CheckCircle2 className="w-3.5 h-3.5 text-em shrink-0" /> {item}
                </li>
              ))}
            </ul>
          </motion.div>
          <motion.div initial={{ opacity: 0, x: -32 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: .6, delay: .1 }}
            className="flex-1 min-w-0 max-w-lg">
            <div className="relative rounded-2xl overflow-hidden border border-ink-700/50 shadow-xl shadow-black/40"
              style={{ boxShadow: '0 20px 60px rgba(0,0,0,.5), 0 0 0 1px rgba(16,185,129,.06)' }}>
              <Image src="/brand/B03-feature-silnik-dark.png" alt="Silnik AI" width={800} height={500} className="w-full h-auto block" />
            </div>
          </motion.div>
        </div>

        {/* Row 3: Kosztorysy */}
        <div className="flex flex-col lg:flex-row items-center gap-12">
          <motion.div initial={{ opacity: 0, x: -32 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: .6 }}
            className="flex-1 min-w-0">
            <span className="text-[10px] font-bold text-em/70 uppercase tracking-[.16em] mb-3 block">Kosztorysy KNR/ICB</span>
            <h3 className="text-2xl md:text-3xl font-bold text-slate-100 mb-4 leading-snug" style={{ fontFamily: 'var(--font-space)' }}>
              Wycena w 10 minut,<br />nie w 3 dni.
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed mb-6">
              Baza InterCenBud z aktualnymi stawkami. Automatyczne pozycje KNR. Symulacja Monte Carlo dla marży. Eksport do Excel lub PDF gotowego do złożenia.
            </p>
            <ul className="space-y-2.5">
              {['Baza KNR + ICB na bieżąco', 'Automatyczne pozycje kosztorysowe', 'Symulacja Monte Carlo marży', 'Eksport Excel / PDF / DOCX'].map((item, i) => (
                <li key={i} className="flex items-center gap-2.5 text-xs text-slate-400">
                  <CheckCircle2 className="w-3.5 h-3.5 text-em shrink-0" /> {item}
                </li>
              ))}
            </ul>
          </motion.div>
          <motion.div initial={{ opacity: 0, x: 32 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: .6, delay: .1 }}
            className="flex-1 min-w-0 max-w-lg">
            <div className="relative rounded-2xl overflow-hidden border border-ink-700/50 shadow-xl shadow-black/40"
              style={{ boxShadow: '0 20px 60px rgba(0,0,0,.5), 0 0 0 1px rgba(16,185,129,.06)' }}>
              <Image src="/brand/B07-feature-kosztorys.png" alt="Kosztorysy KNR/ICB" width={800} height={500} className="w-full h-auto block" />
            </div>
          </motion.div>
        </div>

      </div>
    </section>
  );
}

// ─── "Produkt w akcji" full-width ─────────────────────────────────────────────
function ProductInAction() {
  return (
    <section className="px-6 py-20 bg-ink-900/15 border-y border-ink-800/40">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-12">
          <span className="text-[11px] text-em font-semibold uppercase tracking-[.16em]">Produkt w akcji</span>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-100 mt-3" style={{ fontFamily: 'var(--font-space)' }}>
            Tak wygląda BudOS w pracy
          </h2>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: .7 }}
          className="relative rounded-2xl overflow-hidden border border-ink-700/50"
          style={{ boxShadow: '0 40px 100px rgba(0,0,0,.65), 0 0 0 1px rgba(16,185,129,.07)' }}>
          <div className="flex items-center gap-2 px-4 py-3 bg-ink-900 border-b border-ink-800/80">
            <span className="w-2.5 h-2.5 rounded-full bg-nogo/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-warn/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-go/60" />
            <div className="flex-1 mx-3 bg-ink-800 rounded h-5 flex items-center px-2.5">
              <span className="text-[10px] text-slate-600 font-mono">app.yu-na.io/app/budos</span>
            </div>
          </div>
          <Image src="/brand/B02-hero-dark.png" alt="BudOS — pełny widok" width={1400} height={900} className="w-full h-auto block" />
        </motion.div>
      </div>
    </section>
  );
}

// ─── Marketplace preview ──────────────────────────────────────────────────────
function MarketplaceSection() {
  return (
    <section className="px-6 py-28">
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-col lg:flex-row items-center gap-16">
          {/* Text */}
          <motion.div initial={{ opacity: 0, x: -24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} className="flex-1">
            <span className="text-[10px] font-bold text-em/70 uppercase tracking-[.16em] mb-3 block">Ekosystem YU-NA</span>
            <h2 className="text-2xl md:text-3xl font-bold text-slate-100 mb-5 leading-snug" style={{ fontFamily: 'var(--font-space)' }}>
              BudOS to pierwszy produkt.<br />Będzie ich więcej.
            </h2>
            <p className="text-sm text-slate-500 leading-relaxed mb-8">
              YU-NA to platforma produktów AI dla budownictwa. Kupujesz dostęp do narzędzi których potrzebujesz. Każde działa samodzielnie — razem tworzą pełne zaplecze operacyjne firmy.
            </p>
            <div className="space-y-3">
              {[
                { name: 'BudOS', desc: 'Przetargi i oferty', status: 'Dostępny', color: 'text-go' },
                { name: 'Produkt #2', desc: 'Nowe narzędzie AI', status: 'Q3 2026', color: 'text-slate-600' },
                { name: 'Produkt #3', desc: 'Nowe narzędzie AI', status: 'Q4 2026', color: 'text-slate-600' },
              ].map((p, i) => (
                <div key={i} className={`flex items-center gap-4 p-3.5 rounded-xl border ${i === 0 ? 'border-em/20 bg-em/5' : 'border-ink-800/50 bg-ink-900/20 opacity-50'}`}>
                  <div className={`w-8 h-8 rounded-lg border flex items-center justify-center text-xs font-bold ${i === 0 ? 'bg-em/10 border-em/20 text-em' : 'bg-ink-800 border-ink-700 text-slate-600'}`} style={{ fontFamily: 'var(--font-space)' }}>
                    {i === 0 ? 'b' : '?'}
                  </div>
                  <div className="flex-1">
                    <p className={`text-xs font-semibold ${i === 0 ? 'text-slate-200' : 'text-slate-600'}`}>{p.name}</p>
                    <p className="text-[11px] text-slate-600">{p.desc}</p>
                  </div>
                  <span className={`text-[10px] font-bold ${p.color}`}>{p.status}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Image */}
          <motion.div initial={{ opacity: 0, x: 24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: .1 }}
            className="flex-1 min-w-0 max-w-md">
            <div className="relative rounded-2xl overflow-hidden border border-ink-700/50"
              style={{ boxShadow: '0 24px 64px rgba(0,0,0,.5), 0 0 0 1px rgba(16,185,129,.06)' }}>
              <Image src="/brand/B06-feature-zwiad.png" alt="Zwiad przetargów" width={700} height={500} className="w-full h-auto block" />
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// ─── Social proof ─────────────────────────────────────────────────────────────
const REVIEWS = [
  { name: 'Marek W.', role: 'Dyrektor ds. Ofert', quote: 'BudOS skrócił czas analizy przetargu z 2 dni do 3 godzin. Wygrywamy więcej przetargów przy mniejszym nakładzie pracy.' },
  { name: 'Anna K.', role: 'Estimator, generalny wykonawca', quote: 'Silnik GO/NO-GO jest precyzyjny. Przestałam tracić czas na przetargi, które i tak przegramy.' },
  { name: 'Tomasz P.', role: 'Prezes, firma infrastrukturalna', quote: 'Kosztorysy KNR generowane automatycznie — to był game-changer. Zespół zaoszczędził 2 dni w tygodniu.' },
];

function SocialProof() {
  return (
    <section className="px-6 py-24 bg-ink-900/10 border-y border-ink-800/40">
      <div className="max-w-5xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="flex flex-col items-center mb-14">
          <div className="flex gap-0.5 mb-4">{[...Array(5)].map((_, i) => <Star key={i} className="w-4 h-4 text-warn fill-warn" />)}</div>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-100 text-center" style={{ fontFamily: 'var(--font-space)' }}>
            200+ firm budowlanych już wybrało BudOS
          </h2>
        </motion.div>
        <div className="grid md:grid-cols-3 gap-4">
          {REVIEWS.map((r, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .1 }}
              className="p-6 rounded-2xl bg-ink-900/40 border border-ink-800/50 hover:border-ink-700/70 transition-colors">
              <Quote className="w-5 h-5 text-em/30 mb-4" />
              <p className="text-sm text-slate-400 leading-relaxed mb-5 italic">&ldquo;{r.quote}&rdquo;</p>
              <div>
                <p className="text-xs font-semibold text-slate-200">{r.name}</p>
                <p className="text-[11px] text-slate-600 mt-0.5">{r.role}</p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Testimonial image */}
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: .2 }}
          className="mt-8 rounded-2xl overflow-hidden border border-ink-700/40"
          style={{ boxShadow: '0 16px 48px rgba(0,0,0,.4)' }}>
          <Image src="/brand/B14-testimonial.png" alt="Opinie klientów BudOS" width={1200} height={400} className="w-full h-auto block" />
        </motion.div>
      </div>
    </section>
  );
}

// ─── CTA ──────────────────────────────────────────────────────────────────────
function CTA() {
  return (
    <section className="px-6 py-28">
      <div className="max-w-2xl mx-auto text-center">
        <motion.div initial={{ opacity: 0, scale: .97 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ duration: .5 }}
          className="relative p-10 md:p-14 rounded-3xl border border-em/20 bg-ink-900/50 overflow-hidden animate-border-pulse">
          <div className="absolute inset-0 pointer-events-none"
            style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(16,185,129,.09) 0%, transparent 55%)' }} />
          <span className="text-[10px] text-em font-semibold uppercase tracking-[.16em]">Zacznij dziś</span>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 mt-4 mb-4 leading-tight" style={{ fontFamily: 'var(--font-space)' }}>
            Gotowy na przewagę?
          </h2>
          <p className="text-sm text-slate-500 mb-8">14 dni za darmo. Bez karty kredytowej. Anuluj w dowolnej chwili.</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/signup" className="group flex items-center gap-2 px-8 py-3.5 rounded-xl bg-em text-ink-950 font-bold text-sm hover:bg-em/90 transition-all glow-em shadow-xl shadow-em/25">
              Zacznij za darmo <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link href="/budos" className="flex items-center gap-1.5 px-6 py-3.5 rounded-xl text-sm text-slate-400 hover:text-slate-200 transition-colors">
              Poznaj BudOS <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="flex items-center justify-center gap-5 mt-8">
            {['Bez zobowiązań', 'Darmowe 14 dni', 'Wsparcie PL'].map((t, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[11px] text-slate-600">
                <CheckCircle2 className="w-3 h-3 text-em" /> {t}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ─── Footer ───────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="border-t border-ink-800/50 px-6 py-10">
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-col md:flex-row items-start justify-between gap-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Hexagon className="w-5 h-5 text-em" strokeWidth={1.5} />
              <span className="text-sm font-bold text-slate-300" style={{ fontFamily: 'var(--font-space)' }}>YU-NA</span>
            </div>
            <p className="text-xs text-slate-600 max-w-xs leading-relaxed">Platforma AI narzędzi dla firm budowlanych. Premiera 2026.</p>
          </div>
          <div className="flex gap-12 text-xs">
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">Produkty</p>
              <div className="space-y-2">
                <Link href="/budos" className="block text-slate-600 hover:text-slate-300 transition-colors">BudOS</Link>
                <span className="block text-slate-700">Wkrótce...</span>
              </div>
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">Konto</p>
              <div className="space-y-2">
                <Link href="/signup" className="block text-slate-600 hover:text-slate-300 transition-colors">Rejestracja</Link>
                <Link href="/login"  className="block text-slate-600 hover:text-slate-300 transition-colors">Logowanie</Link>
              </div>
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">Prawne</p>
              <div className="space-y-2">
                <Link href="/terms"   className="block text-slate-600 hover:text-slate-300 transition-colors">Regulamin</Link>
                <Link href="/privacy" className="block text-slate-600 hover:text-slate-300 transition-colors">Prywatność</Link>
              </div>
            </div>
          </div>
        </div>
        <div className="border-t border-ink-800/40 mt-8 pt-6 flex items-center justify-between">
          <p className="text-[11px] text-slate-700">© 2026 YU-NA. Wszelkie prawa zastrzeżone.</p>
          <p className="text-[11px] text-slate-700 font-mono">PRECYZJA · ZWIAD · PRZEWAGA</p>
        </div>
      </div>
    </footer>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <main className="min-h-screen bg-ink-950 overflow-x-hidden">
      <Navbar />
      <Hero />
      <StatsBar />
      <ProductSection />
      <ProductInAction />
      <MarketplaceSection />
      <SocialProof />
      <CTA />
      <Footer />
    </main>
  );
}
