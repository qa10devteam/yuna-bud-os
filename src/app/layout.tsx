import type { Metadata } from 'next';
import { Space_Grotesk, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const spaceGrotesk = Space_Grotesk({ 
  subsets: ['latin'],
  variable: '--font-space',
  display: 'swap',
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Terra.OS — System zarządzania Ziemią',
  description: 'Profesjonalne narzędzie do analizy przetargów budowlanych',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pl">
      <body className={`${spaceGrotesk.variable} ${jetBrainsMono.variable} font-sans`}>
        {children}
      </body>
    </html>
  );
}
