'use client';
import dynamic from 'next/dynamic';

const ProactivePage = dynamic(() => import('@/components/pages/ProactivePage').then(m => m.ProactivePage), { ssr: false });

export default function Page() {
  return <ProactivePage />;
}
