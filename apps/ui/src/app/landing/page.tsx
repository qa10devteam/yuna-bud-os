import type { Metadata } from 'next';
import LandingClient from './LandingClient';

export const metadata: Metadata = {
  title:       'YU-NA BudOS - Wygrywaj przetargi 3x szybciej',
  description: 'System decyzyjny dla firm budowlanych. Automatyczny sync BZP, AI analiza ryzyka SWZ, silnik kosztorysowy KNR. Zacznij bezplatnie - bez karty kredytowej.',
  openGraph: {
    title:       'YU-NA BudOS - Wygrywaj przetargi 3x szybciej',
    description: 'Automatyczny sync BZP, AI analiza ryzyka SWZ i silnik kosztorysowy KNR w jednej platformie.',
    images:      [{ url: '/brand/B04-og-dark.png', width: 1200, height: 630 }],
    type:        'website',
    locale:      'pl_PL',
  },
  twitter: {
    card:        'summary_large_image',
    title:       'YU-NA BudOS - Wygrywaj przetargi 3x szybciej',
    description: 'System decyzyjny dla firm budowlanych.',
    images:      ['/brand/B04-og-dark.png'],
  },
};

export default function LandingPage() {
  return <LandingClient />;
}
