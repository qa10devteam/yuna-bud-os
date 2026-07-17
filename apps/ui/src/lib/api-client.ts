/**
 * api-client.ts — Centralized fetch wrapper for Terra.OS
 *
 * Features:
 *  - Auth header injection (Bearer token from localStorage or Zustand store)
 *  - Request deduplication: parallel identical GET requests collapse to one in-flight fetch
 *  - Typed API errors (ApiError with status, detail, etc.)
 *  - Automatic JSON parsing + error extraction
 *  - Abort controller support
 *  - Interceptors:
 *      401 → clear localStorage auth tokens + redirect to /auth/login
 *      429 → show toast 'Za dużo żądań. Poczekaj chwilę.'
 *      500/503 → swallow error, return null gracefully
 */

// ── Typed errors ────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly raw: unknown;

  constructor(status: number, detail: string, raw?: unknown) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.raw = raw;
  }
}

export class NetworkError extends Error {
  constructor(cause?: unknown) {
    super(cause instanceof Error ? cause.message : 'Network request failed');
    this.name = 'NetworkError';
  }
}

// ── Request deduplication ────────────────────────────────────────────────────

// Map of in-flight GET requests: url → Promise<unknown>
const inflight = new Map<string, Promise<unknown>>();

// ── Response interceptors ────────────────────────────────────────────────────

/**
 * handle401 — clears stored auth tokens and redirects to the login page.
 * Safe to call on the server (window guard) — does nothing in SSR context.
 */
function handle401(): void {
  if (typeof window === 'undefined') return;
  // Clear all known auth storage keys
  localStorage.removeItem('auth_token');
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  // Avoid redirect loops if already on auth pages
  if (!window.location.pathname.startsWith('/auth')) {
    window.location.href = '/auth/login';
  }
}

/**
 * handle429 — shows a user-facing warning toast via the global Toast system.
 * Falls back to console.warn when the DOM is not available (SSR/tests).
 */
function handle429(): void {
  const message = 'Za dużo żądań. Poczekaj chwilę.';
  if (typeof window === 'undefined') {
    console.warn('[api-client] 429:', message);
    return;
  }
  // Dynamically import to avoid pulling React module into SSR bundle
  // showToast is a side-effect-only function exported from Toast.tsx
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { showToast } = require('@/components/Toast');
    showToast('warning', message);
  } catch {
    console.warn('[api-client] 429:', message);
  }
}

// ── Auth token helper ────────────────────────────────────────────────────────

/**
 * Retrieve the auth token. Tries Zustand store first (SSR-safe), falls back
 * to localStorage. Returns null if neither is available.
 */
function getAuthToken(): string | null {
  // Try Zustand store (if available in browser context)
  try {
    // Dynamic import to avoid circular deps — read state synchronously via getState()
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useStore } = require('@/store/useStore');
    const token = useStore.getState?.()?.accessToken;
    if (token) return token;
  } catch {
    // store not available (SSR or test env)
  }

  // Fallback: localStorage key used by the legacy auth flow
  if (typeof window !== 'undefined') {
    return localStorage.getItem('auth_token');
  }

  return null;
}

// ── Core request function ─────────────────────────────────────────────────────

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  /** Parsed JSON body — will be serialized to JSON and Content-Type set automatically */
  body?: unknown;
  /** If true, skip deduplication for this request (useful for mutations) */
  noDedup?: boolean;
  /** If provided, the request will be aborted when this signal fires */
  signal?: AbortSignal;
  /** Override base URL; defaults to process.env.NEXT_PUBLIC_API_URL or '' */
  baseUrl?: string;
}

