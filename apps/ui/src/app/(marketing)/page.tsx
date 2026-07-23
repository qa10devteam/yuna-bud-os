'use client';
/* YU-NA Landing v4 — Platform Intelligence, nie single product
 * Hero: YU-NA jako data intelligence platform
 * Products: BudOS (featured), + "Stay Tuned" upcoming
 * Tone: szeroki, ambicja, market edge — nie "przetargi"
 */

import Link from 'next/link';
import Image from 'next/image';
import { motion, useReducedMotion } from 'motion/react';
import { useState, useEffect, useRef } from 'react';

// ── TOKEN SYSTEM ──────────────────────────────────────────────────────────────
const T = {
  bg0:        '#f7f9fc',
  bg1:        '#ffffff',
  bg2:        '#f0f3f8',
  bg3:        '#e8ecf3',
  edge0:      '#dde3ec',
  edge1:      '#c8d0dd',
  ink:        '#0c1524',
  muted:      '#5a6d84',
  faint:      '#8fa0b4',
  accent:     '#16c984',
  accentDim:  '#0d7a4f',
  accentSub:  'rgba(22,201,132,0.08)',
  accentBrd:  'rgba(22,201,132,0.25)',
  data:       '#2c3e52',
  amber:      '#f59e0b',
  blue:       '#60a5fa',
  serif:      'var(--font-dm-serif)',
  sans:       'var(--font-space)',
  mono:       'var(--font-jetbrains)',
} as const;

// ── ANIMATED COUNTER ──────────────────────────────────────────────────────────
function Counter({ to, suffix = '' }: { to: number; suffix?: string }) {
  const [val, setVal] = useState(0);
  const started = useRef(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !started.current) {
        started.current = true;
        const dur = 1400;
        const start = performance.now();
        const tick = (now: number) => {
          const t = Math.min((now - start) / dur, 1);
          const ease = 1 - Math.pow(1 - t, 3);
          setVal(Math.round(ease * to));
          if (t < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      }
    }, { threshold: 0.3 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [to]);

  return <span ref={ref}>{val.toLocaleString('pl-PL')}{suffix}</span>;
}

// ── NAV ───────────────────────────────────────────────────────────────────────
function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 24);
    window.addEventListener('scroll', h, { passive: true });
    return () => window.removeEventListener('scroll', h);
  }, []);

  return (
    <nav style={{
      position: 'fixed', top: 20, left: '50%', transform: 'translateX(-50%)',
      zIndex: 100, display: 'flex', alignItems: 'center',
      gap: 0,
      background: scrolled ? 'rgba(255,255,255,0.92)' : 'rgba(255,255,255,0.80)',
      backdropFilter: 'blur(20px)',
      border: `1px solid ${scrolled ? T.edge0 : 'rgba(221,227,236,0.6)'}`,
      borderRadius: 999, padding: '8px 10px 8px 20px',
      boxShadow: scrolled ? '0 4px 24px rgba(12,21,36,0.09)' : '0 2px 12px rgba(12,21,36,0.05)',
      transition: 'all 0.3s ease',
      whiteSpace: 'nowrap',
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 32 }}>
        <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={22} height={22} style={{ borderRadius: 6 }} />
        <span style={{ fontFamily: T.sans, fontWeight: 700, fontSize: 14, color: T.ink, letterSpacing: '-0.02em' }}>
          YU-NA
        </span>
      </div>

      {/* Links */}
      {[
        { label: 'BudOS', href: '/budos' },
        { label: 'O platformie', href: '#platforma' },
      ].map(l => (
        <Link key={l.label} href={l.href} style={{
          fontFamily: T.sans, fontSize: 13, color: T.muted, fontWeight: 500,
          padding: '6px 14px', borderRadius: 999,
          transition: 'color 0.2s',
          textDecoration: 'none',
        }}
          onMouseEnter={e => (e.currentTarget.style.color = T.ink)}
          onMouseLeave={e => (e.currentTarget.style.color = T.muted)}
        >
          {l.label}
        </Link>
      ))}

      {/* CTA */}
      <Link href="/signup" style={{
        marginLeft: 8,
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: T.ink, color: '#fff',
        fontFamily: T.sans, fontSize: 13, fontWeight: 700,
        padding: '9px 20px', borderRadius: 999,
        textDecoration: 'none',
        transition: 'background 0.2s',
      }}
        onMouseEnter={e => (e.currentTarget.style.background = '#1a2d47')}
        onMouseLeave={e => (e.currentTarget.style.background = T.ink)}
      >
        Zacznij
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M2 6h8M7 3l3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </Link>
    </nav>
  );
}

