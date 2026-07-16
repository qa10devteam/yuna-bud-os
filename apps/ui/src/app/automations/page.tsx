'use client';
import dynamic from 'next/dynamic';

const AutomationPage = dynamic(() => import('@/components/pages/AutomationPage'), { ssr: false });

export default function Page() {
  return <AutomationPage />;
}
