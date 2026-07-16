'use client';
import dynamic from 'next/dynamic';

const MarketIntelPage = dynamic(() => import('@/components/pages/MarketIntelPage').then(m => m.MarketIntelPage), { ssr: false });

export default function Page() {
  return <MarketIntelPage />;
}
