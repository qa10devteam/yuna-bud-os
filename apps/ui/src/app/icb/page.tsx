'use client';
import dynamic from 'next/dynamic';

const ICBPage = dynamic(() => import('@/components/pages/ICBPage').then(m => m.ICBPage), { ssr: false });

export default function Page() {
  return <ICBPage />;
}
