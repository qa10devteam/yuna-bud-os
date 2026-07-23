'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useStore } from '@/store/useStore';
import type { AuthUser } from '@/store/useStore';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  LogIn,
  Mail,
  UserPlus,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface LoginFormProps {
  onSuccess: () => void;
}

// ── Feature bullets ────────────────────────────────────────────────────────────

const FEATURES = [
  'Scoring AI w 30 sekund',
  'Kosztorys z jednego kliknięcia',
  'Win rate 67% średnio u naszych klientów',
] as const;

// ── Component ──────────────────────────────────────────────────────────────────

export function LoginForm({ onSuccess }: LoginFormProps) {
  const setAuth = useStore((s) => s.setAuth);

  const [tab,           setTab]           = useState<'login' | 'register'>('login');
  const [forgotMode,    setForgotMode]    = useState(false);
  const [forgotEmail,   setForgotEmail]   = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [forgotError,   setForgotError]   = useState('');
  const [email,         setEmail]         = useState('');
  const [password,      setPassword]      = useState('');
  const [showPassword,  setShowPassword]  = useState(false);
  const [name,          setName]          = useState('');
  const [orgName,       setOrgName]       = useState('');
  const [error,         setError]         = useState('');
  const [loading,       setLoading]       = useState(false);

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

      const res = await fetch(endpoint, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        // FastAPI returns { detail: string } or { detail: [{msg, loc, ...}] }
        const raw = data.detail ?? data.message ?? '';
        const detail = typeof raw === 'string'
          ? raw
          : Array.isArray(raw)
            ? (raw as { msg?: string }[]).map(d => {
                const m = d.msg || '';
                // strip Pydantic "Value error, " prefix
                return m.replace(/^Value error,\s*/i, '');
              }).join('\n')
            : String(raw);

        if (res.status === 401 || detail.toLowerCase().includes('invalid') || detail.toLowerCase().includes('nieprawidłow'))
          setError('Nieprawidłowy e-mail lub hasło. Spróbuj ponownie lub zresetuj hasło.');
        else if (res.status === 409 || detail.toLowerCase().includes('exist') || detail.toLowerCase().includes('zarejestrowany'))
          setError('Konto z tym adresem e-mail już istnieje. Zaloguj się lub odzyskaj dostęp.');
        else if (res.status === 422 && detail)
          setError(detail);
        else if (res.status >= 500)
          setError('Problem z serwerem — spróbuj ponownie za chwilę.');
        else
          setError(detail || 'Nie udało się wykonać operacji. Spróbuj ponownie.');
        return;
      }

      setAuth(data.user as AuthUser, data.access_token, data.refresh_token);
      onSuccess();
    } catch (err) {
      // Only network-level errors (fetch itself threw) land here
      const isNetworkErr = err instanceof TypeError && String(err).includes('fetch');
      setError(isNetworkErr
        ? 'Brak połączenia z serwerem. Sprawdź internet i spróbuj ponownie.'
        : 'Wystąpił nieoczekiwany błąd. Spróbuj ponownie.');
    } finally {
      setLoading(false);
    }
  }

  async function handleForgotPassword(e: React.FormEvent) {
    e.preventDefault();
    setForgotLoading(true);
    setForgotError('');
    try {
      const res = await fetch('/api/v2/auth/forgot-password', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email: forgotEmail }),
      });
      if (res.ok) {
        setForgotSuccess(true);
      } else {
        setForgotError('Wystąpił błąd. Spróbuj ponownie.');
      }
    } catch {
      setForgotError('Brak połączenia z serwerem.');
    } finally {
      setForgotLoading(false);
    }
  }

  function switchTab(next: 'login' | 'register') {
    setTab(next);
    setError('');
  }

  return (
    <div
      className="min-h-dvh flex flex-col"
      style={{ backgroundColor: '#080C14' }}
    >
      {/* ── Main split layout ───────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── LEFT PANEL (hidden on mobile) ────────────────────────────── */}
        <div
          className="hidden lg:flex lg:w-[60%] flex-col justify-center px-16 xl:px-24 relative overflow-hidden"
          style={{
            backgroundImage: [
              'radial-gradient(ellipse 80% 60% at 30% 40%, rgba(16,185,129,0.08) 0%, transparent 60%)',
              'linear-gradient(rgba(16,185,129,0.035) 1px, transparent 1px)',
              'linear-gradient(90deg, rgba(16,185,129,0.035) 1px, transparent 1px)',
            ].join(', '),
            backgroundSize: 'auto, 48px 48px, 48px 48px',
          }}
        >
          {/* Subtle vignette on right edge */}
          <div
            className="absolute inset-y-0 right-0 w-32 pointer-events-none"
            style={{
              background: 'linear-gradient(to right, transparent, #080C14)',
            }}
          />

          <motion.div
            initial={{ opacity: 0, x: -24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="relative z-10 max-w-xl"
          >
            {/* Brand pill */}
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/5 mb-10">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-medium text-emerald-400 tracking-wide">YU-NA · BudOS</span>
            </div>

            {/* Main heading */}
            <h1 className="text-4xl xl:text-5xl font-bold text-white leading-tight tracking-tight mb-4">
              Wygrywaj przetargi.{' '}
              <span className="text-emerald-400">Szybciej.</span>
            </h1>

            {/* Subtext */}
            <p className="text-slate-400 text-lg leading-relaxed mb-10 max-w-md">
              YU-NA analizuje 1.4M ogłoszeń BZP i podpowiada gdzie wygrasz.
            </p>

            {/* Feature bullets */}
            <ul className="space-y-4">
              {FEATURES.map((feat) => (
                <li key={feat} className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  <span className="text-slate-300 text-base">{feat}</span>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>

        {/* ── RIGHT PANEL ──────────────────────────────────────────────── */}
        <div className="flex-1 lg:w-[40%] flex flex-col items-center justify-center px-4 py-12 lg:px-10">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="w-full max-w-sm"
          >
            {/* Card */}
            <div className="relative rounded-2xl p-8 border border-slate-700/50 bg-slate-900/80 backdrop-blur-xl shadow-2xl">

              {/* Logo + title */}
              <div className="flex flex-col items-center gap-3 mb-8">
                <img
                  src="/brand/B01-app-icon-budos.png"
                  alt="BudOS"
                  width={48}
                  height={48}
                  className="w-12 h-12 rounded-2xl object-cover"
                  style={{ boxShadow: '0 0 0 1px rgba(16,185,129,0.25), 0 8px 24px rgba(16,185,129,0.12)' }}
                />
                <h2 className="text-xl font-semibold text-white tracking-tight">
                  {tab === 'login' ? 'Zaloguj się' : 'Utwórz konto'}
                </h2>
              </div>

              {/* Tabs */}
              <div className="flex rounded-xl bg-slate-800/60 p-1 mb-6 gap-1">
                {(['login', 'register'] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => switchTab(t)}
                    className={[
                      'flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                      tab === t
                        ? 'bg-emerald-500 text-white shadow-sm shadow-emerald-500/20'
                        : 'text-slate-400 hover:text-slate-200',
                    ].join(' ')}
                  >
                    {t === 'login'
                      ? <><LogIn    className="w-3.5 h-3.5" /> Logowanie</>
                      : <><UserPlus className="w-3.5 h-3.5" /> Rejestracja</>}
                  </button>
                ))}
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">

                {/* Register-only fields */}
                <AnimatePresence mode="popLayout">
                  {tab === 'register' && (
                    <motion.div
                      key="register-fields"
                      initial={{ opacity: 0, scaleY: 0 }}
                      animate={{ opacity: 1, scaleY: 1 }}
                      exit={{ opacity: 0, scaleY: 0 }}
                      transition={{ duration: 0.2 }}
                      style={{ transformOrigin: 'top' }}
                      className="space-y-4 overflow-hidden"
                    >
                      <div>
                        <label className="label-base" htmlFor="reg-name">Imię i nazwisko</label>
                        <input
                          id="reg-name"
                          type="text"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          required
                          autoComplete="name"
                          placeholder="np. Jan Kowalski"
                          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/60 transition-all duration-200"
                        />
                      </div>
                      <div>
                        <label className="label-base" htmlFor="reg-org">Nazwa firmy</label>
                        <input
                          id="reg-org"
                          type="text"
                          value={orgName}
                          onChange={(e) => setOrgName(e.target.value)}
                          autoComplete="organization"
                          placeholder="np. Kowalski Budownictwo Sp. z o.o."
                          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/60 transition-all duration-200"
                        />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* E-mail */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5" htmlFor="auth-email">
                    E-mail
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                    <input
                      id="auth-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      autoComplete="email"
                      placeholder="twoj@firma.pl"
                      className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/60 transition-all duration-200"
                    />
                  </div>
                </div>

                {/* Password */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5" htmlFor="auth-password">
                    Hasło
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                    <input
                      id="auth-password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                      placeholder={tab === 'register' ? 'min. 12 znaków, A, 1, !' : '••••••••'}
                      className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-11 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/60 transition-all duration-200"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((p) => !p)}
                      aria-label={showPassword ? 'Ukryj hasło' : 'Pokaż hasło'}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
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
                      initial={{ opacity: 0, scaleY: 0 }}
                      animate={{ opacity: 1, scaleY: 1 }}
                      exit={{ opacity: 0, scaleY: 0 }}
                      transition={{ duration: 0.2 }}
                      style={{ transformOrigin: 'top' }}
                      className="overflow-hidden"
                    >
                      <div className="flex items-start gap-2 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                        <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                        <span>{error}</span>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Submit */}
                <button
                  type="submit"
                  disabled={loading}
                  className="flex items-center justify-center gap-2 w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold rounded-xl py-3 text-sm transition-all duration-200 shadow-lg shadow-emerald-500/20 mt-1"
                >
                  {loading
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : tab === 'login'
                      ? <LogIn className="w-4 h-4" />
                      : <UserPlus className="w-4 h-4" />}
                  {tab === 'login' ? 'Zaloguj się' : 'Zarejestruj się'}
                </button>

                {/* Forgot password link */}
                {tab === 'login' && (
                  <button
                    type="button"
                    onClick={() => {
                      setForgotMode(true);
                      setForgotEmail(email);
                      setForgotSuccess(false);
                      setForgotError('');
                    }}
                    className="w-full text-center text-sm text-slate-500 hover:text-emerald-400 transition-colors mt-1"
                  >
                    Zapomniałeś hasła?
                  </button>
                )}
              </form>

              {/* ── Forgot password overlay ──────────────────────────────── */}
              <AnimatePresence>
                {forgotMode && (
                  <motion.div
                    key="forgot-overlay"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0 z-20 flex items-center justify-center bg-slate-900/90 backdrop-blur-sm rounded-2xl"
                  >
                    <div className="w-full max-w-sm p-6">
                      {forgotSuccess ? (
                        <div className="text-center space-y-3">
                          <div className="w-12 h-12 mx-auto rounded-full bg-emerald-500/15 flex items-center justify-center">
                            <Mail className="w-6 h-6 text-emerald-400" />
                          </div>
                          <h3 className="text-lg font-semibold text-slate-100">Sprawdź skrzynkę</h3>
                          <p className="text-slate-400 text-sm">
                            Jeśli konto istnieje, wysłaliśmy link do resetowania hasła.
                          </p>
                          <button
                            type="button"
                            onClick={() => setForgotMode(false)}
                            className="w-full bg-emerald-500 hover:bg-emerald-400 text-white font-semibold rounded-xl py-2.5 text-sm transition-all duration-200 mt-4"
                          >
                            Wróć do logowania
                          </button>
                        </div>
                      ) : (
                        <form onSubmit={handleForgotPassword} className="space-y-4">
                          <button
                            type="button"
                            onClick={() => setForgotMode(false)}
                            className="flex items-center gap-1 text-slate-500 hover:text-slate-300 text-sm transition-colors"
                          >
                            <ArrowLeft className="w-3.5 h-3.5" /> Wróć
                          </button>
                          <h3 className="text-lg font-semibold text-slate-100">Odzyskaj dostęp</h3>
                          <p className="text-slate-400 text-sm">
                            Podaj adres e-mail powiązany z kontem.
                          </p>
                          <div className="relative">
                            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                            <input
                              type="email"
                              value={forgotEmail}
                              onChange={(e) => setForgotEmail(e.target.value)}
                              required
                              autoFocus
                              aria-label="Adres e-mail do odzyskania hasła"
                              placeholder="twoj@firma.pl"
                              className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/60 transition-all duration-200"
                            />
                          </div>
                          {forgotError && (
                            <div className="flex items-start gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                              <span>{forgotError}</span>
                            </div>
                          )}
                          <button
                            type="submit"
                            disabled={forgotLoading}
                            className="flex items-center justify-center gap-2 w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold rounded-xl py-2.5 text-sm transition-all duration-200"
                          >
                            {forgotLoading
                              ? <Loader2 className="w-4 h-4 animate-spin" />
                              : <Mail className="w-4 h-4" />}
                            Wyślij link resetujący
                          </button>
                        </form>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </div>
      </div>

      {/* ── Bottom bar ──────────────────────────────────────────────────── */}
      <div className="py-4 text-center">
        <p className="text-slate-600 text-xs">
          YU-NA BudOS &copy; 2026 &middot; yu-na.io
        </p>
      </div>
    </div>
  );
}
