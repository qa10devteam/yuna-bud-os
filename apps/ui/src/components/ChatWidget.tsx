'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { MessageCircle, X, Send, Brain, User, RefreshCw } from 'lucide-react';
import { useStore } from '@/store/useStore';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  streaming?: boolean;
  isError?: boolean;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const STREAM_TIMEOUT_MS = 45_000;
const CHAT_HISTORY_KEY = 'terra_chat_history';
const MAX_HISTORY = 10;

// ── Quick-reply suggestions by page context ───────────────────────────────────

function getQuickReplies(pathname: string): string[] {
  if (pathname.startsWith('/zwiad')) {
    return ['Pokaż top przetargi', 'Filtruj po CPV', 'Analiza deadline'];
  }
  if (pathname.startsWith('/kosztorys')) {
    return ['Oceń kosztorys', 'Szukaj w KNR', 'Porównaj z ICB'];
  }
  if (pathname.startsWith('/dashboard')) {
    return ['Podsumuj dzień', 'Top 5 przetargów', 'Alerty'];
  }
  return ['Jak zacząć?', 'Co to jest CPV?', 'Pomoc'];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function loadHistory(): Message[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(CHAT_HISTORY_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as Message[];
  } catch {
    return [];
  }
}

function saveHistory(messages: Message[]) {
  if (typeof window === 'undefined') return;
  try {
    // Keep only non-streaming, non-error messages (stable state), last MAX_HISTORY
    const stable = messages
      .filter(m => !m.streaming)
      .slice(-MAX_HISTORY);
    localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(stable));
  } catch { /* ignore quota errors */ }
}

