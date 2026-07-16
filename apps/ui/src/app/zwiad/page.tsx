'use client';
import dynamic from 'next/dynamic';

const ZwiadPage = dynamic(() => import('@/components/pages/ZwiadPage').then(m => m.ZwiadPage), { ssr: false });

export default function Page() {
  return <ZwiadPage />;
}
