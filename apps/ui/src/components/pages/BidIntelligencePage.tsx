"use client";

import { useState, useEffect } from "react";
import { useAuthFetch } from "@/lib/api-v2";
import { PageShell } from "@/components/PageShell";
import { GlassCard } from "@/components/ui/GlassCard";
import { TrendingUp, Target, BarChart2, FileText } from "lucide-react";

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

const STATUS_META: Record<string, string> = {
  won:     "text-success bg-success/10",
  lost:    "text-danger bg-danger/10",
  pending: "text-warning bg-warning/10",
};

export default function BidIntelligencePage() {
  const authFetch = useAuthFetch();
  const [bids, setBids]     = useState<BidRecord[]>([]);
  const [stats, setStats]   = useState<BidStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [bidsData, statsData] = await Promise.all([
          authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/bid-intelligence/history`),
          authFetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v2/bid-intelligence/stats`),
        ]);
        setBids(bidsData.bids || []);
        setStats(statsData);
      } catch (err) {
        console.error("Failed to fetch bid intelligence:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [authFetch]);

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
              <div key={i} className="h-24 rounded-token-lg bg-earth-900/50 animate-shimmer" />
            ))}
          </div>
          <div className="h-80 rounded-token-lg bg-earth-900/50 animate-shimmer" />
        </div>
      )}

      {/* Stats Cards */}
      {!loading && stats && (
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Łącznie ofert',     value: String(stats.total_bids),     icon: FileText,  color: 'text-earth-100' },
            { label: 'Win Rate',           value: `${stats.win_rate}%`,          icon: TrendingUp, color: 'text-success' },
            { label: 'Optymalny markup',   value: `${stats.optimal_markup}%`,    icon: Target,    color: 'text-info' },
            { label: 'Średni markup',      value: `${stats.avg_markup}%`,        icon: BarChart2, color: 'text-earth-100' },
          ].map(s => (
            <div key={s.label} className="card rounded-token-lg p-5 shadow-token-sm">
              <div className="flex items-center gap-2 text-earth-500 text-xs mb-2">
                <s.icon size={14} /> {s.label}
              </div>
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Bid History Table */}
      {!loading && (
        <div className="card rounded-token-lg overflow-hidden shadow-token-sm">
          <div className="border-b border-earth-800/60 px-6 py-4">
            <h2 className="text-base font-semibold text-earth-100">Historia ofert</h2>
          </div>
          {bids.length === 0 ? (
            <GlassCard className="flex flex-col items-center justify-center py-16">
              <FileText size={48} className="text-earth-600 mb-3" />
              <p className="text-sm text-earth-400">Brak historii ofert</p>
              <p className="text-xs text-earth-500">Złóż oferty na przetargi, aby zobaczyć analitykę</p>
            </GlassCard>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-earth-800/60 text-left text-xs text-earth-500">
                    <th className="px-6 py-3 font-medium">Przetarg</th>
                    <th className="px-6 py-3 font-medium">Data</th>
                    <th className="px-6 py-3 font-medium">Markup</th>
                    <th className="px-6 py-3 font-medium">Kwota</th>
                    <th className="px-6 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {bids.map((bid) => (
                    <tr key={bid.id} className="border-b border-earth-900 last:border-0 hover:bg-earth-900/40 transition-colors">
                      <td className="px-6 py-3 text-earth-200">{bid.tender_title}</td>
                      <td className="px-6 py-3 text-earth-400">
                        {new Date(bid.submitted_at).toLocaleDateString('pl-PL')}
                      </td>
                      <td className="px-6 py-3 text-earth-200 font-mono">{bid.markup_pct}%</td>
                      <td className="px-6 py-3 text-earth-200 font-mono">
                        {bid.bid_amount.toLocaleString('pl-PL')} PLN
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