function getToken(accessToken: string | null): string | null {
  if (accessToken) return accessToken;
  if (typeof window === 'undefined') return null;
  // Fallback: try several localStorage key names used in the project
  return (
    localStorage.getItem('terra_token') ||
    localStorage.getItem('token') ||
    localStorage.getItem('auth_token') ||
    null
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function TypingDots() {
  return (
    <span className="flex items-center gap-1 py-0.5">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-pulse"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </span>
  );
}

interface QuickRepliesProps {
  suggestions: string[];
  onSelect: (text: string) => void;
  disabled: boolean;
}

function QuickReplies({ suggestions, onSelect, disabled }: QuickRepliesProps) {
  return (
    <div className="flex flex-wrap gap-1.5 px-3 pb-2">
      {suggestions.map(s => (
        <button type="button"
          key={s}
          onClick={() => onSelect(s)}
          disabled={disabled}
          className="px-2.5 py-1 rounded-lg bg-ink-800/70 border border-ink-700/50 text-slate-300 text-xs
                     hover:bg-em/15 hover:border-em/40 hover:text-slate-100
                     transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {s}
        </button>
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

const WELCOME_MSG: Message = {
  id: 'welcome',
  role: 'assistant',
  text: 'Cześć! Jestem asystentem YU-NA. Możesz zapytać mnie o przetargi, kosztorysy, analizę ryzyka lub jak korzystać z systemu.',
};

export function ChatWidget() {
  const { accessToken } = useStore();

  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>(() => {
    const history = loadHistory();
    return history.length > 0 ? history : [WELCOME_MSG];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [timedOut, setTimedOut] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [pathname, setPathname] = useState('/');

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastUserTextRef = useRef<string>('');
  const accessTokenRef = useRef<string | null>(accessToken);
  useEffect(() => { accessTokenRef.current = accessToken; }, [accessToken]);

  // Capture pathname client-side (window is only available in browser)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setPathname(window.location.pathname);
    }
  }, [open]); // re-read on open in case of SPA navigation

  // Cleanup on unmount — abort any open stream
  useEffect(() => {
    return () => { abortControllerRef.current?.abort(); };
  }, []);

  useEffect(() => {
    if (open) {
      const t = setTimeout(() => inputRef.current?.focus(), 200);
      return () => clearTimeout(t);
    }
  }, [open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Persist to localStorage whenever messages change (stable state only)
  useEffect(() => {
    saveHistory(messages);
  }, [messages]);

  // ── Session management ──────────────────────────────────────────────────────

  const ensureSession = useCallback(async (pageContext: string): Promise<string> => {
    if (sessionId) return sessionId;

    const token = getToken(accessTokenRef.current);
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch('/api/v2/chat/sessions', {
      method: 'POST',
      headers,
      body: JSON.stringify({ page_context: pageContext }),
    });

    if (!res.ok) throw new Error(`Session creation failed: ${res.status}`);
    const data = await res.json();
    const sid: string = data.session_id;
    setSessionId(sid);
    return sid;
  }, [sessionId]);

  // ── Send message with SSE streaming ────────────────────────────────────────

  const sendMessage = useCallback(async (retryText?: string) => {
    const text = retryText ?? input.trim();
    if (!text || loading) return;

    if (!retryText) setInput('');
    setTimedOut(false);
    lastUserTextRef.current = text;

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const currentPath = typeof window !== 'undefined' ? window.location.pathname : pathname;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', text };
    const assistantId = (Date.now() + 1).toString();
    const assistantMsg: Message = { id: assistantId, role: 'assistant', text: '', streaming: true };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setLoading(true);

    const timeoutId = setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS);

    try {
      const token = getToken(accessTokenRef.current);
      const authHeaders: Record<string, string> = {};
      if (token) authHeaders['Authorization'] = `Bearer ${token}`;

      // Ensure we have a session
      const sid = await ensureSession(currentPath);

      const res = await fetch(`/api/v2/chat/sessions/${sid}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify({
          message: text,
          page_context: currentPath,
          stream: true,
        }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) throw new Error(`Błąd ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            // Backend sends {type: "token", content: "..."} or {type: "done"} or {type: "error"}
            if (data.type === 'token' && data.content) {
              setMessages(prev => prev.map(m =>
                m.id === assistantId ? { ...m, text: m.text + data.content } : m
              ));
            } else if (data.type === 'error') {
              setMessages(prev => prev.map(m =>
                m.id === assistantId
                  ? { ...m, text: data.message || 'Błąd AI — spróbuj ponownie.', streaming: false, isError: true }
                  : m
              ));
              return;
            }
            // {type: "done"} — stream finished, handled below
          } catch { /* ignore parse errors */ }
        }
      }

      // Stream finished normally
      setMessages(prev => prev.map(m =>
        m.id === assistantId ? { ...m, streaming: false } : m
      ));

    } catch (e: unknown) {
      const wasAborted = controller.signal.aborted;
      const errorMsg = wasAborted
        ? 'Przerwano — przekroczono limit czasu połączenia. Spróbuj ponownie.'
        : (e instanceof Error ? `Błąd połączenia: ${e.message}` : 'Nieznany błąd połączenia.');

      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, text: errorMsg, streaming: false, isError: true }
          : m
      ));

      if (wasAborted) setTimedOut(true);
      // Reset session on error so next message creates a fresh one
      if (!wasAborted) setSessionId(null);
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, input, ensureSession, pathname]);

  const handleRetry = () => {
    const text = lastUserTextRef.current;
    if (!text) return;
    setTimedOut(false);
    sendMessage(text);
  };

  const handleQuickReply = useCallback((text: string) => {
    if (loading) return;
    sendMessage(text);
  }, [loading, sendMessage]);

  const quickReplies = getQuickReplies(pathname);

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.92 }}
            transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
            className="glass-card w-[380px] flex flex-col rounded-2xl border border-ink-800/80 shadow-2xl overflow-hidden"
            style={{ height: '540px', maxHeight: '80vh' }}
          >
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-ink-800/60 bg-ink-900/70 shrink-0">
              <div className="w-8 h-8 rounded-xl overflow-hidden shrink-0" style={{ boxShadow: '0 0 0 1px rgba(16,185,129,0.25)' }}>
                <img src="/brand/B01-app-icon-budos.png" alt="BudOS" className="w-full h-full object-cover" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-slate-100 text-sm font-semibold">Asystent YU-NA</p>
                <p className="text-slate-600 text-xs">
                  {loading ? (
                    <span className="text-em">Pisze…</span>
                  ) : (
                    'Zawsze online'
                  )}
                </p>
              </div>
              <button type="button"
                onClick={() => setOpen(false)}
                className="w-7 h-7 rounded-lg hover:bg-ink-800 flex items-center justify-center transition-colors text-slate-500 hover:text-slate-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map(msg => (
                <div key={msg.id} className={`flex gap-2.5 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                    msg.role === 'user'
                      ? 'bg-em/20 border border-em/20'
                      : 'bg-ink-800 border border-ink-700/40'
                  }`}>
                    {msg.role === 'user'
                      ? <User className="w-3.5 h-3.5 text-em" />
                      : <Brain className="w-3.5 h-3.5 text-slate-400" />}
                  </div>
                  <div className={`max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-em/20 text-slate-100 rounded-tr-sm'
                      : msg.isError
                        ? 'bg-nogo/10 text-nogo rounded-tl-sm border border-nogo-brd'
                        : 'bg-ink-800/80 text-slate-200 rounded-tl-sm border border-ink-700/30'
                  }`}>
                    {msg.streaming && !msg.text ? (
                      <TypingDots />
                    ) : (
                      <>
                        {msg.text}
                        {msg.streaming && msg.text && (
                          <span className="inline-block w-0.5 h-3.5 bg-em ml-0.5 animate-pulse rounded-sm align-middle" />
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            {/* Quick-reply suggestions (visible when not loading) */}
            {!loading && (
              <QuickReplies
                suggestions={quickReplies}
                onSelect={handleQuickReply}
                disabled={loading}
              />
            )}

            {/* Input + retry bar */}
            <div className="px-3 pb-3 border-t border-ink-800/60 bg-ink-900/40 shrink-0 space-y-2 pt-2">
              {/* Retry button — shows when stream was cut */}
              {timedOut && (
                <motion.button
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  onClick={handleRetry}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 py-1.5 rounded-lg bg-warn/10 border border-warn/30 text-warn text-xs font-medium hover:bg-warn/20 transition-colors disabled:opacity-50"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Spróbuj ponownie
                </motion.button>
              )}

              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                  placeholder="Zadaj pytanie…"
                  disabled={loading}
                  className="flex-1 px-3 py-2 rounded-xl bg-ink-800 border border-ink-700/60 text-slate-100 text-sm placeholder:text-slate-600 focus:outline-none focus:border-em/50 disabled:opacity-50 transition-colors"
                />
                <motion.button
                  onClick={() => sendMessage()}
                  disabled={loading || !input.trim()}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="w-9 h-9 rounded-xl bg-em flex items-center justify-center hover:bg-em transition-colors disabled:opacity-40 shrink-0"
                >
                  {loading ? (
                    <div className="w-4 h-4 border-2 border-ink-900 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Send className="w-4 h-4 text-ink-950" />
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      {/* Floating toggle button */}
      <motion.button
        onClick={() => setOpen(v => !v)}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20, delay: 0.3 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="w-14 h-14 rounded-full bg-em shadow-lg shadow-em/30 flex items-center justify-center hover:bg-em transition-colors"
        aria-label="Otwórz asystenta"
      >
        <AnimatePresence mode="wait">
          {open ? (
            <motion.div
              key="x"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <X className="w-6 h-6 text-ink-950" />
            </motion.div>
          ) : (
            <motion.div
              key="msg"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <MessageCircle className="w-6 h-6 text-ink-950" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    </div>
  );
}
