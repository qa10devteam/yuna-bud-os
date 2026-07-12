'use client';

// S6-1 — Next.js 13+ App Router error boundary
// Catches render errors in route segments and shows a recovery UI.
// See: https://nextjs.org/docs/app/api-reference/file-conventions/error

import { useEffect } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // Log to console so it shows in CI / server logs
    console.error('[YU-NA] Unhandled render error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-earth-950 flex items-center justify-center p-8">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-2xl bg-red-500/15 border border-red-500/20 flex items-center justify-center mx-auto mb-5">
          <AlertTriangle className="w-8 h-8 text-red-400" />
        </div>

        <h1 className="text-xl font-bold text-earth-50 mb-2">
          Wystąpił nieoczekiwany błąd
        </h1>
        <p className="text-earth-400 text-sm mb-1">
          {error.message || 'Coś poszło nie tak po stronie aplikacji.'}
        </p>
        {error.digest && (
          <p className="text-earth-600 text-xs font-mono mb-5">
            ID błędu: {error.digest}
          </p>
        )}

        <div className="flex gap-3 justify-center mt-6">
          <button
            onClick={reset}
            className="flex items-center gap-2 px-5 py-2.5 bg-accent-primary text-earth-950 rounded-xl font-semibold text-sm hover:bg-emerald-400 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Spróbuj ponownie
          </button>
          <button
            onClick={() => window.location.href = '/'}
            className="px-5 py-2.5 bg-earth-800 text-earth-300 rounded-xl font-medium text-sm hover:bg-earth-700 transition-colors"
          >
            Wróć do dashboardu
          </button>
        </div>
      </div>
    </div>
  );
}
