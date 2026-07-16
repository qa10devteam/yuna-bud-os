'use client';
import dynamic from 'next/dynamic';

const BookmarksBoardPage = dynamic(() => import('@/components/pages/BookmarksBoardPage').then(m => m.BookmarksBoardPage), { ssr: false });

export default function Page() {
  return <BookmarksBoardPage />;
}
