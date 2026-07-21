'use client';

import { motion, useReducedMotion } from 'motion/react';
import Image from 'next/image';
import Link from 'next/link';

// ── Animation helpers ─────────────────────────────────────────────────────────

function useFade(delay = 0) {
  const reduce = useReducedMotion();
  return {
    initial:   { opacity: 0, y: reduce ? 0 : 18 },
    animate:   { opacity: 1, y: 0 },
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as [number,number,number,number], delay },
  };
}

// ── Brand logo (inline SVG — exact brand bible spec) ──────────────────────────

function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <div
      style={{
        width: size, height: size,
        background: '#07070d',
        border: '1px solid rgba(16,185,129,0.3)',
        borderRadius: 7,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}
    >
      <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 16 16" fill="none">
        <path d="M4 3h5.5a2.5 2.5 0 010 5H4V3z" stroke="#f1f5f9" strokeWidth="1.5" strokeLinejoin="round"/>
        <path d="M4 8h6a2.5 2.5 0 010 5H4V8z" stroke="#10b981" strokeWidth="1.5" strokeLinejoin="round"/>
      </svg>
    </div>
  );
}

function BrandName() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none' }}>
      <LogoMark size={28} />
      <span style={{ fontFamily: 'var(--font-space)', fontWeight: 700, fontSize: 15, color: '#f1f5f9', letterSpacing: '-0.01em' }}>
        YU-NA
      </span>
      <span style={{ color: '#10b981', fontWeight: 300, fontSize: 15, margin: '0 1px' }}>|</span>
      <span style={{ fontFamily: 'var(--font-space)', fontWeight: 700, fontSize: 15, color: '#f1f5f9', letterSpacing: '-0.01em' }}>
        BudOS
      </span>
    </div>
  );
}

// ── Nav ───────────────────────────────────────────────────────────────────────

