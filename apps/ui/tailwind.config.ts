import type { Config } from 'tailwindcss';

/**
 * YU-NA / budos — Tailwind v4 compat config
 *
 * Token hierarchy:
 *   @theme in globals.css  →  earth-* / accent-* / semantic vars (PRIMARY SOURCE)
 *   extend here            →  shadow tokens, radius tokens (supplements)
 *
 * Dead palettes (terra.*, primary.*, surface.*, semantic.*) removed — all
 * colour tokens live in globals.css @theme so there is a single source of truth.
 */
const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans:    ['var(--font-space)', 'sans-serif'],
        mono:    ['var(--font-mono)', 'monospace'],
        display: ['Space Grotesk', 'sans-serif'],
      },
      // ── Elevation shadows (earth-tinted, dark-optimised) ─────────────────────
      boxShadow: {
        'token-sm': '0 1px 3px 0 rgba(0,0,0,0.4), 0 1px 2px -1px rgba(0,0,0,0.3)',
        'token-md': '0 4px 8px -2px rgba(0,0,0,0.5), 0 2px 4px -2px rgba(0,0,0,0.3)',
        'token-lg': '0 12px 24px -4px rgba(0,0,0,0.6), 0 4px 8px -4px rgba(0,0,0,0.4)',
        'token-glow': '0 0 20px rgba(16,185,129,0.15)',
      },
      // ── Border radius scale ───────────────────────────────────────────────────
      borderRadius: {
        token:    '0.5rem',   // 8px  — inputs, badges
        'token-lg':  '0.75rem', // 12px — cards
        'token-xl':  '1rem',    // 16px — modals, panels
      },
      // ── Animation ────────────────────────────────────────────────────────────
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.5' },
        },
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        shimmer:     'shimmer 2s linear infinite',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
        'fade-up':   'fade-up 0.35s ease-out',
      },
    },
  },
  plugins: [],
};

export default config;
