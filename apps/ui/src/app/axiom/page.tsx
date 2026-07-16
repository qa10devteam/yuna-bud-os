'use client';
import dynamic from 'next/dynamic';

const AxiomEnginePage = dynamic(() => import('@/components/pages/AxiomEnginePage'), { ssr: false });

export default function Page() {
  return <AxiomEnginePage />;
}
