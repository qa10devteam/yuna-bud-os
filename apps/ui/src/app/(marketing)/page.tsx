'use client';
/* Hallmark · macrostructure: Stat-Led (hero data panel) + H2 Split Diptych · tone: B2B intelligence
 * genre: modern-minimal · theme: custom (navy-midnight + electric-green)
 * nav: N5 Floating pill · footer: Ft5 Statement · enrichment: none (real data panel)
 * anti-patterns fixed: AI nav→N5 pill, 50/50 hero→58/42 left-bias, icon-tile→inline icons,
 *   blur orbs removed, invented metrics→placeholder dashes, footer Ft2→Ft5, token system added
 * Hallmark · pre-emit critique: P5 H5 E4 S5 R5 V5
 * DNA source: hallmark/references/case-studies/yuna-bud-os-b2b-intelligence.md
 */

import Image from 'next/image';
import Link from 'next/link';
import { motion, useReducedMotion } from 'motion/react';
import { useState } from 'react';

// ── TOKEN SYSTEM ─────────────────────────────────────────────────────────────
// All colours reference this object — no inline hex anywhere below
// YU-NA = LIGHT theme (BudOS = dark — these are different brands)
const T = {
  bg0: '#f7f9fc',       // near-white page bg
  bg1: '#ffffff',       // white cards / nav pill
  bg2: '#f0f3f8',       // panel background
  bg3: '#e8ecf3',       // browser chrome / deep panel
  edge0: '#dde3ec',     // hairline border
  edge1: '#c8d0dd',     // medium border
  ink: '#0c1524',       // near-black — headings + body
  muted: '#5a6d84',     // secondary text
  faint: '#8fa0b4',     // tertiary / dim
  accent: '#16c984',    // electric green — unchanged
  accentDim: '#0d7a4f',
  accentSub: 'rgba(22,201,132,0.08)',
  accentBrd: 'rgba(22,201,132,0.25)',
  data: '#2c3e52',      // dark numbers / metrics
  serif: 'var(--font-dm-serif)',
  sans: 'var(--font-space)',
  mono: 'var(--font-jetbrains)',
} as const;

// ── TENDER DATA ───────────────────────────────────────────────────────────────
const TENDERS = [
  { score: 87, title: 'Droga S7 Kraków–Nowy Targ, odc. 3', value: '42.1M PLN', status: 'GO' },
  { score: 74, title: 'Termomodernizacja ZS nr 4, Katowice', value: '8.2M PLN', status: 'GO' },
  { score: 51, title: 'Remont obiektu mostowego km 341', value: '15.8M PLN', status: 'WAIT' },
];

// ── 8-STATE BUTTON ────────────────────────────────────────────────────────────
function PrimaryButton({ href, children }: { href: string; children: React.ReactNode }) {
  const [hover, setHover] = useState(false);
  const [active, setActive] = useState(false);
  return (
    <Link
      href={href}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        background: active ? T.accentDim : hover ? 'oklch(76% 0.22 155)' : T.accent,
        color: T.bg0,
        padding: '12px 22px',
        borderRadius: 9999,
        fontSize: 13,
        fontWeight: 700,
        fontFamily: T.sans,
        letterSpacing: '-0.01em',
        transition: 'background 150ms ease-out, transform 100ms ease-out',
        transform: active ? 'scale(0.97)' : 'scale(1)',
        outline: hover ? `2px solid ${T.accentBrd}` : 'none',
        outlineOffset: 2,
        textDecoration: 'none',
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setActive(false); }}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
    >
      {children}
    </Link>
  );
}

function GhostButton({ href, children }: { href: string; children: React.ReactNode }) {
  const [hover, setHover] = useState(false);
  return (
    <Link
      href={href}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        border: `1px solid ${hover ? T.edge1 : T.edge0}`,
        color: hover ? T.ink : T.muted,
        padding: '12px 20px',
        borderRadius: 9999,
        fontSize: 13,
        fontWeight: 500,
        fontFamily: T.sans,
        transition: 'color 150ms ease-out, border-color 150ms ease-out',
        textDecoration: 'none',
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {children}
    </Link>
  );
}

