import type { Metadata, Viewport } from 'next';
import { Space_Grotesk, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const space = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-space',
  display: 'swap',
});

const mono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#00ff88',
};

export const metadata: Metadata = {
  title: 'YU-NA — System Zarządzania Przetargami i Budową',
  description: 'Platforma do zarządzania przetargami budowlanymi. AI analiza ryzyka SWZ, automatyczny BZP sync, silnik kalkulacji.',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'YU-NA',
  },
  icons: {
    icon: '/favicon.ico',
    apple: '/icons/icon-192.png',
  },
  other: {
    'mobile-web-app-capable': 'yes',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pl">
      <head>
        {/* PWA Service Worker registration */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js')
                    .then(function(reg) { console.log('[PWA] SW registered:', reg.scope); })
                    .catch(function(err) { console.warn('[PWA] SW registration failed:', err); });
                });
              }
            `,
          }}
        />
      </head>
      <body className={`${space.variable} ${mono.variable} font-display`}>
        {children}
      </body>
    </html>
  );
}
