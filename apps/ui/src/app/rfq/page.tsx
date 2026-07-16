'use client';
import dynamic from 'next/dynamic';

const RfqPage = dynamic(() => import('@/components/pages/RfqPage').then(m => m.RfqPage), { ssr: false });

export default function Page() {
  return <RfqPage />;
}
