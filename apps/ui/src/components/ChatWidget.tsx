'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { MessageCircle, X, Send, Brain, User, RefreshCw } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  streaming?: boolean;
  isError?: boolean;
}

function TypingDots() {
  return (
    <span className="flex items-center gap-1 py-0.5">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-earth-500 animate-pulse"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </span>
  );
}

const STREAM_TIMEOUT_MS = 45_000; // 45 s — poniżej limitu Cloudflare (~60 s)

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'Cześć! Jestem asystentem YU-NA. Możesz zapytać mnie o przetargi, kosztorysy, analizę ryzyka lub jak korzystać z systemu.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [timedOut, setTimedOut] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastUserTextRef = useRef<string>('');

  // Cleanup on unmount — abort any open stream
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 200);
    }
  }, [open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (retryText?: string) => {
    const text = retryText ?? input.trim();
    if (!text || loading) return;

    // Reset state
    if (!retryText) setInput('');
    setTimedOut(false);
    lastUserTextRef.current = text;

    // Abort any previous in-flight request
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', text };
    const assistantId = (Date.now() + 1).toString();
    const assistantMsg: Message = { id: assistantId, role: 'assistant', text: '', streaming: true };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setLoading(true);

    // Kill the stream after STREAM_TIMEOUT_MS — Cloudflare closes it anyway at ~60 s
    const timeoutId = setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS);

    try {
      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
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
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.text) {
                setMessages(prev => prev.map(m =>
                  m.id === assistantId ? { ...m, text: m.text + data.text } : m
                ));
              }
            } catch { /* ignore parse errors */ }
          }
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
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
    }
  };

  const handleRetry = () => {
    const text = lastUserTextRef.current;
    if (!text) return;
    setTimedOut(false);
    sendMessage(text);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.92 }}
            transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
            className="glass-card w-[380px] flex flex-col rounded-2xl border border-earth-800/80 shadow-2xl overflow-hidden"
            style={{ height: '520px', maxHeight: '80vh' }}
          >
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-earth-800/60 bg-earth-900/70 shrink-0">
              <div className="w-8 h-8 rounded-xl bg-accent-primary/20 flex items-center justify-center border border-accent-primary/20">
                <Brain className="w-4 h-4 text-accent-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-earth-100 text-sm font-semibold">Asystent budos</p>
                <p className="text-earth-600 text-xs">
                  {loading ? (
                    <span className="text-accent-primary">Pisze…</span>
                  ) : (
                    'Zawsze online'
                  )}
                </p>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="w-7 h-7 rounded-lg hover:bg-earth-800 flex items-center justify-center transition-colors text-earth-500 hover:text-earth-300"
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
                      ? 'bg-accent-primary/20 border border-accent-primary/20'
                      : 'bg-earth-800 border border-earth-700/40'
                  }`}>
                    {msg.role === 'user'
                      ? <User className="w-3.5 h-3.5 text-accent-primary" />
                      : <Brain className="w-3.5 h-3.5 text-earth-400" />}
                  </div>
                  <div className={`max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-accent-primary/20 text-earth-100 rounded-tr-sm'
                      : msg.isError
                        ? 'bg-red-500/10 text-red-300 rounded-tl-sm border border-red-500/20'
                        : 'bg-earth-800/80 text-earth-200 rounded-tl-sm border border-earth-700/30'
                  }`}>
                    {msg.streaming && !msg.text ? (
                      <TypingDots />
                    ) : (
                      <>
                        {msg.text}
                        {msg.streaming && msg.text && (
                          <span className="inline-block w-0.5 h-3.5 bg-accent-primary ml-0.5 animate-pulse rounded-sm align-middle" />
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            {/* Input + retry bar */}
            <div className="p-3 border-t border-earth-800/60 bg-earth-900/40 shrink-0 space-y-2">
              {/* Retry button — shows when stream was cut */}
              {timedOut && (
                <motion.button
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  onClick={handleRetry}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 py-1.5 rounded-lg bg-accent-warning/10 border border-accent-warning/30 text-accent-warning text-xs font-medium hover:bg-accent-warning/20 transition-colors disabled:opacity-50"
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
                  className="flex-1 px-3 py-2 rounded-xl bg-earth-800 border border-earth-700/60 text-earth-100 text-sm placeholder:text-earth-600 focus:outline-none focus:border-accent-primary/50 disabled:opacity-50 transition-colors"
                />
                <motion.button
                  onClick={() => sendMessage()}
                  disabled={loading || !input.trim()}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="w-9 h-9 rounded-xl bg-accent-primary flex items-center justify-center hover:bg-emerald-400 transition-colors disabled:opacity-40 shrink-0"
                >
                  {loading ? (
                    <div className="w-4 h-4 border-2 border-earth-900 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Send className="w-4 h-4 text-earth-950" />
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
      <motion.button
        onClick={() => setOpen(v => !v)}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20, delay: 0.3 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="w-14 h-14 rounded-full bg-accent-primary shadow-lg shadow-accent-primary/30 flex items-center justify-center hover:bg-emerald-400 transition-colors"
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
              <X className="w-6 h-6 text-earth-950" />
            </motion.div>
          ) : (
            <motion.div
              key="msg"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <MessageCircle className="w-6 h-6 text-earth-950" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    </div>
  );
}
