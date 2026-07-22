'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

const STORAGE_KEY = 'terra_cookie_consent';

interface ConsentPreferences {
  analytics: boolean;
  marketing: boolean;
  third_party: boolean;
}

export default function CookieBanner() {
  const [visible, setVisible] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [preferences, setPreferences] = useState<ConsentPreferences>({
    analytics: false,
    marketing: false,
    third_party: false,
  });

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      setVisible(true);
    }
  }, []);

  const saveConsent = async (consent: ConsentPreferences) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(consent));
    setVisible(false);

    try {
      await fetch('/api/v2/gdpr/consent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(consent),
      });
    } catch {
      // Consent stored locally even if API call fails
    }
  };

  const handleAcceptAll = () => {
    saveConsent({ analytics: true, marketing: true, third_party: true });
  };

  const handleEssentialOnly = () => {
    saveConsent({ analytics: false, marketing: false, third_party: false });
  };

  const handleSaveSettings = () => {
    saveConsent(preferences);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-white/10 bg-[#0A0A0F] p-4 shadow-2xl md:p-6">
      <div className="mx-auto max-w-5xl">
        {!showSettings ? (
          <div className="flex flex-col items-start gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex-1">
              <p className="text-sm text-gray-300">
                Używamy plików cookie, aby zapewnić najlepsze doświadczenia na naszej
                platformie. Możesz zaakceptować wszystkie pliki cookie, wybrać tylko
                niezbędne lub dostosować ustawienia.{' '}
                <Link href="/privacy" className="text-[#B8FF00] underline hover:text-[#B8FF00]/80">
                  Polityka prywatności
                </Link>
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <button type="button"
                onClick={handleAcceptAll}
                className="rounded-md bg-[#B8FF00] px-4 py-2 text-sm font-medium text-[#0A0A0F] transition hover:bg-[#B8FF00]/90"
              >
                Akceptuję
              </button>
              <button type="button"
                onClick={handleEssentialOnly}
                className="rounded-md border border-white/20 px-4 py-2 text-sm font-medium text-gray-300 transition hover:border-white/40 hover:text-white"
              >
                Tylko niezbędne
              </button>
              <button type="button"
                onClick={() => setShowSettings(true)}
                className="rounded-md border border-white/20 px-4 py-2 text-sm font-medium text-gray-300 transition hover:border-white/40 hover:text-white"
              >
                Ustawienia
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-white">Ustawienia plików cookie</h3>
            <div className="space-y-3">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked
                  disabled
                  className="h-4 w-4 rounded border-gray-600 accent-[#B8FF00]"
                />
                <span className="text-sm text-gray-300">
                  Niezbędne — wymagane do działania platformy
                </span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={preferences.analytics}
                  onChange={(e) =>
                    setPreferences((p) => ({ ...p, analytics: e.target.checked }))
                  }
                  className="h-4 w-4 rounded border-gray-600 accent-[#B8FF00]"
                />
                <span className="text-sm text-gray-300">
                  Analityczne — pomagają nam ulepszać platformę
                </span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={preferences.marketing}
                  onChange={(e) =>
                    setPreferences((p) => ({ ...p, marketing: e.target.checked }))
                  }
                  className="h-4 w-4 rounded border-gray-600 accent-[#B8FF00]"
                />
                <span className="text-sm text-gray-300">
                  Marketingowe — personalizacja treści
                </span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={preferences.third_party}
                  onChange={(e) =>
                    setPreferences((p) => ({ ...p, third_party: e.target.checked }))
                  }
                  className="h-4 w-4 rounded border-gray-600 accent-[#B8FF00]"
                />
                <span className="text-sm text-gray-300">
                  Zewnętrzne — integracje z usługami trzecimi
                </span>
              </label>
            </div>
            <div className="flex gap-2">
              <button type="button"
                onClick={handleSaveSettings}
                className="rounded-md bg-[#B8FF00] px-4 py-2 text-sm font-medium text-[#0A0A0F] transition hover:bg-[#B8FF00]/90"
              >
                Zapisz ustawienia
              </button>
              <button type="button"
                onClick={() => setShowSettings(false)}
                className="rounded-md border border-white/20 px-4 py-2 text-sm font-medium text-gray-300 transition hover:border-white/40 hover:text-white"
              >
                Wróć
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
