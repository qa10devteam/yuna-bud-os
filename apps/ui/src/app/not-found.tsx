// S6-2 — Terra.OS branded 404 page (server component — no hooks needed)
// Shown when Next.js App Router cannot find a matching route segment.
// See: https://nextjs.org/docs/app/api-reference/file-conventions/not-found

import Link from 'next/link';

export default function NotFound() {
  return (
    <div
      className="min-h-dvh flex items-center justify-center p-8"
      style={{ backgroundColor: '#0A0A0A' }}
    >
      <div className="text-center max-w-md">
        {/* Big 404 */}
        <p
          className="text-[120px] font-extrabold leading-none select-none"
          style={{ color: '#00FF94' }}
        >
          404
        </p>

        {/* Divider accent line */}
        <div
          className="mx-auto my-6 h-px w-24 rounded-full"
          style={{ backgroundColor: '#00FF94', opacity: 0.4 }}
        />

        {/* Polish heading */}
        <h1 className="text-2xl font-bold text-white mb-3">
          Strony nie znaleziono
        </h1>
        <p className="text-sm mb-8" style={{ color: '#6B7280' }}>
          Podstrona, której szukasz, nie istnieje lub została przeniesiona.
        </p>

        {/* Back to Dashboard */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm transition-colors"
          style={{
            backgroundColor: '#00FF94',
            color: '#0A0A0A',
          }}
        >
          ← Wróć do Dashboardu
        </Link>
      </div>
    </div>
  );
}
