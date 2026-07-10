'use client';

import { useState, useEffect, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { showToast } from '@/components/Toast';

// ── Retry helper — exponential backoff (S6-4) ─────────────────────────────────
const RETRY_DELAYS_V2 = [200, 600, 1800]; // ms

async function retryFetch(fn: () => Promise<Response>, maxAttempts = 3): Promise<Response> {
  let lastErr: unknown;
  for (let i = 0; i < maxAttempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (err instanceof Error && err.name === 'AbortError') throw err;
      if (i < maxAttempts - 1) {
        await new Promise(r => setTimeout(r, RETRY_DELAYS_V2[i]));
      }
    }
  }
  throw lastErr;
}

// ── Base fetch ────────────────────────────────────────────────────────────────

export function useAuthFetch() {
  const { accessToken, refreshToken, setAuth, clearAuth } = useStore();
  return useCallback(
    async (url: string, opts: RequestInit = {}) => {
      const doFetch = async (token: string | null) => {
        return retryFetch(() => fetch(url, {
          ...opts,
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(opts.headers || {}),
          },
        }));
      };

      let res = await doFetch(accessToken);

      // Auto-refresh on 401
      if (res.status === 401 && refreshToken) {
        try {
          const refreshRes = await fetch('/api/v2/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });
          if (refreshRes.ok) {
            const data = await refreshRes.json();
            const { useStore: getStore } = await import('@/store/useStore');
            const state = getStore.getState();
            state.setAuth(state.user!, data.access_token, data.refresh_token);
            // Retry with new token
            res = await doFetch(data.access_token);
          } else {
            clearAuth();
            throw new Error('Sesja wygasła. Zaloguj się ponownie.');
          }
        } catch (e: unknown) {
          const msg = (e as Error).message || '';
          if (msg.includes('Sesja wygasła') || msg.includes('Session expired')) throw e as Error;
          clearAuth();
          throw new Error('Sesja wygasła. Zaloguj się ponownie.');
        }
      }

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        const msg = errBody?.detail || `Błąd API (HTTP ${res.status})`;
        showToast('error', msg);
        throw new Error(msg);
      }
      return res.json();
    },
    [accessToken, refreshToken, setAuth, clearAuth],
  );
}


// ── Types ─────────────────────────────────────────────────────────────────────

export interface IntelSummary {
  cpv_prefix: string | null;
  kpi: {
    n_tenders: number;
    total_value_mln: number;
    avg_value: number;       // raw PLN
    avg_competition: number;
  };
  top_province: { province: string; n: number }[];  // backend returns objects
  last_quarter: string;
  quarterly_trend: 'up' | 'down' | 'stable';
}

export interface TrendRow {
  quarter: string;
  cpv3: string;
  n_tenders: number;
  n_completed: number;
  total_value: number;       // raw PLN from backend
  avg_value: number;         // raw PLN from backend
  avg_competition: number;   // backend field name
}

export interface TrendResponse {
  data: TrendRow[];
  total: number;
}

export interface BenchmarkRow {
  cpv5: string;
  province: string | null;
  quarter: string;
  n_tenders: number;
  n_won: number;
  avg_value: number;
  median_value: number;
  min_value: number;
  max_value: number;
  avg_offers: number;
}

export interface BenchmarkResponse {
  data: BenchmarkRow[];
  total: number;
}

export interface ContractorTop {
  contractor_name: string;
  nip: string;               // backend field (not contractor_nip)
  wins: number;
  total_value: number;       // raw PLN from backend
  avg_value: number;         // raw PLN from backend
  win_rate_pct: number;      // backend field (not win_rate)
  avg_competition: number;   // backend field (not avg_offers)
}

export interface BuyerTop {
  buyer_name: string | null; // backend field (not buyer)
  buyer_nip: string;
  n_tenders: number;         // backend field (not total_tenders)
  total_value: number;       // raw PLN from backend
  avg_value: number;         // raw PLN from backend
  cpv_diversity: number;
}

