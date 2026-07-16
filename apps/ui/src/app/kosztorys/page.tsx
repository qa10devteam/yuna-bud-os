'use client';
import dynamic from 'next/dynamic';

const KosztorysPage = dynamic(() => import('@/components/pages/KosztorysPage').then(m => m.KosztorysPage), { ssr: false });

export default function Page() {
  return <KosztorysPage />;
}
