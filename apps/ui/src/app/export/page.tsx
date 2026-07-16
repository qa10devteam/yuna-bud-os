'use client';
import dynamic from 'next/dynamic';

const ExportPage = dynamic(() => import('@/components/pages/ExportPage'), { ssr: false });

export default function Page() {
  return <ExportPage />;
}
