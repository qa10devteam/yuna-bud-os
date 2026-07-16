'use client';
import dynamic from 'next/dynamic';

const OfertaPage = dynamic(() => import('@/components/pages/OfertaPage').then(m => m.OfertaPage), { ssr: false });

export default function Page() {
  return <OfertaPage />;
}