// ── HERO ──────────────────────────────────────────────────────────────────────
function Hero({ reduce }: { reduce: boolean | null }) {
  return (
    <section style={{
      minHeight: '100vh',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: '120px 24px 80px',
      position: 'relative',
    }}>
      {/* Subtle radial bg */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 70% 50% at 50% 20%, rgba(22,201,132,0.055) 0%, transparent 70%)',
      }} />

      {/* Eyebrow */}
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: T.accentSub,
          border: `1px solid ${T.accentBrd}`,
          borderRadius: 999, padding: '5px 14px',
          marginBottom: 40,
        }}
      >
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: T.accent,
          boxShadow: `0 0 8px ${T.accent}`,
          display: 'block',
          animation: 'pulse 2s ease-in-out infinite',
        }} />
        <span style={{ fontFamily: T.mono, fontSize: 11, fontWeight: 600, color: T.accent, letterSpacing: '0.1em' }}>
          MARKET INTELLIGENCE PLATFORM
        </span>
      </motion.div>

      {/* Headline */}
      <motion.h1
        initial={reduce ? false : { opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
        style={{
          fontFamily: T.serif,
          fontSize: 'clamp(52px, 7vw, 96px)',
          fontWeight: 400,
          color: T.ink,
          textAlign: 'center',
          lineHeight: 1.08,
          letterSpacing: '-0.03em',
          maxWidth: 900,
          marginBottom: 28,
        }}
      >
        Dane, które dają<br />
        <em style={{ fontStyle: 'italic', color: T.accent }}>przewagę.</em>
      </motion.h1>

      {/* Subline */}
      <motion.p
        initial={reduce ? false : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, delay: 0.2 }}
        style={{
          fontFamily: T.sans, fontSize: 18, color: T.muted,
          textAlign: 'center', maxWidth: 560, lineHeight: 1.65,
          marginBottom: 48,
        }}
      >
        YU-NA to platforma intelligence, która zamienia surowe dane rynkowe
        w konkretne decyzje biznesowe — szybciej niż konkurencja.
      </motion.p>

      {/* CTAs */}
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.32 }}
        style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center' }}
      >
        <Link href="/budos" style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: T.accent, color: T.bg1,
          fontFamily: T.sans, fontSize: 15, fontWeight: 700,
          padding: '14px 32px', borderRadius: 999,
          textDecoration: 'none',
          boxShadow: `0 4px 24px rgba(22,201,132,0.28)`,
          transition: 'all 0.2s',
        }}
          onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = `0 8px 32px rgba(22,201,132,0.36)`; }}
          onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = `0 4px 24px rgba(22,201,132,0.28)`; }}
        >
          Odkryj BudOS
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </Link>
        <a href="#platforma" style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          border: `1.5px solid ${T.edge1}`, color: T.muted,
          fontFamily: T.sans, fontSize: 15, fontWeight: 500,
          padding: '13px 28px', borderRadius: 999,
          textDecoration: 'none', background: T.bg1,
          transition: 'all 0.2s',
        }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = T.edge0; e.currentTarget.style.color = T.ink; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = T.edge1; e.currentTarget.style.color = T.muted; }}
        >
          O platformie
        </a>
      </motion.div>

      {/* Stat strip */}
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        style={{
          marginTop: 80,
          display: 'flex', gap: 0, alignItems: 'stretch',
          background: T.bg1,
          border: `1px solid ${T.edge0}`,
          borderRadius: 20,
          overflow: 'hidden',
          boxShadow: '0 2px 16px rgba(12,21,36,0.05)',
        }}
      >
        {[
          { value: 1400000, suffix: '+', label: 'ogłoszeń w bazie' },
          { value: 12, suffix: 'K+', label: 'zamawiających' },
          { value: 30, suffix: 's', label: 'czas analizy AI' },
          { value: 3, suffix: ' branże', label: 'w przygotowaniu' },
        ].map((s, i) => (
          <div key={i} style={{
            padding: '20px 36px',
            borderRight: i < 3 ? `1px solid ${T.edge0}` : undefined,
            textAlign: 'center',
          }}>
            <div style={{ fontFamily: T.mono, fontSize: 26, fontWeight: 700, color: T.ink, letterSpacing: '-0.03em' }}>
              <Counter to={s.value} suffix={s.suffix} />
            </div>
            <div style={{ fontFamily: T.sans, fontSize: 11, color: T.faint, marginTop: 4, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              {s.label}
            </div>
          </div>
        ))}
      </motion.div>
    </section>
  );
}

