'use client';

import { useState, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { showToast } from '@/components/Toast';

// ── API Base — uses relative path so it works through any proxy ──────────────
const API_BASE = '';

// ── Retry helper — exponential backoff, 3 attempts (S6-4) ────────────────────
const RETRY_DELAYS = [200, 600, 1800]; // ms: 0.2s → 0.6s → 1.8s

async function withRetry<T>(fn: () => Promise<T>, maxAttempts = 3): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (err: unknown) {
      lastError = err;
      // Don't retry on auth errors (handled by caller) or if aborted
      if (err instanceof Error && (err.name === 'AbortError')) throw err;
      if (attempt < maxAttempts - 1) {
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAYS[attempt]));
      }
    }
  }
  throw lastError;
}

// ── Auth-aware fetch helper (auto-refresh on 401 + retry backoff) ─────────────
async function authFetchRaw(url: string, accessToken: string | null, refreshToken: string | null, setAuth: any, clearAuth: any): Promise<Response> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;

  // Retry on network errors only (not on HTTP error codes)
  let res = await withRetry(() => fetch(`${API_BASE}${url}`, { headers }));

  if (res.status === 401 && refreshToken) {
    const refreshRes = await fetch(`${API_BASE}/api/v2/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (refreshRes.ok) {
      const tokens = await refreshRes.json();
      setAuth(tokens.access_token, tokens.refresh_token || refreshToken);
      headers['Authorization'] = `Bearer ${tokens.access_token}`;
      res = await withRetry(() => fetch(`${API_BASE}${url}`, { headers }));
    } else {
      clearAuth();
    }
  }
  return res;
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface TenderItem {
  id: string;
  title: string;
  buyer: string | null;
  cpv: string[];
  voivodeship: string | null;
  value_pln: number | null;
  deadline_at: string | null;
  status: string;
  match_score: number;
  match_reason: string | null;
  source: string | null;
}

export interface DashboardStats {
  activeTenders: number;
  totalValue: number;
  avgScore: number;
  redFlags: number;
  pipelineCounts: Record<string, number>;
  recentTenders: TenderItem[];
}

export interface ActivityItem {
  id: string;
  action: string;
  timestamp: string;
  type: 'tender' | 'estimate' | 'decision' | 'alert';
}

// ── Auth helper — reads token from Zustand store ──────────────────────────────

// ── Dashboard Stats (derived from tenders) ───────────────────────────────────

export function useDashboardStats() {
  const [data, setData] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { accessToken, refreshToken, setAuth, clearAuth } = useStore();

  useEffect(() => {
    let cancelled = false;
    async function fetchStats() {
      setIsLoading(true);
      try {
        // Pobierz zagregowane statystyki z dedykowanego endpointu
        const res = await authFetchRaw('/api/v2/dashboard/stats', accessToken, refreshToken, setAuth, clearAuth);
        if (!res.ok) {
          const msg = `Błąd ładowania statystyk (HTTP ${res.status})`;
          showToast('error', msg);
          throw new Error(msg);
        }
        const json = await res.json();

        // Pobierz ostatnie przetargi osobno
        const tendersRes = await authFetchRaw('/api/v2/tenders?limit=5&sort=created_at', accessToken, refreshToken, setAuth, clearAuth);
        const tendersJson = tendersRes.ok ? await tendersRes.json() : { items: json.top_tenders ?? [] };
        const recentTenders: TenderItem[] = tendersJson.items ?? json.top_tenders ?? [];

        if (!cancelled) {
          setData({
            activeTenders: json.total_tenders ?? 0,
            totalValue: json.pipeline_value ?? 0,
            avgScore: json.avg_score != null ? Math.round(json.avg_score * 100) : 0,
            redFlags: json.high_score_count ?? 0,
            pipelineCounts: json.by_source ?? {},
            recentTenders,
          });
        }
      } catch (e: unknown) {
        if (!cancelled) {
          const msg = (e as Error).message || 'Błąd ładowania statystyk';
          setError(msg);
          // showToast only for network errors (HTTP errors already toasted above)
          if (!msg.startsWith('Błąd ładowania')) showToast('error', msg);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    fetchStats();
    return () => { cancelled = true; };
  }, [accessToken]);

  return { data, isLoading, error };
}

// ── Tenders ──────────────────────────────────────────────────────────────────

export function useTenders(statusFilter?: string) {
  const [data, setData] = useState<TenderItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const accessToken = useStore((s) => s.accessToken);

  useEffect(() => {
    let cancelled = false;
    async function fetchTenders() {
      setIsLoading(true);
      try {
        const params = new URLSearchParams({ limit: '50' });
        if (statusFilter) params.set('status', statusFilter);
        const res = await fetch(`${API_BASE}/api/v2/tenders?${params}`, {
          headers: {
            'Content-Type': 'application/json',
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          },
        });
        if (!res.ok) {
          const msg = `Błąd ładowania przetargów (HTTP ${res.status})`;
          showToast('error', msg);
          throw new Error(msg);
        }
        const json = await res.json();
        if (!cancelled) {
          setData(json.items || []);
          setTotal(json.total || 0);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          const msg = (e as Error).message || 'Błąd ładowania przetargów';
          setError(msg);
          if (!msg.startsWith('Błąd ładowania')) showToast('error', msg);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    fetchTenders();
    return () => { cancelled = true; };
  }, [statusFilter, accessToken]);

  return { data, total, isLoading, error };
}

