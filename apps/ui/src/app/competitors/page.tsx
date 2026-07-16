'use client';
import dynamic from 'next/dynamic';

const CompetitorPage = dynamic(() => import('@/components/pages/CompetitorPage').then(m => m.CompetitorPage), { ssr: false });

export default function Page() {
  return <CompetitorPage />;
}
