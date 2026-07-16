'use client';
import dynamic from 'next/dynamic';

const AnalyticsPage = dynamic(() => import('@/components/pages/AnalyticsPage').then(m => m.AnalyticsPage), { ssr: false });

export default function Page() {
  return <AnalyticsPage />;
}