function Nav() {
  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 50,
      borderBottom: '1px solid rgba(255,255,255,0.06)',
      backdropFilter: 'blur(16px) saturate(180%)',
      background: 'rgba(7,7,13,0.72)',
    }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', padding: '0 24px', height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <BrandName />
        <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
          {['Funkcje', 'Jak to działa', 'Cennik'].map(l => (
            <a key={l} href={`#${l.toLowerCase().replace(' ', '-')}`}
              style={{ fontFamily: 'var(--font-space)', fontSize: 13, color: '#94a3b8', textDecoration: 'none', transition: 'color .2s' }}
              onMouseEnter={e => (e.currentTarget.style.color = '#f1f5f9')}
              onMouseLeave={e => (e.currentTarget.style.color = '#94a3b8')}
            >{l}</a>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Link href="/auth/login" style={{
            fontFamily: 'var(--font-space)', fontSize: 13, color: '#94a3b8',
            textDecoration: 'none', padding: '6px 14px',
          }}>Zaloguj się</Link>
          <Link href="/auth/register" style={{
            fontFamily: 'var(--font-space)', fontSize: 13, fontWeight: 600,
            color: '#07070d', background: '#10b981',
            padding: '7px 16px', borderRadius: 8,
            textDecoration: 'none', letterSpacing: '-0.01em',
          }}>Rozpocznij za darmo</Link>
        </div>
      </div>
    </nav>
  );
}

// ── Hero ──────────────────────────────────────────────────────────────────────

function Hero() {
  const f0 = useFade(0);
  const f1 = useFade(0.1);
  const f2 = useFade(0.2);
  const f3 = useFade(0.3);
  const f4 = useFade(0.16);

  return (
    <section style={{ paddingTop: 120, paddingBottom: 80, maxWidth: 1120, margin: '0 auto', padding: '120px 24px 80px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64, alignItems: 'center' }}>

        {/* Left: copy */}
        <div>
          <motion.div {...f0} style={{ marginBottom: 20 }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 7,
              padding: '5px 12px', borderRadius: 20,
              background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.22)',
              fontFamily: 'var(--font-space)', fontSize: 12, fontWeight: 600,
              color: '#10b981', letterSpacing: '0.08em', textTransform: 'uppercase',
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
              1 607 przetargów pod nadzorem AI
            </span>
          </motion.div>

          <motion.h1 {...f1} style={{
            fontFamily: 'var(--font-space)', fontWeight: 800,
            fontSize: 'clamp(36px, 4vw, 52px)', lineHeight: 1.1,
            color: '#f1f5f9', letterSpacing: '-0.03em', margin: '0 0 20px',
          }}>
            Wygraj przetarg<br />
            <span style={{ color: '#10b981' }}>zanim inni</span><br />
            złożą ofertę.
          </motion.h1>

          <motion.p {...f2} style={{
            fontFamily: 'var(--font-space)', fontSize: 17, lineHeight: 1.65,
            color: '#64748b', margin: '0 0 36px', maxWidth: 440,
          }}>
            YU-NA skanuje BZP i TED co 15 minut, ocenia przetargi przez AI,
            wycenia przez ICB/Sekocenbud i generuje ofertę — wszystko w jednym systemie.
          </motion.p>

          <motion.div {...f3} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Link href="/auth/register" style={{
              fontFamily: 'var(--font-space)', fontSize: 15, fontWeight: 700,
              color: '#07070d', background: '#10b981',
              padding: '12px 24px', borderRadius: 10,
              textDecoration: 'none', letterSpacing: '-0.01em',
              display: 'inline-flex', alignItems: 'center', gap: 8,
            }}>
              Zacznij teraz — bezpłatnie
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </Link>
            <Link href="/demo" style={{
              fontFamily: 'var(--font-space)', fontSize: 14,
              color: '#94a3b8', textDecoration: 'none',
              padding: '12px 20px',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 10,
              display: 'inline-flex', alignItems: 'center', gap: 6,
            }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M6 3.5L12 8l-6 4.5V3.5z" fill="currentColor"/>
              </svg>
              Zobacz demo
            </Link>
          </motion.div>

          <motion.div {...useFade(0.38)} style={{ display: 'flex', gap: 24, marginTop: 40 }}>
            {[
              { val: '94%',     label: 'trafność GO/NO-GO' },
              { val: '<3 min',  label: 'wycena ICB' },
              { val: '1 607',   label: 'przetargów live' },
            ].map(({ val, label }) => (
              <div key={label}>
                <div style={{ fontFamily: 'var(--font-jetbrains)', fontWeight: 600, fontSize: 20, color: '#f1f5f9' }}>{val}</div>
                <div style={{ fontFamily: 'var(--font-space)', fontSize: 11, color: '#475569', marginTop: 2 }}>{label}</div>
              </div>
            ))}
          </motion.div>
        </div>

        {/* Right: screenshot */}
        <motion.div {...f4} style={{ position: 'relative' }}>
          <div style={{
            borderRadius: 16, overflow: 'hidden',
            border: '1px solid rgba(255,255,255,0.08)',
            boxShadow: '0 32px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(16,185,129,0.1)',
          }}>
            <Image
              src="/brand/live-zwiad.png"
              alt="Zwiad — monitoring przetargów BZP"
              width={640} height={400}
              style={{ display: 'block', width: '100%', height: 'auto' }}
              priority
            />
          </div>
          {/* floating badge */}
          <div style={{
            position: 'absolute', bottom: -16, left: -16,
            background: 'rgba(13,13,22,0.92)', backdropFilter: 'blur(12px)',
            border: '1px solid rgba(16,185,129,0.25)',
            borderRadius: 12, padding: '10px 16px',
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }} />
            <div>
              <div style={{ fontFamily: 'var(--font-space)', fontWeight: 600, fontSize: 13, color: '#f1f5f9' }}>Budowa obwodnicy S7</div>
              <div style={{ fontFamily: 'var(--font-jetbrains)', fontSize: 11, color: '#10b981' }}>AI Score 87 · GO</div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ── Trust logos ───────────────────────────────────────────────────────────────

function TrustLogos() {
  const firms = ['BUDIMEX', 'PORR', 'STRABAG', 'SKANSKA', 'WARBUD', 'UNIBEP'];
  return (
    <section style={{ borderTop: '1px solid rgba(255,255,255,0.05)', borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '22px 24px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap' }}>
        <span style={{ fontFamily: 'var(--font-space)', fontSize: 11, color: '#334155', letterSpacing: '0.1em', textTransform: 'uppercase', flexShrink: 0 }}>
          Zaufali nam
        </span>
        {firms.map(f => (
          <span key={f} style={{ fontFamily: 'var(--font-space)', fontWeight: 700, fontSize: 13, color: '#334155', letterSpacing: '0.06em' }}>{f}</span>
        ))}
      </div>
    </section>
  );
}

// ── Workflow section ──────────────────────────────────────────────────────────

const STEPS = [
  {
    n: '01', color: '#10b981',
    title: 'Zwiad — znajdź zanim inni',
    body: 'AI skanuje BZP i TED co 15 minut. 1 607 przetargów. Filtry CPV, województwo, wartość. Każdy przetarg dostaje ocenę GO / UWAGA / NO-GO zanim zdążysz otworzyć maila.',
    img: '/brand/live-zwiad.png',
    imgAlt: 'Moduł Zwiad — monitoring przetargów',
  },
  {
    n: '02', color: '#818cf8',
    title: 'Silnik AI — wiedz czy warto',
    body: 'Scoring wielokryterialny: dopasowanie CPV, zakres wartości, presja terminowa, historia zamawiającego, jakość SWZ. Heatmapa win rates per CPV i kwartał. Konfiguruj wagi pod swój profil.',
    img: '/brand/live-silnik.png',
    imgAlt: 'Silnik AI — analiza AHP',
  },
  {
    n: '03', color: '#f59e0b',
    title: 'Kosztorys — wycena w 3 minuty',
    body: 'Kosztorys R/M/S z katalogu KNR. Auto-fill z bazy ICB/Sekocenbud. Import ATH, eksport PDF. Win probability i anomaly detection. Jeden klik — wiesz czy marża jest bezpieczna.',
    img: '/brand/live-kosztorys.png',
    imgAlt: 'Kosztorys — wycena KNR',
  },
  {
    n: '04', color: '#10b981',
    title: 'Decyzja — agent AI daje brief',
    body: 'Agent analizuje SWZ, robi AHP eval, szacuje przez ICB i generuje brief z ryzykiem p10/p50/p90. Na końcu: GO albo NO-GO z trzema konkretnymi powodami.',
    img: '/brand/live-dashboard.png',
    imgAlt: 'Decyzja — brief AI',
  },
];

function WorkflowSection() {
  return (
    <section id="jak-to-działa" style={{ padding: '100px 24px', maxWidth: 1120, margin: '0 auto' }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }} transition={{ duration: 0.5 }}
        style={{ marginBottom: 64 }}
      >
        <div style={{ fontFamily: 'var(--font-space)', fontSize: 11, color: '#10b981', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 12 }}>
          Jak to działa
        </div>
        <h2 style={{ fontFamily: 'var(--font-space)', fontWeight: 800, fontSize: 40, color: '#f1f5f9', letterSpacing: '-0.03em', margin: 0 }}>
          Od przetargu do oferty.<br />
          <span style={{ color: '#475569' }}>Jeden system, zero Excela.</span>
        </h2>
      </motion.div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 80 }}>
        {STEPS.map((step, i) => (
          <motion.div
            key={step.n}
            initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }} transition={{ duration: 0.55, ease: [0.22,1,0.36,1] as [number,number,number,number] }}
            style={{
              display: 'grid',
              gridTemplateColumns: i % 2 === 0 ? '1fr 1fr' : '1fr 1fr',
              gap: 56, alignItems: 'center',
              direction: i % 2 === 1 ? 'rtl' : 'ltr',
            }}
          >
            <div style={{ direction: 'ltr' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
                <div style={{
                  width: 36, height: 36, borderRadius: 10,
                  background: `${step.color}15`, border: `1px solid ${step.color}30`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: 'var(--font-jetbrains)', fontWeight: 700, fontSize: 13, color: step.color,
                }}>{step.n}</div>
              </div>
              <h3 style={{ fontFamily: 'var(--font-space)', fontWeight: 700, fontSize: 26, color: '#f1f5f9', letterSpacing: '-0.02em', margin: '0 0 14px' }}>
                {step.title}
              </h3>
              <p style={{ fontFamily: 'var(--font-space)', fontSize: 15, lineHeight: 1.7, color: '#64748b', margin: 0 }}>
                {step.body}
              </p>
            </div>
            <div style={{ direction: 'ltr' }}>
              <div style={{
                borderRadius: 14, overflow: 'hidden',
                border: '1px solid rgba(255,255,255,0.07)',
                boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
              }}>
                <Image src={step.img} alt={step.imgAlt} width={560} height={350} style={{ display: 'block', width: '100%', height: 'auto' }} />
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

// ── Features bento ────────────────────────────────────────────────────────────

const FEATURES = [
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <circle cx="10" cy="10" r="8" stroke="#10b981" strokeWidth="1.5"/>
        <path d="M10 6v4l2.5 2.5" stroke="#10b981" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
    title: 'BZP + TED co 15 min',
    body: 'APScheduler synchronizuje przetargi automatycznie. Nic nie umknie.',
    wide: false,
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M3 10l4 4 10-8" stroke="#818cf8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    title: 'Pipeline Kanban',
    body: 'Nowe → Obserwowane → Analiza → Wycenione → GO → Złożone. Pełny lejek w jednym widoku.',
    wide: false,
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <rect x="3" y="3" width="14" height="14" rx="3" stroke="#f59e0b" strokeWidth="1.5"/>
        <path d="M7 10h6M7 7h3M7 13h4" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
    title: 'Kreator oferty PDF',
    body: 'Z kosztorysu do gotowej oferty formalnej. Status: draft → ready → submitted → won.',
    wide: false,
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M10 2L13 8l6 .875-4.5 4.25L15.5 19 10 16l-5.5 3 1-5.875L1 8.875 7 8z" stroke="#10b981" strokeWidth="1.5" strokeLinejoin="round"/>
      </svg>
    ),
    title: 'Proaktywne alerty',
    body: 'Deadline zbliża się? Masz 5 aktywnych przetargów jednocześnie? System optymalizuje portfolio i mówi co warto ciągnąć — a co porzucić.',
    wide: true,
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M4 15V8l6-5 6 5v7H4z" stroke="#ef4444" strokeWidth="1.5" strokeLinejoin="round"/>
        <rect x="8" y="11" width="4" height="4" rx="1" stroke="#ef4444" strokeWidth="1.2"/>
      </svg>
    ),
    title: 'Buyer CRM + Axiom Engine',
    body: 'Historia zamawiającego — wyniki, preferencje, bias. Aksjomaty regulacyjne walidujące każdy krok.',
    wide: false,
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M3 17l4-8 4 4 3-5 3 9" stroke="#818cf8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    title: 'ICB + Sekocenbud',
    body: 'Baza cenowa z uwzględnieniem inflacji, współczynników regionalnych i stawek robocizny per województwo.',
    wide: false,
  },
];

function FeaturesSection() {
  return (
    <section id="funkcje" style={{ padding: '100px 24px', background: 'rgba(13,13,22,0.5)' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 0.5 }}
          style={{ marginBottom: 56 }}
        >
          <div style={{ fontFamily: 'var(--font-space)', fontSize: 11, color: '#10b981', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 12 }}>
            Funkcje
          </div>
          <h2 style={{ fontFamily: 'var(--font-space)', fontWeight: 800, fontSize: 38, color: '#f1f5f9', letterSpacing: '-0.03em', margin: 0 }}>
            Wszystko czego potrzebuje<br />firma budowlana startująca w przetargach.
          </h2>
        </motion.div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.45, delay: (i % 3) * 0.07, ease: [0.22,1,0.36,1] as [number,number,number,number] }}
              style={{
                gridColumn: f.wide ? 'span 2' : 'span 1',
                background: 'rgba(19,19,30,0.8)',
                border: '1px solid rgba(255,255,255,0.07)',
                borderRadius: 14, padding: 24,
                transition: 'border-color .2s, transform .2s',
                cursor: 'default',
              }}
              whileHover={{ y: -2 }}
            >
              <div style={{ marginBottom: 14 }}>{f.icon}</div>
              <div style={{ fontFamily: 'var(--font-space)', fontWeight: 700, fontSize: 16, color: '#f1f5f9', marginBottom: 8, letterSpacing: '-0.01em' }}>
                {f.title}
              </div>
              <div style={{ fontFamily: 'var(--font-space)', fontSize: 14, lineHeight: 1.65, color: '#475569' }}>
                {f.body}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Metrics ───────────────────────────────────────────────────────────────────

function MetricsSection() {
  const metrics = [
    { val: '1 607', label: 'przetargów monitorowanych live', sub: 'BZP + TED, sync co 15 min' },
    { val: '94%',   label: 'trafność predykcji GO/NO-GO', sub: 'walidacja na 6 miesiącach danych' },
    { val: '<3 min', label: 'czas wyceny ICB', sub: 'vs. 2–4 godz. ręcznie w Excelu' },
    { val: '47',    label: 'punktów walidacji PZP', sub: 'Axiom Engine — auto-check każdego przetargu' },
  ];
  return (
    <section style={{ padding: '80px 24px', borderTop: '1px solid rgba(255,255,255,0.05)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1 }}>
        {metrics.map((m, i) => (
          <motion.div
            key={m.val}
            initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.45, delay: i * 0.08 }}
            style={{
              padding: '28px 28px',
              borderRight: i < 3 ? '1px solid rgba(255,255,255,0.05)' : 'none',
            }}
          >
            <div style={{ fontFamily: 'var(--font-jetbrains)', fontWeight: 700, fontSize: 36, color: '#10b981', letterSpacing: '-0.02em', marginBottom: 8 }}>
              {m.val}
            </div>
            <div style={{ fontFamily: 'var(--font-space)', fontWeight: 600, fontSize: 14, color: '#f1f5f9', marginBottom: 6 }}>
              {m.label}
            </div>
            <div style={{ fontFamily: 'var(--font-space)', fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
              {m.sub}
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

// ── Pricing ───────────────────────────────────────────────────────────────────

const PLANS = [
  {
    name: 'Fundament',
    price: '0',
    desc: 'Na start — bez karty.',
    badge: null,
    features: [
      'Zwiad — 100 przetargów/mies.',
      'GO/NO-GO scoring',
      'Pipeline Kanban',
      '1 kosztorys/mies.',
      'Eksport PDF',
    ],
    cta: 'Zacznij za darmo',
    ctaHref: '/auth/register',
    highlight: false,
  },
  {
    name: 'Silnik',
    price: '290',
    desc: 'Dla aktywnych wykonawców.',
    badge: 'POPULARNY',
    features: [
      'Zwiad — nieograniczony',
      'Silnik AI — konfiguracja wag',
      'Kosztorys ICB/Sekocenbud',
      'Decyzja — brief AI',
      'Kreator oferty PDF',
      'Proaktywne alerty',
      'Pipeline Kanban nieogr.',
    ],
    cta: 'Zacznij 14 dni za darmo',
    ctaHref: '/auth/register?plan=silnik',
    highlight: true,
  },
  {
    name: 'Mózg',
    price: '890',
    desc: 'Pełna przewaga informacyjna.',
    badge: null,
    features: [
      'Wszystko z Silnik +',
      'Bid Intelligence — win rate',
      'Competitor tracking',
      'Market Intel — trendy CPV',
      'Axiom Engine — 47 walidacji',
      'RFQ — zapytania podwykonawców',
      'API access + Webhooks',
      'Priorytetowe wsparcie',
    ],
    cta: 'Skontaktuj się',
    ctaHref: '/kontakt',
    highlight: false,
  },
];

function PricingSection() {
  return (
    <section id="cennik" style={{ padding: '100px 24px', maxWidth: 1120, margin: '0 auto' }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }} transition={{ duration: 0.5 }}
        style={{ marginBottom: 56 }}
      >
        <div style={{ fontFamily: 'var(--font-space)', fontSize: 11, color: '#10b981', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 12 }}>
          Cennik
        </div>
        <h2 style={{ fontFamily: 'var(--font-space)', fontWeight: 800, fontSize: 38, color: '#f1f5f9', letterSpacing: '-0.03em', margin: 0 }}>
          Jeden przetarg wygrany zwraca<br />koszt rocznej subskrypcji.
        </h2>
      </motion.div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
        {PLANS.map((plan, i) => (
          <motion.div
            key={plan.name}
            initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }}
            style={{
              borderRadius: 16, padding: 28,
              background: plan.highlight ? 'rgba(16,185,129,0.06)' : 'rgba(13,13,22,0.8)',
              border: plan.highlight ? '1px solid rgba(16,185,129,0.3)' : '1px solid rgba(255,255,255,0.07)',
              position: 'relative',
            }}
          >
            {plan.badge && (
              <div style={{
                position: 'absolute', top: -11, left: 28,
                background: '#10b981', color: '#07070d',
                fontFamily: 'var(--font-space)', fontWeight: 700, fontSize: 10,
                letterSpacing: '0.1em', padding: '3px 10px', borderRadius: 20,
              }}>{plan.badge}</div>
            )}
            <div style={{ fontFamily: 'var(--font-space)', fontWeight: 700, fontSize: 15, color: '#f1f5f9', marginBottom: 4 }}>{plan.name}</div>
            <div style={{ fontFamily: 'var(--font-space)', fontSize: 13, color: '#475569', marginBottom: 20 }}>{plan.desc}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 24 }}>
              <span style={{ fontFamily: 'var(--font-jetbrains)', fontWeight: 700, fontSize: 40, color: '#f1f5f9', letterSpacing: '-0.03em' }}>
                {plan.price === '0' ? 'Gratis' : plan.price + ' zł'}
              </span>
              {plan.price !== '0' && (
                <span style={{ fontFamily: 'var(--font-space)', fontSize: 13, color: '#475569' }}>/mies.</span>
              )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }}>
              {plan.features.map(f => (
                <div key={f} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ flexShrink: 0, marginTop: 2 }}>
                    <path d="M2.5 7l3 3 6-6" stroke="#10b981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  <span style={{ fontFamily: 'var(--font-space)', fontSize: 13, color: '#94a3b8', lineHeight: 1.5 }}>{f}</span>
                </div>
              ))}
            </div>

            <Link href={plan.ctaHref} style={{
              display: 'block', textAlign: 'center',
              fontFamily: 'var(--font-space)', fontSize: 14, fontWeight: 600,
              padding: '11px 20px', borderRadius: 10, textDecoration: 'none',
              background: plan.highlight ? '#10b981' : 'transparent',
              color: plan.highlight ? '#07070d' : '#94a3b8',
              border: plan.highlight ? 'none' : '1px solid rgba(255,255,255,0.1)',
            }}>{plan.cta}</Link>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

// ── CTA ───────────────────────────────────────────────────────────────────────

function CTASection() {
  return (
    <section style={{
      padding: '100px 24px',
      background: 'radial-gradient(ellipse 60% 60% at 50% 50%, rgba(16,185,129,0.07) 0%, transparent 70%)',
      borderTop: '1px solid rgba(255,255,255,0.05)',
    }}>
      <div style={{ maxWidth: 640, margin: '0 auto', textAlign: 'center' }}>
        <motion.div
          initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 0.55 }}
        >
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
            <Image src="/brand/B01-app-icon-budos.png" alt="BudOS" width={56} height={56} style={{ borderRadius: 14 }} />
          </div>
          <h2 style={{ fontFamily: 'var(--font-space)', fontWeight: 800, fontSize: 42, color: '#f1f5f9', letterSpacing: '-0.03em', margin: '0 0 18px' }}>
            Twój następny przetarg<br />zaczyna się tutaj.
          </h2>
          <p style={{ fontFamily: 'var(--font-space)', fontSize: 16, color: '#475569', margin: '0 0 36px', lineHeight: 1.65 }}>
            Dołącz do firm, które składają oferty z przewagą informacyjną. 14 dni bezpłatnie. Bez karty kredytowej.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
            <Link href="/auth/register" style={{
              fontFamily: 'var(--font-space)', fontSize: 15, fontWeight: 700,
              color: '#07070d', background: '#10b981',
              padding: '13px 28px', borderRadius: 10,
              textDecoration: 'none', letterSpacing: '-0.01em',
            }}>
              Zacznij za darmo
            </Link>
            <Link href="/kontakt" style={{
              fontFamily: 'var(--font-space)', fontSize: 14,
              color: '#94a3b8', textDecoration: 'none',
              padding: '13px 22px',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 10,
            }}>
              Umów demo
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer style={{ borderTop: '1px solid rgba(255,255,255,0.05)', padding: '48px 24px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 40, marginBottom: 48 }}>
          <div>
            <BrandName />
            <p style={{ fontFamily: 'var(--font-space)', fontSize: 13, color: '#334155', marginTop: 14, lineHeight: 1.6, maxWidth: 260 }}>
              System decyzyjny dla wykonawców przetargów publicznych. AI, kosztorysy, oferty — w jednym narzędziu.
            </p>
          </div>
          {[
            { label: 'Produkt', links: ['Zwiad', 'Silnik AI', 'Kosztorys', 'Decyzja', 'Pipeline'] },
            { label: 'Firma', links: ['O nas', 'Blog', 'Kariera', 'Kontakt'] },
            { label: 'Prawne', links: ['Regulamin', 'Prywatność', 'RODO', 'Status'] },
          ].map(col => (
            <div key={col.label}>
              <div style={{ fontFamily: 'var(--font-space)', fontWeight: 600, fontSize: 12, color: '#334155', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 16 }}>
                {col.label}
              </div>
              {col.links.map(l => (
                <div key={l} style={{ marginBottom: 10 }}>
                  <a href="#" style={{ fontFamily: 'var(--font-space)', fontSize: 13, color: '#475569', textDecoration: 'none' }}>{l}</a>
                </div>
              ))}
            </div>
          ))}
        </div>
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--font-space)', fontSize: 12, color: '#1e293b' }}>© 2026 YU-NA Intelligence. Wszelkie prawa zastrzeżone.</span>
          <span style={{ fontFamily: 'var(--font-space)', fontSize: 12, color: '#1e293b' }}>yu-na.io</span>
        </div>
      </div>
    </footer>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function HomePage() {
  return (
    <div style={{ background: '#07070d', minHeight: '100vh', color: '#f1f5f9' }}>
      <Nav />
      <Hero />
      <TrustLogos />
      <WorkflowSection />
      <FeaturesSection />
      <MetricsSection />
      <PricingSection />
      <CTASection />
      <Footer />
    </div>
  );
}
