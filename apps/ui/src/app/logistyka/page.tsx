'use client';
import dynamic from 'next/dynamic';

const LogistykaPage = dynamic(() => import('@/components/pages/LogistykaPage').then(m => m.LogistykaPage), { ssr: false });

export default function Page() {
  return <LogistykaPage />;
}
