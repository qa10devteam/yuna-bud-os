'use client';
import dynamic from 'next/dynamic';

const WebhooksPage = dynamic(() => import('@/components/pages/WebhooksPage'), { ssr: false });

export default function Page() {
  return <WebhooksPage />;
}