// ── PLATFORM SECTION ──────────────────────────────────────────────────────────
function PlatformSection({ reduce }: { reduce: boolean | null }) {
  return (
    <section id="platforma" style={{
      padding: '100px 24px',
      borderTop: `1px solid ${T.edge0}`,
      background: T.bg1,
    }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>

        {/* Header */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
          style={{ textAlign: 'center', marginBottom: 72 }}
        >
          <p style={{ fontFamily: T.mono, fontSize: 11, letterSpacing: '0.12em', color: T.accent, fontWeight: 600, textTransform: 'uppercase', marginBottom: 20 }}>
            Jak działa YU-NA
          </p>
          <h2 style={{ fontFamily: T.serif, fontSize: 'clamp(36px, 4vw, 60px)', color: T.ink, lineHeight: 1.1, letterSpacing: '-0.025em', marginBottom: 20 }}>
            Dane rynkowe → decyzja<br />w minutach, nie tygodniach.
          </h2>
          <p style={{ fontFamily: T.sans, fontSize: 17, color: T.muted, maxWidth: 520, margin: '0 auto', lineHeight: 1.65 }}>
            Zbieramy, filtrujemy i analizujemy dane z setek źródeł. Dostarczamy gotową inteligencję — dopasowaną do konkretnej branży i konkretnej decyzji.
          </p>
        </motion.div>

        {/* 3-column feature grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
          {[
            {
              icon: (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
                </svg>
              ),
              title: 'Zbieranie danych',
              desc: 'Automatyczny monitoring dziesiątek źródeł — przetargi, ogłoszenia, raporty rynkowe, dane rejestrowe. Zero ręcznej pracy.',
            },
            {
              icon: (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 20V10M18 20V4M6 20v-4"/>
                </svg>
              ),
              title: 'Analiza AI',
              desc: 'Modele wyuczone na specyfice branży. Scoring, klasyfikacja, ekstrakcja sygnałów — kontekst którego generyczne LLM nie rozumieją.',
            },
            {
              icon: (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>
                </svg>
              ),
              title: 'Gotowa decyzja',
              desc: 'Nie "dashboard z wykresami" — konkretna rekomendacja. GO/NO-GO, wycena, profil ryzyka. Działaj, nie analizuj.',
            },
          ].map((f, i) => (
            <motion.div
              key={i}
              initial={reduce ? false : { opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
              style={{
                background: T.bg0,
                border: `1px solid ${T.edge0}`,
                borderRadius: 20, padding: '36px 32px',
              }}
            >
              <div style={{
                width: 48, height: 48, borderRadius: 14,
                background: T.accentSub, border: `1px solid ${T.accentBrd}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: T.accent, marginBottom: 24,
              }}>
                {f.icon}
              </div>
              <h3 style={{ fontFamily: T.sans, fontSize: 17, fontWeight: 700, color: T.ink, marginBottom: 12, letterSpacing: '-0.015em' }}>
                {f.title}
              </h3>
              <p style={{ fontFamily: T.sans, fontSize: 14, color: T.muted, lineHeight: 1.7 }}>
                {f.desc}
              </p>
            </motion.div>
          ))}
        </div>

      </div>
    </section>
  );
}

// ── PRODUCTS SECTION ──────────────────────────────────────────────────────────
function ProductsSection({ reduce }: { reduce: boolean | null }) {
  return (
    <section style={{ padding: '100px 24px', borderTop: `1px solid ${T.edge0}` }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>

        <motion.div
          initial={reduce ? false : { opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          style={{ marginBottom: 56 }}
        >
          <p style={{ fontFamily: T.mono, fontSize: 11, letterSpacing: '0.12em', color: T.accent, fontWeight: 600, textTransform: 'uppercase', marginBottom: 16 }}>
            Produkty
          </p>
          <h2 style={{ fontFamily: T.serif, fontSize: 'clamp(34px, 4vw, 56px)', color: T.ink, lineHeight: 1.1, letterSpacing: '-0.025em' }}>
            Jeden ekosystem.<br />Wiele rynków.
          </h2>
        </motion.div>

        {/* BudOS — featured, full width */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          style={{ marginBottom: 20 }}
        >
          <Link href="/budos" style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr',
            background: T.ink, borderRadius: 24, overflow: 'hidden',
            textDecoration: 'none', position: 'relative',
            boxShadow: '0 8px 48px rgba(12,21,36,0.14)',
          }}
            onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 16px 64px rgba(12,21,36,0.22)')}
            onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 8px 48px rgba(12,21,36,0.14)')}
          >
            {/* Left — copy */}
            <div style={{ padding: '56px 56px 56px 56px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                {/* Badge */}
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  background: T.accentSub, border: `1px solid ${T.accentBrd}`,
                  borderRadius: 999, padding: '5px 14px', marginBottom: 32,
                }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: T.accent, display: 'block' }} />
                  <span style={{ fontFamily: T.mono, fontSize: 10, fontWeight: 700, color: T.accent, letterSpacing: '0.12em' }}>PRODUKT #1 · LIVE</span>
                </div>

                <h3 style={{ fontFamily: T.serif, fontSize: 'clamp(36px, 3.5vw, 52px)', color: '#ffffff', lineHeight: 1.08, letterSpacing: '-0.025em', marginBottom: 20 }}>
                  BudOS
                </h3>
                <p style={{ fontFamily: T.sans, fontSize: 16, color: 'rgba(255,255,255,0.5)', lineHeight: 1.7, maxWidth: '38ch', marginBottom: 40 }}>
                  Intelligence dla rynku zamówień publicznych. Monitoring BZP/TED, analiza SWZ, scoring GO/NO-GO, kosztorys AI — od ogłoszenia do oferty.
                </p>

                {/* Key stats */}
                <div style={{ display: 'flex', gap: 32 }}>
                  {[
                    { v: '1.4M', l: 'ogłoszeń' },
                    { v: '30s', l: 'analiza SWZ' },
                    { v: 'KNR/ICB', l: 'kosztorys' },
                  ].map((s, i) => (
                    <div key={i}>
                      <div style={{ fontFamily: T.mono, fontSize: 22, fontWeight: 700, color: '#fff', letterSpacing: '-0.02em' }}>{s.v}</div>
                      <div style={{ fontFamily: T.sans, fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 3, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{s.l}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* CTA */}
              <div style={{
                marginTop: 48,
                display: 'inline-flex', alignItems: 'center', gap: 8,
                color: T.accent, fontFamily: T.sans, fontSize: 14, fontWeight: 700,
                letterSpacing: '-0.01em',
              }}>
                Odkryj BudOS
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
            </div>

            {/* Right — screenshot */}
            <div style={{ position: 'relative', overflow: 'hidden' }}>
              {/* Ambient glow */}
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, pointerEvents: 'none',
                background: 'radial-gradient(ellipse at 30% 20%, rgba(22,201,132,0.12) 0%, transparent 60%)',
              }} />
              {/* Browser bar */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '12px 16px',
                background: 'rgba(255,255,255,0.04)',
                borderBottom: '1px solid rgba(255,255,255,0.07)',
              }}>
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'rgba(255,59,48,0.45)', display: 'block' }} />
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'rgba(255,159,10,0.45)', display: 'block' }} />
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'rgba(40,205,65,0.45)', display: 'block' }} />
                <div style={{
                  flex: 1, marginLeft: 8, height: 18, borderRadius: 4,
                  background: 'rgba(255,255,255,0.06)',
                  display: 'flex', alignItems: 'center', paddingLeft: 10,
                }}>
                  <span style={{ fontFamily: T.mono, fontSize: 10, color: 'rgba(255,255,255,0.25)' }}>app.yu-na.io/zwiad</span>
                </div>
              </div>
              <Image
                src="/brand/live-dashboard.png"
                alt="BudOS dashboard"
                width={720}
                height={480}
                style={{ width: '100%', height: 'auto', display: 'block' }}
              />
            </div>
          </Link>
        </motion.div>

        {/* Coming soon grid — 2 teaser cards */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {[
            {
              label: 'Wkrótce',
              title: 'Projekt #2',
              desc: 'Nowy rynek. Nowe dane. Ta sama przewaga.',
              accent: T.amber,
              accentSub: 'rgba(245,158,11,0.07)',
              accentBrd: 'rgba(245,158,11,0.2)',
            },
            {
              label: 'Wkrótce',
              title: 'Projekt #3',
              desc: 'Stay tuned.',
              accent: T.blue,
              accentSub: 'rgba(96,165,250,0.07)',
              accentBrd: 'rgba(96,165,250,0.2)',
            },
          ].map((p, i) => (
            <motion.div
              key={i}
              initial={reduce ? false : { opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.45, delay: i * 0.1 }}
              style={{
                background: T.bg0,
                border: `1.5px solid ${T.edge0}`,
                borderRadius: 20, padding: '40px 36px',
                display: 'flex', flexDirection: 'column', gap: 16,
                position: 'relative', overflow: 'hidden',
              }}
            >
              {/* Subtle glow */}
              <div style={{
                position: 'absolute', top: -40, right: -40,
                width: 160, height: 160, borderRadius: '50%',
                background: `radial-gradient(circle, ${p.accentSub.replace('0.07', '0.18')} 0%, transparent 70%)`,
                pointerEvents: 'none',
              }} />

              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: p.accentSub,
                border: `1px solid ${p.accentBrd}`,
                borderRadius: 999, padding: '4px 12px',
                fontFamily: T.mono, fontSize: 10, fontWeight: 700,
                color: p.accent, letterSpacing: '0.1em',
                alignSelf: 'flex-start',
              }}>
                {p.label}
              </span>

              <h3 style={{ fontFamily: T.serif, fontSize: 32, color: T.ink, letterSpacing: '-0.02em', lineHeight: 1.1 }}>
                {p.title}
              </h3>
              <p style={{ fontFamily: T.sans, fontSize: 14, color: T.muted, lineHeight: 1.65 }}>
                {p.desc}
              </p>

              {/* Notify CTA */}
              <div style={{ marginTop: 8 }}>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  fontFamily: T.sans, fontSize: 13, fontWeight: 600, color: T.faint,
                  border: `1px solid ${T.edge0}`, borderRadius: 999,
                  padding: '8px 18px', cursor: 'default',
                }}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
                  </svg>
                  Powiadom mnie
                </span>
              </div>
            </motion.div>
          ))}
        </div>

      </div>
    </section>
  );
}

