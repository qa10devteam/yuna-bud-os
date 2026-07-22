import type { Metadata, Viewport } from 'next';
import { DM_Serif_Display, Space_Grotesk, JetBrains_Mono } from 'next/font/google';
import Script from 'next/script';
import './globals.css';

const dmSerif = DM_Serif_Display({
  subsets: ['latin'],
  weight: '400',
  variable: '--font-dm-serif',
  display: 'swap',
});

const space = Space_Grotesk({
  subsets: ['latin', 'latin-ext'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-space',
  display: 'swap',
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-jetbrains',
  display: 'swap',
});

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#07070d',
};

export const metadata: Metadata = {
  title: 'YU-NA | BudOS — Przetargi budowlane. Opanowane.',
  description: 'Monitoring BZP/TED w czasie rzeczywistym. Silnik GO/NO-GO. Kosztorys KNR/ICB. System ktory wie zanim zlozysz oferte.',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'BudOS',
  },
  icons: {
    icon: '/icons/icon.svg',
    apple: '/icons/icon.svg',
  },
  metadataBase: new URL('https://yu-na.io'),
  openGraph: {
    title: 'YU-NA | BudOS — Przetargi budowlane. Opanowane.',
    description: 'Monitoring BZP/TED w czasie rzeczywistym. Silnik GO/NO-GO. Kosztorys KNR/ICB.',
    type: 'website',
    locale: 'pl_PL',
    url: 'https://yu-na.io/landing',
    siteName: 'YU-NA BudOS',
    images: [
      {
        url: '/brand/B04-og-dark.png',
        width: 1200,
        height: 630,
        alt: 'YU-NA BudOS — System Decyzyjny dla Przetargów Budowlanych',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'YU-NA | BudOS — Przetargi budowlane. Opanowane.',
    description: 'Monitoring BZP/TED w czasie rzeczywistym. Silnik GO/NO-GO. Kosztorys KNR/ICB.',
    images: ['/brand/B04-og-dark.png'],
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
        {process.env.NODE_ENV === 'development' && (
          <>
            <Script
              src="//unpkg.com/react-scan/dist/auto.global.js"
              crossOrigin="anonymous"
              strategy="beforeInteractive"
            />
            <Script
              src="//unpkg.com/react-grab/dist/index.global.js"
              crossOrigin="anonymous"
              strategy="beforeInteractive"
            />
          </>
        )}
      </head>
      <body className={`${dmSerif.variable} ${space.variable} ${jetbrains.variable} font-display antialiased`}>
        {children}
      </body>
    </html>
  );
}
