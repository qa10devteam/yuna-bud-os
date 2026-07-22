// ── BudOS — Core domain types ─────────────────────────────────────────────────
// Single source of truth for tender-related domain models.
// Used by api.ts, store, and all UI components.

// ── Tender ────────────────────────────────────────────────────────────────────

export type TenderStatus = 'go' | 'warn' | 'nogo';

export interface Tender {
  id: string;
  /** External ID from BZP / TED */
  externalId?: string;
  /** Source portal */
  source?: 'BZP' | 'TED' | 'BIP' | string;
  title: string;
  /** Contracting authority name */
  buyer: string | null;
  /** CPV codes list */
  cpv: string[];
  voivodeship: string | null;
  /** Publication date (ISO 8601) */
  publishDate?: string;
  /** Offer submission deadline (ISO 8601) */
  deadline: string | null;
  /** Alias: deadline_at from API v2 */
  deadline_at?: string | null;
  /** Estimated contract value in PLN */
  value_pln: number | null;
  /** Alias: estimatedValue from legacy types */
  estimatedValue?: number;
  /** AI match score 0–100 */
  match_score: number;
  /** Short explanation of the match score */
  match_reason: string | null;
  /** Pipeline status: new → analyzing → ready → accepted/rejected/archived */
  status: 'new' | 'analyzing' | 'ready' | 'accepted' | 'rejected' | 'archived';
  /** GO/WARN/NO-GO decision */
  decision?: TenderStatus | null;
}

// ── Analysis ──────────────────────────────────────────────────────────────────

export interface RedFlag {
  id: string;
  type: 'price' | 'quantity' | 'technical' | 'legal' | 'timeline';
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  sourcePage?: number;
  potentialCost?: number;
  recommendedAction?: string;
}

export interface Analysis {
  id: string;
  tenderId: string;
  /** GO/WARN/NO-GO recommendation */
  decision: TenderStatus;
  /** 0–100 overall score */
  score: number;
  /** One-paragraph executive summary */
  summary: string;
  /** Identified risks / red flags */
  redFlags: RedFlag[];
  /** Formal participation conditions met/unmet */
  conditions: {
    label: string;
    met: boolean;
  }[];
  /** ISO timestamp */
  createdAt: string;
  /** Processing status */
  status: 'pending' | 'processing' | 'ready' | 'error';
  /** Error message if status === 'error' */
  errorMessage?: string | null;
}

// ── Cost Estimate ─────────────────────────────────────────────────────────────

export interface CostEstimateLine {
  id: string;
  /** KNR/KSNR catalog reference, e.g. "KNR 2-01 0101-01" */
  catalogRef?: string | null;
  description: string;
  unit: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  /** Confidence 0–1 from LLM */
  confidence?: number;
}

export interface CostEstimateTotals {
  net: number;
  overhead: number;
  profit: number;
  vat: number;
  gross: number;
}

export interface CostEstimate {
  id: string;
  tenderId: string;
  /** A = conservative, B = aggressive */
  variant: 'A' | 'B';
  version: number;
  lines: CostEstimateLine[];
  totals: CostEstimateTotals;
  /** ISO timestamp */
  createdAt: string;
  updatedAt: string;
  status: 'pending' | 'processing' | 'ready' | 'error';
}

// ── User ──────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name: string;
  /** Organisation / company ID */
  org_id: string | null;
  role: 'admin' | 'manager' | 'estimator' | 'viewer';
}