export async function apiRequest<T = unknown>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    method = 'GET',
    body,
    noDedup = false,
    signal,
    baseUrl = '',
    headers: extraHeaders = {},
    ...restInit
  } = options;

  const url = `${baseUrl}${path}`;
  const isWrite = method !== 'GET' && method !== 'HEAD';

  // Build headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(extraHeaders as Record<string, string>),
  };

  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const init: RequestInit = {
    method,
    headers,
    signal,
    ...restInit,
  };

  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  const doFetch = async (): Promise<T> => {
    let response: Response;
    try {
      response = await fetch(url, init);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') throw err;
      throw new NetworkError(err);
    }

    if (!response.ok) {
      // ── Response interceptors ──────────────────────────────────────────────

      // 401 Unauthorized — expired or missing token → auto-logout
      if (response.status === 401) {
        handle401();
        // Still throw so callers can handle (e.g. clear local state)
        throw new ApiError(401, 'Nieautoryzowany. Zostałeś wylogowany.', null);
      }

      // 429 Too Many Requests — rate-limited → warn user via toast
      if (response.status === 429) {
        handle429();
        throw new ApiError(429, 'Za dużo żądań. Poczekaj chwilę.', null);
      }

      // 500/503 Server Error — backend down / transient — return null gracefully
      if (response.status === 500 || response.status === 503) {
        console.error(`[api-client] ${response.status} on ${url} — returning null`);
        return null as unknown as T;
      }

      // ── All other errors ───────────────────────────────────────────────────
      let raw: unknown;
      try {
        raw = await response.json();
      } catch {
        raw = null;
      }

      const rawDetail = (raw as Record<string, unknown>)?.detail;
      const detail: string = Array.isArray(rawDetail)
        ? rawDetail
            .map((d: { msg?: string; loc?: string[] }) =>
              [d.loc?.slice(-1)[0], d.msg].filter(Boolean).join(': '),
            )
            .join('; ')
        : typeof rawDetail === 'string'
          ? rawDetail
          : `HTTP ${response.status}`;

      throw new ApiError(response.status, detail, raw);
    }

    // 204 No Content
    if (response.status === 204) return undefined as unknown as T;

    return response.json() as Promise<T>;
  };

  // Deduplicate parallel GET requests to the same URL
  if (!isWrite && !noDedup && !signal) {
    const existing = inflight.get(url);
    if (existing) return existing as Promise<T>;

    const promise = doFetch().finally(() => inflight.delete(url));
    inflight.set(url, promise);
    return promise;
  }

  return doFetch();
}

// ── Convenience helpers ──────────────────────────────────────────────────────

export const apiGet = <T = unknown>(path: string, opts?: Omit<ApiRequestOptions, 'method'>) =>
  apiRequest<T>(path, { ...opts, method: 'GET' });

export const apiPost = <T = unknown>(
  path: string,
  body?: unknown,
  opts?: Omit<ApiRequestOptions, 'method' | 'body'>,
) => apiRequest<T>(path, { ...opts, method: 'POST', body, noDedup: true });

export const apiPut = <T = unknown>(
  path: string,
  body?: unknown,
  opts?: Omit<ApiRequestOptions, 'method' | 'body'>,
) => apiRequest<T>(path, { ...opts, method: 'PUT', body, noDedup: true });

export const apiPatch = <T = unknown>(
  path: string,
  body?: unknown,
  opts?: Omit<ApiRequestOptions, 'method' | 'body'>,
) => apiRequest<T>(path, { ...opts, method: 'PATCH', body, noDedup: true });

export const apiDelete = <T = unknown>(path: string, opts?: Omit<ApiRequestOptions, 'method'>) =>
  apiRequest<T>(path, { ...opts, method: 'DELETE', noDedup: true });

// ── React hook wrapper ────────────────────────────────────────────────────────

/**
 * useApiClient — returns stable apiRequest bound to current auth token.
 * Refreshes token on each call (token is read lazily inside apiRequest),
 * so no stale-closure problems.
 *
 * Usage:
 *   const api = useApiClient();
 *   const data = await api.get<MyType>('/api/v2/...');
 */
export function useApiClient() {
  return {
    get: apiGet,
    post: apiPost,
    put: apiPut,
    patch: apiPatch,
    delete: apiDelete,
    request: apiRequest,
  };
}