export interface InflationRow {
  yr: number;                // backend field (not year)
  q: number;                 // backend field (not quarter)
  // quarter_label is derived in the hook: `Q{q} {yr}`
  category: string;
  typ_rms: string;
  avg_price: number;
  yoy_pct: number | null;
  qoq_pct: number | null;
}

export interface FTSResult {
  id: string;
  title: string;
  buyer_nip: string | null;
  buyer: string | null;      // backend field (not buyer_name)
  cpv_code: string | null;
  province: string | null;
  estimated_value: number | null;
  date: string | null;
  procedure_result: string | null;
  rank: number;
}

// Win-rates
export interface WinRateRow {
  contractor_name: string;
  wins: number;
  avg_value_pln: number | null;
  cpvs: string[];
}

export interface WinRatesResponse {
  cpv_prefix: string;
  data: WinRateRow[];
  total: number;
}

// Top buyers per CPV
export interface TopBuyerCpvRow {
  buyer: string;
  tenders: number;
  avg_value_pln: number | null;
  cpvs: string[];
}

export interface TopBuyersCpvResponse {
  cpv_prefix: string;
  data: TopBuyerCpvRow[];
  total: number;
}

// Alerts
export interface TenderAlert {
  id: string;
  name: string;
  cpv_prefixes: string[];
  keywords: string[];
  buyer_nips: string[];
  province: string | null;
  value_min: number | null;
  value_max: number | null;
  frequency: string;
  channel: string;
  is_active: boolean;
  match_count: number;
  created_at: string;
}

export interface AlertCreateBody {
  name: string;
  cpv_prefixes?: string[];
  keywords?: string[];
  buyer_nips?: string[];
  province?: string;
  value_min?: number;
  value_max?: number;
  frequency: 'realtime' | 'daily' | 'weekly';
  channel: 'email' | 'webhook' | 'push';
  webhook_url?: string;
}

// Bookmarks
export interface TenderBookmark {
  id: string;
  ht_id: string | null;
  tender_id: string | null;
  stage: string;
  priority: number;
  notes: string | null;
  tags: string[];
  due_date: string | null;
  created_at: string;
  updated_at: string;
  // enriched
  title: string | null;
  buyer_nip: string | null;
  buyer_name: string | null;
  cpv_code: string | null;
  estimated_value: number | null;
  date: string | null;
}

export interface BookmarkStats {
  stats: Array<{ stage: string; count: number; overdue: number }>;
}

// Competitors
export interface CompetitorWatch {
  id: string;
  competitor_nip: string;
  competitor_name: string | null;
  added_at: string;
  created_at: string;
  notes: string | null;
  tags: string[];
  notify_on_win: boolean;
  // enriched from atlas_contractors (may be null if NIP not in atlas)
  total_wins: number | null;
  total_value: number | null;
  win_rate: number | null;
  top_cpv: Record<string, number> | null;
  city: string | null;
  province: string | null;
}

export interface CompetitorIntel {
  nip: string;
  // flat fields (from profile object in API response)
  name: string | null;
  city: string | null;
  province: string | null;
  total_wins: number;
  total_value: number;
  win_rate: number;
  top_cpv: Record<string, number> | null;
  // arrays
  cpv_breakdown: Array<{ cpv5: string; wins: number; avg_value: number; total_value: number }>;
  region_breakdown: Array<{ province: string; wins: number; avg_value: number; total_value: number }>;
  recent_wins: Array<{
    win_date: string;
    title: string;
    buyer_name: string | null;
    value: number | null;
    cpv5: string | null;
    tender_province: string | null;
    ht_id: string | null;
  }>;
}

// Buyer CRM
export interface BuyerCRM {
  id: string;
  buyer_nip: string;
  crm_stage: string;
  priority: number;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  notes: string | null;
  annual_budget_est: number | null;
  territory: string | null;
  last_contact: string | null;
  next_followup: string | null;
  created_at: string;
  updated_at: string;
  buyer_name: string | null;
  buyer_city: string | null;
  buyer_province: string | null;
  total_tenders: number | null;
}

