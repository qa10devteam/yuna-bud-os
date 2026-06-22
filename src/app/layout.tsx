import type { Metadata } from 'next';
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

export const metadata: Metadata = {
  title: 'Terra.OS — System Zarządzania Przetargami i Budową',
  description: 'Lokalny system dla wykonawców robót ziemnych — zwiad, kosztorys, silnik decyzyjny',
  icons: {
    icon: '/assets/logo.svg',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pl">
      <body className={`${space.variable} ${mono.variable} font-display`}>
        {children}
      </body>
    </html>
  );
}
