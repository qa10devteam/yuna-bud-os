'use client';
import dynamic from 'next/dynamic';

const DashboardPage = dynamic(() => import('@/components/pages/DashboardPage').then(m => m.DashboardPage), { ssr: false });

export default function Page() {
  return <DashboardPage />;
}