export interface Followup {
  id: string;
  buyer_nip: string;
  buyer_name: string | null;
  crm_stage: string;
  next_followup: string;
  contact_name: string | null;
  contact_phone: string | null;
  notes: string | null;
}

// ── Market Intelligence hooks ─────────────────────────────────────────────────

export function useIntelSummary(cpv_prefix?: string) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<IntelSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams();
    if (cpv_prefix) params.set('cpv_prefix', cpv_prefix);
    fetch(`/api/v2/intelligence/summary?${params}`)
      .then(d => { if (!cancelled) setData(d); })
      .catch(e => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, cpv_prefix]);

  return { data, loading, error };
}

export function useIntelTrends(cpv_prefix?: string, quarters = 8, province?: string) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<TrendRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams({ quarters: String(quarters) });
    if (cpv_prefix) params.set('cpv_prefix', cpv_prefix);
    if (province) params.set('province', province);
    fetch(`/api/v2/intelligence/trends?${params}`)
      .then((d: TrendResponse) => { if (!cancelled) setData(d.data || []); })
      .catch(e => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, cpv_prefix, quarters, province]);

  return { data, loading, error };
}

export function useCompetitorsTop(cpv_prefix?: string, province?: string, limit = 15) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<ContractorTop[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams({ limit: String(limit) });
    if (cpv_prefix) params.set('cpv_prefix', cpv_prefix);
    if (province) params.set('province', province);
    fetch(`/api/v2/intelligence/competitors/top?${params}`)
      .then((d: { data: ContractorTop[] }) => { if (!cancelled) setData(d.data || []); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, cpv_prefix, province, limit]);

  return { data, loading };
}

export function useBuyersTop(cpv_prefix?: string, province?: string, limit = 15) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<BuyerTop[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams({ limit: String(limit) });
    if (cpv_prefix) params.set('cpv_prefix', cpv_prefix);
    if (province) params.set('province', province);
    fetch(`/api/v2/intelligence/buyers/top?${params}`)
      .then((d: { data: BuyerTop[] }) => { if (!cancelled) setData(d.data || []); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, cpv_prefix, province, limit]);

  return { data, loading };
}

export function useInflation(category?: string, typ_rms?: string) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<(InflationRow & { quarter_label: string })[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams({ limit: '80' });
    if (category) params.set('category', category);
    if (typ_rms) params.set('typ_rms', typ_rms);
    fetch(`/api/v2/intelligence/prices/inflation?${params}`)
      .then((d: { data: InflationRow[] }) => {
        if (!cancelled) {
          // derive quarter_label from backend's yr/q fields
          const rows = (d.data || []).map(r => ({ ...r, quarter_label: `Q${r.q} ${r.yr}` }));
          setData(rows);
        }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, category, typ_rms]);

  return { data, loading };
}

export function useFTS(q: string) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<FTSResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!q || q.length < 3) { setData([]); return; }
    let cancelled = false;
    setLoading(true);
    const params = new URLSearchParams({ q, limit: '20' });
    fetch(`/api/v2/intelligence/fts?${params}`)
      .then((d: { items?: FTSResult[]; data?: FTSResult[]; total?: number }) => {
        if (!cancelled) { setData(d.items || d.data || []); setTotal(d.total || 0); }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, q]);

  return { data, loading, total };
}

export function useWinRates(cpv_prefix: string, limit = 20) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<WinRateRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!cpv_prefix || cpv_prefix.length < 2) { setData([]); return; }
    let cancelled = false;
    setLoading(true);
    const params = new URLSearchParams({ cpv_prefix, limit: String(limit) });
    fetch(`/api/v2/intelligence/win-rates?${params}`)
      .then((d: WinRatesResponse) => {
        if (!cancelled) { setData(d.data || []); setTotal(d.total || 0); }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, cpv_prefix, limit]);

  return { data, loading, total };
}

