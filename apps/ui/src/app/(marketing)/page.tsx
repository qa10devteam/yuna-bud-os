'use client';

import { motion, MotionConfig } from 'motion/react';
import Image from 'next/image';
import Link from 'next/link';
import React, { useState } from 'react';

// ── Design tokens ─────────────────────────────────────────────────────────────
// YU-NA Intelligence · trendsetter v1 · Hallmark macrostructure: Stat-Led
// genre: modern-minimal · theme: custom (bespoke B2B intelligence)
// paper: oklch(8% 0.018 240) · accent: oklch(72% 0.22 155) · display: DM Serif Display
const T = {
  // Paper — navy-tinted dark, NOT pure black
  bg0:       '#05080f',  // oklch(8% 0.018 240) — deepest surface
  bg1:       '#080c17',  // oklch(10% 0.022 240) — primary surface
  bg2:       '#0d1220',  // oklch(13% 0.025 240) — elevated panel
  bg3:       '#141926',  // oklch(16% 0.025 240) — card surface
  // Borders
  edge0:     '#1a2235',  // hairline border dark
  edge1:     '#232f45',  // border medium
  // Text
  ink:       '#e8edf5',  // primary text — cold white
  muted:     '#7a8ba8',  // secondary text
  faint:     '#3a4a62',  // tertiary / hints
  // Accent — electric intelligence green
  accent:    '#16c984',  // oklch(72% 0.22 155) — THE signal color
  accentDim: '#0d7a4f',  // accent dark
  accentSub: 'rgba(22,201,132,0.06)',  // subtle accent tint bg
  accentBrd: 'rgba(22,201,132,0.18)',  // accent border
  // Data accent — platinum for numbers
  data:      '#94a8c4',  // oklch(68% 0.03 245) — numbers/metrics
  // Font families (already defined in layout)
  serif:    'var(--font-dm-serif)',   // DM Serif Display — headlines
  sans:     'var(--font-space)',      // Space Grotesk — body/UI
  mono:     'var(--font-jetbrains)', // JetBrains Mono — numbers
} as const;

// ── Brand ─────────────────────────────────────────────────────────────────────

function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <div style={{
      width: size, height: size,
      background: T.bg2,
      border: `1px solid ${T.accentBrd}`,
      borderRadius: 7,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 16 16" fill="none">
        <path d="M4 3h5.5a2.5 2.5 0 010 5H4V3z" stroke={T.ink} strokeWidth="1.5" strokeLinejoin="round"/>
        <path d="M4 8h6a2.5 2.5 0 010 5H4V8z" stroke={T.accent} strokeWidth="1.5" strokeLinejoin="round"/>
      </svg>
    </div>
  );
}

function BrandName() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none' }}>
      <LogoMark size={28} />
      <span style={{ fontFamily: T.sans, fontWeight: 700, fontSize: 15, color: T.ink, letterSpacing: '-0.01em' }}>
        YU-NA
      </span>
      <span style={{ color: T.accent, fontWeight: 300, fontSize: 15, margin: '0 1px' }}>|</span>
      <span style={{ fontFamily: T.sans, fontWeight: 700, fontSize: 15, color: T.ink, letterSpacing: '-0.01em' }}>
        BudOS
      </span>
    </div>
  );
}

// ── Nav ───────────────────────────────────────────────────────────────────────