// ── FINAL CTA ─────────────────────────────────────────────────────────────────
function FinalCTA({ reduce }: { reduce: boolean | null }) {
  return (
    <section style={{
      padding: '120px 24px',
      borderTop: `1px solid ${T.edge0}`,
      background: T.bg1,
      textAlign: 'center',
    }}>
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        style={{ maxWidth: 640, margin: '0 auto' }}
      >
        <p style={{ fontFamily: T.mono, fontSize: 11, letterSpacing: '0.12em', color: T.accent, fontWeight: 600, textTransform: 'uppercase', marginBottom: 24 }}>
          Zacznij teraz
        </p>
        <h2 style={{ fontFamily: T.serif, fontSize: 'clamp(40px, 5vw, 68px)', color: T.ink, lineHeight: 1.08, letterSpacing: '-0.03em', marginBottom: 24 }}>
          Twój rynek.<br />Twoja przewaga.
        </h2>
        <p style={{ fontFamily: T.sans, fontSize: 17, color: T.muted, lineHeight: 1.65, marginBottom: 48 }}>
          Dołącz do firm które już działają szybciej dzięki YU-NA.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link href="/budos" style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: T.accent, color: T.bg1,
            fontFamily: T.sans, fontSize: 15, fontWeight: 700,
            padding: '15px 36px', borderRadius: 999,
            textDecoration: 'none',
            boxShadow: `0 4px 24px rgba(22,201,132,0.28)`,
          }}>
            Odkryj BudOS
          </Link>
          <Link href="/signup" style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            border: `1.5px solid ${T.edge1}`, color: T.muted,
            fontFamily: T.sans, fontSize: 15, fontWeight: 500,
            padding: '14px 28px', borderRadius: 999,
            textDecoration: 'none', background: T.bg1,
          }}>
            Zarejestruj się
          </Link>
        </div>
      </motion.div>
    </section>
  );
}

