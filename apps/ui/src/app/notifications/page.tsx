'use client';
import dynamic from 'next/dynamic';

const NotificationsPage = dynamic(() => import('@/components/pages/NotificationsPage').then(m => m.NotificationsPage), { ssr: false });

export default function Page() {
  return <NotificationsPage />;
}
