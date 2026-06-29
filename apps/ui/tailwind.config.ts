import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-space)', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
        display: ['Space Grotesk', 'sans-serif'],
      },
      colors: {
        terra: {
          black: '#0A0A0A',
          dark: '#1A1A1A',
          medium: '#3D3D3C',
          light: '#6B6B68',
          green: '#00FF94',
          red: '#FF3300',
          blue: '#3B82F6',
          purple: '#A855F7',
        },
      },
    },
  },
  plugins: [],
};

export default config;