// ── FOOTER ────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer style={{
      borderTop: `1px solid ${T.edge0}`,
      padding: '32px 24px',
      background: T.bg0,
    }}>
      <div style={{
        maxWidth: 1100, margin: '0 auto',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={20} height={20} style={{ borderRadius: 5, opacity: 0.7 }} />
          <span style={{ fontFamily: T.sans, fontSize: 13, color: T.faint }}>
            © 2026 YU-NA · Market Intelligence Platform
          </span>
        </div>
        <div style={{ display: 'flex', gap: 24 }}>
          {[
            { l: 'BudOS', h: '/budos' },
            { l: 'Logowanie', h: '/login' },
            { l: 'Regulamin', h: '/terms' },
            { l: 'Prywatność', h: '/privacy' },
          ].map(item => (
            <Link key={item.l} href={item.h} style={{
              fontFamily: T.sans, fontSize: 12, color: T.faint,
              textDecoration: 'none',
              transition: 'color 0.2s',
            }}
              onMouseEnter={e => (e.currentTarget.style.color = T.muted)}
              onMouseLeave={e => (e.currentTarget.style.color = T.faint)}
            >
              {item.l}
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}

// ── PAGE ──────────────────────────────────────────────────────────────────────
export default function YunaLandingPage() {
  const reduce = useReducedMotion();

  return (
    <div style={{ background: T.bg0, minHeight: '100vh' }}>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.6; transform: scale(0.85); }
        }
      `}</style>

      <Nav />
      <Hero reduce={reduce} />
      <PlatformSection reduce={reduce} />
      <ProductsSection reduce={reduce} />
      <FinalCTA reduce={reduce} />
      <Footer />
    </div>
  );
}
