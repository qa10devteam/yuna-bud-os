// Terra.OS Design Tokens — Earth palette
export const tokens = {
  colors: {
    // Primary — deep earth
    primary: { 50: '#f5f0eb', 100: '#e8ddd0', 500: '#8B6914', 700: '#5C4409', 900: '#2D1F03' },
    // Surface
    surface: { bg: '#FAFAF8', card: '#FFFFFF', border: '#E5E0D8' },
    // Semantic
    success: '#2D6A4F', warning: '#E9C46A', danger: '#E76F51', info: '#457B9D',
    // Text
    text: { primary: '#1A1208', secondary: '#4A3F2F', muted: '#8C7B6B' },
  },
  typography: {
    fontFamily: { sans: 'Inter, system-ui, sans-serif', mono: 'JetBrains Mono, monospace' },
    fontSize: { xs: '0.75rem', sm: '0.875rem', base: '1rem', lg: '1.125rem', xl: '1.25rem', '2xl': '1.5rem', '3xl': '1.875rem' },
    fontWeight: { normal: 400, medium: 500, semibold: 600, bold: 700 },
  },
  spacing: { 1: '0.25rem', 2: '0.5rem', 3: '0.75rem', 4: '1rem', 6: '1.5rem', 8: '2rem', 12: '3rem', 16: '4rem' },
  radius: { sm: '0.375rem', md: '0.5rem', lg: '0.75rem', xl: '1rem', full: '9999px' },
  shadow: {
    sm: '0 1px 2px 0 rgba(26, 18, 8, 0.05)',
    md: '0 4px 6px -1px rgba(26, 18, 8, 0.07), 0 2px 4px -2px rgba(26, 18, 8, 0.05)',
    lg: '0 10px 15px -3px rgba(26, 18, 8, 0.08), 0 4px 6px -4px rgba(26, 18, 8, 0.04)',
  },
} as const
