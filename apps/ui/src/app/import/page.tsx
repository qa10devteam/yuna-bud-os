'use client';
import dynamic from 'next/dynamic';

const ImportPage = dynamic(() => import('@/components/pages/ImportPage').then(m => m.ImportPage), { ssr: false });

export default function Page() {
  return <ImportPage />;
}
