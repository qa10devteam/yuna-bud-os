// ── BudOS — API client ────────────────────────────────────────────────────────
// Plain fetch functions (no hooks) — safe to call in server components,
// event handlers, and zustand actions.
//
// Auth token source: Zustand store 'terra-auth' persisted to localStorage.
// The persisted format is: { state: { accessToken: '...' }, version: N }
// We read it directly so this module has zero React dependencies.

import type { Tender, Analysis, CostEstimate } from '@/types/tender';

// ── Base URL ──────────────────────────────────────────────────────────────────

const BASE =
  typeof process !== 'undefined'
    ? (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
    : 'http://localhost:8000';

// ── Token helper ──────────────────────────────────────────────────────────────
// Reads from localStorage key 'terra-auth'.
// Zustand persist format: { "state": { "accessToken": "..." }, "version": 0 }

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem('terra-auth');
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { state?: { accessToken?: string | null } };
    return parsed?.state?.accessToken ?? null;
  } catch {
    return null;
  }
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

export interface FetchOptions extends Omit<RequestInit, 'headers'> {
  headers?: Record<string, string>;
  /** Explicitly pass a token (e.g. from a hook context). Falls back to localStorage. */
  token?: string | null;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  opts: FetchOptions = {},
): Promise<T> {
  const { token: explicitToken, headers: extraHeaders, ...rest } = opts;
  const token = explicitToken !== undefined ? explicitToken : getToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extraHeaders,
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, { ...rest, headers });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string; message?: string };
      msg = body.detail ?? body.message ?? msg;
    } catch {
      // ignore parse errors — keep the HTTP status message
    }
    throw new ApiError(res.status, msg);
  }

  // Handle empty responses (204 No Content)
  if (res.status === 204) return undefined as unknown as T;

  return res.json() as Promise<T>;
}

// ── Query param helpers ───────────────────────────────────────────────────────

export interface TenderParams {
  limit?: number;
  offset?: number;
  status?: string;
  score_min?: number;
  sort?: string;
  q?: string;
}

// ── Tender endpoints ──────────────────────────────────────────────────────────

export interface TendersResponse {
  items: Tender[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * GET /api/v2/tenders — paginated tender list with optional filters.
 */
export function getTenders(params?: TenderParams): Promise<TendersResponse> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v != null)
      .map(([k, v]) => [k, String(v)]),
  ).toString() : '';
  return apiFetch<TendersResponse>(`/api/v2/tenders${qs}`);
}

/**
 * GET /api/v2/tenders/:id — single tender detail.
 */
export function getTender(id: string): Promise<Tender> {
  return apiFetch<Tender>(`/api/v2/tenders/${id}`);
}

// ── Analysis endpoints ────────────────────────────────────────────────────────

/**
 * GET /api/v2/analysis/:tenderId — GO/NO-GO analysis for a tender.
 */
export function getAnalysis(tenderId: string): Promise<Analysis> {
  return apiFetch<Analysis>(`/api/v2/analysis/${tenderId}`);
}

/**
 * POST /api/v2/tenders/:tenderId/analyze — trigger analysis for a tender.
 */
export function triggerAnalysis(tenderId: string): Promise<{ job_id: string }> {
  return apiFetch<{ job_id: string }>(`/api/v2/tenders/${tenderId}/analyze`, {
    method: 'POST',
  });
}

// ── Cost Estimate endpoints ───────────────────────────────────────────────────

export interface CostEstimatesResponse {
  items: CostEstimate[];
  total: number;
}

/**
 * GET /api/v2/cost-estimates — list all cost estimates.
 */
export function getCostEstimates(tenderId?: string): Promise<CostEstimatesResponse> {
  const qs = tenderId ? `?tender_id=${tenderId}` : '';
  return apiFetch<CostEstimatesResponse>(`/api/v2/cost-estimates${qs}`);
}

/**
 * GET /api/v2/cost-estimates/:id — single cost estimate detail.
 */
export function getCostEstimate(id: string): Promise<CostEstimate> {
  return apiFetch<CostEstimate>(`/api/v2/cost-estimates/${id}`);
}

/**
 * POST /api/v2/cost-estimates — trigger cost estimate generation.
 */
export function createCostEstimate(
  tenderId: string,
  variant: 'A' | 'B' = 'A',
): Promise<CostEstimate> {
  return apiFetch<CostEstimate>('/api/v2/cost-estimates', {
    method: 'POST',
    body: JSON.stringify({ tender_id: tenderId, variant }),
  });
}

// ── Re-export types for convenience ──────────────────────────────────────────
export type { Tender, Analysis, CostEstimate };
