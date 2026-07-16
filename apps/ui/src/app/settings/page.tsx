'use client';
import dynamic from 'next/dynamic';

const SettingsPage = dynamic(() => import('@/components/pages/SettingsPage').then(m => m.SettingsPage), { ssr: false });

export default function Page() {
  return <SettingsPage />;
}
