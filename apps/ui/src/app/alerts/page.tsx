'use client';
import dynamic from 'next/dynamic';

const AlertsPage = dynamic(() => import('@/components/pages/AlertsPage').then(m => m.AlertsPage), { ssr: false });

export default function Page() {
  return <AlertsPage />;
}
