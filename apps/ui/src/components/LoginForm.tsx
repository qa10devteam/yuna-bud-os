'use client';

import { useState } from 'react';
import { useStore } from '@/store/useStore';
import type { AuthUser } from '@/store/useStore';
import { Eye, EyeOff, Loader2, LogIn } from 'lucide-react';

interface LoginFormProps {
  onSuccess: () => void;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const setAuth = useStore((s) => s.setAuth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [name, setName] = useState('');
  const [orgName, setOrgName] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = tab === 'login' ? '/api/v2/auth/login' : '/api/v2/auth/register';
      const body = tab === 'login'
        ? { email, password }
        : { email, password, name, org_name: orgName };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || 'Błąd logowania');
        return;
      }

      setAuth(data.user as AuthUser, data.access_token, data.refresh_token);
      onSuccess();
    } catch {
      setError('Błąd połączenia z serwerem');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-earth-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 mb-4">
            <span className="text-2xl font-bold text-accent-primary">T</span>
          </div>
          <h1 className="text-2xl font-bold text-earth-100">
            Terra<span className="text-accent-primary">.OS</span>
          </h1>
          <p className="text-earth-500 text-sm mt-1">Platforma zarządzania przetargami</p>
        </div>

        {/* Card */}
        <div className="bg-earth-900/60 border border-earth-800/60 rounded-2xl p-6 backdrop-blur-sm shadow-xl shadow-black/40">
          {/* Tabs */}
          <div className="flex rounded-xl bg-earth-800/50 p-1 mb-6 gap-1">
            {(['login', 'register'] as const).map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); setError(''); }}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  tab === t
                    ? 'bg-accent-primary text-earth-950 shadow-sm'
                    : 'text-earth-400 hover:text-earth-200'
                }`}
              >
                {t === 'login' ? 'Logowanie' : 'Rejestracja'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {tab === 'register' && (
              <>
                <div>
                  <label className="block text-xs font-medium text-earth-400 mb-1.5">
                    Imię i nazwisko
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    placeholder="Jan Kowalski"
                    className="w-full bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60 focus:ring-1 focus:ring-accent-primary/30 transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-earth-400 mb-1.5">
                    Nazwa firmy
                  </label>
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="Kowalski Budownictwo Sp. z o.o."
                    className="w-full bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60 focus:ring-1 focus:ring-accent-primary/30 transition-all"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-medium text-earth-400 mb-1.5">
                Adres email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="jan@firma.pl"
                className="w-full bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60 focus:ring-1 focus:ring-accent-primary/30 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-earth-400 mb-1.5">
                Hasło
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                  placeholder={tab === 'register' ? 'min. 8 znaków' : '••••••••'}
                  className="w-full bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 pr-11 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60 focus:ring-1 focus:ring-accent-primary/30 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-earth-500 hover:text-earth-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                <span className="w-4 h-4 shrink-0">⚠</span>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-accent-primary hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-earth-950 font-semibold rounded-xl transition-all duration-200 mt-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <LogIn className="w-4 h-4" />
              )}
              {tab === 'login' ? 'Zaloguj się' : 'Zarejestruj się'}
            </button>
          </form>
        </div>

        <p className="text-center text-earth-600 text-xs mt-4">
          YU-NA © 2026 — System zarządzania przetargami budowlanymi
        </p>
      </div>
    </div>
  );
}
