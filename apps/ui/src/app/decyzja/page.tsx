'use client';
import dynamic from 'next/dynamic';

const DecyzjaPage = dynamic(() => import('@/components/pages/DecyzjaPage').then(m => m.DecyzjaPage), { ssr: false });

export default function Page() {
  return <DecyzjaPage />;
}