function Nav() {
  return (
    <nav style={{ position: 'fixed', top: 20, left: 0, right: 0, zIndex: 50 }}>
      <div style={{
        maxWidth: 720, margin: '0 auto',
        background: 'rgba(8,12,23,0.88)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        border: `1px solid ${T.edge1}`,
        borderRadius: 9999,
        padding: '0 8px 0 20px',
        display: 'flex', alignItems: 'center', height: 52,
      }}>
        <BrandName />
        <div style={{ flex: 1 }} />
        {/* Nav links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginRight: 16 }}>
          {[
            { label: 'Jak działa', href: '#jak-to-dziala' },
            { label: 'Cennik', href: '#cennik' },
          ].map(({ label, href }) => (
            <a key={href} href={href} style={{
              fontFamily: T.sans, fontSize: 13, color: T.muted,
              textDecoration: 'none', padding: '6px 12px',
              borderRadius: 9999,
              transition: 'color 150ms ease-out',
            }}
              onMouseEnter={e => (e.currentTarget.style.color = T.ink)}
              onMouseLeave={e => (e.currentTarget.style.color = T.muted)}
            >{label}</a>
          ))}
          {/* Live indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px' }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: T.accent, display: 'inline-block',
              boxShadow: `0 0 6px ${T.accent}`,
            }} />
            <span style={{ fontFamily: T.mono, fontSize: 11, color: T.muted, letterSpacing: '0.04em' }}>
              LIVE
            </span>
          </div>
        </div>
        <NavLoginLink />
        <NavCTALink />
      </div>
    </nav>
  );
}

function NavLoginLink() {
  const [hover, setHover] = useState(false);
  return (
    <Link
      href="/auth/login"
      tabIndex={0}
      style={{
        fontFamily: T.sans, fontSize: 13, color: hover ? T.ink : T.muted,
        textDecoration: 'none', padding: '7px 16px',
        borderRadius: 9999,
        transition: 'color 150ms ease-out',
        marginRight: 6,
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      Zaloguj się
    </Link>
  );
}

function NavCTALink() {
  const [hover, setHover] = useState(false);
  const [active, setActive] = useState(false);
  return (
    <Link
      href="/auth/register"
      tabIndex={0}
      style={{
        fontFamily: T.sans, fontSize: 13, fontWeight: 600,
        color: T.bg0,
        background: active ? T.accentDim : hover ? 'oklch(76% 0.22 155)' : T.accent,
        padding: '8px 18px', borderRadius: 9999,
        textDecoration: 'none', letterSpacing: '-0.01em',
        display: 'inline-flex', alignItems: 'center',
        transition: 'background 150ms ease-out, transform 100ms ease-out',
        transform: active ? 'scale(0.97)' : 'scale(1)',
        outline: 'none',
        // focus-visible ring for keyboard users
      }}
      onFocus={(e) => { if (e.target.matches(':focus-visible')) e.target.style.outline = '2px solid ' + T.accent; e.target.style.outlineOffset = '2px'; }}
      onBlur={(e) => { e.target.style.outline = 'none'; }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setActive(false); }}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
    >
      Zacznij za darmo
    </Link>
  );
}

// ── Hero ──────────────────────────────────────────────────────────────────────

function PrimaryButton({ href, children }: { href: string; children: React.ReactNode }) {
  const [hover, setHover] = useState(false);
  const [active, setActive] = useState(false);
  return (
    <Link
      href={href}
      tabIndex={0}
      style={{
        background: active ? T.accentDim : hover ? 'oklch(76% 0.22 155)' : T.accent,
        color: T.bg0,
        padding: '11px 24px', borderRadius: 9999,
        fontFamily: T.sans, fontSize: 14, fontWeight: 600,
        letterSpacing: '-0.01em', textDecoration: 'none',
        transition: 'background 150ms ease-out, transform 100ms ease-out',
        display: 'inline-flex', alignItems: 'center',
        transform: active ? 'scale(0.97)' : 'scale(1)',
        outline: hover ? `2px solid rgba(22,201,132,0.6)` : 'none',
        outlineOffset: 3,
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setActive(false); }}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
    >
      {children}
    </Link>
  );
}

function GhostButton({ href, children }: { href: string; children: React.ReactNode }) {
  const [hover, setHover] = useState(false);
  const [active, setActive] = useState(false);
  return (
    <Link
      href={href}
      tabIndex={0}
      style={{
        background: 'transparent',
        color: hover ? T.ink : T.muted,
        border: `1px solid ${hover ? T.edge1 : T.edge0}`,
        padding: '11px 24px', borderRadius: 9999,
        fontFamily: T.sans, fontSize: 14, fontWeight: 400,
        letterSpacing: '-0.01em', textDecoration: 'none',
        transition: 'border-color 150ms ease-out, color 150ms ease-out, transform 100ms ease-out',
        display: 'inline-flex', alignItems: 'center',
        transform: active ? 'scale(0.97)' : 'scale(1)',
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setActive(false); }}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
    >
      {children}
    </Link>
  );
}

function Hero() {
  return (
    <section style={{
      background: T.bg0,
      paddingTop: 130,
      paddingBottom: 100,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Subtle diagonal grid pattern */}
      <div style={{
        position: 'absolute', inset: 0, zIndex: 0,
        backgroundImage: `repeating-linear-gradient(
          45deg,
          transparent,
          transparent 79px,
          rgba(255,255,255,0.04) 79px,
          rgba(255,255,255,0.04) 80px
        )`,
        pointerEvents: 'none',
      }} />

      <div style={{
        maxWidth: 1120, margin: '0 auto', padding: '0 24px',
        display: 'grid', gridTemplateColumns: '58% 42%',
        gap: 48, alignItems: 'center',
        position: 'relative', zIndex: 1,
      }}>
        {/* Left column */}
        <div>
          {/* Live tag */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            marginBottom: 28,
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%',
              background: T.accent, display: 'inline-block',
              boxShadow: `0 0 6px ${T.accent}`,
              flexShrink: 0,
            }} />
            <span style={{
              fontFamily: T.mono, fontSize: 12, color: T.accent,
              letterSpacing: '0.06em',
            }}>
              1 626 przetargów · sync 15 min
            </span>
          </div>

          {/* H1 */}
          <motion.h1
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            style={{
              fontFamily: T.serif,
              fontSize: 'clamp(52px, 5.5vw, 80px)',
              lineHeight: 1.02,
              letterSpacing: '-0.02em',
              fontWeight: 400,
              color: T.ink,
              margin: '0 0 24px',
            }}
          >
            Wygraj przetarg<br />
            zanim inni złożą{' '}
            <span style={{ color: T.accent }}>ofertę.</span>
          </motion.h1>

          {/* Subline */}
          <p style={{
            fontFamily: T.sans, fontSize: 17, lineHeight: 1.7,
            color: T.muted, margin: '0 0 36px',
            maxWidth: 420,
          }}>
            YU-NA skanuje BZP i TED co 15 minut, ocenia przez AI i generuje wycenę ICB — wszystko w jednym systemie dla firm budowlanych.
          </p>

          {/* CTA row */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <PrimaryButton href="/auth/register">Zacznij za darmo</PrimaryButton>
            <GhostButton href="/demo">Zobacz demo</GhostButton>
          </div>
        </div>

        {/* Right column — data panel */}
        <motion.div
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          style={{
            background: T.bg2,
            borderRadius: 20,
            border: `1px solid ${T.edge0}`,
            padding: 32,
          }}
        >
          {/* Header */}
          <div style={{
            fontFamily: T.mono, fontSize: 12, color: T.muted,
            letterSpacing: '0.1em', textTransform: 'uppercase',
            marginBottom: 24,
          }}>
            LIVE DATABASE — BZP+TED+BIP
          </div>

          {/* Metrics */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 20 }}>
            <div>
              <div style={{
                fontFamily: T.mono, fontSize: 56, lineHeight: 1,
                color: T.accent, letterSpacing: '-0.03em', marginBottom: 4,
              }}>
                1 626
              </div>
              <div style={{ fontFamily: T.sans, fontSize: 12, color: T.muted }}>
                przetargów aktywnych
              </div>
            </div>
            <div style={{ display: 'flex', gap: 32 }}>
              <div>
                <div style={{
                  fontFamily: T.mono, fontSize: 40, lineHeight: 1,
                  color: T.ink, letterSpacing: '-0.03em', marginBottom: 4,
                }}>
                  1,4 mln
                </div>
                <div style={{ fontFamily: T.sans, fontSize: 12, color: T.muted }}>
                  baza historyczna
                </div>
              </div>
              <div>
                <div style={{
                  fontFamily: T.mono, fontSize: 40, lineHeight: 1,
                  color: T.ink, letterSpacing: '-0.03em', marginBottom: 4,
                }}>
                  9 913
                </div>
                <div style={{ fontFamily: T.sans, fontSize: 12, color: T.muted }}>
                  wyniki przetargów
                </div>
              </div>
            </div>
          </div>

          {/* Separator */}
          <div style={{ height: 1, background: T.edge0, marginBottom: 20 }} />

          {/* Screenshot */}
          <div style={{
            borderRadius: 10,
            border: `1px solid ${T.edge1}`,
            overflow: 'hidden',
            marginBottom: 12,
          }}>
            <Image
              src="/brand/live-zwiad.png"
              alt="YU-NA BudOS — monitoring przetargów BZP i TED"
              width={560} height={320}
              style={{ display: 'block', width: '100%', height: 'auto' }}
              priority
            />
          </div>

          {/* Timestamp */}
          <div style={{
            fontFamily: T.mono, fontSize: 12, color: T.faint,
            letterSpacing: '0.04em',
          }}>
            ostatnia synchronizacja 3 min temu
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ── TrustLogos ────────────────────────────────────────────────────────────────

const TRUST_FIRMS = ['BUDIMEX', 'PORR', 'STRABAG', 'SKANSKA', 'WARBUD', 'UNIBEP'];

function TrustLogos() {
  const firms = TRUST_FIRMS;
  return (
    <section style={{
      background: T.bg1,
      borderTop: `1px solid ${T.edge0}`,
      borderBottom: `1px solid ${T.edge0}`,
      padding: '20px 24px',
    }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap' }}>
        <span style={{
          fontFamily: T.sans, fontSize: 12, color: T.faint,
          letterSpacing: '0.1em', textTransform: 'uppercase', flexShrink: 0,
        }}>
          Używają
        </span>
        {firms.map(f => (
          <span key={f} style={{
            fontFamily: T.sans, fontWeight: 700, fontSize: 13,
            color: T.faint, letterSpacing: '0.06em',
          }}>{f}</span>
        ))}
      </div>
    </section>
  );
}

// ── Workflow ──────────────────────────────────────────────────────────────────

const STEPS = [
  {
    n: '01',
    title: 'Zwiad — znajdź zanim inni',
    body: 'AI skanuje BZP i TED co 15 minut. 1 626 przetargów. Filtry CPV, województwo, wartość. Każdy przetarg dostaje ocenę GO / UWAGA / NO-GO zanim zdążysz otworzyć maila.',
    img: '/brand/live-zwiad.png',
    imgAlt: 'Moduł Zwiad — monitoring przetargów',
  },
  {
    n: '02',
    title: 'Silnik AI — wiedz czy warto',
    body: 'Scoring wielokryterialny: dopasowanie CPV, zakres wartości, presja terminowa, historia zamawiającego, jakość SWZ. Heatmapa win rates per CPV i kwartał. Konfiguruj wagi pod swój profil.',
    img: '/brand/live-silnik.png',
    imgAlt: 'Silnik AI — analiza AHP',
  },
  {
    n: '03',
    title: 'Kosztorys — wycena w 3 minuty',
    body: 'Kosztorys R/M/S z katalogu KNR. Auto-fill z bazy ICB/Sekocenbud. Import ATH, eksport PDF. Win probability i anomaly detection. Jeden klik — wiesz czy marża jest bezpieczna.',
    img: '/brand/live-kosztorys.png',
    imgAlt: 'Kosztorys — wycena KNR',
  },
  {
    n: '04',
    title: 'Decyzja — agent AI daje brief',
    body: 'Agent analizuje SWZ, robi AHP eval, szacuje przez ICB i generuje brief z ryzykiem p10/p50/p90. Na końcu: GO albo NO-GO z trzema konkretnymi powodami.',
    img: '/brand/live-dashboard.png',
    imgAlt: 'Decyzja — brief AI',
  },
];

function WorkflowSection() {
  return (
    <section id="jak-to-dziala" style={{ background: T.bg0, padding: '96px 24px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        {/* Section header — left-aligned */}
        <div style={{ marginBottom: 72 }}>
          <h2 style={{
            fontFamily: T.serif,
            fontWeight: 400,
            fontSize: 'clamp(36px, 4vw, 48px)',
            lineHeight: 1.08,
            color: T.ink,
            letterSpacing: '-0.02em',
            margin: '0 0 8px',
          }}>
            Od przetargu do oferty.
          </h2>
          <div style={{
            fontFamily: T.serif,
            fontWeight: 400,
            fontSize: 'clamp(28px, 3vw, 36px)',
            lineHeight: 1.2,
            color: T.muted,
            letterSpacing: '-0.01em',
          }}>
            Jeden system.
          </div>
        </div>

        {/* Steps — alternating layout, static */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {STEPS.map((step, i) => {
            const isEven = i % 2 === 0;
            return (
              <div key={step.n} style={{
                borderTop: `1px solid ${T.edge0}`,
                padding: '64px 0',
              }}>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: 64,
                  alignItems: 'center',
                }}>
                  {/* Copy */}
                  <div style={{ order: isEven ? 0 : 1 }}>
                    <div style={{
                      fontFamily: T.mono, fontSize: 12, color: T.accent,
                      letterSpacing: '0.08em', marginBottom: 16,
                    }}>
                      {step.n}
                    </div>
                    <h3 style={{
                      fontFamily: T.serif,
                      fontWeight: 400,
                      fontSize: 'clamp(24px, 2.5vw, 32px)',
                      lineHeight: 1.15,
                      color: T.ink,
                      letterSpacing: '-0.02em',
                      margin: '0 0 16px',
                    }}>
                      {step.title}
                    </h3>
                    <p style={{
                      fontFamily: T.sans, fontSize: 16, lineHeight: 1.7,
                      color: T.muted, margin: 0,
                    }}>
                      {step.body}
                    </p>
                  </div>

                  {/* Screenshot */}
                  <div style={{ order: isEven ? 1 : 0 }}>
                    <div style={{
                      borderRadius: 12, overflow: 'hidden',
                      border: `1px solid ${T.edge1}`,
                    }}>
                      <Image
                        src={step.img} alt={step.imgAlt}
                        width={560} height={350}
                        style={{ display: 'block', width: '100%', height: 'auto' }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ── Metrics ───────────────────────────────────────────────────────────────────

const METRICS_DATA = [
  { val: '1 626',   label: 'przetargów live',          sub: 'BZP 1 195 · TED 360 · BIP 58 · BK 13', accent: true },
  { val: '1,4 mln', label: 'przetargów historycznych', sub: 'baza od 2010 roku — trendy, win rates, benchmarki', accent: false },
  { val: '9 913',   label: 'wyników przetargów',       sub: 'kto wygrał, za ile, jaki markup — w bazie', accent: true },
  { val: '47',      label: 'punktów walidacji PZP',    sub: 'Axiom Engine art. 63 · 108 · 116 · 224', accent: false },
];

function MetricsSection() {
  const metrics = METRICS_DATA;
  return (
    <section style={{
      background: T.bg1,
      borderTop: `1px solid ${T.edge0}`,
      borderBottom: `1px solid ${T.edge0}`,
      padding: '64px 24px',
    }}>
      <div style={{
        maxWidth: 1120, margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: '1.6fr 1fr 1fr 1fr',
        gap: 1,
      }}>
        {metrics.map((m, i) => (
          <div
            key={m.val}
            style={{
              padding: '0 28px',
              borderRight: i < 3 ? `1px solid ${T.edge0}` : 'none',
            }}
          >
            <div style={{
              fontFamily: T.mono,
              fontSize: 64, lineHeight: 1,
              color: m.accent ? T.accent : T.ink,
              letterSpacing: '-0.03em', marginBottom: 10,
            }}>
              {m.val}
            </div>
            <div style={{
              fontFamily: T.sans, fontWeight: 500,
              fontSize: 15, color: T.ink, marginBottom: 6,
            }}>
              {m.label}
            </div>
            <div style={{ fontFamily: T.sans, fontSize: 12, color: T.faint, lineHeight: 1.5 }}>
              {m.sub}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── Features ──────────────────────────────────────────────────────────────────

function FeatureCard({
  icon, title, body, wide, narrow,
  extra,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  wide?: boolean;
  narrow?: boolean;
  extra?: React.ReactNode;
}) {
  const [hover, setHover] = useState(false);
  return (
    <div
      style={{
        background: T.bg2,
        border: `1px solid ${hover ? T.edge1 : T.edge0}`,
        borderRadius: 16,
        padding: 28,
        transition: 'border-color 150ms ease-out',
        cursor: 'default',
        gridColumn: wide ? 'span 2' : narrow ? 'span 1' : 'span 1',
        display: 'flex', flexDirection: 'column',
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <span style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>{icon}</span>
        <div style={{
          fontFamily: T.sans, fontWeight: 600,
          fontSize: 16, color: T.ink,
          letterSpacing: '-0.01em',
        }}>
          {title}
        </div>
      </div>
      <div style={{ fontFamily: T.sans, fontSize: 13, lineHeight: 1.7, color: T.muted }}>
        {body}
      </div>
      {extra && (
        <div style={{ marginTop: 20 }}>
          {extra}
        </div>
      )}
    </div>
  );
}

function CodeSnippet({ lines }: { lines: string[] }) {
  return (
    <div style={{
      background: T.bg0,
      border: `1px solid ${T.edge0}`,
      borderRadius: 8,
      padding: '12px 16px',
      fontFamily: T.mono,
      fontSize: 12,
      color: T.muted,
      lineHeight: 1.7,
    }}>
      {lines.map((l, i) => (
        <div key={`item-${i}`} style={{ color: l.startsWith('>') ? T.accent : T.muted }}>
          {l}
        </div>
      ))}
    </div>
  );
}

function FeaturesSection() {
  return (
    <section id="funkcje" style={{ background: T.bg0, padding: '96px 24px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        {/* Section header — left-aligned, no eyebrow */}
        <div style={{ marginBottom: 48 }}>
          <h2 style={{
            fontFamily: T.serif,
            fontWeight: 400,
            fontSize: 42,
            lineHeight: 1.1,
            color: T.ink,
            letterSpacing: '-0.02em',
            margin: 0,
          }}>
            Co robi YU-NA
          </h2>
        </div>

        {/* Asymmetric bento grid */}
        {/* Row 1: BZP+TED (2/3) | Pipeline Kanban (1/3) */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12, marginBottom: 12 }}>
          <FeatureCard
            wide
            icon={
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="8" stroke={T.accent} strokeWidth="1.5"/>
                <path d="M10 6v4l2.5 2.5" stroke={T.accent} strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            }
            title="BZP + TED co 15 min"
            body="APScheduler synchronizuje przetargi automatycznie z BZP, TED i BIP. Nic nie umknie — każdy nowy przetarg trafia do systemu i dostaje scoring AI zanim zdążysz otworzyć maila."
            extra={
              <CodeSnippet lines={[
                '> sync BZP ... 1 195 rekordów ✓',
                '> sync TED ... 360 rekordów ✓',
                '> AI scoring ... 1 626 / 1 626 ✓',
                'last sync: 3 min ago',
              ]} />
            }
          />
          <FeatureCard
            narrow
            icon={
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <path d="M3 10l4 4 10-8" stroke="#818cf8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            }
            title="Pipeline Kanban"
            body="Nowe → Obserwowane → Analiza → Wycenione → GO → Złożone. Pełny lejek przetargowy w jednym widoku."
          />
        </div>

        {/* Row 2: Kreator oferty (1/3) | Alerty (2/3) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 12, marginBottom: 12 }}>
          <FeatureCard
            narrow
            icon={
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <rect x="3" y="3" width="14" height="14" rx="3" stroke="#f59e0b" strokeWidth="1.5"/>
                <path d="M7 10h6M7 7h3M7 13h4" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            }
            title="Kreator oferty PDF"
            body="Z kosztorysu do gotowej oferty formalnej. Status: draft → ready → submitted → won."
          />
          <FeatureCard
            wide
            icon={
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <path d="M10 2L13 8l6 .875-4.5 4.25L15.5 19 10 16l-5.5 3 1-5.875L1 8.875 7 8z" stroke={T.accent} strokeWidth="1.5" strokeLinejoin="round"/>
              </svg>
            }
            title="Proaktywne alerty"
            body="Deadline zbliża się? Masz 5 aktywnych przetargów jednocześnie? System optymalizuje portfolio i mówi co warto ciągnąć — a co porzucić."
            extra={
              <div style={{
                display: 'flex', flexDirection: 'column', gap: 8,
              }}>
                {[
                  { label: '⚡ Deadline za 48h', sub: 'Roboty ziemne — Warszawa — 2,4 mln zł', accent: true },
                  { label: '📊 Nowy przetarg GO', sub: 'CPV 45000000 — Kraków — dopasowanie 94%', accent: false },
                ].map((a, i) => (
                  <div key={`item-${i}`} style={{
                    background: T.bg0,
                    border: `1px solid ${a.accent ? T.accentBrd : T.edge0}`,
                    borderRadius: 8,
                    padding: '10px 14px',
                  }}>
                    <div style={{ fontFamily: T.sans, fontSize: 12, fontWeight: 600, color: a.accent ? T.accent : T.ink, marginBottom: 2 }}>
                      {a.label}
                    </div>
                    <div style={{ fontFamily: T.sans, fontSize: 12, color: T.muted }}>
                      {a.sub}
                    </div>
                  </div>
                ))}
              </div>
            }
          />
        </div>

        {/* Row 3: Buyer CRM (1/2) | ICB+Sekocenbud (1/2) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <FeatureCard
            icon={
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <path d="M4 15V8l6-5 6 5v7H4z" stroke="#ef4444" strokeWidth="1.5" strokeLinejoin="round"/>
                <rect x="8" y="11" width="4" height="4" rx="1" stroke="#ef4444" strokeWidth="1.2"/>
              </svg>
            }
            title="Buyer CRM + Axiom Engine"
            body="Historia zamawiającego — wyniki, preferencje, bias. Aksjomaty regulacyjne walidujące każdy krok. 47 punktów walidacji PZP art. 63 · 108 · 116 · 224."
          />
          <FeatureCard
            icon={
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <path d="M3 17l4-8 4 4 3-5 3 9" stroke="#818cf8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            }
            title="ICB + Sekocenbud"
            body="Baza cenowa z uwzględnieniem inflacji, współczynników regionalnych i stawek robocizny per województwo. Auto-fill w kosztorysie KNR."
          />
        </div>
      </div>
    </section>
  );
}

// ── Pricing ───────────────────────────────────────────────────────────────────

const FEATURE_ROWS = [
  { label: 'Monitoring przetargów',        fundament: '100/mies.',   silnik: 'nieograniczony', mozg: 'nieograniczony' },
  { label: 'GO/NO-GO AI scoring',          fundament: true,          silnik: true,             mozg: true },
  { label: 'Pipeline Kanban',              fundament: true,          silnik: true,             mozg: true },
  { label: 'Kosztorys ICB/Sekocenbud',     fundament: '1/mies.',     silnik: true,             mozg: true },
  { label: 'Silnik AI — konfiguracja wag', fundament: false,         silnik: true,             mozg: true },
  { label: 'Decyzja — brief AI',           fundament: false,         silnik: true,             mozg: true },
  { label: 'Kreator oferty PDF',           fundament: false,         silnik: true,             mozg: true },
  { label: 'Proaktywne alerty',            fundament: false,         silnik: true,             mozg: true },
  { label: 'Bid Intelligence — win rate',  fundament: false,         silnik: false,            mozg: true },
  { label: 'Competitor tracking',          fundament: false,         silnik: false,            mozg: true },
  { label: 'API access + Webhooks',        fundament: false,         silnik: false,            mozg: true },
  { label: 'Priorytetowe wsparcie',        fundament: false,         silnik: false,            mozg: true },
];

function CellValue({ v }: { v: boolean | string }) {
  if (v === true) return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M3 8l3.5 3.5 6.5-6.5" stroke={T.accent} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
  if (v === false) return (
    <span style={{ color: T.faint, fontSize: 14 }}>—</span>
  );
  return <span style={{ fontFamily: T.mono, fontSize: 12, color: T.muted }}>{v}</span>;
}

function PricingSection() {
  return (
    <section id="cennik" style={{ background: T.bg1, padding: '96px 24px', borderTop: `1px solid ${T.edge0}` }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        {/* Section header — left-aligned */}
        <div style={{ marginBottom: 48 }}>
          <h2 style={{
            fontFamily: T.serif,
            fontWeight: 400,
            fontSize: 42,
            lineHeight: 1.1,
            color: T.ink,
            letterSpacing: '-0.02em',
            margin: 0,
          }}>
            Cennik
          </h2>
        </div>

        {/* Table */}
        <div style={{
          background: T.bg2,
          border: `1px solid ${T.edge0}`,
          borderRadius: 16,
          overflow: 'hidden',
        }}>
          {/* Header row */}
          <div style={{
            display: 'grid', gridTemplateColumns: 'auto 1fr 1fr 1fr',
            borderBottom: `1px solid ${T.edge0}`,
          }}>
            <div style={{ padding: '20px 28px', minWidth: 240 }} />
            {/* Fundament */}
            <div style={{ padding: '20px 24px' }}>
              <div style={{ fontFamily: T.sans, fontWeight: 600, fontSize: 15, color: T.ink, marginBottom: 4 }}>
                Fundament
              </div>
              <div style={{ fontFamily: T.mono, fontSize: 32, color: T.ink, letterSpacing: '-0.02em', marginBottom: 2 }}>
                0 zł
              </div>
              <div style={{ fontFamily: T.sans, fontSize: 12, color: T.muted }}>Na start — bez karty.</div>
            </div>
            {/* Silnik — highlighted */}
            <div style={{ padding: '20px 24px', background: T.accentSub }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <div style={{ fontFamily: T.sans, fontWeight: 600, fontSize: 15, color: T.ink }}>
                  Silnik
                </div>
                <span style={{
                  fontFamily: T.sans, fontWeight: 700, fontSize: 11,
                  color: T.bg0, background: T.accent,
                  padding: '2px 8px', borderRadius: 9999,
                  letterSpacing: '0.06em',
                }}>
                  POPULARNY
                </span>
              </div>
              <div style={{ fontFamily: T.mono, fontSize: 32, color: T.accent, letterSpacing: '-0.02em', marginBottom: 2 }}>
                290 zł
              </div>
              <div style={{ fontFamily: T.sans, fontSize: 12, color: T.muted }}>Dla aktywnych wykonawców.</div>
            </div>
            {/* Mózg */}
            <div style={{ padding: '20px 24px' }}>
              <div style={{ fontFamily: T.sans, fontWeight: 600, fontSize: 15, color: T.ink, marginBottom: 4 }}>
                Mózg
              </div>
              <div style={{ fontFamily: T.mono, fontSize: 32, color: T.ink, letterSpacing: '-0.02em', marginBottom: 2 }}>
                890 zł
              </div>
              <div style={{ fontFamily: T.sans, fontSize: 12, color: T.muted }}>Pełna przewaga informacyjna.</div>
            </div>
          </div>

          {/* Feature rows */}
          {FEATURE_ROWS.map((row, i) => (
            <div
              key={row.label}
              style={{
                display: 'grid', gridTemplateColumns: 'auto 1fr 1fr 1fr',
                borderBottom: i < FEATURE_ROWS.length - 1 ? `1px solid ${T.edge0}` : 'none',
              }}
            >
              <div style={{
                padding: '14px 28px', minWidth: 240,
                fontFamily: T.sans, fontSize: 13, color: T.muted,
                display: 'flex', alignItems: 'center',
              }}>
                {row.label}
              </div>
              <div style={{ padding: '14px 24px', display: 'flex', alignItems: 'center' }}>
                <CellValue v={row.fundament} />
              </div>
              <div style={{ padding: '14px 24px', background: T.accentSub, display: 'flex', alignItems: 'center' }}>
                <CellValue v={row.silnik} />
              </div>
              <div style={{ padding: '14px 24px', display: 'flex', alignItems: 'center' }}>
                <CellValue v={row.mozg} />
              </div>
            </div>
          ))}

          {/* CTA row */}
          <div style={{
            display: 'grid', gridTemplateColumns: 'auto 1fr 1fr 1fr',
            borderTop: `1px solid ${T.edge0}`,
          }}>
            <div style={{ padding: '20px 28px', minWidth: 240 }} />
            <div style={{ padding: '20px 24px' }}>
              <Link href="/auth/register" style={{
                fontFamily: T.sans, fontSize: 13, fontWeight: 500,
                color: T.muted, textDecoration: 'none',
                border: `1px solid ${T.edge0}`,
                borderRadius: 9999, padding: '8px 16px',
                display: 'inline-block',
                transition: 'border-color 150ms, color 150ms',
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = T.edge1; e.currentTarget.style.color = T.ink; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = T.edge0; e.currentTarget.style.color = T.muted; }}
              >
                Zacznij za darmo
              </Link>
            </div>
            <div style={{ padding: '20px 24px', background: T.accentSub }}>
              <Link href="/auth/register?plan=silnik" style={{
                fontFamily: T.sans, fontSize: 13, fontWeight: 600,
                color: T.bg0, background: T.accent,
                textDecoration: 'none',
                borderRadius: 9999, padding: '8px 16px',
                display: 'inline-block',
                transition: 'background 150ms',
              }}
                onMouseEnter={e => { e.currentTarget.style.background = 'oklch(76% 0.22 155)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = T.accent; }}
              >
                14 dni za darmo
              </Link>
            </div>
            <div style={{ padding: '20px 24px' }}>
              <Link href="/kontakt" style={{
                fontFamily: T.sans, fontSize: 13, fontWeight: 500,
                color: T.muted, textDecoration: 'none',
                border: `1px solid ${T.edge0}`,
                borderRadius: 9999, padding: '8px 16px',
                display: 'inline-block',
                transition: 'border-color 150ms, color 150ms',
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = T.edge1; e.currentTarget.style.color = T.ink; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = T.edge0; e.currentTarget.style.color = T.muted; }}
              >
                Skontaktuj się
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── CTA ───────────────────────────────────────────────────────────────────────

function CTASection() {
  return (
    <section style={{
      background: T.bg0,
      padding: '128px 24px 100px',
      borderTop: `1px solid ${T.edge0}`,
    }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <h2 style={{
          fontFamily: T.serif,
          fontWeight: 400,
          fontSize: 'clamp(40px, 5vw, 64px)',
          lineHeight: 1.05,
          letterSpacing: '-0.02em',
          color: T.ink,
          margin: '0 0 20px',
          maxWidth: 600,
        }}>
          Twój następny<br />
          przetarg zaczyna<br />
          się tutaj.
        </h2>
        <p style={{
          fontFamily: T.sans, fontSize: 17, color: T.muted,
          margin: '0 0 40px', lineHeight: 1.65,
        }}>
          14 dni bezpłatnie. Bez karty kredytowej.
        </p>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <PrimaryButton href="/auth/register">Zacznij za darmo</PrimaryButton>
          <GhostButton href="/kontakt">Umów demo</GhostButton>
        </div>
      </div>
    </section>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────

const FOOTER_LINKS = [
  { label: 'Regulamin', href: '/regulamin' },
  { label: 'Prywatność', href: '/prywatnosc' },
  { label: 'RODO', href: '/rodo' },
  { label: 'Kontakt', href: '/kontakt' },
  { label: 'Status', href: '/status' },
];

function Footer() {
  const links = FOOTER_LINKS;
  return (
    <footer style={{
      background: T.bg0,
      borderTop: `1px solid ${T.edge0}`,
      padding: '80px 24px 48px',
    }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        {/* Top: brand + tagline */}
        <div style={{ marginBottom: 40 }}>
          <BrandName />
          <p style={{
            fontFamily: T.sans, fontSize: 13,
            color: T.faint, marginTop: 12, lineHeight: 1.6,
          }}>
            System decyzyjny dla wykonawców przetargów publicznych.
          </p>
        </div>

        {/* Middle: inline links */}
        <div style={{
          display: 'flex', gap: 0, flexWrap: 'wrap',
          marginBottom: 40,
          borderTop: `1px solid ${T.edge0}`,
          paddingTop: 28,
        }}>
          {links.map((l, i) => (
            <React.Fragment key={l.label}>
              <a href={l.href} style={{
                fontFamily: T.sans, fontSize: 13, color: T.faint,
                textDecoration: 'none', transition: 'color 150ms',
              }}
                onMouseEnter={e => (e.currentTarget.style.color = T.muted)}
                onMouseLeave={e => (e.currentTarget.style.color = T.faint)}
              >
                {l.label}
              </a>
              {i < links.length - 1 && (
                <span style={{ color: T.edge1, margin: '0 12px', fontSize: 13 }}>·</span>
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Bottom: copyright + domain */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderTop: `1px solid ${T.edge0}`,
          paddingTop: 24,
        }}>
          <span style={{ fontFamily: T.sans, fontSize: 12, color: T.faint }}>
            © 2026 YU-NA Intelligence. Wszelkie prawa zastrzeżone.
          </span>
          <span style={{ fontFamily: T.mono, fontSize: 12, color: T.faint }}>
            yu-na.io
          </span>
        </div>
      </div>
    </footer>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function HomePage() {
  return (
    <MotionConfig reducedMotion="user">
    <div style={{ background: T.bg0, minHeight: '100dvh', color: T.ink }}>
      <Nav />
      <Hero />
      <TrustLogos />
      <WorkflowSection />
      <MetricsSection />
      <FeaturesSection />
      <PricingSection />
      <CTASection />
      <Footer />
    </div>
    </MotionConfig>
  );
}
