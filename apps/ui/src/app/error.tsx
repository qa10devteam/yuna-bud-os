'use client';

// S6-1 — Next.js 13+ App Router error boundary
// Catches render errors in route segments and shows a recovery UI.
// See: https://nextjs.org/docs/app/api-reference/file-conventions/error

import { useEffect, useState } from 'react';
import { AlertTriangle, RefreshCw, Clipboard, ClipboardCheck } from 'lucide-react';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Log to console so it shows in CI / server logs
    console.error('[YU-NA] Unhandled render error:', error);
  }, [error]);

  async function handleReport() {
    const text = [
      `Błąd: ${error.message || 'Nieznany błąd'}`,
      error.digest ? `ID błędu (digest): ${error.digest}` : null,
    ]
      .filter(Boolean)
      .join('\n');

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Fallback for environments without clipboard API
      console.warn('[YU-NA] Clipboard unavailable. Error info:', text);
    }
  }

  return (
    <div className="min-h-screen bg-ink-950 flex items-center justify-center p-8">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-2xl bg-nogo/15 border border-nogo-brd flex items-center justify-center mx-auto mb-5">
          <AlertTriangle className="w-8 h-8 text-nogo" />
        </div>

        <h1 className="text-xl font-bold text-ink-950/30 mb-2">
          Wystąpił nieoczekiwany błąd
        </h1>
        <p className="text-slate-400 text-sm mb-1">
          {error.message || 'Coś poszło nie tak po stronie aplikacji.'}
        </p>

        {/* Digest / error code */}
        {error.digest && (
          <div className="inline-flex items-center gap-2 mt-2 mb-5 px-3 py-1.5 rounded-lg bg-ink-900 border border-ink-800">
            <span className="text-slate-500 text-xs">Kod błędu:</span>
            <code className="text-slate-300 text-xs font-mono">{error.digest}</code>
          </div>
        )}

        <div className="flex flex-wrap gap-3 justify-center mt-6">
          {/* Primary: retry */}
          <button type="button"
            onClick={reset}
            className="flex items-center gap-2 px-5 py-2.5 bg-em text-ink-950 rounded-xl font-semibold text-sm hover:bg-em transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Spróbuj ponownie
          </button>

          {/* Secondary: copy error info */}
          <button type="button"
            onClick={handleReport}
            className="flex items-center gap-2 px-5 py-2.5 bg-ink-800 text-slate-300 rounded-xl font-medium text-sm hover:bg-ink-700 transition-colors"
          >
            {copied ? (
              <>
                <ClipboardCheck className="w-4 h-4 text-em" />
                <span className="text-em">Skopiowano!</span>
              </>
            ) : (
              <>
                <Clipboard className="w-4 h-4" />
                Zgłoś błąd
              </>
            )}
          </button>

          {/* Tertiary: back to dashboard */}
          <button type="button"
            onClick={() => (window.location.href = '/')}
            className="px-5 py-2.5 bg-ink-800 text-slate-300 rounded-xl font-medium text-sm hover:bg-ink-700 transition-colors"
          >
            Wróć do dashboardu
          </button>
        </div>
      </div>
    </div>
  );
}
