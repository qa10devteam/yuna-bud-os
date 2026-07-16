'use client';
import dynamic from 'next/dynamic';

const BidIntelligencePage = dynamic(() => import('@/components/pages/BidIntelligencePage'), { ssr: false });

export default function Page() {
  return <BidIntelligencePage />;
}