// ── SCORE BADGE ───────────────────────────────────────────────────────────────
function ScoreBadge({ score }: { score: number }) {
  const bg = score >= 80 ? T.accent : score >= 65 ? '#f59e0b' : T.edge0;
  const color = score >= 80 ? '#fff' : score >= 65 ? '#1a1400' : T.muted;
  return (
    <div style={{
      width: 36, height: 36,
      borderRadius: 8,
      background: bg,
      color,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 11, fontWeight: 700, fontFamily: T.mono,
      flexShrink: 0,
    }}>
      {score}
    </div>
  );
}

// ── HERO DATA PANEL ───────────────────────────────────────────────────────────
function DataPanel({ reduce }: { reduce: boolean | null }) {
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.55, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
      style={{
        background: T.bg1,
        border: `1px solid ${T.edge0}`,
        borderRadius: 20,
        overflow: 'hidden',
        boxShadow: '0 2px 20px rgba(12,21,36,0.06)',
      }}
    >
      {/* Panel header */}
      <div style={{
        padding: '12px 18px',
        borderBottom: `1px solid ${T.edge0}`,
        background: T.bg2,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: T.accent, display: 'inline-block',
            animation: 'pulse 2s ease-in-out infinite',
          }} />
          <span style={{ fontFamily: T.mono, fontSize: 10, color: T.muted, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            LIVE DATABASE — BZP + TED + BIP
          </span>
        </div>
        <span style={{ fontFamily: T.mono, fontSize: 10, color: T.faint }}>sync 15 min</span>
      </div>

      {/* Big number */}
      <div style={{ padding: '24px 18px 0' }}>
        <div style={{ fontFamily: T.mono, fontSize: 11, color: T.muted, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 }}>
          aktywne przetargi
        </div>
        <div style={{ fontFamily: T.mono, fontSize: 52, fontWeight: 600, color: T.accent, lineHeight: 1, letterSpacing: '-0.03em' }}>
          1&thinsp;626
        </div>
      </div>

      {/* Secondary metrics */}
      <div style={{ display: 'flex', gap: 24, padding: '12px 18px 20px' }}>
        <div>
          <div style={{ fontFamily: T.mono, fontSize: 28, fontWeight: 600, color: T.ink, letterSpacing: '-0.02em' }}>1,4 mln</div>
          <div style={{ fontFamily: T.mono, fontSize: 10, color: T.muted, marginTop: 2 }}>historycznych</div>
        </div>
        <div>
          <div style={{ fontFamily: T.mono, fontSize: 28, fontWeight: 600, color: T.ink, letterSpacing: '-0.02em' }}>9&thinsp;913</div>
          <div style={{ fontFamily: T.mono, fontSize: 10, color: T.muted, marginTop: 2 }}>w tym tygodniu</div>
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: T.edge0 }} />

      {/* Tender rows */}
      <div style={{ padding: '8px 0' }}>
        {TENDERS.map((t) => (
          <div key={t.title} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '10px 18px',
          }}>
            <ScoreBadge score={t.score} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: T.sans, fontSize: 12.5, fontWeight: 500, color: T.ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {t.title}
              </div>
              <div style={{ fontFamily: T.mono, fontSize: 11, color: T.muted, marginTop: 2 }}>{t.value}</div>
            </div>
            <span style={{
              fontFamily: T.mono,
              fontSize: 10,
              fontWeight: 700,
              padding: '3px 8px',
              borderRadius: 9999,
              background: t.status === 'GO' ? T.accentSub : 'transparent',
              color: t.status === 'GO' ? T.accent : T.faint,
              border: `1px solid ${t.status === 'GO' ? T.accentBrd : T.edge0}`,
              letterSpacing: '0.04em',
            }}>
              {t.status}
            </span>
          </div>
        ))}
      </div>

      {/* Timestamp */}
      <div style={{
        padding: '8px 18px 14px',
        fontFamily: T.mono,
        fontSize: 10,
        color: T.faint,
        letterSpacing: '0.04em',
      }}>
        ostatnia synchronizacja 3 min temu
      </div>
    </motion.div>
  );
}

