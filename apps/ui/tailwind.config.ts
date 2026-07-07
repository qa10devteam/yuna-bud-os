import type { Config } from 'tailwindcss';

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
        // Terra.OS Design Tokens — Earth palette (Task 131)
        primary: {
          50: '#f5f0eb',
          100: '#e8ddd0',
          500: '#8B6914',
          700: '#5C4409',
          900: '#2D1F03',
        },
        surface: {
          bg: '#FAFAF8',
          card: '#FFFFFF',
          border: '#E5E0D8',
        },
        semantic: {
          success: '#2D6A4F',
          warning: '#E9C46A',
          danger: '#E76F51',
          info: '#457B9D',
        },
      },
      boxShadow: {
        'token-sm': '0 1px 2px 0 rgba(26, 18, 8, 0.05)',
        'token-md': '0 4px 6px -1px rgba(26, 18, 8, 0.07), 0 2px 4px -2px rgba(26, 18, 8, 0.05)',
        'token-lg': '0 10px 15px -3px rgba(26, 18, 8, 0.08), 0 4px 6px -4px rgba(26, 18, 8, 0.04)',
      },
      borderRadius: {
        token: '0.5rem',
        'token-lg': '0.75rem',
        'token-xl': '1rem',
      },
    },
  },
  plugins: [],
};

export default config;
