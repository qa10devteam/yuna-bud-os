'use client';
import dynamic from 'next/dynamic';

const SystemPage = dynamic(() => import('@/components/pages/SystemPage').then(m => m.SystemPage), { ssr: false });

export default function Page() {
  return <SystemPage />;
}