export function useTopBuyersCpv(cpv_prefix: string, limit = 20) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<TopBuyerCpvRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!cpv_prefix || cpv_prefix.length < 2) { setData([]); return; }
    let cancelled = false;
    setLoading(true);
    const params = new URLSearchParams({ cpv_prefix, limit: String(limit) });
    fetch(`/api/v2/intelligence/top-buyers-cpv?${params}`)
      .then((d: TopBuyersCpvResponse) => {
        if (!cancelled) { setData(d.data || []); setTotal(d.total || 0); }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, cpv_prefix, limit]);

  return { data, loading, total };
}

// Seasonality
export interface SeasonalityRow {
  month: number;
  n_tenders: number;
  avg_value: number;
  total_value: number;
  avg_competition: number;
}

export interface SeasonalityResponse {
  data: SeasonalityRow[];
}

export function useSeasonality(cpv_prefix?: string) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<SeasonalityRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams();
    if (cpv_prefix) params.set('cpv_prefix', cpv_prefix);
    fetch(`/api/v2/intelligence/seasonality?${params}`)
      .then((d: SeasonalityResponse) => { if (!cancelled) setData(d.data || []); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, cpv_prefix]);

  return { data, loading };
}

// ── Alerts hooks ──────────────────────────────────────────────────────────────

