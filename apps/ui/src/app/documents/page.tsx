'use client';
import dynamic from 'next/dynamic';

const DocumentsPage = dynamic(() => import('@/components/pages/DocumentsPage').then(m => m.DocumentsPage), { ssr: false });

export default function Page() {
  return <DocumentsPage />;
}