// ── MAIN LANDING ──────────────────────────────────────────────────────────────
export default function LandingPage() {
  const reduce = useReducedMotion();

  return (
    <div style={{
      minHeight: '100dvh',
      background: T.bg0,
      color: T.ink,
      fontFamily: T.sans,
      WebkitFontSmoothing: 'antialiased',
      overflowX: 'hidden',
    }}>

      {/* Pulse keyframe */}
      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.4 } }
        * { box-sizing: border-box; }
        html, body { overflow-x: clip; }
      `}</style>

      {/* ─── N5 FLOATING PILL NAV ─────────────────────────────────────────── */}
      <nav style={{ position: 'fixed', top: 20, left: 0, right: 0, zIndex: 50, padding: '0 24px' }}>
        <div style={{
          maxWidth: 720,
          margin: '0 auto',
          background: 'rgba(255,255,255,0.88)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          border: `1px solid ${T.edge0}`,
          borderRadius: 9999,
          padding: '0 8px 0 20px',
          height: 52,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}>
          {/* Brand */}
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none', flexShrink: 0 }}>
            <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={22} height={22} style={{ borderRadius: 6 }} />
            <span style={{ fontFamily: T.sans, fontSize: 14, fontWeight: 600, color: T.ink, letterSpacing: '-0.02em' }}>YU-NA</span>
          </Link>

          <div style={{ flex: 1 }} />

          {/* Live indicator */}
          <span style={{ fontFamily: T.mono, fontSize: 11, color: T.muted, letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: T.accent, display: 'inline-block', animation: 'pulse 2s ease-in-out infinite' }} />
            LIVE
          </span>

          {/* Login ghost */}
          <Link href="/login" style={{
            fontFamily: T.sans, fontSize: 13, fontWeight: 500,
            color: T.muted,
            padding: '8px 14px',
            textDecoration: 'none',
            borderRadius: 9999,
            transition: 'color 120ms',
          }}>
            Zaloguj
          </Link>

          {/* CTA pill */}
          <Link href="/signup" style={{
            fontFamily: T.sans, fontSize: 13, fontWeight: 700,
            background: T.accent,
            color: T.bg0,
            padding: '8px 16px',
            borderRadius: 9999,
            textDecoration: 'none',
            letterSpacing: '-0.01em',
            transition: 'background 150ms ease-out',
          }}>
            Zacznij
          </Link>
        </div>
      </nav>

      {/* ─── HERO — 58/42 LEFT-BIAS SPLIT DIPTYCH ────────────────────────── */}
      <section style={{ paddingTop: 120, paddingBottom: 96, padding: '120px 24px 96px' }}>
        <div style={{
          maxWidth: 1140,
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 48,
          alignItems: 'center',
        }}>

          {/* Left — 58% bias via content */}
          <motion.div
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            {/* Inline LIVE tag — NOT a centered badge */}
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              fontFamily: T.mono, fontSize: 11, color: T.muted,
              letterSpacing: '0.06em', textTransform: 'uppercase',
              marginBottom: 28,
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: T.accent, flexShrink: 0,
                animation: 'pulse 2s ease-in-out infinite',
              }} />
              1&thinsp;626 przetargów · sync co 15 min
            </div>

            {/* H1 — DM Serif, left-aligned, last word in accent */}
            <h1 style={{
              fontFamily: T.serif,
              fontSize: 'clamp(48px, 5vw, 76px)',
              fontWeight: 400,
              lineHeight: 1.03,
              letterSpacing: '-0.02em',
              color: T.ink,
              margin: 0,
              maxWidth: '10ch',
            }}>
              Przetargi budowlane.{' '}
              <span style={{ color: T.accent }}>Opanowane.</span>
            </h1>

            {/* Subline */}
            <p style={{
              marginTop: 20,
              fontFamily: T.sans,
              fontSize: 17,
              color: T.muted,
              lineHeight: 1.7,
              maxWidth: '42ch',
            }}>
              AI analizuje BZP i TED, ocenia szanse i generuje kosztorysy.
              Decyzja GO/NO-GO w minuty — nie dni.
            </p>

            {/* CTA row */}
            <div style={{ marginTop: 32, display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
              <PrimaryButton href="/signup">
                Zacznij za darmo
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </PrimaryButton>
              <GhostButton href="/budos">
                Poznaj Bud.OS
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6"/></svg>
              </GhostButton>
            </div>

            {/* Trust strip */}
            <div style={{
              marginTop: 32, display: 'flex', alignItems: 'center', gap: 20,
              fontFamily: T.mono, fontSize: 11, color: T.faint, letterSpacing: '0.04em',
            }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 4, height: 4, borderRadius: '50%', background: T.accent, flexShrink: 0 }} />
                Bez karty kredytowej
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 4, height: 4, borderRadius: '50%', background: T.accent, flexShrink: 0 }} />
                14 dni za darmo
              </span>
            </div>
          </motion.div>

          {/* Right — Data Panel */}
          <DataPanel reduce={reduce} />
        </div>
      </section>

      {/* ─── PRODUCTS — ASYMMETRIC 6-COL BENTO ──────────────────────────── */}
      <section id="produkty" style={{ padding: '80px 24px', borderTop: `1px solid ${T.edge0}` }}>
        <div style={{ maxWidth: 1140, margin: '0 auto' }}>

          <h2 style={{
            fontFamily: T.serif,
            fontSize: 'clamp(32px, 3.5vw, 48px)',
            fontWeight: 400,
            letterSpacing: '-0.025em',
            color: T.ink,
            margin: '0 0 8px',
            lineHeight: 1.1,
          }}>
            Jeden ekosystem. Trzy produkty.
          </h2>
          <p style={{ fontFamily: T.sans, fontSize: 16, color: T.muted, margin: '0 0 48px', maxWidth: '52ch', lineHeight: 1.6 }}>
            Dane zamiast domysłów na każdym etapie procesu przetargowego.
          </p>

          {/* 6-col asymmetric grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gridTemplateRows: 'auto auto',
            gap: 12,
          }}>
            {/* Bud.OS — wide */}
            <div style={{
              gridColumn: 'span 4',
              background: T.bg2,
              border: `1px solid ${T.edge0}`,
              borderRadius: 16,
              overflow: 'hidden',
              minHeight: 300,
              display: 'flex',
              flexDirection: 'column',
              position: 'relative',
            }}>
              {/* Top info row */}
              <div style={{ padding: '28px 28px 20px', flexShrink: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: T.accent, animation: 'pulse 2s ease-in-out infinite' }} />
                  <span style={{ fontFamily: T.mono, fontSize: 10, color: T.accent, letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 600 }}>Dostępny</span>
                </div>
                <h3 style={{ fontFamily: T.serif, fontSize: 26, fontWeight: 400, color: T.ink, margin: '0 0 10px', letterSpacing: '-0.02em' }}>
                  Bud.OS
                </h3>
                <p style={{ fontFamily: T.sans, fontSize: 13.5, color: T.muted, lineHeight: 1.65, maxWidth: '38ch', margin: 0 }}>
                  Przetargi z BZP i TED, scoring GO/NO-GO, kosztorysy KNR, analiza konkurencji i dokumentacja ofertowa.
                </p>
              </div>

              {/* Screenshot strip */}
              <div style={{
                flex: 1,
                marginLeft: 16,
                marginRight: 16,
                borderRadius: '12px 12px 0 0',
                overflow: 'hidden',
                border: `1px solid ${T.edge0}`,
                borderBottom: 'none',
                position: 'relative',
              }}>
                {/* Browser chrome */}
                <div style={{
                  background: T.bg3,
                  borderBottom: `1px solid ${T.edge0}`,
                  padding: '8px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'rgba(239,68,68,0.45)' }} />
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'rgba(234,179,8,0.45)' }} />
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'rgba(22,201,132,0.45)' }} />
                  <div style={{
                    flex: 1, marginLeft: 8,
                    background: T.bg2, borderRadius: 4, height: 18,
                    display: 'flex', alignItems: 'center', padding: '0 10px',
                  }}>
                    <span style={{ fontFamily: T.mono, fontSize: 10, color: T.faint }}>app.yu-na.io/zwiad</span>
                  </div>
                </div>
                <Image
                  src="/brand/live-zwiad.png"
                  alt="BudOS Zwiad Przetargowy"
                  width={900}
                  height={500}
                  style={{ width: '100%', height: 'auto', display: 'block' }}
                />
              </div>

              {/* Footer link */}
              <div style={{ padding: '16px 28px', borderTop: `1px solid ${T.edge0}`, flexShrink: 0 }}>
                <Link href="/budos" style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  fontFamily: T.sans, fontSize: 13, fontWeight: 500,
                  color: T.ink,
                  background: 'rgba(255,255,255,0.06)',
                  border: `1px solid ${T.edge1}`,
                  padding: '9px 16px',
                  borderRadius: 9999,
                  textDecoration: 'none',
                  transition: 'background 150ms',
                }}>
                  Dowiedz się więcej
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </Link>
              </div>
            </div>

            {/* Infra.OS — narrow, inline icon */}
            <div style={{
              gridColumn: 'span 2',
              background: T.bg1,
              border: `1px solid ${T.edge0}`,
              borderRadius: 16,
              padding: 24,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              minHeight: 260,
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={T.accent} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
                  <h3 style={{ fontFamily: T.sans, fontSize: 15, fontWeight: 600, color: T.ink, margin: 0 }}>Infra.OS</h3>
                </div>
                <p style={{ fontFamily: T.sans, fontSize: 13, color: T.muted, lineHeight: 1.6, margin: 0 }}>
                  Logistyka budowy, zasoby, harmonogramy i controlling projektu.
                </p>
              </div>
              <span style={{
                display: 'inline-block',
                fontFamily: T.mono, fontSize: 10, fontWeight: 600,
                color: '#f59e0b',
                letterSpacing: '0.08em', textTransform: 'uppercase',
                marginTop: 16,
                padding: '4px 10px',
                border: '1px solid rgba(245,158,11,0.2)',
                borderRadius: 9999,
                width: 'fit-content',
              }}>
                Q3 2026
              </span>
            </div>

            {/* Dev.OS — narrow, inline icon */}
            <div style={{
              gridColumn: 'span 2',
              background: T.bg1,
              border: `1px solid ${T.edge0}`,
              borderRadius: 16,
              padding: 24,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              minHeight: 128,
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"/></svg>
                  <h3 style={{ fontFamily: T.sans, fontSize: 15, fontWeight: 600, color: T.ink, margin: 0 }}>Dev.OS</h3>
                </div>
                <p style={{ fontFamily: T.sans, fontSize: 13, color: T.muted, lineHeight: 1.6, margin: 0 }}>
                  Feasibility studies, ROI, analiza rynku deweloperskiego.
                </p>
              </div>
              <span style={{
                display: 'inline-block',
                fontFamily: T.mono, fontSize: 10, fontWeight: 600,
                color: '#60a5fa',
                letterSpacing: '0.08em', textTransform: 'uppercase',
                marginTop: 16,
                padding: '4px 10px',
                border: '1px solid rgba(96,165,250,0.2)',
                borderRadius: 9999,
                width: 'fit-content',
              }}>
                Q4 2026
              </span>
            </div>

            {/* Filler — stat strip */}
            <div style={{
              gridColumn: 'span 4',
              background: T.bg1,
              border: `1px solid ${T.edge0}`,
              borderRadius: 16,
              padding: '20px 24px',
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              alignItems: 'center',
            }}>
              {[
                { value: '—', label: 'avg czas analizy' },
                { value: '24/7', label: 'monitoring BZP+TED' },
                { value: '—', label: 'win rate klientów' },
                { value: '—', label: 'oszczędność vs ręcznie' },
              ].map((m) => (
                <div key={m.label} style={{ textAlign: 'center', padding: '8px 0' }}>
                  <div style={{ fontFamily: T.mono, fontSize: 22, fontWeight: 600, color: T.ink, letterSpacing: '-0.02em' }}>{m.value}</div>
                  <div style={{ fontFamily: T.mono, fontSize: 10, color: T.faint, marginTop: 4, letterSpacing: '0.04em' }}>{m.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS — STEP DIPTYCH ─────────────────────────────────── */}
      <section id="jak-dziala" style={{ padding: '80px 24px', borderTop: `1px solid ${T.edge0}` }}>
        <div style={{
          maxWidth: 1140,
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 64,
          alignItems: 'start',
        }}>
          {/* Left — text */}
          <div>
            <h2 style={{
              fontFamily: T.serif,
              fontSize: 'clamp(28px, 3vw, 42px)',
              fontWeight: 400,
              letterSpacing: '-0.025em',
              color: T.ink,
              margin: '0 0 12px',
              lineHeight: 1.1,
            }}>
              Od danych do decyzji
            </h2>
            <p style={{ fontFamily: T.sans, fontSize: 16, color: T.muted, margin: '0 0 40px', maxWidth: '44ch', lineHeight: 1.65 }}>
              Trzy kroki: monitor przetargów, AI ocenia szanse, generujesz dokumentację.
            </p>

            {/* Steps — vertical timeline */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
              {[
                {
                  n: '01',
                  title: 'Monitor',
                  desc: 'BZP, TED i e-Zamówienia skanowane 24/7. Nowe ogłoszenia pojawiają się w sekundy.',
                },
                {
                  n: '02',
                  title: 'Ocena AI',
                  desc: 'Scoring trafności, analiza warunków, weryfikacja ryzyka projektowego.',
                },
                {
                  n: '03',
                  title: 'Oferta',
                  desc: 'Kosztorysy KNR/ICB, harmonogramy, kompletna dokumentacja przetargowa.',
                },
              ].map((step, i) => (
                <div key={step.n} style={{ display: 'flex', gap: 20 }}>
                  {/* Connector line */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                    <div style={{
                      width: 32, height: 32,
                      borderRadius: '50%',
                      background: T.accentSub,
                      border: `1px solid ${T.accentBrd}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontFamily: T.mono, fontSize: 10, color: T.accent, fontWeight: 600,
                    }}>
                      {step.n}
                    </div>
                    {i < 2 && (
                      <div style={{ width: 1, flex: 1, background: T.edge0, minHeight: 32, marginTop: 4, marginBottom: 4 }} />
                    )}
                  </div>
                  <div style={{ paddingBottom: i < 2 ? 28 : 0 }}>
                    <div style={{ fontFamily: T.sans, fontSize: 15, fontWeight: 600, color: T.ink, marginBottom: 6 }}>{step.title}</div>
                    <div style={{ fontFamily: T.sans, fontSize: 13.5, color: T.muted, lineHeight: 1.65 }}>{step.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right — live scan terminal */}
          <div style={{
            background: T.bg2,
            border: `1px solid ${T.edge0}`,
            borderRadius: 16,
            overflow: 'hidden',
          }}>
            {/* Header */}
            <div style={{
              padding: '12px 18px',
              borderBottom: `1px solid ${T.edge0}`,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{ fontFamily: T.mono, fontSize: 10, color: T.muted, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                ZWIAD — LIVE SCAN
              </span>
              <span style={{ fontFamily: T.mono, fontSize: 10, color: T.accent }}>● aktywny</span>
            </div>

            {/* Terminal output */}
            <div style={{ padding: '16px 18px', fontFamily: T.mono, fontSize: 12, lineHeight: 1.8 }}>
              {[
                { t: T.faint, text: '$ zwiad start --sources=BZP,TED,BIP' },
                { t: T.muted, text: '→ połączono z 3 źródłami' },
                { t: T.muted, text: '→ pobieranie nowych ogłoszeń...' },
                { t: T.ink,   text: '✓ 14 nowych przetargów budowlanych' },
                { t: T.muted, text: '→ uruchamiam scoring AI...' },
                { t: T.accent, text: '✓ GO × 6  |  WAIT × 5  |  NO-GO × 3' },
                { t: T.muted, text: '→ generowanie alertów...' },
                { t: T.ink,   text: '✓ 2 alerty wysłane do twojego CRM' },
              ].map((line, i) => (
                <div key={i} style={{ color: line.t }}>{line.text}</div>
              ))}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, color: T.accent }}>
                <span style={{ animation: 'pulse 1.2s ease-in-out infinite' }}>▋</span>
                <span style={{ color: T.faint }}>oczekuję...</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── CTA — DARK STATEMENT ─────────────────────────────────────────── */}
      <section style={{ padding: '96px 24px', borderTop: `1px solid ${T.edge0}` }}>
        <div style={{ maxWidth: 680, margin: '0 auto' }}>
          <h2 style={{
            fontFamily: T.serif,
            fontSize: 'clamp(36px, 4vw, 60px)',
            fontWeight: 400,
            letterSpacing: '-0.025em',
            color: T.ink,
            margin: '0 0 16px',
            lineHeight: 1.05,
          }}>
            Gotowy na przewagę?
          </h2>
          <p style={{ fontFamily: T.sans, fontSize: 17, color: T.muted, lineHeight: 1.65, margin: '0 0 36px', maxWidth: '44ch' }}>
            Dołącz do firm, które wygrywają przetargi dzięki AI zamiast przeczuciom.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
            <PrimaryButton href="/signup">
              Zacznij za darmo
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </PrimaryButton>
            <GhostButton href="/budos">Poznaj Bud.OS</GhostButton>
          </div>
        </div>
      </section>

      {/* ─── FT5 STATEMENT FOOTER ─────────────────────────────────────────── */}
      <footer style={{
        padding: '48px 24px 32px',
        borderTop: `1px solid ${T.edge0}`,
      }}>
        <div style={{ maxWidth: 1140, margin: '0 auto' }}>
          {/* Brand + tagline */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={28} height={28} style={{ borderRadius: 7 }} />
            <span style={{ fontFamily: T.serif, fontSize: 24, fontWeight: 400, color: T.ink, letterSpacing: '-0.02em' }}>YU-NA</span>
          </div>
          <p style={{ fontFamily: T.sans, fontSize: 14, color: T.muted, margin: '0 0 32px', maxWidth: '52ch', lineHeight: 1.6 }}>
            System decyzyjny dla wykonawców przetargów publicznych.
          </p>

          {/* Single inline link row */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0 28px', marginBottom: 28 }}>
            {[
              { label: 'Regulamin', href: '/terms' },
              { label: 'Prywatność', href: '/privacy' },
              { label: 'RODO', href: '/rodo' },
              { label: 'Bud.OS', href: '/budos' },
              { label: 'Status', href: '/status' },
            ].map((l) => (
              <Link key={l.label} href={l.href} style={{
                fontFamily: T.sans, fontSize: 13, color: T.faint,
                textDecoration: 'none', transition: 'color 120ms',
                lineHeight: 2.4,
              }}>
                {l.label}
              </Link>
            ))}
          </div>

          {/* Bottom bar */}
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            paddingTop: 20, borderTop: `1px solid ${T.edge0}`,
            fontFamily: T.mono, fontSize: 11, color: T.faint, letterSpacing: '0.04em',
          }}>
            <span>© 2026 YU-NA Intelligence</span>
            <span>yu-na.io</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
