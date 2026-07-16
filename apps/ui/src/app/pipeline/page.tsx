'use client';
import dynamic from 'next/dynamic';

const PipelinePage = dynamic(() => import('@/components/pages/PipelinePage').then(m => m.PipelinePage), { ssr: false });

export default function Page() {
  return <PipelinePage />;
}
