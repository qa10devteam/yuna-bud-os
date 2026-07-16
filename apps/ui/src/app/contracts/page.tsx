'use client';
import dynamic from 'next/dynamic';

const ContractsPage = dynamic(() => import('@/components/pages/ContractsPage').then(m => m.ContractsPage), { ssr: false });

export default function Page() {
  return <ContractsPage />;
}
