"use client";

import { useState, useEffect } from "react";
import { useAuthFetch } from "@/lib/api-v2";

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

export default function BidIntelligencePage() {
  const authFetch = useAuthFetch();
  const [bids, setBids] = useState<BidRecord[]>([]);
  const [stats, setStats] = useState<BidStats | null>(null);
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

  const statusColor = (status: string) => {
    switch (status) {
      case "won": return "text-emerald-400 bg-emerald-400/10";
      case "lost": return "text-red-400 bg-red-400/10";
      default: return "text-yellow-400 bg-yellow-400/10";
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A1628] p-6">
        <div className="mb-8">
          <div className="h-8 w-48 animate-pulse rounded bg-white/10" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-[#1E293B]" />
          ))}
        </div>
        <div className="mt-6 h-96 animate-pulse rounded-xl bg-[#1E293B]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A1628] p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Bid Intelligence</h1>
        <p className="mt-1 text-sm text-gray-400">Analyze bid performance and optimize markup strategy</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-white/5 bg-[#1E293B] p-5">
            <p className="text-xs text-gray-400">Total Bids</p>
            <p className="mt-1 text-2xl font-bold text-white">{stats.total_bids}</p>
          </div>
          <div className="rounded-xl border border-white/5 bg-[#1E293B] p-5">
            <p className="text-xs text-gray-400">Win Rate</p>
            <p className="mt-1 text-2xl font-bold text-emerald-400">{stats.win_rate}%</p>
          </div>
          <div className="rounded-xl border border-white/5 bg-[#1E293B] p-5">
            <p className="text-xs text-gray-400">Optimal Markup</p>
            <p className="mt-1 text-2xl font-bold text-[#3B82F6]">{stats.optimal_markup}%</p>
          </div>
          <div className="rounded-xl border border-white/5 bg-[#1E293B] p-5">
            <p className="text-xs text-gray-400">Avg Markup</p>
            <p className="mt-1 text-2xl font-bold text-white">{stats.avg_markup}%</p>
          </div>
        </div>
      )}

      {/* Bid History Table */}
      <div className="rounded-xl border border-white/5 bg-[#1E293B]">
        <div className="border-b border-white/5 px-6 py-4">
          <h2 className="text-lg font-semibold text-white">Bid History</h2>
        </div>
        {bids.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <svg className="h-12 w-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="mt-3 text-sm text-gray-400">No bid history yet</p>
            <p className="text-xs text-gray-500">Submit bids on tenders to see analytics here</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/5 text-left text-xs text-gray-400">
                  <th className="px-6 py-3 font-medium">Tender</th>
                  <th className="px-6 py-3 font-medium">Date</th>
                  <th className="px-6 py-3 font-medium">Markup</th>
                  <th className="px-6 py-3 font-medium">Amount</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {bids.map((bid) => (
                  <tr key={bid.id} className="border-b border-white/5 last:border-0">
                    <td className="px-6 py-3 text-sm text-white">{bid.tender_title}</td>
                    <td className="px-6 py-3 text-sm text-gray-400">
                      {new Date(bid.submitted_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-3 text-sm text-white">{bid.markup_pct}%</td>
                    <td className="px-6 py-3 text-sm text-white">
                      R{bid.bid_amount.toLocaleString()}
                    </td>
                    <td className="px-6 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${statusColor(bid.status)}`}>
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
    </div>
  );
}
