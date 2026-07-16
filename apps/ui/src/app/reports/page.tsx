'use client';
import dynamic from 'next/dynamic';

const ReportsPage = dynamic(() => import('@/components/pages/ReportsPage').then(m => m.ReportsPage), { ssr: false });

export default function Page() {
  return <ReportsPage />;
}
