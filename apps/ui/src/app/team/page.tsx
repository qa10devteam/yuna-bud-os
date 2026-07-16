'use client';
import dynamic from 'next/dynamic';

const TeamPage = dynamic(() => import('@/components/pages/TeamPage').then(m => m.TeamPage), { ssr: false });

export default function Page() {
  return <TeamPage />;
}
