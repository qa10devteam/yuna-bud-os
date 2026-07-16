'use client';
import dynamic from 'next/dynamic';

const ResourcesPage = dynamic(() => import('@/components/pages/ResourcesPage').then(m => m.ResourcesPage), { ssr: false });

export default function Page() {
  return <ResourcesPage />;
}
