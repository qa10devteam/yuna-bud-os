'use client';
import dynamic from 'next/dynamic';

const BuyerCRMPage = dynamic(() => import('@/components/pages/BuyerCRMPage').then(m => m.BuyerCRMPage), { ssr: false });

export default function Page() {
  return <BuyerCRMPage />;
}
