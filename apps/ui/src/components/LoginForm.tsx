'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useStore } from '@/store/useStore';
import type { AuthUser } from '@/store/useStore';
import { Eye, EyeOff, Loader2, LogIn, UserPlus } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface LoginFormProps {
  onSuccess: () => void;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function LoginForm({ onSuccess }: LoginFormProps) {
  const setAuth = useStore((s) => s.setAuth);

  const [tab,          setTab]          = useState<'login' | 'register'>('login');
  const [email,        setEmail]        = useState('');
  const [password,     setPassword]     = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [name,         setName]         = useState('');
  const [orgName,      setOrgName]      = useState('');
  const [error,        setError]        = useState('');
  const [loading,      setLoading]      = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = tab === 'login'
        ? '/api/v2/auth/login'
        : '/api/v2/auth/register';

      const body = tab === 'login'
        ? { email, password }
        : { email, password, name, org_name: orgName };

      const res  = await fetch(endpoint, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        // Human-readable error messages
        const detail = data.detail ?? '';
        if (res.status === 401 || detail.toLowerCase().includes('invalid'))
          setError('Nieprawidłowy e-mail lub hasło. Spróbuj ponownie lub zresetuj hasło.');
        else if (res.status === 409 || detail.toLowerCase().includes('exist'))
          setError('Konto z tym adresem e-mail już istnieje. Zaloguj się lub odzyskaj dostęp.');
        else if (res.status >= 500)
          setError('Problem z serwerem — spróbuj ponownie za chwilę.');
        else
          setError(detail || 'Nie udało się wykonać operacji. Spróbuj ponownie.');
        return;
      }

      setAuth(data.user as AuthUser, data.access_token, data.refresh_token);
      onSuccess();
    } catch {
      setError('Brak połączenia z serwerem. Sprawdź internet i spróbuj ponownie.');
    } finally {
      setLoading(false);
    }
  }

  function switchTab(next: 'login' | 'register') {
    setTab(next);
    setError('');
  }

  return (
    <div className="min-h-screen bg-earth-950 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="w-full max-w-md"
      >
        {/* ── Logo ──────────────────────────────────────────────────── */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 mb-4">
            <span className="text-2xl font-bold text-accent-primary">Y</span>
          </div>
          <h1 className="text-2xl font-bold text-earth-100 tracking-tight">YU-NA</h1>
          <p className="text-earth-500 text-sm mt-1">Platforma zarządzania przetargami budowlanymi</p>
        </div>

        {/* ── Card ──────────────────────────────────────────────────── */}
        <div className="bg-earth-900/60 border border-earth-700/50 rounded-token-xl p-6 backdrop-blur-sm shadow-token-lg">

          {/* Tabs */}
          <div className="flex rounded-token bg-earth-800/50 p-1 mb-6 gap-1">
            {(['login', 'register'] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => switchTab(t)}
                className={[
                  'flex-1 flex items-center justify-center gap-1.5 py-2 rounded-token text-sm font-medium transition-all duration-200',
                  tab === t
                    ? 'bg-accent-primary text-earth-950 shadow-sm'
                    : 'text-earth-400 hover:text-earth-200',
                ].join(' ')}
              >
                {t === 'login'
                  ? <><LogIn    className="w-3.5 h-3.5" /> Logowanie</>
                  : <><UserPlus className="w-3.5 h-3.5" /> Rejestracja</>}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Register-only fields */}
            <AnimatePresence mode="popLayout">
              {tab === 'register' && (
                <motion.div
                  key="register-fields"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-4 overflow-hidden"
                >
                  <div>
                    <label className="label-base">Imię i nazwisko</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      autoComplete="name"
                      placeholder="np. Jan Kowalski"
                      className="input-base"
                    />
                  </div>
                  <div>
                    <label className="label-base">Nazwa firmy</label>
                    <input
                      type="text"
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                      autoComplete="organization"
                      placeholder="np. Kowalski Budownictwo Sp. z o.o."
                      className="input-base"
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* E-mail */}
            <div>
              <label className="label-base">E-mail</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="twoj@firma.pl"
                className="input-base"
              />
            </div>

            {/* Password */}
            <div>
              <label className="label-base">Hasło</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                  placeholder={tab === 'register' ? 'min. 8 znaków' : '••••••••'}
                  className="input-base pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  aria-label={showPassword ? 'Ukryj hasło' : 'Pokaż hasło'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-earth-500 hover:text-earth-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            <AnimatePresence mode="popLayout">
              {error && (
                <motion.div
                  key="error"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="flex items-start gap-2 px-3 py-2.5 bg-accent-danger/10 border border-accent-danger/20 rounded-token text-accent-danger text-sm">
                    <span className="mt-0.5 shrink-0">⚠</span>
                    <span>{error}</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-2.5 mt-2"
            >
              {loading
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : tab === 'login'
                  ? <LogIn className="w-4 h-4" />
                  : <UserPlus className="w-4 h-4" />}
              {tab === 'login' ? 'Zaloguj się' : 'Zarejestruj się'}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-earth-700 text-xs mt-4">
          YU-NA &copy; 2026 — System zarządzania przetargami budowlanymi
        </p>
      </motion.div>
    </div>
  );
}
