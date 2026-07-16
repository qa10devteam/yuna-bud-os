'use client';
import dynamic from 'next/dynamic';

const SilnikPage = dynamic(() => import('@/components/pages/SilnikPage').then(m => m.SilnikPage), { ssr: false });

export default function Page() {
  return <SilnikPage />;
}
