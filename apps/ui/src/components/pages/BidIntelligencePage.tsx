"use client";

import { useCallback, useState, useEffect } from "react";
import { useStore } from "@/store/useStore";
import { PageShell } from "@/components/PageShell";
import { GlassCard } from "@/components/ui/GlassCard";
import { TrendingUp, Target, BarChart2, FileText } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface BidRecord {
  id: string;
  tender_title: string;
  submitted_at: string;
  markup_pct: number;
  bid_amount: number;
  status: "won" | "lost" | "pending";
}

interface BidStats {
  total_bids: number;
  win_rate: number;
  avg_markup: number;
  optimal_markup: number;
  total_revenue: number;
}

// Analytics dashboard response shape from /api/v2/analytics/dashboard
interface AnalyticsDashboardResponse {
  pipeline_value: number;
  active_bids: number;
  win_rate: number;       // 0..1
  win_rate_pct: number;   // 0..100
  total_won: number;
  total_lost: number;
  avg_margin: number | null;
}

// Offers response (fallback: tenders)
interface OfferRecord {
  id: string;
  tender_title?: string;
  title?: string;
  submitted_at?: string;
  created_at?: string;
  markup_pct?: number;
  bid_amount?: number;
  amount?: number;
  status?: string;
}

interface ListResponse {
  items: OfferRecord[];
  total: number;
}

// ── Status helpers ──────────────────────────────────────────────────────────────

const STATUS_META: Record<string, string> = {
  won:     "text-success bg-success/10",
  lost:    "text-danger bg-danger/10",
  pending: "text-warning bg-warning/10",
};

function normaliseStatus(s: string | undefined): "won" | "lost" | "pending" {
  if (!s) return "pending";
  const lower = s.toLowerCase();
  if (lower === "won" || lower === "decided_go") return "won";
  if (lower === "lost" || lower === "decided_nogo" || lower === "archived") return "lost";
  return "pending";
}

function normaliseBid(r: OfferRecord): BidRecord {
  return {
    id:           r.id,
    tender_title: r.tender_title ?? r.title ?? "—",
    submitted_at: r.submitted_at ?? r.created_at ?? new Date().toISOString(),
    markup_pct:   r.markup_pct ?? 0,
    bid_amount:   r.bid_amount ?? r.amount ?? 0,
    status:       normaliseStatus(r.status),
  };
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function BidIntelligencePage() {
  const accessToken = useStore((s) => s.accessToken);
  const [bids,    setBids]    = useState<BidRecord[]>([]);
  const [stats,   setStats]   = useState<BidStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Silent GET — no toast on non-OK, returns null on error
  const silentGet = useCallback(
    async <T,>(url: string): Promise<T | null> => {
      try {
        const res = await fetch(url, {
          headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        });
        if (!res.ok) return null;
        return (await res.json()) as T;
      } catch {
        return null;
      }
    },
    [accessToken],
  );

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      // ── 1. Fetch analytics/dashboard for stats ─────────────────────────────
      let statsResult: BidStats | null = null;
      const d = await silentGet<AnalyticsDashboardResponse>('/api/v2/analytics/dashboard');
      if (d) {
        statsResult = {
          total_bids:     (d.total_won ?? 0) + (d.total_lost ?? 0) + (d.active_bids ?? 0),
          win_rate:       d.win_rate_pct ?? 0,
          avg_markup:     d.avg_margin ?? 0,
          optimal_markup: 0,
          total_revenue:  d.pipeline_value ?? 0,
        };
      }

      // ── 2. Fetch bid/offer history ─────────────────────────────────────────
      let bidsResult: BidRecord[] = [];
      // Try /api/v2/offers first; 404 → silentGet returns null
      const offersResp = await silentGet<ListResponse>('/api/v2/offers?limit=20');
      if (offersResp) {
        bidsResult = (offersResp.items ?? []).map(normaliseBid);
      } else {
        // Fallback to tenders with decided/terminal statuses
        const tendersResp = await silentGet<ListResponse>('/api/v2/tenders?limit=20&sort=created_at');
        if (tendersResp) {
          bidsResult = (tendersResp.items ?? [])
            .filter((r) => r.status && ['decided_go','decided_nogo','archived','won','lost'].includes(r.status))
            .map(normaliseBid);
        }
      }

      if (!cancelled) {
        setStats(statsResult);
        setBids(bidsResult);
        setLoading(false);
      }
    }

    fetchAll();
    return () => { cancelled = true; };
  }, [silentGet]);

  return (
    <PageShell
      title="Bid Intelligence"
      subtitle="Analiza historii ofertowania"
    >
      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-ink-900/50 animate-shimmer" />
            ))}
          </div>
          <div className="h-80 rounded-xl bg-ink-900/50 animate-shimmer" />
        </div>
      )}

      {/* Stats Cards */}
      {!loading && stats && (
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Łącznie ofert',     value: String(stats.total_bids),                   icon: FileText,   color: 'text-slate-100' },
            { label: 'Win Rate',           value: `${stats.win_rate.toFixed(1)}%`,             icon: TrendingUp, color: 'text-success'   },
            { label: 'Optymalny markup',   value: stats.optimal_markup ? `${stats.optimal_markup}%` : '—', icon: Target, color: 'text-info' },
            { label: 'Średni markup',      value: stats.avg_markup ? `${stats.avg_markup.toFixed(1)}%` : '—', icon: BarChart2, color: 'text-slate-100' },
          ].map(s => (
            <div key={s.label} className="card rounded-xl p-5 shadow-md-sm">
              <div className="flex items-center gap-2 text-slate-500 text-xs mb-2">
                <s.icon size={14} /> {s.label}
              </div>
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Bid History Table */}
      {!loading && (
        <div className="card rounded-xl overflow-hidden shadow-md-sm">
          <div className="border-b border-ink-800/60 px-6 py-4">
            <h2 className="text-base font-semibold text-slate-100">Historia ofert</h2>
          </div>
          {bids.length === 0 ? (
            <GlassCard className="flex flex-col items-center justify-center py-16">
              <FileText size={48} className="text-slate-600 mb-3" />
              <p className="text-sm text-slate-400">Brak historii ofert</p>
              <p className="text-xs text-slate-500">Złóż oferty na przetargi, aby zobaczyć analitykę</p>
            </GlassCard>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-ink-800/60 text-left text-xs text-slate-500">
                    <th className="px-6 py-3 font-medium">Przetarg</th>
                    <th className="px-6 py-3 font-medium">Data</th>
                    <th className="px-6 py-3 font-medium">Markup</th>
                    <th className="px-6 py-3 font-medium">Kwota</th>
                    <th className="px-6 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {bids.map((bid) => (
                    <tr key={bid.id} className="border-b border-ink-900 last:border-0 hover:bg-ink-900/40 transition-colors">
                      <td className="px-6 py-3 text-slate-200">{bid.tender_title}</td>
                      <td className="px-6 py-3 text-slate-400">
                        {new Date(bid.submitted_at).toLocaleDateString('pl-PL')}
                      </td>
                      <td className="px-6 py-3 text-slate-200 font-mono">{bid.markup_pct}%</td>
                      <td className="px-6 py-3 text-slate-200 font-mono">
                        {(bid.bid_amount ?? 0).toLocaleString('pl-PL')} PLN
                      </td>
                      <td className="px-6 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_META[bid.status] ?? ''}`}>
                          {bid.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </PageShell>
  );
}
