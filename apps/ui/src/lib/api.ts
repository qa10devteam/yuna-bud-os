'use client';

import { useState, useEffect } from 'react';
import { useStore } from '@/store/useStore';

// ── API Base — uses relative path so it works through any proxy ──────────────
const API_BASE = '';

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
  const accessToken = useStore((s) => s.accessToken);

  useEffect(() => {
    let cancelled = false;
    async function fetchStats() {
      setIsLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/v1/tenders?limit=50`, {
          headers: {
            'Content-Type': 'application/json',
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        const tenders: TenderItem[] = json.items || [];
        if (!cancelled) {
          const pipelineCounts = tenders.reduce((acc, t) => {
            acc[t.status] = (acc[t.status] || 0) + 1;
            return acc;
          }, {} as Record<string, number>);
          
          setData({
            activeTenders: tenders.length,
            totalValue: tenders.reduce((s, t) => s + (t.value_pln || 0), 0),
            avgScore: tenders.length > 0
              ? Math.round(tenders.reduce((s, t) => s + (t.match_score || 0), 0) / tenders.length * 100)
              : 0,
            redFlags: pipelineCounts['decided_nogo'] || 0,
            pipelineCounts,
            recentTenders: tenders.slice(0, 5),
          });
        }
      } catch (e: unknown) {
        if (!cancelled) setError((e as Error).message || 'Failed to load stats');
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
        const res = await fetch(`${API_BASE}/api/v1/tenders?${params}`, {
          headers: {
            'Content-Type': 'application/json',
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) {
          setData(json.items || []);
          setTotal(json.total || 0);
        }
      } catch (e: unknown) {
        if (!cancelled) setError((e as Error).message || 'Failed to load tenders');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    fetchTenders();
    return () => { cancelled = true; };
  }, [statusFilter, accessToken]);

  return { data, total, isLoading, error };
}

