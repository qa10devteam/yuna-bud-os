"use client";

import { useState, useEffect } from "react";
import { useAuthFetch } from "@/lib/api-v2";

interface KPIMetric {
  id: string;
  label: string;
  value: string | number;
  change?: number;
  unit?: string;
}

interface KPIBarResponse {
  metrics: KPIMetric[];
}

export default function KPIBar() {
  const authFetch = useAuthFetch();
  const [metrics, setMetrics] = useState<KPIMetric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    const fetchKPIs = async () => {
      try {
        const data: KPIBarResponse = await authFetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v2/market/kpi-bar`
        );
        setMetrics(data.metrics || []);
      } catch (err) {
        console.error("Failed to fetch KPI bar:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchKPIs();
    interval = setInterval(fetchKPIs, 30000);
    return () => clearInterval(interval);
  }, [authFetch]);

  if (loading) {
    return (
      <div className="flex h-12 items-center gap-6 overflow-x-auto border-b border-white/10 bg-[#0A1628] px-6">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="h-3 w-16 animate-pulse rounded bg-white/10" />
            <div className="h-4 w-12 animate-pulse rounded bg-white/10" />
          </div>
        ))}
      </div>
    );
  }

  if (metrics.length === 0) {
    return (
      <div className="flex h-12 items-center border-b border-white/10 bg-[#0A1628] px-6">
        <span className="text-xs text-gray-500">No KPI data available</span>
      </div>
    );
  }

  return (
    <div className="flex h-12 items-center gap-6 overflow-x-auto border-b border-white/10 bg-[#0A1628] px-6">
      {metrics.map((metric) => (
        <div key={metric.id} className="flex shrink-0 items-center gap-2">
          <span className="text-xs text-gray-400">{metric.label}</span>
          <span className="text-sm font-semibold text-white">
            {metric.value}
            {metric.unit && <span className="ml-0.5 text-xs text-gray-400">{metric.unit}</span>}
          </span>
          {metric.change !== undefined && (
            <span
              className={`text-xs font-medium ${
                metric.change > 0 ? "text-emerald-400" : metric.change < 0 ? "text-red-400" : "text-gray-400"
              }`}
            >
              {metric.change > 0 ? "+" : ""}
              {metric.change}%
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