export function useAlerts() {
  const fetch = useAuthFetch();
  const [data, setData] = useState<TenderAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  const reload = useCallback(() => {
    setLoading(true);
    fetch('/api/v2/alerts')
      .then((d: { alerts: TenderAlert[]; alert_count: number }) => {
        setData(d.alerts || []);
        setTotal(d.alert_count || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [fetch]);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (body: AlertCreateBody) => {
    const res = await fetch('/api/v2/alerts', { method: 'POST', body: JSON.stringify(body) });
    reload();
    return res;
  }, [fetch, reload]);

  const toggle = useCallback(async (id: string, _is_active: boolean) => {
    // Backend uses POST /alerts/{id}/toggle (not PATCH)
    await fetch(`/api/v2/alerts/${id}/toggle`, { method: 'PATCH' });
    reload();
  }, [fetch, reload]);

  const remove = useCallback(async (id: string) => {
    await fetch(`/api/v2/alerts/${id}`, { method: 'DELETE' });
    reload();
  }, [fetch, reload]);

  return { data, loading, total, reload, create, toggle, remove };
}

// ── Bookmarks hooks ───────────────────────────────────────────────────────────

export function useBookmarks(stage?: string) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<TenderBookmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<BookmarkStats['stats']>([]);

  const reload = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({ limit: '100' });
    if (stage) params.set('stage', stage);
    Promise.all([
      fetch(`/api/v2/bookmarks?${params}`),
      fetch('/api/v2/bookmarks/stats'),
    ])
      .then(([items, statsRes]) => {
        setData(items.items || []);
        setTotal(items.total || 0);
        setStats(statsRes.stats || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [fetch, stage]);

  useEffect(() => { reload(); }, [reload]);

  const patch = useCallback(async (id: string, updates: Record<string, unknown>) => {
    await fetch(`/api/v2/bookmarks/${id}`, { method: 'PATCH', body: JSON.stringify(updates) });
    reload();
  }, [fetch, reload]);

  const remove = useCallback(async (id: string) => {
    await fetch(`/api/v2/bookmarks/${id}`, { method: 'DELETE' });
    reload();
  }, [fetch, reload]);

  return { data, loading, total, stats, reload, patch, remove };
}

// ── Competitor Watch hooks ────────────────────────────────────────────────────

export function useCompetitorWatch() {
  const fetch = useAuthFetch();
  const [data, setData] = useState<CompetitorWatch[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    setLoading(true);
    fetch('/api/v2/competitors?limit=50')
      .then((d: { items: CompetitorWatch[]; total: number }) => setData(d.items || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [fetch]);

  useEffect(() => { reload(); }, [reload]);

  const add = useCallback(async (nip: string, notes?: string) => {
    await fetch('/api/v2/competitors', { method: 'POST', body: JSON.stringify({ competitor_nip: nip, notes }) });
    reload();
  }, [fetch, reload]);

  const remove = useCallback(async (id: string) => {
    await fetch(`/api/v2/competitors/${id}`, { method: 'DELETE' });
    reload();
  }, [fetch, reload]);

  return { data, loading, reload, add, remove };
}

export function useCompetitorIntel(nip: string | null) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<CompetitorIntel | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!nip) return;
    let cancelled = false;
    setLoading(true);
    fetch(`/api/v2/competitors/intel/${nip}`)
      .then((d: { nip: string; profile: Record<string, unknown> | null; cpv_breakdown: unknown[]; region_breakdown: unknown[]; recent_wins: unknown[] }) => {
        if (!cancelled) {
          // Flatten: merge profile fields to top-level
          const flat: CompetitorIntel = {
            nip: d.nip,
            name: (d.profile?.name as string) ?? null,
            city: (d.profile?.city as string) ?? null,
            province: (d.profile?.province as string) ?? null,
            total_wins: (d.profile?.total_wins as number) ?? 0,
            total_value: (d.profile?.total_value as number) ?? 0,
            win_rate: (d.profile?.win_rate as number) ?? 0,
            top_cpv: (d.profile?.top_cpv as Record<string, number>) ?? null,
            cpv_breakdown: (d.cpv_breakdown || []) as CompetitorIntel['cpv_breakdown'],
            region_breakdown: (d.region_breakdown || []) as CompetitorIntel['region_breakdown'],
            recent_wins: (d.recent_wins || []) as CompetitorIntel['recent_wins'],
          };
          setData(flat);
        }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, nip]);

  return { data, loading };
}

export function useCompetitorSearch(q: string) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<Array<{ nip: string; name: string; city: string | null; wins: number }>>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!q || q.length < 2) { setData([]); return; }
    let cancelled = false;
    setLoading(true);
    fetch(`/api/v2/competitors/search?q=${encodeURIComponent(q)}&limit=10`)
      .then((d: { results: typeof data }) => { if (!cancelled) setData(d.results || []); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetch, q]);

  return { data, loading };
}

// ── Buyer CRM hooks ───────────────────────────────────────────────────────────

export function useBuyerCRM() {
  const fetch = useAuthFetch();
  const [data, setData] = useState<BuyerCRM[]>([]);
  const [loading, setLoading] = useState(true);
  const [followups, setFollowups] = useState<Followup[]>([]);

  const reload = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetch('/api/v2/buyer-crm?limit=50'),
      fetch('/api/v2/buyer-crm/followups?days=7'),
    ])
      .then(([items, fu]) => {
        setData(items.items || []);
        setFollowups(fu.today?.concat(fu.this_week || []) || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [fetch]);

  useEffect(() => { reload(); }, [reload]);

  const update = useCallback(async (id: string, body: Record<string, unknown>) => {
    await fetch(`/api/v2/buyer-crm/${id}`, { method: 'PUT', body: JSON.stringify(body) });
    reload();
  }, [fetch, reload]);

  const remove = useCallback(async (id: string) => {
    await fetch(`/api/v2/buyer-crm/${id}`, { method: 'DELETE' });
    reload();
  }, [fetch, reload]);

  return { data, loading, followups, reload, update, remove };
}

// ── Utils ─────────────────────────────────────────────────────────────────────

export function fmtMln(v: number | null | undefined, suffix = ' mln zł') {
  if (v == null) return '—';
  if (v >= 1000) return (v / 1000).toFixed(1) + ' mld zł';
  if (v >= 1) return v.toFixed(1) + suffix;
  return (v * 1000).toFixed(0) + ' tys. zł';
}

export function fmtPLN(v: number | null | undefined) {
  if (v == null) return '—';
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + ' M zł';
  if (v >= 1_000) return (v / 1_000).toFixed(0) + ' tys. zł';
  return v.toFixed(0) + ' zł';
}

export function fmtPct(v: number | null | undefined) {
  if (v == null) return '—';
  return (v >= 0 ? '+' : '') + v.toFixed(1) + '%';
}

export const PROVINCE_MAP: Record<string, string> = {
  PL02: 'dolnośląskie', PL04: 'kuj-pom', PL06: 'lubelskie',
  PL08: 'lubuskie', PL10: 'łódzkie', PL12: 'małopolskie',
  PL14: 'mazowieckie', PL16: 'opolskie', PL18: 'podkarpackie',
  PL20: 'podlaskie', PL22: 'pomorskie', PL24: 'śląskie',
  PL26: 'świętokrzyskie', PL28: 'warmińsko-maz', PL30: 'wlkp',
  PL32: 'zachodniopom',
};

export const CPV_LABELS: Record<string, string> = {
  '45': 'Roboty budowlane',
  '450': 'Og. budowlane',
  '452': 'Roboty inżynieryjne',
  '453': 'Inst. budowlane',
  '454': 'Wykończenie',
  '4523': 'Drogi i chodniki',
  '4500': 'Roboty og.',
  '4524': 'Kanalizacja/woda',
  '4521': 'Budownictwo og.',
};

// ─── Faza 5 Types ─────────────────────────────────────────

export interface BuyerCRMItem {
  id: string;
  buyer_nip: string;
  buyer_name?: string | null;
  crm_stage: 'prospect' | 'contacted' | 'demo' | 'active' | 'churned';
  priority: number;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  annual_budget_est: number | null;
  preferred_cpv: string[];
  territory: string | null;
  notes: string | null;
  last_contact: string | null;
  next_followup: string | null;
  city?: string | null;
  province?: string | null;
  total_tenders?: number | null;
  total_value?: number | null;
  created_at: string;
  updated_at: string;
}

export interface BuyerSearchResult {
  nip: string;
  name: string;
  city: string | null;
  province: string | null;
  total_tenders: number;
  total_value: number;
  top_cpv: { code: string; name: string; count: number }[];
}

export interface OrgInfo {
  id: string;
  name: string;
  nip: string | null;
  plan: 'free' | 'pro' | 'enterprise';
  settings: { default_cpv: string[]; default_regions: string[] };
  member_count: number;
  created_at: string;
}

export interface OrgMember {
  id: string;
  email: string;
  name: string | null;
  role: 'owner' | 'admin' | 'estimator';
  is_active: boolean;
  created_at: string;
  is_me: boolean;
}

export interface OrgInvite {
  id: string;
  email: string;
  role: string;
  invited_by: string | null;
  created_at: string;
  expires_at: string | null;
}

export interface Notification {
  id: string;
  type: 'alert_match' | 'competitor_win' | 'bookmark_deadline' | 'system';
  title: string;
  body: string;
  read: boolean;      // backend column is 'read', not 'is_read'
  is_read?: boolean;  // alias for compatibility
  link: string | null;
  created_at: string;
}

export function useBuyerCRMList(params?: { stage?: string; search?: string; limit?: number }) {
  const fetch = useAuthFetch();
  const [data, setData] = useState<BuyerCRMItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(() => {
    setLoading(true);
    const q = new URLSearchParams();
    if (params?.stage) q.set('stage', params.stage);
    if (params?.search) q.set('search', params.search);
    q.set('limit', String(params?.limit ?? 50));
    fetch(`/api/v2/buyer-crm?${q}`)
      .then((d: { items: BuyerCRMItem[]; total: number }) => { setData(d.items || []); setTotal(d.total || 0); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [fetch, params?.stage, params?.search, params?.limit]);
  useEffect(() => { reload(); }, [reload]);
  return { data, total, loading, reload };
}

export function useNotifications() {
  const fetch = useAuthFetch();
  const [data, setData] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(() => {
    Promise.all([
      fetch('/api/v2/notifications?limit=50'),
      fetch('/api/v2/notifications/count'),
    ]).then(([list, count]: [{ items: Notification[]; total: number }, { unread_count: number }]) => {
      setData(list.items || []); setUnread(count.unread_count || 0);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [fetch]);
  useEffect(() => { reload(); const t = setInterval(reload, 30000); return () => clearInterval(t); }, [reload]);
  const markRead = useCallback(async (id: string) => {
    await fetch(`/api/v2/notifications/${id}/read`, { method: 'POST' }); reload();
  }, [fetch, reload]);
  const markAllRead = useCallback(async () => {
    await fetch('/api/v2/notifications/read-all', { method: 'POST' }); reload();
  }, [fetch, reload]);
  return { data, unread, loading, reload, markRead, markAllRead };
}

export function useOrgSettings() {
  const fetch = useAuthFetch();
  const [org, setOrg] = useState<OrgInfo | null>(null);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [invites, setInvites] = useState<OrgInvite[]>([]);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(() => {
    Promise.all([
      fetch('/api/v2/organizations/me'),
      fetch('/api/v2/organizations/me/members'),
      fetch('/api/v2/organizations/me/invites'),
    ]).then(([o, m, i]: [OrgInfo, { items: OrgMember[] }, { items: OrgInvite[] }]) => {
      setOrg(o); setMembers(m.items || []); setInvites(i.items || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [fetch]);
  useEffect(() => { reload(); }, [reload]);
  const invite = useCallback(async (email: string, role: string) => {
    await fetch('/api/v2/organizations/me/invite', { method: 'POST', body: JSON.stringify({ email, role }) });
    reload();
  }, [fetch, reload]);
  const revokeInvite = useCallback(async (id: string) => {
    await fetch(`/api/v2/organizations/me/invites/${id}`, { method: 'DELETE' }); reload();
  }, [fetch, reload]);
  const removeMember = useCallback(async (id: string) => {
    await fetch(`/api/v2/organizations/me/members/${id}`, { method: 'DELETE' }); reload();
  }, [fetch, reload]);
  const updateMemberRole = useCallback(async (id: string, role: string) => {
    await fetch(`/api/v2/organizations/me/members/${id}`, { method: 'PATCH', body: JSON.stringify({ role }) }); reload();
  }, [fetch, reload]);
  const updateOrg = useCallback(async (data: Partial<OrgInfo>) => {
    await fetch('/api/v2/organizations/me', { method: 'PUT', body: JSON.stringify(data) }); reload();
  }, [fetch, reload]);
  return { org, members, invites, loading, reload, invite, revokeInvite, removeMember, updateMemberRole, updateOrg };
}

// ── Faza 6 types ────────────────────────────────────────────────────────────
export interface ZwiadTender {
  id: string;
  title: string;
  buyer: string;
  cpv: string[];
  voivodeship: string | null;
  value_pln: number | null;
  deadline_at: string | null;
  status: string;
  match_score: number | null;
  match_reason: string | null;
  source?: string | null;
  url?: string | null;
  published_at?: string | null;
}
export interface KosztorysItem {
  id: string;
  description: string;
  unit: string;
  quantity: number;
  unit_price: number;
  total_price?: number;
}
export interface EmployeeResource {
  id: string;
  name: string;
  phone: string | null;
  role: string | null;
  skills: string[];
}
export interface EquipmentResource {
  id: string;
  type: string;
  model: string;
  reg_no: string | null;
  active: boolean;
}

// ─── Scoring Config ──────────────────────────────────────────────────────────

export interface ScoringConfig {
  tenant_id: string;
  cpv_weight: number;
  value_weight: number;
  region_weight: number;
  deadline_weight: number;
  historical_win_weight: number;
  min_value_pln: number | null;
  max_value_pln: number | null;
  preferred_cpvs: string[];
  preferred_regions: string[];
  is_default: boolean;
}

export interface RescoreResult {
  total: number;
  processed: number;
  avg_score_before: number;
  avg_score_after: number;
  message: string;
}

export interface WinRateItem {
  cpv_prefix: string;
  wins: number;
  win_rate: number;
  top_contractors: string[];
}
