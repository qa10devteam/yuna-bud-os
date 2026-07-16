'use client';
import dynamic from 'next/dynamic';

const PogodaPage = dynamic(() => import('@/components/pages/PogodaPage').then(m => m.PogodaPage), { ssr: false });

export default function Page() {
  return <PogodaPage />;
}
